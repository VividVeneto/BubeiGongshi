### CORE-65 账户客户端控制器与安全令牌存取

**目标**：账户客户端控制器与安全令牌存取，与原卡分开实施与验收。

**范围**
- 包含：账户状态客户端、注册/登录/找回、档案打开与 TokenStore 实现。
- 不包含：依赖卡已定义的业务算法、存储与平台能力；不修改其契约。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-22、CORE-23、CORE-45、CORE-62

**接口契约**

```dart
// app/lib/account/account_controller.dart
abstract class AccountController {
  Stream<AccountState> get state;
  Future<void> continueAsGuest();
  Future<void> requestEmailCode({required String email, required EmailCodePurpose purpose}); // POST /v1/auth/email-codes（CORE-45）
  Future<void> register({required String email, required String emailCode, required String password});
      // POST /v1/auth/register → 201 { account_id } → 与 login() 相同的授权码 + PKCE 流程（系统浏览器）→ /v1/auth/token 换令牌 → create_registered → 询问是否开启同步（默认不开启）
  Future<void> login();                                    // 经系统浏览器打开 /v1/auth/authorize（授权码 + PKCE，回调深链）
  Future<void> resetPassword({required String email, required String emailCode, required String newPassword});
  Future<void> logout({bool deleteLocalData = false});     // 默认只锁库；删除需二次确认
}
enum EmailCodePurpose { register, resetPassword }
// app/lib/account/secure_token_store.dart：implements TokenStore（CORE-62）；访问令牌只在内存，刷新令牌经 SecureKeyValueStore 包装后存 profile_blob
```



`AccountState` 为 CORE-23 五状态的 Dart 镜像枚举（`uninitialized, guestUnlocked, registeredUnlocked, registeredLocked, upgradingGuest`），由 CORE-67 从 account.state schema 生成，wire 为 snake_case，未知值拒绝；state stream 每次成功转换只发一次，订阅者先收到当前快照。EmailCodePurpose 的 wire 为 register/reset_password。TokenStore契约归CORE-62。

档案会话唯一所有者（app/lib/account/profile_session.dart）：

```dart
final class ProfileSession {
  final String profileId, handle;
  final CoreBinding core; // root.scopedTo(handle)，只注入特性层，不进入ui/
  Future<void> close();   // 幂等，同一关闭Future；关闭成功后本视图永久失效
}
abstract interface class ProfileSessionSource {
  ProfileSession? get current;
  Stream<ProfileSession?> get changes; // 先给当前快照；关闭开始即发null，打开完成才发新会话
}
```

CORE-36 composition注入ProfileSessionSource：依赖档案的用例在调用开始捕获current.core；current=null时走账户入口，绝不回退root绑定。切换串行执行：停止旧用例/网络并等待取消→changes(null)→account.close_profile→清空访问令牌、缓存和旧VM→解包新DbKey→account.open_profile→构造新ProfileSession→changes(new)。关闭失败保持空快照并给出重试，不能在旧写者未关闭时打开新库。logout先set_logged_out(true)，再执行同一关闭序列；只在完成后发布registeredLocked。异常/退出都走close，进程崩溃由OS释放、启动重新解包不复用handle。DbKey、refreshToken只短暂在端口/FFI之间传递，finally清零；平台软件密钥警告由账户页状态通知CORE-47展示。

| 生命周期 | 句柄所有者 | 密钥处理 | 对外快照 |
| --- | --- | --- | --- |
| 创建/恢复中 | AccountController局部变量 | wrap/unwrap后finally清零，失败关闭已创建handle | null |
| 使用中 | ProfileSession | 原生Store持Zeroizing；Dart不保留DbKey | 当前session |
| 切换/登出/退出 | 原ProfileSession，等待close | 排空任务后清原生密钥及访问令牌 | null |
| 升级合库 | CORE-24局部目标handle | 只在合库任务中持有，成功失败都close | 不发布目标session |

产品约束追踪：见README §6 Q41；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 当前交互档案仍只打开一个；升级迁移专用双库句柄由 CORE-24（下游说明，非契约）持有，不暴露到界面。
- 明文 DbKey 只在端口/FFI 调用期间存活，使用后清零；异常路径同样清理。
- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**
- [R24][R25] Fake 端口注册/登录/游客路径改变客户端状态；登出后进入 registeredLocked，重新登录恢复；切换档案先关闭旧库。
- [R27] 刷新令牌仅包装密文落 profile_blob，访问令牌仅内存，登出清理。

- [R24][R27] Fake连续切换A→B：在A请求未排空前B的open不执行，changes依次A/null/B；close失败时仍为null；创建后的wrap/put_blob/open每处注入失败，明文临时缓冲均填零且没有Unlocked通知。

**规模**：约 460 行；主包 `app/lib/account/`（controller/token_store约240、profile_session约120、测试约100）（含测试与必要的同构建单元接缝）。

