### CORE-60 公式导入与用户单位管理界面

**目标**：公式导入与用户单位管理界面，与原卡分开实施与验收。

**范围**
- 包含：导入四步向导、报告导出、用户单位增删与路由。
- 不包含：依赖卡已定义的业务算法、存储与平台能力；不修改其契约。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-08、CORE-14、CORE-36、CORE-55、CORE-58

**接口契约**

```dart
final class ImportWizardVm extends ChangeNotifier {
  ImportWizardVm(CoreBinding core, PlatformPorts ports);
  Future<bool> pick();                       // DocumentPicker：['csv', 'tex', 'txt']，maxBytes 8 MiB
  Future<ImportReportDto> run({CancelToken? cancel});   // library.import（长任务）
  Future<bool> exportFailedRows();           // FileExporter.saveAs('import-failed.csv', …)：原行 + 错误码 + 消息
}
final class UserUnitsVm extends ChangeNotifier {
  UserUnitsVm(CoreBinding core);
  List<UnitDefinitionDto> get units;         // units.list_user
  Future<void> define(UnitDefinitionDto def); Future<void> delete(String unitId);   // units.define_user / units.delete_user
}

List<GoRoute> libraryToolsRoutes(AppDeps deps);
```
静态路由 `/library/import`、`/library/units` 先于 `/library/:itemId` 注册。

**实现约束**
- 导入步骤为选择→前20行预览→可取消运行→报告；错误显示只复用 CORE-14/CORE-04/CORE-08。单位算法与持久化只经 CORE-14 op。
- 控件取 CORE-58、令牌取 CORE-55；平台只经端口。
- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**
- [R04][R04.j] 导入 100 行 CSV（其中 3 行错误）：报告 accepted 97、rejected 3 且行号正确；失败行可导出为 CSV。
- [R15] 单位页：定义 `user:li = 500 m` 后出现在列表且 units.list_user 返回该单位；循环定义显示 `UNIT_CYCLE`；被公式引用的单位删除时显示 `UNIT_IN_USE`。

- [R11][R42.b] Fake导入5001行或超过8MiB时停在选择文件；行错误列入报告并继续；textScaler=2.0无异常、向导每步恰一主按钮；单位页UNIT_*复用CORE-14/08错误在表单就地显示。

**规模**：约 320 行；主包 `app/lib/library/import/`、`app/lib/library/units/`、`app/lib/ui/library/import/`、`app/lib/ui/library/units/`（含测试与必要的同构建单元接缝）。

