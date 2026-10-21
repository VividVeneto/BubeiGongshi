### CORE-50 识别结果、云端确认与识别历史界面

**目标**：提供识别主页面与路由、候选选择与逐符号校正、保存到公式库、云识别功能级同意页与逐次上传预览页，以及识别历史页。

**范围**
- 包含：识别主页面（按 `RecognitionFlow.step` 切换子页面，入口选择手写 / 导入）；候选页（Top-3、逐符号替换、保存前完整校验、保存到公式库或复制公式（CORE-87 `FormulaCopyButton`））；云识别同意页（供应商、模型版本、地区、保留期、是否用于训练、年龄与监护人确认）；上传预览页（实际上传图片、尺寸与字节数、政策摘要、今日剩余额度）；识别历史页（分页列表、Pin、查看、删除、一键清空、“识别图片已清理”）。
- 不包含：流程编排、画布与裁剪（CORE-40）；历史保留设置（CORE-47）；存储压力检查、GC与档案生命周期守护（由本卡拆至 CORE-101）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-31、CORE-32、CORE-34、CORE-36、CORE-37、CORE-38、CORE-40、CORE-55、CORE-59、CORE-58、CORE-65、CORE-87、CORE-88、CORE-101

**接口契约**

```dart
// app/lib/recognition/pages/routes.dart（页面在 app/lib/ui/recognition/pages/）
List<GoRoute> recognitionRoutes(AppDeps deps);   // /recognize、/recognize/history、/recognize/history/:sessionId

// app/lib/ui/recognition/pages/recognize_page.dart
class RecognizePage extends StatefulWidget { const RecognizePage({super.key, required this.flow, required this.deps}); final RecognitionFlow flow; final UiDeps deps; }   // recognitionRoutes 构造 lookup 模式的 RecognitionFlow 后传入

// app/lib/recognition/pages/candidate_vm.dart
final class CandidateVm extends ChangeNotifier {
  CandidateVm(ProfileSessionSource sessions, {required String sessionId, required List<CandidateDto> candidates,
              required String notationProfileId, List<SymbolDeclDto> userDecls = const []});   // 取自 RecognitionFlow，用于 recog.correct / final_check 请求体
  int get selected; void select(int index);
  CandidateDto get current;
  void replaceSymbol(int spanIndex, String replacement);   // recog.correct
  Future<List<DiagnosticDto>> check();                     // recog.final_check
  Future<void> stopAndDrain(ProfileSession session);
  Future<void> disposeAsync();
  String get latex;                                        // 复制用（交给 FormulaCopyButton）
  Future<bool> save(BuildContext context);                 // push('/library/new', extra: NewFormulaArgs(latex))；返回 Saved 时调 recog.adopt {id, revision}
}

// app/lib/ui/recognition/pages/cloud_pages.dart
class CloudConsentPage extends StatelessWidget {
  const CloudConsentPage({super.key, required this.policy, required this.onGrant, required this.onDecline});
  final ProviderPolicy policy; final void Function(FeatureConsentInput) onGrant; final VoidCallback onDecline;
}
class UploadPreviewPage extends StatelessWidget {
  const UploadPreviewPage({super.key, required this.preview, required this.onConfirm, required this.onBack});
  final UploadPreview preview; final VoidCallback onConfirm, onBack;
}

// app/lib/recognition/pages/history_vm.dart
final class HistoryVm extends ChangeNotifier {
  HistoryVm(ProfileSessionSource sessions, {required HistoryKeyUnlocker keys});
  List<SessionSummaryDto> get items; bool get hasMore;
  Future<void> loadMore();                                 // recog.history.list {page}
  Future<void> setPinned(String sessionId, bool on);       // recog.pin
  Future<HistoryDetail> open(String sessionId);            // recog.session.get；图片缺失时 imageLost = true
  Future<void> clearAll();                                 // 二次确认后 HistoryKeyUnlocker.clearAll()（CORE-32）
  Future<void> stopAndDrain(ProfileSession session);
  Future<void> disposeAsync();
}
final class HistoryDetail { final SessionSummaryDto summary; final String? confirmedImagePath; final List<CandidateDto> candidates; final bool imageLost; }

// app/lib/recognition/pages/drop.dart（接缝；WIN-19 实现时只 import 此文件）
abstract interface class ImageDropSource {          // 平台卡经 platformInstallers 登记（WIN-19）；未登记时识别页不响应拖放
  Stream<DroppedImages> drops({Future<bool> Function(int count, int bytes, int other)? confirmFolder}); }
final class DroppedImages { final List<ImportedImage> images /* 0–10，0只提示跳过 */; final int skippedNotImage, skippedOverLimit; }

// CORE-101 唯一定义 StorageStatus 与 installStorageGuard；本卡只读消费状态，不复制声明。
```

