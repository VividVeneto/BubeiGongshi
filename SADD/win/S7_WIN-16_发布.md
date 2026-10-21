### WIN-16 启动器与更新恢复

**目标**：以独立 C++ 构建单元安全选择版本、等待安装、验证首帧与档案打开，失败时恢复更新前数据库；并发启动不触发重复回滚。

**范围**
- 包含：固定路径 BubeiGongshi.exe、CMake/CTest、单启动器互斥、进程等待与命名管道确认、安装登记命令、WIN-20持久化/恢复端口编排与进程故障夹具。
- 不包含：下载/签名校验（WIN-03）；安装脚本（WIN-02）；业务迁移算法（CORE-13，下游说明，非契约）；SecureKV 迁移；整库恢复后的设备身份更换（同步客户端按 ADR-V5-33 处理）。

**依赖**：CORE-01、CORE-02、WIN-01、WIN-06、WIN-07、WIN-17、WIN-20

**接口契约**

installRoot布局、控制文件格式、原子journal与快照/恢复实现唯一归WIN-20；本卡只消费其LauncherStorage端口并拥有CLI/状态推进/进程管道与救援对话框，不重复实现文件算法。控制协议仍为launcher_protocol=1。

决策依据：ADR-V5-31（启动、安装与恢复时序，补充见附录 A §A.4.5）；整库恢复后的设备身份见 ADR-V5-33。


- 构建：`cmake -S installer/windows/launcher -B build/launcher` 后 `cmake --build build/launcher --config Release`；输出 `BubeiGongshi.exe`。只链接 Windows 系统库，不链接 Flutter/Rust/安装器；首版协议固定 launcher_protocol=1，协议升级须另立 ADR 与迁移安装器；WIN-02 用 /DLauncher 消费制品，因此不存在 WIN-02 ↔ WIN-03 循环。启动器 VERSIONINFO 的 FileVersion 在 `installer/windows/launcher/launcher_version.h` 单独维护（CORE-42 bump_version 不改它），仅启动器代码变更时递增，供 WIN-02 按版本比较替换。
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
| rolling-back → rolled-back → idle | 调用WIN-20 `restore_backup`，由其按持久化restore_step执行none→moved-failed→restored；成功后原子current=C、删pending、写rolled-back.txt=N与state=rolled-back，再启动C并清journal/healthy/opened与已用备份 | 每步磁盘恢复与目录判据唯一见WIN-20；failed-N保留到下一轮idle，失败不启动C |

- verifying 状态重启：先核验 pid/created，若旧 N 仍活着则继续同 nonce 验证，不能重开；否则恢复备份。创建 N 后尚未来得及写 PID 的崩溃窗口，必须先检查 SingleInstance；存在时只提示关闭后恢复，不能凭缺 PID 改库。
- 文件重试与唯一有效备份保护由WIN-20端口保证；端口失败或journal损坏时本卡显示独立原生救援对话框（重试、打开日志/数据目录、退出）。旧程序只有恢复并核验成功才能启动；不绕开端口直接改库。
- 错误复用 CORE-04 的 PLATFORM_IO / PLATFORM_UPDATE_ROLLED_BACK，不记录内容/密钥；CLI 失败退出码 1，转发为 10，成功为 0。本卡不新增公共错误码。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-18汇总（下游说明，非契约）。

- 控制读取/写入/删除经WIN-20 read_control/atomic_control/remove_control；read_journal的nullopt表示idle。healthy/opened由端口严格解析，本卡比较N/nonce及存活进程。转发退出10仅用discard_unmodified_backup撤回本轮备份；若现库已变化，保留证据并救援，不绕开端口删除文件。StorageFailure按const引用捕获，显示动作与本机错误码。

**实现约束**
- 持久化顺序按上述表，文件/进程/管道调用封装可注入；所有等待在启动器进程执行。无常驻服务、无网络访问。
- 备份/回滚只允许写文档指定目录，路径正规化拒绝重解析点逃逸；写者退出之前禁止复制与恢复。备份保留到 opened 后的 committed → idle 清理或恢复核验完成；committed 期间保留 app-<C>。
- 首帧健康只表示壳与路由可呈现；opened 只表示档案打开（含迁移）成功；二者都不代表同步成功。后续同步、账户失败由对应模块报告，不自动回滚用户已打开的档案；整库恢复后由同步客户端按 ADR-V5-33 更换设备身份，本卡不改库内容。

**验收标准**：测试方案全文见 [Test/win/S7_WIN-16_TEST.md](../Test/win/S7_WIN-16_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约580行；`installer/windows/launcher/`中`main.cpp`、`process.cpp`、`pipe.cpp`、`state_machine.cpp`及本卡构建接入。分阶段：① CLI/互斥/激活/进程等待/管道250行；② 状态推进、提交/重启救援/open_attempts330行；分别以可注入存储端口独立构建验收，不计WIN-20实现、数据及自身CTest。
