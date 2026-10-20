### WIN-03 自更新客户端

**目标**：检查、下载、校验新版本并在用户退出时安装；新版本首次启动失败时由启动器自动回滚到旧版本与更新前的数据库。

**范围**
- 包含：Dart 侧 `WindowsUpdater`（清单获取、下载与续传、哈希与 Authenticode 校验、退出时安装、健康确认与档案打开确认）；设置页“检查更新”区；更新清单格式。
- 不包含：独立启动器、验证与回滚状态机（WIN-16）；安装脚本（WIN-02）；托管与 CDN（CORE-43 提供 `/windows/update.json`）；资源包更新（CORE-51）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-23、CORE-36、CORE-43、WIN-02、WIN-16、CORE-65、CORE-28、WIN-17

**接口契约**

更新清单（`https://<FML_PACK_HOST>/windows/update.json`，CORE-43 托管，本卡定义）：

```json
{ "schema": 1, "launcher_protocol": 1, "version": "1.2.0", "min_os_build": 17763,
  "url": "https://<FML_PACK_HOST>/windows/BubeiGongshi-1.2.0-setup.exe",
  "size": 61234567, "sha256": "<64 位小写十六进制>", "released_at": "2026-10-18T00:00:00Z", "notes": "简体中文更新说明" }
```

```dart
// app/lib/platform/windows/update/windows_updater.dart
final class UpdateOffer { final String version; final Uri url; final int size; final String sha256; final String notes; }
sealed class UpdateState { const UpdateState(); }
final class UpdateIdle extends UpdateState {}             final class UpdateChecking extends UpdateState {}
final class UpdateAvailable extends UpdateState { final UpdateOffer offer; }
final class UpdateDownloading extends UpdateState { final UpdateOffer offer; final int received; }
final class UpdateReady extends UpdateState { final UpdateOffer offer; }      // 已校验，退出时安装
final class UpdateFailed extends UpdateState { final String errorCode; }      // 含上次回滚：PLATFORM_UPDATE_ROLLED_BACK
final class WindowsUpdater extends ValueNotifier<UpdateState> {
  WindowsUpdater({required HttpTransport http /* ctx.http，即 CORE-28 NetworkGuard */, required LocalFileStore files,
                  required AppLifecycle lifecycle, required String currentVersion, required Uri manifestUrl});
  Future<UpdateOffer?> check();                  // RequestPurpose.updateCheck；无更新或已被标记跳过返回 null
  Future<void> download({CancelToken? cancel});  // 用户点击下载后调用；RequestPurpose.updateCheck（含清单与安装包），允许计量网络； 写 staging\updates\BubeiGongshi-<v>-setup.exe.part，按已收字节 rangeStart 续传
  void installOnExit();                          // 仅 UpdateReady 有效；退出前先向 WIN-16 提交等待安装请求，取得 armed 确认后才 exitApp
  Future<void> confirmHealthy();                 // 经 WIN-16 --confirm-healthy 确认当前 version/nonce；无 nonce 时 no-op；子进程至多等 1500 ms
  Future<void> confirmOpened();                  // 经 WIN-16 --confirm-opened 确认档案已打开；无 nonce 时 no-op；子进程至多等 1500 ms
}
void installWindowsUpdater(CompositionContext ctx);
// install读取 WIN-01 的 windowsLaunchArguments 解析 --update-nonce，版本取本构建常量，nonce只在内存且不记日志；
// 登记 WindowsUpdater；向 SettingsSections 加入 order 90 的“检查更新”区；启动钩子 order 85：距上次检查 ≥ 24 h 时自动 check（只提示，不下载）；
// firstFrameHooks order 20：confirmHealthy（独立于顺序 startupHooks，早于其 order 20 档案打开）；读取 installRoot\rolled-back.txt 存在时置 UpdateFailed(PLATFORM_UPDATE_ROLLED_BACK)、
//   installRoot\update-failed.txt 存在时置 UpdateFailed(PLATFORM_IO)，读后删除该文件；
// 有 nonce 时订阅 ctx.features 中 CORE-23 的 AccountController.state，首次出现 GuestUnlocked 或 RegisteredUnlocked 时调用一次 confirmOpened（档案打开含迁移已成功）
```

