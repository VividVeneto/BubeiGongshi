### CORE-86 计算链计划、界面与仓储

**目标**：编辑、运行、保存和重开计算链，提供计划持久化、同步投影与op。

**范围**
- 包含：PlanVm、计算链页与calcPlanRoutes；SavedPlan/仓储、codec/applier（含删除）、library.plan_*的fml-ffi处理及calculation_plan迁移。
- 不包含：计算器/代入向导（CORE-48）、derive.run_plan等领域算法（CORE-11）、公式编辑。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-05、CORE-11、CORE-13、CORE-14、CORE-36、CORE-37、CORE-55、CORE-58

**接口契约**

```dart
// app/lib/calc/plan_routes.dart；由composition聚合维护者与calcRoutes并列登记
// /calc/plan?revision=<id>
List<GoRoute> calcPlanRoutes(AppDeps deps);
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
// crates/fml-store/src/library/plan.rs（仓储/codec/applier；op处理另在本卡fml-ffi）
pub struct SavedPlan { pub id: Uuid, pub name: String, pub revision_id: RevisionId /* 第一步修订 */,
                       pub plan: CalculationPlan /* CORE-11 */, pub updated_at_ms: i64 }
pub fn put_plan(tx: &mut WriteTx, p: &SavedPlan) -> Result<(), FmlError>;   // 写 outbox（实体类型 calculation_plan）
pub fn list_plans(rx: &ReadTx, revision: Option<&RevisionId>) -> Result<Vec<SavedPlan>, FmlError>;
pub fn delete_plan(tx: &mut WriteTx, id: Uuid) -> Result<(), FmlError>;     // 写墓碑
```

- 表 `calculation_plan`（迁移 `crates/fml-store/migrations/0086_calculation_plan.sql`；通用列约定见 CORE-13）：`id TEXT PK`，`name TEXT NOT NULL`（1–100 字符），`revision_id TEXT NOT NULL`，`plan_json TEXT NOT NULL`（CORE-11 `CalculationPlan`，≤ 20 步），`updated_at_ms INTEGER NOT NULL`；索引 `(revision_id)`；可同步、可备份。
- 本卡登记的 op：`library.plan_put`、`library.plan_list`（`{revision_id?}`）、`library.plan_delete`（同步）。
library.plan_put body={plan:SavedPlan}、ok={id}；list body={revision_id?}、ok={plans:[SavedPlan]}；delete body={id}、ok={}，均call；新计划id由调用方生成UUIDv7并在重试保留，name为1..100Unicode标量、steps为1..20。例list空库 body={}→ok={"plans":[]}。Dart SavedPlanDto/PlanStepDto/CalcResultDto引用binding/dto生成类型。

- calculation_plan codec/applier 使用 CORE-13 EntityRegistry 接缝：按ID UTF-8稳定枚举/回读本表SavedPlan，name/revision_id/plan/updated_at_ms按单字段FieldClock合并（plan是一个完整有序链字段，不按到达次序拼接步骤）。验证名称/步数/修订引用/链结构后写入；不在远端应用时重跑数值求值而产生副作用。Delete 保存原实体类型墓碑，较旧Upsert不能复活；同值同钟Duplicate，非法引用/结构Invalid，存储错误Err。仅使用传入WriteTx，不stamp/enqueue/新Store.write；本机put/delete仍按原本写命令入outbox。S3用Fake分派测试，无CORE26反向依赖。
- 新表calculation_plan归本卡，DDL独立0086迁移，不再宣称0048所有权；实体codec/applier和墓碑删除分支在本卡，业务写用CORE-13 Store.write/enqueue_outbox与changed_fields，不自行分配Lamport。op处理在本卡编写的crates/fml-ffi/src/ops/library_plan.rs，不放UI或领域crate。
- 调用CORE-11 derive.run_plan；上一步输出符号只能接到下一步量纲相同输入，规则由领域算法校验，保存前必须先成功运行一次。增删步骤、输入和feed映射属于PlanVm，页面不持CoreBinding。
- PlanVm在app/lib/calc/plan_vm.dart，页面在app/lib/ui/calc/plan_page.dart，路由在plan_routes.dart；Widget只接状态/抽象/回调，不取裸绑定、CoreLibrarySpec或HttpTransport。CORE-36聚合维护者单写共享routes，详情页只发路由字符串，不反向import本卡VM。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| EVAL_* | CORE-10 / CORE-93（EVAL_NO_CONVERGE、EVAL_NEEDS_INTERVAL、EVAL_MULTI_BRANCH） | 标记失败步骤/输入，显示原诊断；超时可重试 |
| DERIVE_TYPE_MISMATCH、DERIVE_NOT_VERIFIED、DERIVE_DEPTH_EXCEEDED、DERIVE_CYCLE、DERIVE_NODE_LIMIT | CORE-11 | 不保存无效链，定位失败步骤 |
| LIB_NOT_VERIFIED | CORE-14 | 拒绝无效来源，显示诊断 |

**实现约束**
- 视觉/布局按CORE-55令牌与密度、CORE-58控件，不判断平台。12步滚到第8步旋转保持PlanVm/页面State/滚动与结果，禁止旋转重复运行；textScaler=2.0不截断值/单位/区间，唯一primary为“运行”，矮高度位于右侧操作区底部。
- 运行/保存/重开是S3闭环，跨设备仅由CORE-46在S6联测，不误报S3通过。
- 无新增第三方包，DDL不计规模；SavedPlanDto/PlanStepDto/CalcResultDto使用生成类型，不复制定义。

**验收标准**：测试方案全文见 [Test/core/S3_CORE-86_TEST.md](../Test/core/S3_CORE-86_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约345行；app/lib/calc/{plan_vm,plan_routes}.dart、app/lib/ui/calc/plan_page.dart，crates/fml-store/src/library/plan.rs及本卡编写的crates/fml-ffi/src/ops/library_plan.rs与composition接入；DDL归migrations/0086_calculation_plan.sql但不计行；不计schema、生成物、自测及夹具。
