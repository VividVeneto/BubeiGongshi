### CORE-40 识别流程编排、手写画布与图片预处理界面

**目标**：在 Dart 侧编排一次识别会话的完整流程（输入 → 裁剪增强 → 选后端 → 本地或云端识别 → 候选），并提供手写画布、图片裁剪增强页与手写作答输入。

**范围**
- 包含：RecognitionFlow、图片裁剪增强页面、作答输入适配与识别安装点。
- 不包含：墨迹控制器与画布，迁至 CORE-64；结果/历史页面由 CORE-50（下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-29、CORE-30、CORE-31、CORE-32、CORE-34、CORE-35、CORE-37、CORE-39、CORE-55、CORE-64、CORE-58、CORE-59、CORE-95、CORE-87、CORE-65、CORE-36

**接口契约**

```dart
// app/lib/recognition/flow/recognition_flow.dart（流程控制器；页面在 app/lib/ui/recognition/，只收 flow 与回调）
enum RecognitionModeDto { lookup, answer }
enum InputSourceDto { ink, camera, gallery, file, clipboard, dragDrop }

sealed class RecognitionStep {}
final class Idle extends RecognitionStep {}
final class Cropping extends RecognitionStep {            // 图片输入；previewPath 为 img.prepare 输出（暂存区）
  final String sessionId; final ImageInfoDto info; final CropDto crop; final EnhanceOptionsDto options;
  final String? previewPath; final QualityReportDto? quality; final int queueIndex, queueLength; }
final class ChoosingBackend extends RecognitionStep { final String sessionId; final List<BackendCapsDto> backends; }
final class CloudConsentNeeded extends RecognitionStep { final String sessionId; final ProviderPolicy policy; }
final class CloudPreviewing extends RecognitionStep { final UploadPreview preview; }
final class Running extends RecognitionStep { final String sessionId; final String backendId; final bool networked; }
final class CandidatesReady extends RecognitionStep { final String sessionId; final List<CandidateDto> candidates; }
final class FlowFailed extends RecognitionStep { final String sessionId; final String errorCode; final bool canRetry; }
final class FlowCancelled extends RecognitionStep { final String? sessionId; }

final class RecognitionFlow extends ChangeNotifier {
  RecognitionFlow({required ProfileSessionSource sessions, required PlatformPorts ports, required RecognitionModeDto mode,
                   required String notationProfileId, List<SymbolDeclDto> userDecls = const [],
                   CloudRecognitionService? cloud});
  // notationProfileId/userDecls 原样填入 recog.postprocess、recog.correct、recog.final_check 的请求体（CORE-31）：
  // lookup 模式由调用页传当前记号方案（未选择时为 'cn-default'），answer 模式传所答题目期望修订（CORE-05 FormulaRevision）的 notation_profile_id，userDecls 为空
  RecognitionStep get step;
  Future<bool> needsKeepLastWarning(int imageCount);       // recog.settings.get：0 < keep_last < imageCount 时为 true
  Future<void> startInk(InkStrokesDto ink);                // session.start{ink} → 写墨迹文件 → transition Preview{Ink} → ChoosingBackend
  Future<void> startImages(List<ImportedImage> images, InputSourceDto source);   // 1–10 张；逐张：写暂存区 → img.probe → session.start → Cropping
  Future<void> updateCrop(CropDto crop, EnhanceOptionsDto options);   // img.prepare（长任务，可取消，最新者生效）
  Future<void> confirmInput();                             // transition Preview{Confirmed[, Original], quality} → ChoosingBackend
  Future<void> run(String backendId);                      // 本地：transition Running → recog.run → recog.postprocess → Succeeded{candidates}
                                                           // 远程：fetchPolicy；无 consentId → CloudConsentNeeded，否则 preparePreview → CloudPreviewing
  Future<void> grantCloudConsent(FeatureConsentInput input);   // CloudConsentNeeded → CloudPreviewing
  Future<void> confirmUpload();                            // confirmUpload → submit → watch；CloudSucceeded → recog.postprocess → CandidatesReady
  Future<void> backToCrop();                               // CloudPreviewing → Cropping（原预览作废）
  Future<void> stopAndDrain(ProfileSession session); // beforeClose：只对捕获的旧会话执行取消与清理并等待完成
  Future<void> cancel();                                   // 取消当前长任务或云任务，会话转 Cancelled
  Future<void> retry();                                    // FlowFailed 且 canRetry：复用原会话重新 run
  Future<bool> next();                                     // 队列中还有图片时处理下一张，返回是否还有
}

// app/lib/ui/recognition/crop/crop_enhance_page.dart
class CropEnhancePage extends StatelessWidget { const CropEnhancePage({super.key, required this.flow}); final RecognitionFlow flow; }
// app/lib/recognition/answer_input.dart（特性目录；交给学习页的只是 AnswerInputFactory）
final class HandwritingAnswerInput implements AnswerInputFactory { const HandwritingAnswerInput(this.deps); final AppDeps deps; }
// app/lib/recognition/install.dart
void installRecognition(CompositionContext ctx);
```

