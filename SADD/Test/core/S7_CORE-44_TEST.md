# CORE-44 测试方案

> 来源卡：[S7_CORE-44_发布.md](../../core/S7_CORE-44_发布.md)（鸿蒙预留与 C 头文件消费者验证）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R02] CI 的 ohos-smoke 作业中 `build.sh --target ohos` 成功，`libfmlcore.so` 导出 `fmlcore.h` 声明的全部函数；人为引入一个只支持 Windows 的依赖后作业失败并阻止合并（manual checklist：改依赖→推送分支→记录作业失败链接与提交哈希→回退）；片段以变更单交接（本卡不改 ci.yml），作业只出现一次；片段合入校验与拒绝回退按 CORE-41 的片段交接协议（判据不在本卡重述）；`OHOS_NDK_HOME`/SDK 未就绪时作业记 pending-target 并写入 pending.json，发布阶段拒绝 pending。
- [R02] `build.sh --target host` 运行 `consumer.c` 五个步骤全部通过并打印 OK，固定非零 32hex 请求在成功响应回显；能力断言按 JSON 数组元素精确匹配 `"op":"engine.check"` 且其 `"mode"` 为 `"call"`（仅出现子串 "engine.check" 不算匹配）；未知 op 用形状合法但未登记的 `nonexistent.op`，外层与内层 error.trace_id 均与请求一致；全零 trace 被拒且两处 trace 非零一致，不能只检查错误码而漏 trace；受限提取器 `fmlx_extract_trace` 对缺失/重复/越界/大写或非 hex 的合成响应分别返回 1/3/4/2，`--self-test` 全部通过；`out.len==0` 的分配失败记该步骤失败且错误消息与“字段缺失/不合法”可区分；AddressSanitizer 不报告泄漏或越界。
- [R02] 删除 `OHOS_NDK_HOME` 后 `build.sh` 以退出码 2 结束并提示缺失的环境变量。
