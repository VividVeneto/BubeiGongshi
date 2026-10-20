# CORE-35 测试方案

> 来源卡：[S5_CORE-35_扩展.md](../../core/S5_CORE-35_扩展.md)（本地识别模型后端）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R06] 编码验收：断网安装 tests/fixtures/model-fake/（项目自有固定输入与 token，无第三方权重）后，固定样本经 FakeEngine 给出预期候选，完整验证注册、预处理、解码、卸载与错误映射。真实 ≥200 条样本及 ExpRate ±2 个百分点移到附录 C M-MODEL，不作为本卡编码完成条件。
- [R06] 用 `FakeEngine`：`preprocess` 输出形状与数值与金标准一致；束搜索在 `eos` 与 `max_tokens` 处正确停止；取消后 100 ms 内返回 `RECOG_CANCELLED`。
- [R29] 主安装包中不含模型权重（构建产物文件清单检查）；未安装模型时 `recog.backends` 不含本地后端，识别入口显示“不可用”。
- [R03] FakeEngine 下验证 OOM 释放与时限分支；真实运行时性能由 M-MODEL 验收：识别时内存峰值不超过 `memory_budget_mb`；`unload_all` 后 5 s 内驻留内存回落到加载前 +20 MB 以内；单式识别与首次加载满足 CORE-01 预算表。
- [R07] 本地后端与云端后端经同一 `Registry` 注册与替换；安装新版本模型包后重新 `register` 即替换旧后端。
- [R29] `model.json` 缺许可字段、含未知字段或运行时不匹配时拒绝注册，错误码符合上表；不带 `fake-engine` feature 的构建注册 `runtime = "fake"` 的夹具包返回 `RECOG_MODEL_INCOMPATIBLE`。
- [R29] 已注册并加载的模型包执行 `pack.uninstall` 成功，之后 `recog.backends` 不再列出该后端，版本目录已删除。