- Dart wire DTO（统一由CORE-67生成到`app/lib/binding/dto/`；特性dto.dart只允许re-export或页面状态）：`InkStrokesDto`、`ImageInfoDto`、`CropDto`、`EnhanceOptionsDto`、`QualityReportDto`、`BackendCapsDto`、`CandidateDto`（含 `SymbolSpanDto`）、`SessionSummaryDto`、`SessionStateDto`。
- 调用的 op：`recog.session.start / transition / get`、`recog.settings.get`、`recog.recover`（CORE-32）；`img.probe / prepare`（CORE-30）；`recog.backends / run`（CORE-29）；`recog.postprocess`（CORE-31）；`recog.local.register / unload_all`（CORE-35）；云端经 CORE-34 `CloudRecognitionService`。
- 错误码与界面行为（本卡不新增错误码）：

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `IMG_*`（CORE-30 解码与尺寸错误） | CORE-30 | 跳过该图并在队列末尾汇总；已创建会话才转Cancelled，probe在创建前失败不生成/转换会话；全部图片probe失败时删除本批暂存并回到导入入口，不产生空历史记录 |
| `RECOG_MODEL_NOT_INSTALLED` | CORE-35 | 显示“手工输入”与“选择其他本地模型”，不出现自动改用云端 |
| `RECOG_BACKEND_UNAVAILABLE` | CORE-29 | 显示“手工输入”与“选择其他本地模型”，不出现自动改用云端 |
| `RECOG_MODEL_TIMEOUT` / `RECOG_MODEL_OOM` | CORE-35 | `FlowFailed(canRetry: true)` |
| `CLOUD_*` | CORE-33（服务端返回，经 CORE-34 透传）；`CLOUD_TOKEN_EXPIRED`、`CLOUD_PREVIEW_STALE` 为 CORE-34 | `CloudUnknown`、`CloudExpiredUnknown` 显示“结果未知，可能已计费”，不自动重提 |

- Dart RecognitionModeDto 只是 CORE-29 RecognitionMode 的客户端映射；lookup/answer 逐字一致，不能扩展服务端未知的枚举值。

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/recognition/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/recognition/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `RECOG_ACTIVE_TASK_EXISTS` | CORE-32 | 提示“已有识别在进行”，提供“查看”与“取消它” |
| `RECOG_NO_CANDIDATE` | CORE-29 | 提示重写或调整裁剪 |

