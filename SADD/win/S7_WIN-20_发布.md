### WIN-20 启动器持久化与数据库恢复

**目标**：为独立C++启动器提供严格控制文件、原子journal、校验快照与幂等恢复；不依赖CLI状态机，供WIN-16注入调用。

**范围**
- 包含：installRoot文件布局/控制文件格式唯一权威；严格解析/原子写/日志/路径安全；备份manifest与回读；restore_step幂等恢复、共享冲突重试与唯一备份保护。
- 不包含：CLI、互斥与应用激活、进程/管道、状态推进/用户救援对话框（WIN-16）；下载/安装（WIN-03/02）；迁移业务（CORE-13）。

**依赖**：CORE-01、CORE-02、CORE-04、WIN-01、WIN-07、WIN-17

**接口契约**

沿用ADR-V5-31/33，以下从WIN-16迁入，launcher_protocol仍为1。

```text
installRoot = %LOCALAPPDATA%\Programs\BubeiGongshi\（控制文件只由启动器写；安装器只放置程序文件）
  BubeiGongshi.exe     启动器（launcher_protocol=1）
  app-<v>\             WIN-01 构建输出；稳定后只保留当前与上一版两个
  current.txt          当前版本，如 1.2.0
  pending.txt          待验证版本（仅 pending/verifying 期间存在）
  journal.json         更新 journal（idle 时不存在）
  healthy.json         本轮首帧确认 {"version":"<N>","nonce":"<nonce>"}
  opened.json          本轮档案已打开确认，格式同 healthy.json
  rolled-back.txt      被回滚的版本号 N；WIN-03 读取后删除
  update-failed.txt    "<N> <Inno 退出码十进制>"（一个空格分隔）；WIN-03 读取后删除
  launcher.log         本机日志，达到 1 MiB 轮转为 launcher.log.1（只留一份）；不记录内容、密钥与 nonce
数据根（WIN-07）：备份集 = StoreArea.database 整个目录 + StoreArea.packs 下 CORE-95 的 pack_meta.db 及其 -wal/-shm；
                 不含 security_state.json 与包版本目录；下文“数据库”均指这一备份集
备份：<数据根>\staging\updates\db-backup-<C>\{database\…, packs\pack_meta.db[-wal|-shm], manifest.txt}；构建中名为 db-backup-<C>.tmp
```

- 文本格式：全部控制文件为 UTF-8、无 BOM、无尾换行；版本号为严格 SemVer 2.0（不含构建元数据，拒绝路径字符）；nonce 为 BCryptGenRandom 生成的 128 bit，写成 32 个小写十六进制字符。
- journal.json：单行 JSON，键按下列顺序、无多余空白：`{"schema":1,"state":"verifying","C":"1.1.0","N":"1.2.0","nonce":"<32 hex>","pid":1234,"created":"133414560000000000","backup_ready":true,"restore_step":"none","open_attempts":0}`。state ∈ `pending`、`verifying`、`committed`、`rolling-back`、`rolled-back`（idle 即文件不存在）；pid 为 JSON 整数（未登记为 0）；created 为进程创建时间 FILETIME 的 u64 十进制字符串（未登记为 "0"，避免 JSON 数值精度损失）；restore_step ∈ `none`、`moved-failed`、`restored`；open_attempts 为 0～255 的整数。解析失败、schema≠1、缺键或出现未知键视为 journal 损坏：不改任何文件，进入救援对话框。
- manifest.txt：首行 `fml-db-backup 1`，其后每个文件一行 `<字节数十进制>\t<SHA-256 小写 hex>\t<相对备份根的路径，分隔符 />`，按路径的 UTF-8 字节序升序，每行以 LF 结尾，不列 manifest 自身。备份回读与恢复都按它逐文件核验大小与哈希。
- 原子写：任何控制文件写同目录 `<name>.tmp` → FlushFileBuffers → 关闭句柄 → MoveFileExW(MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)；写失败不推进状态。journal 是恢复依据，不能把多个 rename 声称为跨文件事务。

