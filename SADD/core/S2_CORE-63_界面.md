### CORE-63 账户入口、注册登录与隐私页面

**目标**：账户入口、注册登录与隐私页面，与原卡分开实施与验收。

**范围**
- 包含：游客/注册/登录/找回页面、隐私展示与路由。
- 不包含：依赖卡已定义的业务算法、存储与平台能力；不修改其契约。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-36、CORE-55、CORE-58、CORE-65

**接口契约**

```dart
List<GoRoute> accountRoutes(AppDeps deps);
```
提供 `/`、`/account/register`、`/account/login`、`/account/reset`、`/privacy`，表单 ViewModel 归 app/lib/account/pages/，Widget 只收 VM、UiDeps 与回调。

**实现约束**
- 无档案只放行账户与隐私路由；注册先验证邮箱再创建，登录走 CORE-65 的系统浏览器 PKCE。
- 路由尚未安装时 CORE-36 显示本地不可用占位；不调用网络。
- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-63_TEST.md](../Test/core/S2_CORE-63_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 300 行；主包 `app/lib/account/pages/`、`app/lib/ui/account/`（含测试与必要的同构建单元接缝）。

