### CORE-50 识别结果、云端确认与识别历史界面

**目标**：提供识别主页面与路由、候选选择与逐符号校正、保存到公式库、云识别功能级同意页与逐次上传预览页，以及识别历史页。

**范围**
- 包含：识别主页面（按 `RecognitionFlow.step` 切换子页面，入口选择手写 / 导入）；候选页（Top-3、逐符号替换、保存前完整校验、保存到公式库或复制公式（CORE-59 `FormulaCopyButton`））；云识别同意页（供应商、模型版本、地区、保留期、是否用于训练、年龄与监护人确认）；上传预览页（实际上传图片、尺寸与字节数、政策摘要、今日剩余额度）；识别历史页（分页列表、Pin、查看、删除、一键清空、“识别图片已清理”）。
- 不包含：流程编排、画布与裁剪（CORE-40）；历史保留设置（CORE-47）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-31、CORE-32、CORE-34、CORE-36、CORE-37、CORE-38、CORE-40、CORE-55、CORE-59、CORE-58

**接口契约**

```dart
// app/lib/recognition/pages/routes.dart（页面在 app/lib/ui/recognition/pages/）
List<GoRoute> recognitionRoutes(AppDeps deps);   // /recognize、/recognize/history、/recognize/history/:sessionId

// app/lib/ui/recognition/pages/recognize_page.dart
class RecognizePage extends StatefulWidget { const RecognizePage({super.key, required this.flow, required this.deps}); final RecognitionFlow flow; final UiDeps deps; }   // recognitionRoutes 构造 lookup 模式的 RecognitionFlow 后传入

// app/lib/recognition/pages/candidate_vm.dart
final class CandidateVm extends ChangeNotifier {
  CandidateVm(this._core, {required String sessionId, required List<CandidateDto> candidates,
              required String notationProfileId, List<SymbolDeclDto> userDecls = const []});   // 取自 RecognitionFlow，用于 recog.correct / final_check 请求体
  int get selected; void select(int index);
  CandidateDto get current;
  void replaceSymbol(int spanIndex, String replacement);   // recog.correct
  Future<List<DiagnosticDto>> check();                     // recog.final_check
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
  HistoryVm(this._core);
  List<SessionSummaryDto> get items; bool get hasMore;
  Future<void> loadMore();                                 // recog.history.list {page}
  Future<void> setPinned(String sessionId, bool on);       // recog.pin
  Future<HistoryDetail> open(String sessionId);            // recog.session.get；图片缺失时 imageLost = true
  Future<void> clearAll();                                 // 二次确认后 HistoryKeyUnlocker.clearAll()（CORE-32）
}
final class HistoryDetail { final SessionSummaryDto summary; final String? confirmedImagePath; final List<CandidateDto> candidates; final bool imageLost; }

// app/lib/recognition/pages/drop.dart（接缝；WIN-04 实现时只 import 此文件）
abstract interface class ImageDropSource {          // 平台卡经 platformInstallers 登记（WIN-04）；未登记时识别页不响应拖放
  Stream<DroppedImages> drops({Future<bool> Function(int count, int bytes, int other)? confirmFolder}); }
final class DroppedImages { final List<ImportedImage> images /* 0–10，0只提示跳过 */; final int skippedNotImage, skippedOverLimit; }

// app/lib/recognition/pages/storage_guard.dart
final class StorageStatus extends ValueNotifier<bool> { StorageStatus() : super(false); }   // true = 存储紧张，识别页顶部显示提示条
void installStorageGuard(CompositionContext ctx);
```

- 调用的 op：`recog.correct / final_check`（CORE-31）；`recog.history.list / pin / adopt / session.get / transition`（CORE-32，删除单条走 `transition` 到 `Deleting` 由 GC 完成；一键清空经 `HistoryKeyUnlocker.clearAll()`，首次列出前 `ensure()`）；云端经 `RecognitionFlow` 转调 CORE-34。
- 组装：`recognitionRoutes` 追加到 `app/lib/composition/routes.dart`；`installStorageGuard` 追加到 `featureInstallers`（紧跟 `installRecognition`）。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
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
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 候选项用 `AnswerOption` 样式，云端确认与上传进度用 `LoadingState`；`expanded` 时左侧原图或墨迹、右侧候选与操作。
- 拖放：`RecognizePage` 可见时订阅 `features.get<ImageDropSource>()?.drops()`，通过confirmFolder回调显示共享确认框“将导入n张图片（约x MB），跳过m个其他文件”；拒绝不复制。收到非空images才 `flow.startImages(images, InputSourceDto.dragDrop)`，空批次只提示；`skippedNotImage` 或 `skippedOverLimit` 非 0 时提示“已导入 n 张，跳过 a 个非图片文件、b 张超出上限”。
- 候选页显示 Top-3（不足 3 个按实际数），默认选中第 1 个；查找模式可显示置信度分档（高 / 中 / 低），作答模式不经过本页（CORE-40 自带转写确认）。
- 逐符号校正：点公式中的符号显示 `alternatives` 与“自定义”输入；每次替换后重新 `final_check`，Error 级诊断阻止保存。
- 保存：经 CORE-38 新建页（预填 LaTeX）完成，本卡不直接写公式库；新建页返回 `Saved` 后由本卡调用 `recog.adopt`（会话标记 Adopted，不受次数 GC）；返回 null 表示用户放弃。
- 同意页：未勾选年龄问题不可提交；选“未满 14 周岁”时必须勾选监护人同意；拒绝后返回后端选择且本次不再提示。
- 预览页显示的图片就是 `UploadPreview.image` 文件（同一哈希）；剩余额度为 0 时“上传识别”禁用并说明次日重置。
- 历史页：按序号倒序；Pinned 置顶标记；`has_images = false` 的项显示“识别图片已清理”；游客与注册用户界面一致，但游客永不出现云端标识。
- 页面销毁时删除 `recog.session.get` 返回的暂存图片。
- 存储守护：`installStorageGuard` 登记 `StorageStatus` 与 order 55 启动钩子，并订阅 `ports.lifecycle.events()` 的 `resumed` 与 `lowMemory`（两次检查间隔至少 10 分钟）：`ports.files.freeBytes()` < 500 MiB 时 `core.submit('recog.gc', {})` 一次并置 `StorageStatus` 为 true，恢复到 ≥ 600 MiB 后置回 false；提示条文案“存储空间不足，已清理识别缓存；可在设置中减少保留的识别记录”，并提供跳转 `/settings/history`。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-50_TEST.md](../Test/core/S5_CORE-50_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 480 行；用例/状态目录 `app/lib/recognition/pages/`；`app/lib/ui/recognition/pages/`。

