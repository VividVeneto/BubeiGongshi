### AND-15 Android主机集成测试基础设施

**目标**：让外部主机驱动进程死亡、旋转、内存回收、系统选择器与通知验收，提供可复用证据协议。

**范围**
- 包含：Python adb驱动、UiAutomator hierarchy选择、场景协议、自包含fixture APK与框架自测。
- 不包含：AND-12的S7性能预算和业务恢复场景；不在测试框架实现公式/学习逻辑。

**依赖**：CORE-01、CORE-02、CORE-04、AND-01

**接口契约**
python tools/android/host_tests/run.py --serial <adb-id> --apk <file> --case <id> --out <dir> [--timeout-seconds 120]；退出0通过/1断言失败/2输入或工具错误/3环境或场景pending。case从cases.json注册：{version:1,cases:[{id,owner,stage,driver,fixture,timeout_seconds}]}；id为lifecycle/picker/notification/rotation/trim_memory及业务卡前缀追加项，唯一；框架不依赖晚期业务卡才能自测。
主机步骤：adb get-state校验目标唯一→安装指定APK→am start指定fixture入口→等待ready JSON→操作→收集证据。kill使用am kill并先退后台，force-stop单独场景记录差异，不以force-stop模拟系统回收；旋转保存accelerometer_rotation/user_rotation，trim用am send-trim-memory；选择器/系统通知用adb shell uiautomator dump导出XML，以resource-id/text/可访问描述定位，缺控件失败，禁止固定像素点击。Flutter存活阶段integration_test或fixture只写结果JSON，主机杀死后由主机重启/断言，不要求被杀进程继续测试。
out/result.json固定{version:1,case_id,owner,status:pass|fail|pending,device:{serial,api,build},app_sha256,steps:[{name,status,elapsed_ms}],reason?,artifacts:[relative_path]}；日志、hierarchy XML、截图、重启前后JSON均归本次out，不采集真实用户数据。每步受总超时控制；Ctrl+C/超时结束子进程，finally恢复旋转/权限等已改设置、移除测试夹具；失败证据保留，清理失败单列，不掩盖原失败。设备缺失/锁屏/测试APK不匹配标pending退出3，发布CI将3视为失败。
CI android-host-fixture作业使用锁定platform-tools与专用模拟器跑fixture四类自检；真机/OEM/性能由AND-12在S7汇总，未装业务场景登记pending。CORE-70 acceptance_jobs将S2框架自测和S7业务验收分开，外部设备未到不伪称通过（下游说明，非契约）。

自包含制品：tools/android/host_tests/build_fixture.py在本卡fixture_app/使用锁定Flutter生成标准Android模板（生成代码列清单，不手写计入预算），项目名host_fixture、org=org.bubeigongshi，applicationId=org.bubeigongshi.host_fixture，组件org.bubeigongshi.host_fixture/.MainActivity。入口fixture_app/lib/main.dart；flutter build apk --debug --target lib/main.dart生成build/app/outputs/flutter-apk/app-debug.apk；build_fixture.py输出fixture-artifact.json={version:1,package,component,apk,sha256,target:"host-fixture"}，run.py增加--artifact参数，验证--apk哈希一致且仅安装这个专用debug包，禁止将生产包当fixture。Gradle/Activity模板补丁由本卡最多20行，Activity的fixture专用MethodChannel返回filesDir与已校验Intent extras fml_run_id/fml_case_id；Dart只消费该测试通道，业务进程不暴露它。

fixture握手version=1，JSON UTF-8无BOM、未知键拒绝，run_id为主机新UUID小写连字符，case_id来自cases.json，boot为本run持久化的0起启动次数。ready.json={version,run_id,case_id,boot,pid,state:"ready"}在首帧后原子改名写入；probe.json={version,run_id,case_id,boot,phase,assertions:[{id,pass:bool}],state:{}}仅含合成状态，phase为before/after/done。主机按run/case/boot精确核对，拒绝旧run/重复倒退boot、缺字段/超时或不匹配pid；fixture probe不是最终pass，最终result.json由主机结合外部操作与probe断言生成。每次run独占根，重启沿用run根且boot加1，新run不复用旧ready/probe，取消保留失败证据。

Android路径为filesDir/host-fixture/<run_id>/{ready,probe}.json，主机am start -n <component> --es fml_run_id <UUID> --es fml_case_id <注册case>，通过adb exec-out run-as <package> cat files/host-fixture/<run_id>/ready.json或probe.json读取，不访问真实应用目录。参数均白名单校验并以argv传递；run-as不可用为环境pending/3，读到畸形/旧run为断言fail/1。模板fake picker/notify/lifecycle由fixture目标自包含，不依赖晚期业务类；业务APK与S7场景另登记其测试入口、结果传输和证据，缺目标为pending，不能借fixture通过宣称生产Release已验证。

**实现约束**
- 外部前提：Python/SDK读CORE-01及AND-01锁文件；甲方提供OEM/无GMS/平板真机。锁定Flutter语义树、UiAutomator可见性须M0探针；不可见时使用明确的fixture结果文件，不猜坐标。
- 主包tools/android/host_tests/，附属fixture仅假端口/无个人数据；所有命令用参数数组，不拼shell输入。

**验收标准**：测试方案全文见 [Test/and/S2_AND-15_TEST.md](../Test/and/S2_AND-15_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 655 行；。组件估算：adb/UiAutomator驱动与受控操作约 160 行，握手/注册/超时/取消恢复/证据约 245 行，fixture应用与测试桥约 180 行，模板构建/制品哈希/CI编排约 70 行。分阶段：① 主机协议与驱动约 405 行；② fixture与构建封装约 250 行；各阶段以替身隔离后续能力，分别可构建、验收与提交，未交付阶段不声明通过。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。本卡交付的主机/fixture基础设施实现计入规模，其自身验证测试不计。
