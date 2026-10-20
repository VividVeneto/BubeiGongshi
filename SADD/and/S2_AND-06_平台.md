### AND-06 本地存储与 Keystore

**目标**：提供 Android 私有目录与 Keystore 密钥包装，使数据库与识别历史只存在本机私有目录并排除出系统备份与设备迁移。

**范围**
- 包含：`LocalFileStore`、`SecureKeyValueStore` 端口实现；各 `StoreArea` 的根目录；备份与迁移排除规则文件；安全等级探测；Kotlin 侧 `KeystoreBridge.kt`。
- 不包含：数据库本身（CORE-13）；密钥层次与 AEAD（CORE-21）；账户状态机（CORE-23）；不提供生物识别与应用锁（README §6 Q41）；档案子目录的创建（共享层在各根目录下建 `<profile_id>/`）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-13、CORE-21、AND-01、AND-15

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

本卡实现：`AndroidKeyStore implements SecureKeyValueStore`、`AndroidFileStore implements LocalFileStore`（`app/lib/platform/android/storage/`），经 MethodChannel `"fml/android/keystore"` 调用 Kotlin：

```text
keystore.wrap      {alias, secret: bytes}   → bytes   格式：0x01 ‖ IV(12) ‖ AES-256-GCM 密文与标签；别名不存在则先创建密钥
keystore.unwrap    {alias, wrapped: bytes}  → bytes
keystore.delete    {alias}                  → null
keystore.level     {alias}                  → "strong_box" 或 "tee" 或 "software"
Kotlin 异常映射：KeyPermanentlyInvalidatedException、AEADBadTagException、别名不存在 → PLATFORM_KEY_UNAVAILABLE；
                 其他 IO 错误 → PLATFORM_IO
```

目录（`root(area)` 的返回值；全部位于 `noBackupFilesDir` 之下，不存在时创建）：

| `StoreArea` | Android 位置 | 使用者 |
| --- | --- | --- |
| database | `noBackupFilesDir/database/` | `<profile_id>.db` 与 WAL（CORE-13、CORE-23）、`device_registry.db`（CORE-23） |
| packs | `noBackupFilesDir/packs/` | 已验证的资源包（CORE-15） |
| recognition | `noBackupFilesDir/recognition/` | 识别历史密文资产（CORE-32） |
| staging | `noBackupFilesDir/staging/` | 导入、下载与导出的暂存文件 |
| drafts | `noBackupFilesDir/drafts/` | 编辑器与笔迹草稿 |
| exports | `noBackupFilesDir/exports/` | 导出前的临时产物（随后经 `FileExporter` 保存） |
| logs | `noBackupFilesDir/logs/` | 本地脱敏日志（CORE-28） |

Keystore 别名（由 CORE-23 使用，见 CORE-23 实现约束）：只有 `fml.<profile_id>.db`（无需认证，不调用 setUserAuthenticationRequired）；其他密钥由 CORE-21 在已解包密钥之下派生或包装，不建别名。

securityLevel==software仅报告能力，不在Kotlin或端口弹界面；CORE-65账户控制器经共享账户/CORE-47安全页展示“本机密钥保护能力较弱”及原因。平台包装仍不持久化明文，提示不可被误读为应用锁。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

**实现约束**
- 创建密钥：API 28+ 先请求 StrongBox（`setIsStrongBoxBacked(true)`），`StrongBoxUnavailableException` 时降级为普通 Keystore；`keystore.level` 由 `KeyInfo` 判定（API 31+ 用 `securityLevel`，更早用 `isInsideSecureHardware`），如实返回 `software`。
- 备份：清单 `android:allowBackup="false"`，并提供 `data_extraction_rules.xml`（Android 12+：cloud-backup 与 device-transfer 均排除全部域）与 `full_backup_content.xml`（排除全部域）；`excludeFromSystemBackup` 对上述根目录内的路径为空操作，对根目录之外的路径抛 `ArgumentError`。
- 不使用 MediaStore 与公共目录；恢复出厂或清除应用数据会丢失本机密钥，提示文案由 CORE-23/CORE-47 负责。
- `freeBytes()` 取 `StatFs(noBackupFilesDir).availableBytes`；空间不足的处理由调用方按 CORE-15、CORE-32 的规则执行，本卡不删除任何文件。

**验收标准**
- [R27] CORE-04 的 `SecureKeyValueStore`、`LocalFileStore` 契约套件在真机（`integration_test/android/storage_test.dart`）全部通过。
- [R27] 手动：执行 `adb shell bmgr backupnow <package>` 与设备迁移后，新设备上不存在 `database/`、`recognition/`、`drafts/` 内容。
- [R27] 在支持 StrongBox、仅 TEE、模拟器三类设备上 `securityLevel` 分别返回 `strongBox`、`tee`、`software`。
- [R27] 篡改 `wrap` 结果中任一字节后 `unwrap` 抛 `PLATFORM_KEY_UNAVAILABLE`。

**规模**：约 420 行；`app/lib/platform/android/storage/` 与 `app/android/.../KeystoreBridge.kt`、两个备份规则 XML（同属 `app/` 构建单元）。

---

