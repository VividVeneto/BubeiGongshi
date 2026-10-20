### WIN-16 启动器与更新恢复

**目标**：以独立 C++ 构建单元安全选择版本、等待安装、验证首帧与档案打开，失败时恢复更新前数据库；并发启动不触发重复回滚。

**范围**
- 包含：固定路径 BubeiGongshi.exe、CMake/CTest、installRoot 文件布局与控制文件格式（本卡为唯一权威）、原子状态文件与持久化 journal、单启动器互斥、进程等待与命名管道确认、安装登记命令、数据库快照与恢复、故障注入夹具。
- 不包含：下载/签名校验（WIN-03）；安装脚本（WIN-02）；业务迁移算法（CORE-13，下游说明，非契约）；SecureKV 迁移；整库恢复后的设备身份更换（同步客户端按 ADR-V5-33 处理）。

**依赖**：CORE-01、CORE-02、WIN-01、WIN-06、WIN-07、WIN-17

**接口契约**

决策依据：ADR-V5-31（启动、安装与恢复时序，补充见附录 A §A.4.5）；整库恢复后的设备身份见 ADR-V5-33。

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
数据根（WIN-07）：备份集 = StoreArea.database 整个目录 + StoreArea.packs 下 CORE-15 的 pack_meta.db 及其 -wal/-shm；
                 不含 security_state.json 与包版本目录；下文“数据库”均指这一备份集
