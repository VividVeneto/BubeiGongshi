### WIN-17 Windows主机集成测试基础设施

**目标**：在Flutter进程之外驱动Windows系统界面、进程重启与窗口集成验收。

**范围**
- 包含：Python pywinauto UIA后端驱动、进程/窗口控制、证据收集与自包含fixture。
- 不包含：WIN-13性能判定、WIN-16更新恢复算法或晚期业务功能实现。

**依赖**：CORE-01、CORE-02、CORE-04、WIN-01

**接口契约**
python tools/windows/host_tests/run.py --exe <absolute-path> --case <id> --out <dir> [--timeout-seconds 120]；0通过/1断言失败/2工具或参数错误/3环境或场景pending。cases.json固定version=1、每项{id,owner,stage,driver,fixture,timeout_seconds}，ID唯一；框架先实现window/restart/dialog/tray自测，业务卡单独登记场景，不反向依赖晚期卡。
pywinauto使用backend=uia，按automation_id/control_type/name定位；Win32窗口/进程控制仅针对本次启动PID及已验证子PID，禁止按模糊进程名杀其他实例。等待窗口/JSON握手有总超时，保存PID句柄后终止并等待真正退出；主机保持存活并重启fixture，断言恢复结果。Profile允许integration_test内部脚本，Release只用外部UIA/日志采样；UIA不可见时显式pending并记录M0探针，不用固定坐标充通过。测试入口编译期隔离，正式Release不能暴露fixture指令。
result.json固定{version:1,case_id,owner,status:pass|fail|pending,device:{os_build,session,dpi},app_sha256,steps:[{name,status,elapsed_ms}],reason?,artifacts:[relative_path]}。保存UIA树、窗口截图、日志与状态JSON。取消/超时结束本次子进程并finally恢复本次修改的窗口/DPI测试设置和测试注册表根；不改变真实用户档案，失败证据保留，清理失败单列。
CI windows-host-fixture作业定义写入 .github/workflows/ci.yml（该文件单写维护者为 CORE-41，登记于 contracts/policies/shared-writes.json 的 kind=file 条目，措辞参照 CORE-44 的 ohos-smoke 片段），本卡只交付 tools/windows/host_tests/run.py、build_fixture.py 与可调用的 YAML 步骤片段，不直接编辑该文件，作业注册待 CORE-41 追加；该作业在有交互桌面的专用Windows runner运行，锁屏/Session0/无桌面/工具缺失退出3并归档pending；无交互的普通CI只验收schema/命令/fixture注册，不能冒称UIA通过。S7由WIN-18汇总，发布门禁不接受pending（下游说明，非契约）。

自包含制品：tools/windows/host_tests/build_fixture.py用锁定Flutter生成fixture_app/标准windows模板，项目名host_fixture，入口lib/main.dart，flutter build windows --debug --target lib/main.dart，产物build/windows/x64/runner/Debug/host_fixture.exe连同data/flutter DLL目录整体保留；fixture-artifact.json={version:1,exe,sha256,target:"host-fixture"}。run.py增加--artifact参数并验证--exe绝对路径/哈希及target，拒绝生产exe当fixture；不依赖产品启动器或晚期业务。main(List<String> args)只接受--host-run=<UUID>、--host-case=<注册case>、--host-root=<本次out/fixture绝对目录>，模板runner原样传参。构建脚本记录模板生成清单与工具版本；生产app目标不含此main和参数处理。

fixture握手version=1，JSON UTF-8无BOM、未知键拒绝，run_id为主机新UUID小写连字符，case_id来自cases.json，boot为本run持久化的0起启动次数。ready.json={version,run_id,case_id,boot,pid,state:"ready"}在首帧后原子改名写入；probe.json={version,run_id,case_id,boot,phase,assertions:[{id,pass:bool}],state:{}}仅含合成状态，phase为before/after/done。主机按run/case/boot精确核对，拒绝旧run/重复倒退boot、缺字段/超时或不匹配pid；fixture probe不是最终pass，最终result.json由主机结合外部操作与probe断言生成。每次run独占根，重启沿用run根且boot加1，新run不复用旧ready/probe，取消保留失败证据。

Windows ready/probe在--host-root/<run_id>/，主机仅读取该已解析绝对根下文件，原子改名完成前不读；传输为本机文件而非UIA控件文字。启动使用argv，case/run校验不通过退出2；专用runner有交互桌面才执行UIA，窗口PID必须等于ready.pid，重启需旧PID已退出且boot递增；其他同名进程和旧run文件不得满足握手。Release业务验收只收其独立登记的外部日志/trace，不把debug fixture证据替代生产Release性能。

**实现约束**
- 外部前提：Python、pywinauto、comtypes 的精确版本登记在新建的 `tools/windows/requirements.txt`，该文件由本卡唯一维护，每行只写 `包名==精确版本`；不并入 CORE-01 的 `tools/requirements.txt`（避免非 Windows 的 CI 环境安装 pywinauto/comtypes）。三项版本的取值由本卡编码时按 ADR-V5-15 到各官方发布页查询后回填，来源 URL 与查询日期记入 ADR-V5-15 的查询记录与 PR 证据，文档阶段不写版本号。WIN-01 的 `app/windows/toolchain.versions` 只锁 msvc/windows_sdk/cmake/inno，不含这三项，本卡不改该文件。M0验证UIA与锁定Flutter的可访问性树。甲方提供1809/11交互桌面、双DPI及笔设备，缺失仍pending。
- 主包tools/windows/host_tests/，参数数组启动；路径校验后仅清理专用fixture根，不碰其他进程与用户目录。

**验收标准**：测试方案全文见 [Test/win/S2_WIN-17_TEST.md](../Test/win/S2_WIN-17_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 660 行；主包 `tools/windows/host_tests/`（`run.py`、`build_fixture.py` 与 `fixture_app/`，约 660 行），附属数据 `tools/windows/requirements.txt`（依赖锁文件为数据，不计行数）。组件估算：UIA/进程/窗口驱动与等待约 175 行，注册/握手/隔离/取消/证据约 240 行，fixture Dart与模板runner补丁约 175 行，模板构建/制品验证与自检入口约 70 行（.github/workflows/ci.yml 的作业定义归 CORE-41，不计入本卡）。分阶段：① 主机驱动约 415 行；② fixture与构建约 245 行；各阶段以替身隔离后续能力，分别可构建、验收与提交，未交付阶段不声明通过。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。本卡交付的主机/fixture基础设施实现计入规模，其自身验证测试不计。
