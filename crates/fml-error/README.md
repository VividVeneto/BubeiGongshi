# fml-error

不背公式的公共错误模型 crate（Cargo package `fml-error`）。

## 边界

- 只承载全领域共享的错误码与错误类型；不做 I/O、不读时钟、不依赖任何其他 `fml-*` crate。
- 所有领域 crate 都可以依赖本 crate（CORE-01 依赖方向的通用例外）。
- 新增错误码先写入 `contracts/errors/registry.yaml` 再生成代码（CORE-02）。

## 线程模型

类型只做值传递：不持有锁、不启动线程、不缓存全局状态；需要跨线程共享时，`Send`/`Sync` 由使用者按需在上界声明，本 crate 不内置同步原语。

## 错误语义

- 错误值只描述失败原因与必要上下文，不携带 I/O 句柄、平台对象或时间戳；需要时间时由调用方显式传入 `now_ms`（UTC 毫秒）。
- 领域错误与控制流信号分离：取消由 `fml-ast` 的 `CancelFlag` 表示，不混进错误类型。
- 错误码、错误类型与展示文案分离；文案属于界面层，不在本 crate 定义。

## 当前状态

CORE-02 阶段1 已交付正式错误模型：

- `ErrorCode`（`src/codes.rs`，由 `tools/ci/gen_errors.py` 从 `contracts/errors/registry.yaml` 生成），带 `as_str`、`domain`、`severity`、`retryable`、`message_key`、`fix_hint`、`surface`、`is_server_output`、`http_status` 访问器，并实现 `Display`、`FromStr`、`TryFrom<&str>` 与 serde（未知码解析失败返回 `UnknownErrorCode`）。
- `FmlError`（字段顺序 `code`、`domain`、`retryable`、`trace_id`、`diagnostics`）、`Diagnostic`（可选手写位置、UTF-8 半开区间、参数表、修复建议与确认标记）、`Severity` 与 `TraceId`（32 位小写十六进制）。
- 线上格式以 `contracts/vectors/errors-v1.json` 为黄金样例，根信封为 `{"error": {...}}`；错误对象与诊断对象反序列化都拒绝未知字段，并校验 `domain`、`retryable`、`severity` 与 `recovery` 与注册表一致。
- `registry.yaml` 是错误元数据唯一真源；改码先改注册表与 `app/lib/l10n/errors_zh.arb`，再运行 `python tools/ci/gen_errors.py`。守护检查用 `--check`（0 无漂移、1 漂移、2 输入或环境错误）。

Dart 侧异常桥（`FmlException`）与其 `DiagnosticDto` 别名属 CORE-02 阶段2，由 CORE-67 生成诊断数据类之后交付；本阶段只生成 `app/lib/binding/error_codes.g.dart` 元数据。
