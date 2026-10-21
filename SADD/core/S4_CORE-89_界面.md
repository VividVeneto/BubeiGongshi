### CORE-89 学习首页、书架与计划界面

**目标**：以不背单词为功能原型，提供学习首页、书架与计划设置，导航至稳定的学习会话入口。

**范围**
- 包含：首页今日新学/复习/错题数、考试倒计时、续学入口；书架内容包书与自建书、按章节浏览条目与考试标签；计划字段编辑/校验/保存、study.primary首页绑定及路由安装。
- 不包含：会话状态、作答/反馈/默写与输入注册（CORE-39）；统计计算与统计页（CORE-20、CORE-49）；提醒/自建书编辑（CORE-90，下游说明，非契约）；书/计划存储及排程（CORE-19）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-19、CORE-36、CORE-37、CORE-39、CORE-49、CORE-55、CORE-58、CORE-28、CORE-82

**接口契约**

```dart
// app/lib/study/home_routes.dart（页面在app/lib/ui/study/，只收VM与deps.ui）
List<GoRoute> studyHomeRoutes(AppDeps deps); // /study、/study/books、/study/books/:bookId、/study/plan/:bookId
// app/lib/study/view_models.dart
final class StudyHomeVm extends ChangeNotifier {
  StudyHomeVm(this._core, {int Function()? nowMs});
  TodayInfoDto? get today; Object? get error;
  Future<void> refresh();                                  // study.today
  Future<String> start(SessionKindDto kind);               // study.session.start → session_id；STUDY_NO_CARDS 时显示空态
}
final class BookshelfVm extends ChangeNotifier {
  List<BookDto> get books; Future<void> load();            // study.books.list
  Future<BookDto> open(String bookId);                     // study.books.get
}
final class PlanSettingsVm extends ChangeNotifier {
  PlanSettingsVm(this._core, String bookId);               // 已有 active 计划且同书时载入，否则用 CORE-19 默认值
  StudyPlanDto get draft; Map<String, String> get fieldErrors;   // 键为字段名，值为消息键
  void update(StudyPlanDto Function(StudyPlanDto) edit);  // 同步做范围校验
  Future<bool> save();                                     // study.plan.set；后端错误映射到字段
}
```

- StudyHomeVm、BookshelfVm、PlanSettingsVm只在本卡定义；会话类型与installStudy只由CORE-39定义。本卡按/study/session/:id导航，不把首页VM反向注入会话卡。
- 调用op：study.today、study.session.start、study.books.list/get、study.plan.set（CORE-82；纯DTO归CORE-19）；DTO TodayInfoDto、BookDto、ChapterDto、StudyPlanDto、SessionKindDto均复用领域schema经CORE-67生成的binding/dto，不重定义wire结构。
- 首页以CORE-55 FmlCommandScope绑定study.primary开始/续学，命令ID唯一来源CORE-58；首页恰有一个primary。书架与计划入口只导航，新增书编辑/提醒路由不在本卡实现。
- 组装：studyHomeRoutes与CORE-39 studyRoutes由composition并列安装；静态/study/books/new由其所有卡在/study/books/:bookId之前登记，不由本卡导入其实现。无新增Installer，聚合维护者单写共享文件。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `STUDY_NO_CARDS` | CORE-19 | 首页显示空态与“调整计划”入口 |
| `STUDY_K_OUT_OF_RANGE` / `STUDY_PLAN_INVALID` | CORE-19 | 计划页对应字段标红，不离开页面 |

Dart文件归属：VM/用例在app/lib/study/，Widget/首页/书架/计划页面在app/lib/ui/study/，保持既有路径；Widget只接VM与回调，不收CoreBinding/HttpTransport。

产品约束追踪：见README §6 Q23、Q26、Q33；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 计划页字段与 CORE-19 一一对应：每日新学 0–200、复习上限 10–2000、组大小 5–30、K 新学 1–5、K 复习 1–3、目标保留率 0.80–0.95、题型开关、考试日期、考研科目（数一 / 数二 / 数三 / 不选）；考研科目只在书含 `exam_scope` 时可选。
- 外部前提：go_router（ADR-V5-15 锁定版本）。
- 首页显示与CORE-19 TodayInfo一致，不在UI重算排程；首页需要图表/统计时单向消费CORE-49，不能使统计页依赖首页卡。
- 原型只求功能近似，不引入平台判断。首页primary在紧凑档处下部40%，矮高度在右半下半；计划草稿与页面State在旋转/分档/textScaler变化时保持，不额外提交study.plan.set。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-89_TEST.md](../Test/core/S4_CORE-89_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约470行；app/lib/study/、app/lib/ui/study/中首页/书架VM与页面约250行、计划VM/表单约200行、路由及本卡编写的composition接入约20行；不计自测、夹具、DTO/schema数据与生成物。