```text
installRoot = File(Platform.resolvedExecutable).parent.parent（即 %LOCALAPPDATA%\Programs\BubeiGongshi\）
check：GET 清单 → schema != 1、launcher_protocol != 1 或字段缺失视为无更新；version 按 SemVer 不高于当前、等于 state.json 中 skipped_version、
       或 min_os_build 大于 RuntimeSnapshot.osVersion 的 build 号 → null
download：freeBytes < size × 3 → PLATFORM_UPDATE_DISK_FULL；完成后 SHA-256 不符 → 删除文件，PLATFORM_UPDATE_HASH_MISMATCH；
          通道 "fml/windows/update" verify {path} → {ok, signer_cert_sha256}（WinVerifyTrust 验链/时间戳/吊销策略后计算实际签名叶证书 DER 的 SHA-256）；ok 为 false 或指纹不在
          编译期 kAllowedSignerCertSha256 集合 → 删除文件，PLATFORM_UPDATE_SIG_INVALID；全部通过后去掉 .part 后缀并进入 UpdateReady
安装：退出前启动 WIN-16 的 --install-after-exit <installer 绝对路径> --version <offer.version> --pid <本进程 PID> --created <本进程创建 FILETIME>；
      update 通道按 WIN-16 命名管道协议 10 s 内连接、核验服务端 PID，读到 armed\n 后 shell.exitApp；连接失败、超时或内容不符
      → UpdateFailed(PLATFORM_IO)，保留安装包、不退出。不在 detached 事件中竞争启动 Inno；安装成功后不自动重启应用，下次启动由 WIN-16 验证。
state.json（staging\updates\）：{last_check_ms, skipped_version?}；回滚后把失败版本写入 skipped_version。
健康确认：firstFrameHooks 中只调用 BubeiGongshi.exe --confirm-healthy <nonce> --version <currentVersion>；档案首次打开后调用 --confirm-opened（参数同）；
          两者都至多等待子进程 1500 ms（在 CORE-36 每项 2 s 上限内），超时记 AppLog、不重试、不终止子进程；
          启动器按 WIN-16 协议写带 nonce 的 healthy/opened 文件；账户入口等待与网络同步不延迟健康确认。
版本选择、数据备份、首启等待、原子提交与回滚全部由 WIN-16 唯一定义。
```

- 错误码：只使用 CORE-04 登记的 `PLATFORM_UPDATE_SIG_INVALID`、`PLATFORM_UPDATE_HASH_MISMATCH`、`PLATFORM_UPDATE_DISK_FULL`、`PLATFORM_UPDATE_ROLLED_BACK`、`PLATFORM_IO` 与 CORE-04 的 `NET_*`；本卡不新增错误码。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

产品约束追踪：见README §6 Q36；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 不在应用运行时替换已加载文件：新版本装入新目录，切换由启动器在下次启动完成；不静默强制重启。
- 清单完整性依靠 HTTPS 与安装包 Authenticode 签名（实际签名证书指纹在编译期白名单内）；不另设清单签名私钥。
- 游客也可检查更新；请求不带账户令牌与设备标识（NetworkGuard 对 `updateCheck` 的规则见 CORE-28）。
- 下载客户端不控制或终止验证进程；仅实现 WIN-16 的安装与健康协议。
- 外部前提：签名叶证书 DER SHA-256 小写64位十六进制在 S7 登记后写入 `kAllowedSignerCertSha256`；证书获取见 WIN-12。

**验收标准**：测试方案全文见 [Test/win/S7_WIN-03_TEST.md](../Test/win/S7_WIN-03_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 360 行；`app/lib/platform/windows/update/` 与 `app/windows/runner/update_channel.cpp`（同属 `app/` 构建单元）。