```cpp
// installer/windows/launcher/storage.h；类型、序列化和实现均由本卡拥有。
struct Journal; // 字段/范围/严格顺序逐项见上述journal.json协议
struct BackupManifest; // manifest.txt的类型化结果
enum class ControlFile { current, pending, healthy, opened, rolled_back, update_failed };
struct StorageFailure { unsigned long native_code; std::string action; }; // 以此类型抛出，WIN-16按const引用捕获并决定救援UI
class LauncherStorage {
 public:
  virtual ~LauncherStorage() = default;
  virtual std::optional<Journal> read_journal() = 0; // 缺失返回nullopt，由调用方按idle处理；损坏抛StorageFailure，不写磁盘
  virtual void write_journal(const Journal&) = 0;
  virtual std::optional<std::string> read_control(ControlFile file) = 0; // 严格校验对应文件格式；缺失nullopt，损坏抛StorageFailure
  virtual void atomic_control(ControlFile file, const std::string& utf8) = 0; // 仅枚举白名单；严格校验后原子写
  virtual void remove_control(ControlFile file) = 0; // 缺失幂等，拒删current；journal仅经write/cleanup处理
  virtual void discard_unmodified_backup(const Journal&) = 0; // 转发退出10且未opened，现库清单/哈希仍与备份相同才允许撤回本轮备份；否则保留并抛StorageFailure
  virtual BackupManifest create_backup(const std::string& current_version) = 0;
  virtual void verify_backup(const BackupManifest&) = 0;
  virtual void restore_backup(Journal&) = 0; // 每项幂等推进并原子持久化restore_step
  virtual void cleanup_committed(const Journal&) = 0; // 仅调用者确认opened/恢复完成后调用
};
// 所有端口I/O或格式失败均抛StorageFailure；native_code为Win32错误码（格式错误用ERROR_INVALID_DATA），action为稳定动作标识、不含路径/内容/nonce。缺失仅read返回nullopt，remove幂等；成功void不另返回错误码。不新增公共错误码。
```

| 恢复阶段 | 磁盘动作与状态机调用边界 | 幂等与保留约束 |
| --- | --- | --- |
| rolling-back → rolled-back → idle | none：把现库各项移到 database.failed-<N> 与 packs\pack_meta.failed-<N>\ → moved-failed：删除残留 .restoring 后从备份复制到 database.restoring 与 packs\pack_meta.restoring\，按 manifest 核验后 rename 就位 → restored：原子 current=C、删 pending、写 rolled-back.txt=N 与 state=rolled-back，启动 C；之后删 journal、healthy/opened 与已用备份 | 每步按项幂等，重启按 restore_step 与目录存在判定续做；failed-<N> 库保留到下一轮更新进入 idle |

以上恢复行只定义磁盘幂等动作，current切换/启动C仍由WIN-16状态机调用端口；本卡不启动/等待进程。备份：构建db-backup-C.tmp→写manifest→逐文件回读大小/哈希→rename为db-backup-C，最后才删上一轮备份；中断只删不完整tmp，不覆盖有效备份。

**实现约束**
- rename/替换遇共享冲突重试 5 次、间隔 200 ms；耗尽保留 app-C、journal、备份和失败库，不在未恢复或部分迁移的库上启动 C。恢复失败或 journal 损坏向调用方返回StorageFailure，由WIN-16显示独立原生救援对话框（重试、打开日志/数据目录、退出）；旧程序只有恢复并核验成功才能启动。程序不删除唯一有效备份。
- 备份/回滚只允许写文档指定目录，路径正规化拒绝重解析点逃逸；写者退出之前禁止复制与恢复。备份保留到 opened 后的 committed → idle 清理或恢复核验完成；committed 期间保留 app-<C>。
- 调用方必须在写者退出后才发起复制/恢复；端口不查询进程，测试用可注入文件系统验证。路径正规化拒绝绝对manifest路径、父级逃逸、重解析点；只触及指定数据根。
- cleanup_committed只能在WIN-16已收到匹配opened或恢复核验完成后执行；没有可用替代前不删唯一有效备份。清理/日志可重试，不把多文件rename声称事务。
- 所有等待在启动器进程，没有常驻服务/网络；只系统库，WIN-01锁定CMake/MSVC。复用CORE-04 PLATFORM_IO/PLATFORM_UPDATE_ROLLED_BACK，不新增错误码，不记录内容/密钥/nonce。
- WIN-17主机协议自检可本地夹具完成；真实Release/设备汇总由WIN-18，未提供设备保持pending。

**验收标准**：测试方案全文见 [Test/win/S7_WIN-20_TEST.md](../Test/win/S7_WIN-20_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约700行；`installer/windows/launcher/storage.h`、`formats.cpp`、`atomic_file.cpp`、`backup.cpp`、`restore.cpp`及本卡CMake接入。分阶段：① 严格格式/原子文件/日志/路径220与manifest/备份回读220，共440行；② 幂等恢复/重试/清理/唯一备份保护260行。各阶段用故障文件系统独立构建验收；WIN-16代码、静态配置及自测夹具不计。
