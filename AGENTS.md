# AGENTS.md：编码助手约定

> 本文件只是索引与速查，规则以 `SADD/` 为准；两者不一致时以 SADD 为准，并提出修订本文件。

## 项目

不背公式（BubeiGongshi）：以“不背单词”为原型、强化公式背诵的 Windows 与 Android 双平台应用（Flutter 共享界面 + Rust 核心 + 服务端），预留鸿蒙 C ABI 接口，支持手写与拍照识别公式。

## 文档位置

- `SADD/README.md`：需求基线、追踪总表（§5）、已确认与待确认事项（§6）、使用说明与就绪定义（§8）。
- `SADD/README.md` §8.6 前后端编程索引：全部模块卡按前端（Flutter/Dart：共享界面、平台层）、端侧核心（Rust）、后端（server/）、工程与发布（tools/、.github/）分组，列出代码目录、阶段与工具链；开会话前先查本卡属于哪一类。
- `SADD/01-公共核心-v5.md`：CORE 模块卡（公共契约只在此定义）；`SADD/02-Android端-v5.md`：AND 模块卡；`SADD/03-Windows端-v5.md`：WIN 模块卡。
- `SADD/附录A-架构决策与评审记录.md`：ADR；`SADD/附录D-编码就绪检查记录.md`：逐卡就绪结论与遗留问题。

## 每次会话的材料（README §8.1）

1. 目标模块卡全文（从 `### CORE-xx` / `### AND-xx` / `### WIN-xx` 标题到下一张卡标题之前）。
2. 该卡依赖的全部模块卡（含间接依赖）的“接口契约”段。
3. CORE-01、CORE-02 的“接口契约”段。
4. 卡片引用“README §6 Qx”时，附上 §6 对应行。

只实现本卡“范围/包含”中的内容，遵守“实现约束”；不修改依赖模块的接口，确需修改时停止并说明需要改哪张卡。

## 规则（README §8.4）

- 模块编号全局唯一，不重排；撤销的卡在所在文档 §3 索引下注明，编号不复用。
- 一张卡的改动集中在它“规模”中列出的目录，约 500 行以内；超出时先拆卡再编码。
- 修改公共契约必须先修订 01 中对应的卡，并检查所有引用它的平台卡；涉及决策的改动在附录 A 新增或修订 ADR。
- 需求与验收的对应关系以 README §5 为准；新增验收标准必须标注需求编号 [Rxx]。
- 新增错误码先写入 `contracts/errors/registry.yaml` 再生成代码（CORE-02）。

## 依赖方向（CORE-01）

1. `fml-ast` 不依赖解析器、存储与 UI；`fml-type` 只依赖 `fml-ast`、`fml-units`、`fml-notation`；`fml-eval` 只依赖 `fml-ast`、`fml-type`、`fml-units`；`fml-typeset` 不直接读字体文件。
2. 领域 crate 无 I/O（不访问网络、文件、时钟与平台 API），时间、随机数与文件内容由调用方传入。
3. `fml-store` 可依赖领域 crate，反之不可。
4. `fml-ffi` 是唯一允许出现 `extern "C"` 的 crate。
5. Dart 的 `ui/` 不得直接 import `binding/`、`platform/` 或发起 HTTP，只调用 `lib/<feature>/` 用例；共享界面中不得出现平台判断。
6. 平台层不得实现公式解析、量纲与单位换算、排版布局、FSRS 调度、同步合并、资源包验签。

## 提交约定（CORE-01）

- Conventional Commits：`<type>(<模块编号小写>): <摘要>`，如 `feat(core-05): 定义公式 AST 节点`；type 取 feat、fix、refactor、perf、test、docs、build、ci、chore。
- 契约破坏性变更在正文写 `BREAKING CHANGE:` 并引用 ADR；一个提交只涉及一张卡；main 始终可构建。

## 格式化、静态检查与测试

```text
Rust（crates/、server/）
  cargo fmt --all --check
  cargo clippy --workspace --all-targets -- -D warnings
  cargo test --workspace
Dart / Flutter（app/）
  dart format --set-exit-if-changed .
  flutter analyze
  flutter test
Python（tools/）
  python tools/ci/run_all.py        # 依次运行全部 CI 检查脚本（CORE-41）
```

为验收标准中的每一条写出自动化测试；无法自动化的手动步骤写成 checklist 放在 PR 描述中。工具链版本见 `rust-toolchain.toml` 与各 `toolchain.versions`（ADR-V5-15）。