备份：<数据根>\staging\updates\db-backup-<C>\{database\…, packs\pack_meta.db[-wal|-shm], manifest.txt}；构建中名为 db-backup-<C>.tmp
```

- 构建：`cmake -S installer/windows/launcher -B build/launcher` 后 `cmake --build build/launcher --config Release`；输出 `BubeiGongshi.exe`。只链接 Windows 系统库，不链接 Flutter/Rust/安装器；首版协议固定 launcher_protocol=1，协议升级须另立 ADR 与迁移安装器；WIN-02 用 /DLauncher 消费制品，因此不存在 WIN-02 ↔ WIN-03 循环。启动器 VERSIONINFO 的 FileVersion 在 `installer/windows/launcher/launcher_version.h` 单独维护（CORE-42 bump_version 不改它），仅启动器代码变更时递增，供 WIN-02 按版本比较替换。
- 文本格式：全部控制文件为 UTF-8、无 BOM、无尾换行；版本号为严格 SemVer 2.0（不含构建元数据，拒绝路径字符）；nonce 为 BCryptGenRandom 生成的 128 bit，写成 32 个小写十六进制字符。
- journal.json：单行 JSON，键按下列顺序、无多余空白：`{"schema":1,"state":"verifying","C":"1.1.0","N":"1.2.0","nonce":"<32 hex>","pid":1234,"created":"133414560000000000","backup_ready":true,"restore_step":"none","open_attempts":0}`。state ∈ `pending`、`verifying`、`committed`、`rolling-back`、`rolled-back`（idle 即文件不存在）；pid 为 JSON 整数（未登记为 0）；created 为进程创建时间 FILETIME 的 u64 十进制字符串（未登记为 "0"，避免 JSON 数值精度损失）；restore_step ∈ `none`、`moved-failed`、`restored`；open_attempts 为 0～255 的整数。解析失败、schema≠1、缺键或出现未知键视为 journal 损坏：不改任何文件，进入救援对话框。
- manifest.txt：首行 `fml-db-backup 1`，其后每个文件一行 `<字节数十进制>\t<SHA-256 小写 hex>\t<相对备份根的路径，分隔符 />`，按路径的 UTF-8 字节序升序，每行以 LF 结尾，不列 manifest 自身。备份回读与恢复都按它逐文件核验大小与哈希。
- 原子写：任何控制文件写同目录 `<name>.tmp` → FlushFileBuffers → 关闭句柄 → MoveFileExW(MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)；写失败不推进状态。journal 是恢复依据，不能把多个 rename 声称为跨文件事务。
- 普通模式（无参数或用户参数）：按下表推进；用户参数原样透传给应用，verifying 与 committed 期间追加 `--update-nonce <nonce>`。
- `--install-after-exit <installer> --version <N> --pid <u32> --created <u64 FILETIME>`：打开 SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION 句柄并核验创建时间后，创建命名管道 `\\.\pipe\BubeiGongshi.Launcher.<pid 十进制>`（PIPE_ACCESS_OUTBOUND | FILE_FLAG_FIRST_PIPE_INSTANCE、PIPE_REJECT_REMOTE_CLIENTS，DACL 只允许当前用户 SID），接受一个连接后写入 6 字节 ASCII `armed\n` 并关闭；10 s 内无连接则退出 1、不安装。客户端（WIN-03）须在 10 s 内连接，以 GetNamedPipeServerProcessId 核验服务端是自己启动的启动器 PID，只接受恰好 `armed\n`。随后最多等待 30 s 至句柄结束且 SingleInstance 不存在，再启动 `<installer> /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /UPDATE=1` 并等待其退出：退出码 0 且 `app-<N>\bubeigongshi_app.exe` 存在 → 按 `--register-install` 规则登记 pending=N，不自动启动应用（下次用户启动时验证）；非零或文件缺失 → current/pending 不变，写 update-failed.txt 并弹原生 MessageBoxW“更新未完成（代码 <x>），仍使用 <C>”。不阻塞 UI 线程、不仅按 PID 轮询。
- `--register-install <V>`（只供 WIN-02 普通模式调用）：10 s 内取得 Launcher mutex，否则退出 1；无 current.txt → 原子写 current=V；current=V → 无操作；journal 为 verifying 或 rolling-back → 退出 1、不改文件；其余情况原子写 pending=V（committed 尚未 opened 时同样允许，旧备份在新备份核验后才删除）。成功退出 0。
- `--confirm-healthy <nonce> --version <N>`：只在 journal.state=verifying、N/nonce 匹配且登记的 pid/created 仍存活时原子写 healthy.json；不取得 Launcher mutex、不改 journal；否则退出 1。普通启动不能用此分支切换版本。
- `--confirm-opened <nonce> --version <N>`：journal.state ∈ verifying、committed 且 N/nonce 匹配时原子写 opened.json，表示档案已打开（含 CORE-13 迁移成功）；同样不取得 mutex、不改 journal；否则退出 1。
- 互斥：普通/安装/登记/恢复模式从入口到完成持有 `Local\BubeiGongshi.Launcher` mutex；拿不到时只按 WIN-06 的 WM_COPYDATA 格式激活现有窗口，没有窗口则提示“正在安装或恢复，请稍后”，不碰文件、不启动第二个验证进程。进入 pending → verifying 前以 OpenMutexW(SYNCHRONIZE) 检查 `Local\BubeiGongshi.SingleInstance`：存在则只激活、不开始验证。应用返回码 10 只表示转发：N 以 10 退出时把 journal 原子改回 pending（backup_ready=false、pid=0、created="0"），删除本轮备份与 healthy/opened，不恢复数据库，下次无实例运行时重新验证。

| 状态转换 | 先决条件与持久化动作 | 失败/重启规则 |
| --- | --- | --- |
| idle → pending | `--register-install` 或安装模式已写 pending=N（current=C、app-N 存在）；普通启动写 journal（state=pending） | 无 pending 时启动 current 后退出；有运行实例只激活、不开始验证 |
| pending → verifying | SingleInstance 不存在；复制数据库到 db-backup-<C>.tmp，写 manifest 并回读核验后 rename 为 db-backup-<C>，再删除上一轮遗留备份；journal.backup_ready=true；删旧 healthy/opened，写新 nonce；CreateProcess N 透传 --update-nonce；登记 pid/created 并写 state=verifying | 备份不完整删除 .tmp 并启动 C；重启读取 journal，不覆盖有效备份 |
| verifying → committed | 500 ms 轮询，120 s 内出现匹配 healthy 且目标仍存活；原子 current=N、删 pending，再写 state=committed（open_attempts=0） | current=N 而 journal 未提交时按匹配 nonce 补提交；不重复验证 |
| committed → idle | 匹配本轮的 opened.json 已存在（提交时或后续启动时检查） | 删备份、journal、healthy/opened 与多余 app 目录；清理失败记日志、下次重试 |
| committed（未 opened） | 启动时 open_attempts+1 并原子写回，再以同一 nonce 启动 N；超过 3 次时弹原生对话框 [继续尝试]（open_attempts 归 0）/[恢复到 <C> 与更新前数据]（转 rolling-back）/[退出]，阈值见 README §6 Q36（待确认） | 期间保留 app-<C> 与备份；选择恢复同样要求 SingleInstance 不存在 |
| verifying → rolling-back | N 非 10 退出，或 120 s 超时且无匹配 healthy；超时时 TerminateProcess 后 WaitForSingleObject 直到句柄结束，未结束绝不动数据库；写 state=rolling-back、restore_step=none | 见下一行 |
| rolling-back → rolled-back → idle | none：把现库各项移到 database.failed-<N> 与 packs\pack_meta.failed-<N>\ → moved-failed：删除残留 .restoring 后从备份复制到 database.restoring 与 packs\pack_meta.restoring\，按 manifest 核验后 rename 就位 → restored：原子 current=C、删 pending、写 rolled-back.txt=N 与 state=rolled-back，启动 C；之后删 journal、healthy/opened 与已用备份 | 每步按项幂等，重启按 restore_step 与目录存在判定续做；failed-<N> 库保留到下一轮更新进入 idle |

- verifying 状态重启：先核验 pid/created，若旧 N 仍活着则继续同 nonce 验证，不能重开；否则恢复备份。创建 N 后尚未来得及写 PID 的崩溃窗口，必须先检查 SingleInstance；存在时只提示关闭后恢复，不能凭缺 PID 改库。
- rename/替换遇共享冲突重试 5 次、间隔 200 ms；耗尽保留 app-C、journal、备份和失败库，不在未恢复或部分迁移的库上启动 C。恢复失败或 journal 损坏显示独立原生救援对话框（重试、打开日志/数据目录、退出）；旧程序只有恢复并核验成功才能启动。程序不删除唯一有效备份。
- 错误复用 CORE-04 的 PLATFORM_IO / PLATFORM_UPDATE_ROLLED_BACK，不记录内容/密钥；CLI 失败退出码 1，转发为 10，成功为 0。本卡不新增公共错误码。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

**实现约束**
- 持久化顺序按上述表，文件/进程/管道调用封装可注入；所有等待在启动器进程执行。无常驻服务、无网络访问。
- 备份/回滚只允许写文档指定目录，路径正规化拒绝重解析点逃逸；写者退出之前禁止复制与恢复。备份保留到 opened 后的 committed → idle 清理或恢复核验完成；committed 期间保留 app-<C>。
- 首帧健康只表示壳与路由可呈现；opened 只表示档案打开（含迁移）成功；二者都不代表同步成功。后续同步、账户失败由对应模块报告，不自动回滚用户已打开的档案；整库恢复后由同步客户端按 ADR-V5-33 更换设备身份，本卡不改库内容。

**验收标准**：测试方案全文见 [Test/win/S7_WIN-16_TEST.md](../Test/win/S7_WIN-16_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 420 行；`installer/windows/launcher/`（独立 C++/CMake 构建单元；状态机约 310 行，文件/进程/管道适配约 110 行；不含 CTest 故障夹具约 80 行；超过预算先再拆卡）。

