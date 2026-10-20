# AND-15 测试方案

> 来源卡：[S2_AND-15_基座.md](../../and/S2_AND-15_基座.md)（Android主机集成测试基础设施）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R19][R38] fixture执行lifecycle/picker/notification/rotation均产出pass与必需证据；每场景故意错误控件/超时/取消得到fail，设备缺失得到pending/3。
- [R19] 杀死fixture后主机仍存活并验证重启状态；trim/旋转后恢复原设置，两个并行serial输出不混写；未知case退出2。

- [R19] build_fixture产物哈希/包名/组件可校验；新run与重启boot握手均成功；旧run/错误case/PID/截断JSON被拒绝；run-as不可用为pending，fixture未生成退出2；生产APK不能替代fixture。