产品约束追踪：见README §6 Q4、Q38；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 手写画布放在 `FmlInputArea` 中，撤销、清空与“识别”放在 `ActionBar`；墨迹颜色取 `FmlColors.onSurface`，深色主题下同样可读；`stylus` 下手写区内不触发滚动；识别等待超过 1 s 显示进度并提供取消（CORE-55 P4）。
- 每次 startInk/startImages 捕获 sessions.current，读取该 session 的 account.state，游客策略不得来自构造时冻结的 account 参数；无 current 不调用任何 profile op。全批图片使用同一 session.core，不能在 next/retry 时换到新库。所有 awaited probe/prepare/推理/云/密钥结果发布或持久化前再次核对 identity/handle；过期结果只清理，不转入新会话。
- routes/AnswerInputFactory 用 deps.sessions 构造 flow；changes(null) 立即使公开方法不可启动并抹去候选/预览，下一 session 重建 flow；每个 flow 以唯一 id 登记 addBeforeClose，stopAndDrain 先取消长任务和 watch/HTTP，再等待任务、用旧 core 完成必要 Cancelled/暂存清理，最后释放订阅和回调，成功才注销。云任务取消使用 CORE-34 的旧任务控制路径，不再次上传/转投；失败向 close 传播，不能无等待 dispose 后释放句柄。无 scope 的 img/推理调用也绑定本次 Dart 世代以免迟到结果污染界面。
- 一个 `RecognitionFlow` 同时只推进一个会话；多图逐张处理，每张一个会话（CORE-32 计数口径）；空导入与进入 `Cropping` 前取消不调用 `recog.session.start`。
- `ImportedImage` 字节写入 `StoreArea.staging` 后立即交 `img.probe`（暂存文件的扩展名须与实际格式一致，或统一用 `.bin`；扩展名比较由 CORE-30 适配层完成，CORE-40 不自行判断；`img.prepare` 被新的 `updateCrop` 取消时返回的 `IMG_CANCELLED` 视为正常，不弹错误）；HEIC 已由平台卡转为 JPEG（CORE-04），若仍收到未知格式按 `IMG_*` 处理；暂存文件在会话转换写入资产后删除，页面销毁时删除剩余暂存文件。
- 增强选项或裁剪变化后旧 `previewPath` 作废；在 `CloudPreviewing` 返回裁剪必须重新 `preparePreview` 与确认（同一哈希原则见 CORE-34）。
- 后端列表：游客只列 `networked = false`；作答模式只列 `faithful_transcription = true`；`cloud` 为 null 时不出现任何云端项。本地失败不得自动切换后端。
- 墨迹采样、擦除、增量绘制及延迟唯一归CORE-64；本卡只接收其 `InkController.strokes`（`InkStrokesDto`）快照并驱动识别，不重复实现。
- 手写作答：`HandwritingAnswerInput` 以 `RecognitionModeDto.answer`、`notationProfileId = 期望修订的 notation_profile_id` 运行流程；展示 Top-1 转写到 CORE-87 编辑器（LaTeX 模式，控制器契约 CORE-59）供用户修改，点“确认作答”后才调用 `AnswerSink`（`answer_mode = handwriting`、`Graded(Latex)`）；不显示识别置信度。
- 安装点：`installRecognition(ctx)` 以 ctx.features.require<ProfileSessionSource>() 与 ctx.ports.keys 构造 CORE-32 `HistoryKeyUnlocker` 并登记到 `ctx.features`；`RecognitionFlow` 在档案解锁后首次调用 `recog.session.*` 前 `ensure()`，返回 true 时提示一次“本机密钥失效，识别历史已清空”；以进程 startup order 40 登记“本地模型注册”（CORE-95 `pack.list` 中 `model-` 开头的包逐个 `recog.local.register`，失败只记录）；从 ctx.features 取 CORE-36 ProfileHooks，以档案 order 50 登记先 await keys.ensure() 再用传入 session.core 调 `recog.recover`；向 `ctx.features` 中的 `AnswerInputRegistry`（CORE-39）注册 `HandwritingAnswerInput`；订阅 `ports.lifecycle.events()`，`paused` 持续 30 s 或 `lowMemory` 时调用 `recog.local.unload_all`。在 CORE-36 `installers.dart` 追加一行，位于 `installStudy` 之后。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 不把图片写入系统相册或公共目录。
- 外部前提：无新增第三方库（裁剪手势用 Flutter 内置 `InteractiveViewer` 与自绘裁剪框）。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-40_TEST.md](../Test/core/S5_CORE-40_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 750 行；主包 `app/lib/recognition/flow/`、`app/lib/recognition/answer_input.dart`、`app/lib/recognition/install.dart`、`app/lib/ui/recognition/crop/`。分阶段：① 识别流程编排、作答输入与安装点（RecognitionStep、RecognitionFlow、HandwritingAnswerInput、installRecognition，约 490）；② 图片裁剪增强页（CropEnhancePage、裁剪框状态 crop_state.dart 与路由登记，约 260）。

---

