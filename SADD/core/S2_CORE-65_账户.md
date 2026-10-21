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
final class DefaultAccountController implements AccountController {
  DefaultAccountController({required CoreBinding root, required PlatformPorts ports,
    required ApiClient api, required SecureTokenStore tokens, required ProfileSessionHost sessions});
  // 实现 AccountController 全部方法；root 只调用 CORE-23 全局档案管理 op。
}
// app/lib/account/secure_token_store.dart
final class SecureTokenStore implements TokenStore {
  SecureTokenStore(CoreBinding root, SecureKeyValueStore keys, ProfileSessionSource sessions);
  // 严格实现 CORE-62 的 accessToken()/refreshToken()/save(String access, String refresh)/clear()。
  // 访问令牌只在内存，刷新令牌经 keys 包装后存 profile_blob。
}
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
  void Function() addBeforeClose(String id, Future<void> Function(ProfileSession session) stopAndDrain);
}
final class ProfileSessionHost implements ProfileSessionSource {
  ProfileSessionHost(CoreBinding root);
  // 实现 current/changes/addBeforeClose；发布/转移句柄仅供同包 DefaultAccountController，非特性 API。
}
```

CORE-36 composition 创建唯一 ProfileSessionHost 并以 ProfileSessionSource 注入。依赖档案的用例在每次调用开始捕获同一个 session/handle/core，await 后验证 identity 与 handle 仍是 current；current=null 时回账户入口，不能回退 root 或改用新档案重试。相同 profileId 再打开也有新 handle/世代，不得只比较 profileId。

关闭的同步前半段先把 host 标记 closing、拒绝新业务并设置 current=null/发布 changes(null)，不能等待第一个异步取消后才置空。旧 session 私有保留给已登记 beforeClose 的取消/排空控制路径，原生 scoped core 此时仍有效。随后按登记顺序先调用所有 beforeClose（各回调在第一个 await 前同步禁止新任务/发取消信号），再等待全部 drain 完成 → account.close_profile(旧 handle) → 清空访问令牌、缓存和旧 VM → 解包新 DbKey → account.open_profile → 构造新 session → changes(new)。任何 drain 或原生 close 失败保持 closing/null，保留未完成阶段以显式重试；不重新开放旧业务，不打开新库，不宣称已关闭。正常业务不能借 private 旧引用绕过 closing。

addBeforeClose 的 id 全局唯一，重复抛 StateError；按登记顺序启动回调，不等前一项 drain 才启动下一项，以免档案钩子等待特性任务、特性取消却尚未启动的死锁；所有返回 Future 均收集结果（含同步抛错），等待已启动项全部 settle 后按登记顺序确定失败（不按完成竞态）再报告，不用 Future.wait 的提前失败释放句柄。返回函数只注销本次登记。调用 close 时冻结回调列表；注销不取消已启动的 drain。同一关闭中的并发 close 返回同一 Future，成功后幂等；失败后新的 close 重试未完成阶段，已完成回调不重复执行。账户切换/login/logout/启动恢复共用串行队列，禁止两个 open 或 open 与 close 交错。logout 在此队列内先 set_logged_out(true)，并立即进入上述 closing；该本地标志写失败则不伪造登出，成功排空关闭后才发布 registeredLocked。异常/退出也走 close；崩溃由 OS 释放，启动重新解包不复用 handle。

SecureTokenStore 的异步 unwrap/save/refresh 在开始捕获档案与世代，完成后再验证；过期结果清零丢弃，绝不能写入另一个档案。关闭 drain 期间只允许已捕获旧任务的取消控制使用原有访问令牌，不启动刷新或新业务；关闭后 clear 不得误删下一档案令牌。DbKey、刷新令牌可变字节缓冲在成功/失败/过期各路径 finally 清零；不可变字符串只短暂持有并释放，不声称可原地擦除。平台软件密钥警告交账户页状态，由 CORE-47（下游说明，非契约）展示。

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

**验收标准**：测试方案全文见 [Test/core/S2_CORE-65_TEST.md](../Test/core/S2_CORE-65_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 590 行；主包 `app/lib/account/`。分阶段：① 账户控制器与档案会话（接口、状态流与启动恢复、游客与注册账户落地、logout、SecureTokenStore、ProfileSession/Source 与串行切换及档案钩子、清零与安装点，约 480）；② OIDC 授权与邮箱验证码客户端流程（`app/lib/account/auth/`：PKCE 与 state/nonce、系统浏览器授权与回调校验、令牌交换、注册/验证码/找回请求，约 110）。

