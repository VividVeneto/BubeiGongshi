# CORE-02 测试方案

> 来源卡：[S0_CORE-02_基座.md](../../S0/S0_CORE-02_基座.md)（错误码注册表与诊断模型）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R19] 单元测试：生成器对样例注册表输出确定（两次生成逐字节一致）；重复 code、未知命名空间、缺 message_key 时生成失败。
- [R19] 构造：`FmlError::new(ErrorCode::UnitOverflow)` 的 domain 为 `"unit"`、retryable 与注册表一致、diagnostics 为空、trace_id 为零值；`with_trace` 只覆盖零值；FFI 输出中出现零值 trace_id 的用例被测试拒绝。
- [R19] 漂移检查：修改 `registry.yaml` 而未重新生成时 `tools/ci/gen_errors.py --check` 失败。
- [R20] `contracts/errors/README.md` 由生成器产出，含全部错误码、级别与是否可重试。
- [R19] 往返测试：上例 JSON（用真实32位 trace_id，去掉说明文字）经 Rust 反序列化再序列化后字段语义一致；规范输出固定字段顺序、args 按键排序，再以黄金文件验证逐字节一致；Dart `FmlException.fromJson` 读出相同的 code、trace_id 与诊断数。
