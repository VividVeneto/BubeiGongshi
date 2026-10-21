### CORE-48 计算器与代入向导

**目标**：查看公式时进行带单位数值计算/反解/数值求根，并通过量纲匹配向导代入另一公式、预览和保存派生修订。

**范围**
- 包含：计算器页（目标/输入单位、输出单位、有效数字/区间、常数来源、数值求根6步）、代入向导（槽位/候选、跨种类确认、预览/保存）。
- 不包含：公式编辑/单位定义；领域算法（CORE-10/11）；计算链页面、仓储、codec/applier与op（CORE-86，下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-08、CORE-10、CORE-11、CORE-14、CORE-36、CORE-37、CORE-55、CORE-56、CORE-58、CORE-79、CORE-88

**接口契约**

```dart
// app/lib/calc/routes.dart —— 在 CORE-36 composition/routes.dart 追加一行；页面只收 VM 与 deps.ui（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
// /calc?revision=<id>   /calc/substitute?revision=<id> （/calc无revision为空状态）；/calc/plan由CORE-86独立注册（下游说明，非契约）
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
```

- 调用op：`library.get`、`library.create`（CORE-14）；`library.substitution_pool`（CORE-79）；`engine.check`、`calc.evaluate`、`calc.solvable_targets`（DTO/处理唯一登记CORE-56，算法CORE-09/10/93）；`derive.rank`、`derive.substitute`（CORE-11）；`units.compatible`、`units.list_user`（CORE-08/14）。
- 错误码与界面行为：

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `EVAL_NEEDS_INTERVAL` | CORE-93 | 自动 bracket 失败：进入数值求根第 2 步，要求输入区间 |
| `EVAL_MULTI_BRANCH` | CORE-93 | 多值反解：列出各支，用户选择后显示 |
| `EVAL_TIMEOUT` | CORE-10 | 结果区显示“重试”按钮 |
| 其他 `EVAL_*` | CORE-10/CORE-93 | 结果区显示消息与定位的输入行或子式 |
| `DERIVE_TYPE_MISMATCH` | CORE-11 | 不应出现在列表中（排序已排除）；出现时候选置灰 |
| `DERIVE_CROSS_KIND_UNCONFIRMED` | CORE-11 | 弹二次确认框；确认后带 `ConfirmRecord` 重新调用 `derive.substitute` |
| `DERIVE_NOT_VERIFIED`、`DERIVE_DEPTH_EXCEEDED`、`DERIVE_CYCLE`、`DERIVE_NODE_LIMIT` | CORE-11 | 向导内提示原因，不生成修订 |

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/calc/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/calc/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `LIB_NOT_VERIFIED` | CORE-14 | 派生结果校验未通过：预览页显示诊断，不允许保存 |


**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 不带 `revision` 的 `/calc` 显示 CORE-55 `EmptyState`“从公式库选择一个公式”，主操作跳转 `/library`；结果区固定在 `ActionBar` 上方，`expanded` 时输入行与结果左右并排。
- 只有 Verified 或 VerifiedPolymorphic 的修订可进入计算器与代入向导；其他状态显示原因并链接到编辑页（CORE-88）。
- 数值求根 6 步依次为：选择未知量 → 给出区间或初值 → 求解 → 显示残差 → 标注“数值解” → 用户确认是否把结果写入计算链；任何一步可返回上一步。
- 结果按 `CalcResult` 显示：值与单位、有效数字位数、不确定度区间、求解方式（直接/符号/数值）、`constants_used` 的来源与版本。
- 代入向导：默认不列跨种类候选；打开“显示跨种类候选”后列出并标记，选择时必须二次确认，确认记录随推导写入修订；派生修订保存后只读。
- 数值求根末步若用户选择加入计算链，只通过路由字符串传递结果/修订给上层已注册入口；不import PlanVm或计算链仓储，不形成CORE-48→CORE-86依赖。
- 组装：`calcRoutes` 追加到 `app/lib/composition/routes.dart`；详情页（CORE-38）以路由字符串跳转本卡页面。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 外部前提：无新增第三方包。

- 单位下拉直接消费 units.list_user；CORE-60（下游说明，非契约）新增单位之后刷新可选项。

**验收标准**：测试方案全文见 [Test/core/S3_CORE-48_TEST.md](../Test/core/S3_CORE-48_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约555行，分阶段：① CalculatorVm/计算器界面、求根6步及接入约350行；② SubstituteVm/代入向导、确认/保存及接入约205行；各阶段可独立构建与测试。app/lib/calc/及app/lib/ui/calc/中计算器/代入文件与本卡编写的composition接入；不含计算链，不计DDL/schema、生成物、自测及夹具。
