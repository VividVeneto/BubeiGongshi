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
CI windows-host-fixture在有交互桌面的专用Windows runner运行，锁屏/Session0/无桌面/工具缺失退出3并归档pending；无交互的普通CI只验收schema/命令/fixture注册，不能冒称UIA通过。S7由WIN-13汇总，发布门禁不接受pending（下游说明，非契约）。

自包含制品：tools/windows/host_tests/build_fixture.py用锁定Flutter生成fixture_app/标准windows模板，项目名host_fixture，入口lib/main.dart，flutter build windows --debug --target lib/main.dart，产物build/windows/x64/runner/Debug/host_fixture.exe连同data/flutter DLL目录整体保留；fixture-artifact.json={version:1,exe,sha256,target:"host-fixture"}。run.py增加--artifact参数并验证--exe绝对路径/哈希及target，拒绝生产exe当fixture；不依赖产品启动器或晚期业务。main(List<String> args)只接受--host-run=<UUID>、--host-case=<注册case>、--host-root=<本次out/fixture绝对目录>，模板runner原样传参。构建脚本记录模板生成清单与工具版本；生产app目标不含此main和参数处理。

fixture握手version=1，JSON UTF-8无BOM、未知键拒绝，run_id为主机新UUID小写连字符，case_id来自cases.json，boot为本run持久化的0起启动次数。ready.json={version,run_id,case_id,boot,pid,state:"ready"}在首帧后原子改名写入；probe.json={version,run_id,case_id,boot,phase,assertions:[{id,pass:bool}],state:{}}仅含合成状态，phase为before/after/done。主机按run/case/boot精确核对，拒绝旧run/重复倒退boot、缺字段/超时或不匹配pid；fixture probe不是最终pass，最终result.json由主机结合外部操作与probe断言生成。每次run独占根，重启沿用run根且boot加1，新run不复用旧ready/probe，取消保留失败证据。

Windows ready/probe在--host-root/<run_id>/，主机仅读取该已解析绝对根下文件，原子改名完成前不读；传输为本机文件而非UIA控件文字。启动使用argv，case/run校验不通过退出2；专用runner有交互桌面才执行UIA，窗口PID必须等于ready.pid，重启需旧PID已退出且boot递增；其他同名进程和旧run文件不得满足握手。Release业务验收只收其独立登记的外部日志/trace，不把debug fixture证据替代生产Release性能。

**实现约束**
- 外部前提：Python与pywinauto/comtypes精确版本由WIN-01锁入app/windows/toolchain.versions及平台requirements；M0验证UIA与锁定Flutter的可访问性树。甲方提供1809/11交互桌面、双DPI及笔设备，缺失仍pending。
- 主包tools/windows/host_tests/，参数数组启动；路径校验后仅清理专用fixture根，不碰其他进程与用户目录。

**验收标准**
- [R19][R37] window/restart/dialog/tray fixture四场景输出pass和完整证据；错误automation_id/超时失败，Session0/锁屏输出pending/3，未知case退出2。
- [R19] 终止目标fixture后主机重启验证状态；同名其他进程不受影响；取消保留日志并恢复测试偏好。

- [R19] 构建fixture后由artifact定位exe/校验哈希，启动/重启boot握手成功；旧run/错误case/PID/截断JSON拒绝；生产目标无fixture参数，未知exe或缺artifact退出2。

**规模**：约 460 行；主包tools/windows/host_tests/（UIA/进程130、场景/证据100、自测100），附属fixture_app/lib/main.dart（90）、模板构建/CI（40）。
