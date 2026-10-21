### CORE-39 学习会话界面

**目标**：提供组学习作答、即时反馈、组后默写、跳过暂停与“记错了”申诉界面。

**范围**
- 包含：组学习页与内置作答方式（选择、公式输入、自评）；作答方式扩展点（手写由CORE-40注册）；即时反馈、Undetermined后自评、组后默写；跳过/暂停/续学、“记错了”申诉与组结束小结。
- 不包含：学习首页/书架/计划设置（CORE-89，下游说明，非契约）；统计页（CORE-49，下游说明，非契约）；提醒设置/自建书编辑（CORE-90，下游说明，非契约）；手写画布与识别（CORE-40，下游说明，非契约）；出题/判分/排程（CORE-17～19）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-19、CORE-36、CORE-37、CORE-38、CORE-55、CORE-58、CORE-59、CORE-87、CORE-28、CORE-82

**接口契约**

```dart
// app/lib/study/routes.dart（页面在app/lib/ui/study/，只收VM与deps.ui）
List<GoRoute> studyRoutes(AppDeps deps); // 仅 /study/session/:id；首页/书架/计划由独立上层路由组装

// app/lib/study/session_vm.dart
sealed class SessionScreen {}
final class Loading extends SessionScreen {}
final class Asking extends SessionScreen { final QuestionViewDto q; final int index; final int total; }
final class ShowingFeedback extends SessionScreen { final FeedbackDto f; }
final class SelfRating extends SessionScreen { final String attemptId; final String expectedLatex; final String reason; }
final class Dictating extends SessionScreen { final List<QuestionViewDto> qs; }
final class Paused extends SessionScreen {}
final class Summary extends SessionScreen { final GroupSummaryDto s; }
final class Expired extends SessionScreen {}

final class SessionVm extends ChangeNotifier {
  SessionVm({required CoreBinding core, required String sessionId, required AnswerInputRegistry inputs, int Function()? nowMs});
  SessionScreen get screen;
  Future<void> open();                                     // study.session.resume
  Future<void> submit(AnswerSubmissionDto a);              // study.session.step Answer
  Future<void> next();                                     // ShowingFeedback → 下一条 Ask
  Future<void> skip(); Future<void> pause(); Future<void> resumeSession();
  Future<void> selfRate(bool knew);
  Future<void> appeal(String attemptId);                   // study.appeal，“记错了”
  Future<void> submitDictation(List<AnswerSubmissionDto> answers);
}

// app/lib/study/answer_input.dart（作答方式扩展点；Widget 由各 factory 的 build 返回，放 app/lib/ui/study/answer/ 或提供方卡的 ui/ 目录）
typedef AnswerSink = void Function(AnswerSubmissionDto submission);
abstract interface class AnswerInputFactory {
  AnswerModeDto get mode;
  Widget build(BuildContext context, QuestionViewDto q, AnswerSink sink, {required bool dictation});
}
final class AnswerInputRegistry {
  void register(AnswerInputFactory f);                     // 同一 mode 后注册者覆盖
  AnswerInputFactory resolve(AnswerModeDto mode);          // 无 Handwriting 实现时返回 Input 并带“手写不可用”提示
}
// app/lib/study/install.dart
void installStudy(CompositionContext ctx);                 // 在 ctx.features 注册 AnswerInputRegistry（含 Choice、Input、SelfRate）
```

- 学习命令ID唯一来源为CORE-58 StudyCommand.id；本卡只绑定会话状态动作，CORE-55 FmlCommandScope声明当前可用命令，平台处理键位。首页绑定迁至CORE-89（下游说明，非契约），会话不调用首页VM。

| 命令 ID | 在哪些状态可用 | 动作 |
| --- | --- | --- |
| study.primary | Asking（公式输入题）、ShowingFeedback、Dictating（末题）、Paused、Summary、Expired | 提交作答、next()、提交默写、继续、继续、返回/study（当前状态唯一主操作） |
| `study.option1`～`study.option4` | `Asking`（选择题，按选项数） | 选择 A～D 并提交 |
| `study.rateKnew` / `study.rateForgot` | `SelfRating` | 自评“会” / “不会” |
| `study.skip` | `Asking` | 跳过本题 |
| `study.pause` | 会话各进行中状态 | 暂停（与系统返回同一动作） |
| `study.appeal` | `ShowingFeedback`、`SelfRating` | “记错了”申诉 |
| `study.prevQuestion` / `study.nextQuestion` | `Dictating` | 默写上一题 / 下一题 |

