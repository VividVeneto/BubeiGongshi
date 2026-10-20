### CORE-48 计算器、代入与计算链界面

**目标**：查看公式时把它当计算器使用（代入数值与单位求值、反解、数值求根），在量纲匹配处把另一公式代入，编辑并运行计算链。

**范围**
- 包含：计算器页（目标选择、输入行与单位下拉、输出单位、有效数字与区间显示、所用常数来源、数值求根 6 步）、代入向导（选槽位、候选列表、跨种类确认、预览并保存派生修订）、计算链页（步骤增删、上一步输出接下一步输入、运行、保存）；附属的计算链仓储与 op（`calculation_plan` 表）。
- 不包含：公式编辑与单位定义（CORE-37、CORE-38）；求值、代入与计算链算法（CORE-10、CORE-11）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-09、CORE-10、CORE-11、CORE-13、CORE-14、CORE-36、CORE-37、CORE-55、CORE-58

**接口契约**

```dart
// app/lib/calc/routes.dart —— 在 CORE-36 composition/routes.dart 追加一行；页面只收 VM 与 deps.ui（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
// /calc?revision=<id>   /calc/substitute?revision=<id>   /calc/plan?revision=<id>   （/calc 无 revision 时为空状态，见实现约束）
List<GoRoute> calcRoutes(AppDeps deps);

// app/lib/calc/calculator_vm.dart
enum NumericStep { chooseUnknown, giveInterval, solve, showResidual, markNumeric, confirm }
final class InputRow { final int symbolId; final String glyph; String value; String unit; String? uncertainty;
                       final List<String> unitChoices; }   // unitChoices 来自 units.compatible
final class CalculatorVm extends ChangeNotifier {
  static Future<CalculatorVm> open(CoreBinding core, String revisionId);
  // 打开流程：library.get 取修订 → engine.check（source_latex + 修订 symbols 作 user_decls）取 typed → calc.solvable_targets
  List<(int symbolId, String capability)> get targets; int get target; void setTarget(int symbolId);
  List<InputRow> get inputs; String? outputUnit; String precision;   // 'least_sig_figs' | 'full' | 'fixed:<3..10>'
  NumericStep? get numericStep; (String, String)? interval; void nextNumericStep();
  CalcResultDto? get result;
  Future<void> evaluate();   // calc.evaluate，budget_ms 200
}
// app/lib/calc/substitute_vm.dart
final class SubstituteVm extends ChangeNotifier {
  static Future<SubstituteVm> open(CoreBinding core, String targetRevisionId);
  List<NodePathDto> get slots;                 // 目标修订中可代入的 Symbol 叶节点
  Future<void> selectSlot(NodePathDto path);   // library.substitution_pool → derive.rank
  bool includeCrossKind;                       // 打开后列出跨种类候选并标记
  List<RankedCandidateDto> get candidates;     // (候选, MatchLevel)
  Future<SubstitutePreviewDto> preview(RankedCandidateDto c, {int? branch});   // derive.substitute
  Future<String> commit(SubstitutePreviewDto p, {required String title, ConfirmRecordDto? confirm});
  // commit：library.create，meta.title 为参数、subject 与 course 取目标条目、tags 为空，NewRevision.derived_from = preview.derivation，返回新条目 ID
}
// app/lib/calc/plan_vm.dart
final class PlanVm extends ChangeNotifier {
  static Future<PlanVm> open(CoreBinding core, {String? planId, String? startRevision});
  List<PlanStepDto> get steps; void addStep(String revisionId); void removeStep(int index);
  void setInput(int step, int symbolId, String value, String unit); void setFeed(int step, int? symbolId);
  Future<List<CalcResultDto>> run();           // derive.run_plan
  Future<String> save(String name);            // library.plan_put
}
```

```rust
// crates/fml-store/src/library/plan.rs（附属：Rust 侧计算链仓储与 op）
pub struct SavedPlan { pub id: Uuid, pub name: String, pub revision_id: RevisionId /* 第一步修订 */,
                       pub plan: CalculationPlan /* CORE-11 */, pub updated_at_ms: i64 }
pub fn put_plan(tx: &mut WriteTx, p: &SavedPlan) -> Result<(), FmlError>;   // 写 outbox（实体类型 calculation_plan）
pub fn list_plans(rx: &ReadTx, revision: Option<&RevisionId>) -> Result<Vec<SavedPlan>, FmlError>;
pub fn delete_plan(tx: &mut WriteTx, id: Uuid) -> Result<(), FmlError>;     // 写墓碑
```

