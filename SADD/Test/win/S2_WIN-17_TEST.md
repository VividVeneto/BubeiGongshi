# WIN-17 测试方案

> 来源卡：[S2_WIN-17_基座.md](../../win/S2_WIN-17_基座.md)（Windows主机集成测试基础设施）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R19][R37] window/restart/dialog/tray fixture四场景输出pass和完整证据；错误automation_id/超时失败，Session0/锁屏输出pending/3，未知case退出2。
- [R19] 终止目标fixture后主机重启验证状态；同名其他进程不受影响；取消保留日志并恢复测试偏好。

- [R19] 构建fixture后由artifact定位exe/校验哈希，启动/重启boot握手成功；旧run/错误case/PID/截断JSON拒绝；生产目标无fixture参数，未知exe或缺artifact退出2。