- 调用的 op：`recog.correct / final_check`（CORE-31）；`recog.history.list / pin / adopt / session.get / transition`（CORE-32，删除单条走 `transition` 到 `Deleting` 由 GC 完成；一键清空经 `HistoryKeyUnlocker.clearAll()`，首次列出前 `ensure()`）；云端经 `RecognitionFlow` 转调 CORE-34。
- 组装：recognitionRoutes 的路由片段由 CORE-36 聚合维护者单写合入；StorageStatus 由 CORE-101 安装并从 deps.features 读取，routes 只把 ValueListenable<bool>/回调传给页面。本卡不再登记 installStorageGuard/order55 或执行 GC。
- 错误码与界面行为：

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `PRIVACY_CONSENT_MISSING` | CORE-28 | 回到云识别同意页 |
| `CLOUD_CONSENT_INVALID` | CORE-33 | 回到云识别同意页并重新拉取政策版本 |
| `CLOUD_TOKEN_EXPIRED`、`AUTH_UPLOAD_RECONFIRM_REQUIRED` | CORE-34、CORE-62 | 回到预览页重新确认 |
| 其他 `CLOUD_*` | CORE-33、CORE-34 | 显示所有者定义的消息 |

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/recognition/pages/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/recognition/pages/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `RECOG_SPAN_INVALID` | CORE-31 | 替换被拒，保持原候选 |
| `RECOG_IMAGE_LOST` | CORE-32 | 详情页显示“识别图片已清理”，结果文本仍可查看 |
| `RECOG_SESSION_NOT_FOUND` | CORE-32 | 从列表移除该项并提示 |
| `RECOG_QUOTA_EXCEEDED` | CORE-32 | 历史页顶部提示“固定记录过多，建议取消部分固定” |

候选页FormulaCopyButton传RecognitionFlow使用的notationProfileId与userDecls快照；候选替换/最终校验后更新快照，不能只传latex或沿用其他档案声明。