- 表 `calculation_plan`（迁移 `crates/fml-store/migrations/0048_calculation_plan.sql`；通用列约定见 CORE-13）：`id TEXT PK`，`name TEXT NOT NULL`（1–100 字符），`revision_id TEXT NOT NULL`，`plan_json TEXT NOT NULL`（CORE-11 `CalculationPlan`，≤ 20 步），`updated_at_ms INTEGER NOT NULL`；索引 `(revision_id)`；可同步、可备份。
- 本卡登记的 op：`library.plan_put`、`library.plan_list`（`{revision_id?}`）、`library.plan_delete`（同步）。
- 调用的 op：`library.get`、`library.create`、`library.substitution_pool`（CORE-14）；`engine.check`（CORE-09）；`calc.evaluate`、`calc.solvable_targets`（CORE-10）；以上三者的 DTO 与处理由 CORE-56 登记；`derive.rank`、`derive.substitute`、`derive.run_plan`（CORE-11）；`units.compatible`（CORE-08）。
- 错误码与界面行为：

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `EVAL_NEEDS_INTERVAL` | CORE-10 | 自动 bracket 失败：进入数值求根第 2 步，要求输入区间 |
| `EVAL_MULTI_BRANCH` | CORE-10 | 多值反解：列出各支，用户选择后显示 |
| `EVAL_TIMEOUT` | CORE-10 | 结果区显示“重试”按钮 |
| 其他 `EVAL_*` | CORE-10 | 结果区显示消息与定位的输入行或子式 |
| `DERIVE_TYPE_MISMATCH` | CORE-11 | 不应出现在列表中（排序已排除）；出现时候选置灰 |
| `DERIVE_CROSS_KIND_UNCONFIRMED` | CORE-11 | 弹二次确认框；确认后带 `ConfirmRecord` 重新调用 `derive.substitute` |
| `DERIVE_NOT_VERIFIED`、`DERIVE_DEPTH_EXCEEDED`、`DERIVE_CYCLE`、`DERIVE_NODE_LIMIT` | CORE-11 | 向导内提示原因，不生成修订 |

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/calc/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/calc/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `LIB_NOT_VERIFIED` | CORE-14 | 派生结果校验未通过：预览页显示诊断，不允许保存 |

library.plan_put body={plan:SavedPlan}、ok={id}；list body={revision_id?}、ok={plans:[SavedPlan]}；delete body={id}、ok={}，均call；新计划id由调用方生成UUIDv7并在重试保留，name为1..100Unicode标量、steps为1..20。例list空库 body={}→ok={"plans":[]}。Dart SavedPlanDto/PlanStepDto/CalcResultDto引用binding/dto生成类型。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 不带 `revision` 的 `/calc` 显示 CORE-55 `EmptyState`“从公式库选择一个公式”，主操作跳转 `/library`；结果区固定在 `ActionBar` 上方，`expanded` 时输入行与结果左右并排。
- 只有 Verified 或 VerifiedPolymorphic 的修订可进入计算器与代入向导；其他状态显示原因并链接到编辑页（CORE-38）。
- 数值求根 6 步依次为：选择未知量 → 给出区间或初值 → 求解 → 显示残差 → 标注“数值解” → 用户确认是否把结果写入计算链；任何一步可返回上一步。
- 结果按 `CalcResult` 显示：值与单位、有效数字位数、不确定度区间、求解方式（直接/符号/数值）、`constants_used` 的来源与版本。
- 代入向导：默认不列跨种类候选；打开“显示跨种类候选”后列出并标记，选择时必须二次确认，确认记录随推导写入修订；派生修订保存后只读。
- 计算链：上一步的输出符号只能接到下一步量纲相同的输入（由 `derive.run_plan` 校验），保存前先运行一次。
- 组装：`calcRoutes` 追加到 `app/lib/composition/routes.dart`；详情页（CORE-38）以路由字符串跳转本卡页面。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 外部前提：无新增第三方包。

- 单位下拉直接消费 units.list_user；CORE-60（下游说明，非契约）新增单位之后刷新可选项。

**验收标准**
- [R12] 计算器（CX-01）：`F = m a` 代入 m = 2 kg、a = 3 m/s²，显示 6 N、有效数字 1 位、求解方式“直接”；切换目标为 a 后反解得到 a = F/m 的数值。
- [R12] 数值求根：`x \cdot e^{x} = 1`（CX-09）依次经过 6 步，显示残差 < 1e-12 与“数值解”标注；CX-08 显示区间 [9.98, 10.02]；CX-07 显示常数 c 的来源与版本。
- [R16] 代入向导：把 `v = a t` 代入 `E_k = \frac{1}{2} m v^2` 的 v 槽位，生成派生修订且校验为 Verified；派生条目只读。
- [R17] 防误代：能量量纲的式子代入力矩槽位时默认不出现；打开跨种类候选后选择须二次确认，修订中的 `cross_kind_confirmation` 非空；量纲不同的候选不出现。
- [R12] 计算链：两步计划（`v = a t` 输出 v 接 `E_k = \frac{1}{2} m v^2`）运行、保存、重开后运行结果一致；保存事务写出一条 calculation_plan outbox，重开可读（S3验收）；跨设备断言由CORE-46在S6联测执行。
- [R42.e] Widget 测试：打开不带 `revision` 的 `/calc` 显示空状态“从公式库选择一个公式”，点主操作后路由为 `/library`；宽 1200 时输入行与结果左右并排。

- [R42.e][R42.b] 页面接入验收（Fake CoreBinding，`calc.evaluate` 计数）：计算器 3 个输入行已填值与单位、焦点在第 2 行数值框且已有结果时 360×800 ↔ 800×360 往返 3 次，`CalculatorVm` 与页面 `State` 不变，输入行、结果与焦点保持，`calc.evaluate` 调用次数不因旋转增加；数值求解停在 `NumericStep.showResidual` 时旋转仍在该步；计算链 12 步滚到第 8 步时旋转滚动偏移不变；`textScaler` 2.0 下计算器、代入与计算链页 `tester.takeException()` 为 null，结果值、单位与区间不截断；每页恰有 1 个 `FmlButtonVariant.primary`（“计算”/“代入”/“运行”），矮高度时位于右侧操作区底部。

**规模**：约 480 行；用例/状态目录 `app/lib/calc/`；主包 `app/lib/ui/calc/`（约 430）；附属 `crates/fml-store/src/library/plan.rs` 与迁移（约 50，DDL 不计）。

