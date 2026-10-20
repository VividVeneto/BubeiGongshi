### WIN-07 本地存储与 DPAPI

**目标**：提供 Windows 私有目录与 DPAPI 密钥包装，并在设置页如实说明 DPAPI 的安全边界。

**范围**
- 包含：`LocalFileStore`、`SecureKeyValueStore` 端口实现；各 `StoreArea` 根目录与私有 ACL；设置页“安全说明”区。
- 不包含：数据库（CORE-13）；密钥层次与 AEAD（CORE-21）；账户状态机（CORE-23）；不提供 Windows Hello、应用锁与防截屏（README §6 Q41）；档案子目录（共享层在各根目录下建 `<profile_id>/`）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-13、CORE-21、CORE-36、WIN-01、WIN-17

**接口契约**

实现的端口（CORE-04，逐字摘录）：

```dart
/// 平台密钥保护：只包装/解包核心生成的密钥，不向 UI 暴露原始密钥。
abstract interface class SecureKeyValueStore {
  Future<Uint8List> wrap(String alias, Uint8List secret);     // 返回包装后的密文；alias 匹配 ^[a-z0-9_.-]{1,64}$
  Future<Uint8List> unwrap(String alias, Uint8List wrapped);  // 密钥失效抛 PLATFORM_KEY_UNAVAILABLE；包装与解包都不要求用户认证
  Future<void> delete(String alias);                          // 别名不存在时静默成功
  Future<KeySecurityLevel> securityLevel(String alias);
}
/// 应用私有目录；返回的目录都位于应用私有根目录之内，不存在时自动创建。
abstract interface class LocalFileStore {
  Future<Directory> root(StoreArea area);
  Future<int> freeBytes();                                    // 应用私有根目录所在卷的可用字节数
  /// dir须在本应用私有根目录内（解析符号链接后的真实路径）；越界抛ArgumentError，不创建/修改目标。
  Future<void> excludeFromSystemBackup(Directory dir);
}
```

本卡实现：`WindowsKeyStore`、`WindowsFileStore`（`app/lib/platform/windows/storage/`）与 `installWindowsStorage(CompositionContext ctx)`（向 `SettingsSections` 加入 order 70 的“安全说明”区），经 MethodChannel `"fml/windows/keystore"`（`app/windows/runner/keystore_channel.cpp`）调用：

```text
wrap   {alias, secret}  → bytes   0x02 ‖ CryptProtectData(secret, entropy = UTF-8(alias), CRYPTPROTECT_UI_FORBIDDEN)
unwrap {alias, wrapped} → bytes   版本字节不是 0x02 或 DPAPI 解密失败 → PLATFORM_KEY_UNAVAILABLE
delete {alias}          → null    只删除调用方保存的包装结果对应的本地状态
level  {alias}          → "dpapi"
free_bytes              → int     GetDiskFreeSpaceExW(数据根)
```

目录（`root(area)` 的返回值，不存在时创建）：

| `StoreArea` | Windows 位置 | 使用者 |
| --- | --- | --- |
| database | `%LOCALAPPDATA%\BubeiGongshi\database\` | `<profile_id>.db` 与 WAL（CORE-13、CORE-23）、`device_registry.db`（CORE-23）；WIN-16 启动器按此路径备份 |
| packs | `…\packs\` | 已验证的资源包（CORE-15） |
| recognition | `…\recognition\` | 识别历史密文资产（CORE-32） |
| staging | `…\staging\` | 导入、下载与导出暂存；更新下载在 `staging\updates\`（WIN-03） |
| drafts | `…\drafts\` | 编辑器与笔迹草稿 |
| exports | `…\exports\` | 导出前的临时产物（随后经 `FileExporter` 保存） |
| logs | `…\logs\` | 本地脱敏日志（CORE-28） |

- 错误码：只使用 CORE-04 登记的 `PLATFORM_KEY_UNAVAILABLE`、`PLATFORM_IO`；本卡不新增错误码。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

**实现约束**
- 首次创建 `%LOCALAPPDATA%\BubeiGongshi\` 时设置受保护 DACL（`SetNamedSecurityInfoW` + `PROTECTED_DACL_SECURITY_INFORMATION`）：只授予当前用户与 SYSTEM 完全控制，不继承父目录权限。
- 数据只写 `%LOCALAPPDATA%`（不漫游）；不写安装目录、桌面、下载与公共文档目录；`excludeFromSystemBackup` 对数据根内路径为空操作，对根外路径抛 `ArgumentError`。
- “安全说明”区必须列出：数据由 Windows 账户加密（DPAPI），打开应用不需要额外验证；更换 Windows 用户或重置系统后密钥不可恢复；同机管理员与已解锁会话中的恶意软件不在防护范围内；卸载、重装、重置前应导出备份或开启同步；第三方整盘备份软件可能复制密文目录。
- `freeBytes` 只读不删；空间不足由调用方按 CORE-15、CORE-32、CORE-50 的规则处理。
- 外部前提：DPAPI 与 ACL API 随 Windows SDK 提供，不引入其他库。

**验收标准**
- [R27] CORE-04 的 `SecureKeyValueStore`、`LocalFileStore` 契约套件（`integration_test/windows/storage_test.dart`）全部通过；`securityLevel` 返回 `dpapi`。
- [R27] 把数据目录复制到另一 Windows 用户下运行，`unwrap` 抛 `PLATFORM_KEY_UNAVAILABLE`，应用提示且不崩溃；篡改包装结果任一字节同样抛该码。
- [R27] `icacls "%LOCALAPPDATA%\BubeiGongshi"` 只列出当前用户与 SYSTEM，且无继承项。
- [R27] 设置页显示“安全说明”区，包含上述各项说明。

**规模**：约 450 行；`app/lib/platform/windows/storage/` 与 `app/windows/runner/keystore_channel.cpp`（同属 `app/` 构建单元）。

---