**实现约束**
- recognitionRoutes 用 deps.sessions 构造 RecognitionFlow、CandidateVm 与 HistoryVm，HistoryVm 的 keys 从 deps.features.require<HistoryKeyUnlocker>() 注入，不暗取全局注册表。路由按对象身份+handle 绑定 VM/识别 sessionId/notationProfileId/userDecls；changes(null) 立即禁用动作并清空候选、预览和敏感详情，旧 VM disposeAsync 完成才构造新 handle 的 VM（同 profileId 重开也重建），Widgets 不接收会话源或裸 core。
- 每次校正/校验/保存/历史加载/Pin/详情/清空只捕获一个 current，null 不调档案 op、不打开保存页，需结果的入口以 StateError 拒绝本地调用前置条件（不新增业务错误码）；每个 await 后及后续副作用前核对身份+handle。同步 replaceSymbol 入队于同 handle 的串行校正链，check/save 等待该链，过代结果不发布。保存页返回 Saved 只可在原会话仍 current 时调用原 core 的 recog.adopt，A 迟到 Saved 不向 B 采用，也不在关闭后补写 A。历史 ensure→list/clearAll 保持同一代，迟到结果/错误不能变更 B 列表/错误条。
- 每个 VM 以唯一实例 id 向 sessions.addBeforeClose 登记 stopAndDrain；同步前缀拒绝新动作并取消任务/订阅，随后 await 已发 FFI/校正/详情/保存回调收尾及本页暂存图清理（只删本实例持有的 staging 副本，不删持久历史图）。外部保存页面不能取消时撤销其待处理回调并等待本页收尾，不等待用户无限停留；迟到返回独立丢弃。disposeAsync 同样可重复等待这条排空链，成功后才注销 beforeClose；ChangeNotifier.dispose 仅同步解绑 UI，不能代替排空。失败上抛，CORE-65 保持 closing/null，不释放旧 handle/开 B。其他 beforeClose 同步取消前缀都先执行再 await，不互相串等。
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 候选项用 `AnswerOption` 样式，云端确认与上传进度用 `LoadingState`；`expanded` 时左侧原图或墨迹、右侧候选与操作。
- 拖放：`RecognizePage` 可见时订阅 `features.get<ImageDropSource>()?.drops()`，通过confirmFolder回调显示共享确认框“将导入n张图片（约x MB），跳过m个其他文件”；拒绝不复制。收到非空images才 `flow.startImages(images, InputSourceDto.dragDrop)`，空批次只提示；`skippedNotImage` 或 `skippedOverLimit` 非 0 时提示“已导入 n 张，跳过 a 个非图片文件、b 张超出上限”。
- 候选页显示 Top-3（不足 3 个按实际数），默认选中第 1 个；查找模式可显示置信度分档（高 / 中 / 低），作答模式不经过本页（CORE-40 自带转写确认）。
- 逐符号校正：点公式中的符号显示 `alternatives` 与“自定义”输入；每次替换后重新 `final_check`，Error 级诊断阻止保存。
- 保存：经 CORE-88 新建页（预填 LaTeX）完成，本卡不直接写公式库；新建页返回 `Saved` 后由本卡调用 `recog.adopt`（会话标记 Adopted，不受次数 GC）；返回 null 表示用户放弃。
- 同意页：未勾选年龄问题不可提交；选“未满 14 周岁”时必须勾选监护人同意；拒绝后返回后端选择且本次不再提示。
- 预览页显示的图片就是 `UploadPreview.image` 文件（同一哈希）；剩余额度为 0 时“上传识别”禁用并说明次日重置。
- 历史页：按序号倒序；Pinned 置顶标记；`has_images = false` 的项显示“识别图片已清理”；游客与注册用户界面一致，但游客永不出现云端标识。
- 页面销毁时删除 `recog.session.get` 返回的暂存图片。
- 存储提示 UI：只读订阅 CORE-101 StorageStatus，true 显示“存储空间不足，已清理识别缓存；可在设置中减少保留的识别记录”，提供 /settings/history 跳转，false/null 关闭提示；页面销毁取消订阅，不修改状态、不触发 GC/权限/原生调用。阈值、节流和关闭排空全部由 CORE-101 唯一实现。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-50_TEST.md](../Test/core/S5_CORE-50_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约710行，分阶段（Ⅰ 来源流程/drop、候选VM/UI与会话栅栏及接入约355行；Ⅱ 云同意/预览、历史VM/UI与排空、存储提示只读消费及接入约355行；各阶段可独立构建与测试）；app/lib/recognition/pages/、app/lib/ui/recognition/pages/及本卡编写的composition接入行；不计自测、夹具、schema与生成物。原780行扣除完整存储守护110，再加候选/历史生命周期40=710；存储守护110及其生命周期新增30迁CORE-101计140，总计850不丢量。拆卡与接线仍需非作者独立复核，不据此认定就绪。