- 选项与主按钮的 `AnswerOption.commandId`、`ShortcutHint(commandId)` 取上表 ID。

- Dart wire DTO统一由CORE-67从CORE-19等领域契约生成：AnswerModeDto、QuestionViewDto、FeedbackDto（含RelatedFormulaDto）、VerdictDto、AnswerSubmissionDto、GroupSummaryDto、UiCommandDto（sealed）；不因拆卡复制DTO定义。
- 调用的op：CORE-82 study.session.*、study.appeal；公式显示经CORE-37 MathText与EditorWorker.layoutStatic，输入题使用CORE-59 FormulaEditorController。
- 组装：studyRoutes追加到composition/routes.dart；installStudy追加到featureInstallers，须排在installRecognition之前。首页路由由独立组装片段登记，本卡只按/study导航，不导入CORE-89；登记片段由聚合维护者单写合入。

- 错误码与界面行为：

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `STUDY_SESSION_EXPIRED` | CORE-19 | 进入 `Expired`，显示已完成部分并返回首页 |
| `STUDY_INPUT_INVALID` | CORE-19 | 重新 `open()` 同步当前题，记录 AppLog |
| `GRADE_PARSE_FAILED` | CORE-18 | 留在当前题，输入框标出错误位置，不计作答 |

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/study/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/study/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

产品约束追踪：见README §6 Q23、Q26、Q33；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 键盘命令：各状态只在 `FmlCommandScope` 中声明上表命令，不处理具体按键；同一状态只有一个 `study.primary`。
- 系统返回：学习会话页以 `PopScope(canPop: false)` 拦截，返回等同会话顶栏“暂停”（同一动作），不直接离开会话；对照见 AND-13 表 e。
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 作答选项用 `AnswerOption`、判定用 `VerdictBanner`，每个状态至多一个 `FmlButtonVariant.primary`（CORE-55 P1）；判对、判错与自评后调用 CORE-55 `FmlFeedback.emit`（未登记 `UiFeedbackSink` 或已关闭触感时为空操作）；判定反馈在 CORE-01“作答到判定反馈”预算内出现，不弹对话框。
- 界面状态完全由 `UiCommand` 驱动：`Ask` → `Asking`，`Feedback` → `ShowingFeedback`，`NeedSelfRate` → `SelfRating`，`StartDictation` → `Dictating`，`Finished` → `Summary`；VM 不自行判断对错，不缓存标准答案。
- 每次作答立即提交（不去抖）；提交中禁用作答控件，防止重复提交；`duration_ms` 从题目显示到提交计时，暂停与切后台期间不计。
- 反馈页：判错时显示标准答案与“将在本组稍后重现”；`related` 非空时列出易混与派生公式，点击进入 CORE-38 详情页；判对、判错都提供“记错了”按钮，申诉后提示“已更正，排程已重算”。
- Undetermined：显示标准答案与原因，请用户选“会 / 不会”，界面标注“自评”；自评结果不显示为“正确”。
- 公式输入题：Windows 默认 LaTeX 模式，Android 默认结构化模式（CORE-59 `defaultEditorMode`）；`required_form` 非空时在题干下提示要求形式（如“须带 +C”）。
- 题干与反馈不显示识别置信度；考试标签（`exam_tags`）显示在题干上方。
- 外部前提：go_router（ADR-V5-15 锁定版本）。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-39_TEST.md](../Test/core/S4_CORE-39_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约690行，分阶段（Ⅰ 会话VM、输入注册/工厂及接入约370行；Ⅱ 会话界面、听写/反馈及接入约320行；各阶段可独立构建与测试）；app/lib/study/、app/lib/ui/study/中会话/作答实现与本卡编写的composition接入行；首页/书架/计划实现归CORE-89，不重复计；不计自测、夹具、DTO/schema数据与生成物。
