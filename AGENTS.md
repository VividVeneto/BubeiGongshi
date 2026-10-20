# AGENTS.md：编码助手约定

> 本文件只是索引与速查，规则以 `SADD/` 为准；两者不一致时以 SADD 为准，并提出修订本文件。

## 项目

不背公式（BubeiGongshi）：以“不背单词”为原型、强化公式背诵的 Windows 与 Android 双平台应用（Flutter 共享界面 + Rust 核心 + 服务端），预留鸿蒙 C ABI 接口，支持手写与拍照识别公式。

## 文档位置

- `SADD/README.md`：需求基线、追踪总表（§5）、已确认与待确认事项（§6）、使用说明与就绪定义（§8）。
- `SADD/README.md` §8.6 前后端编程索引：全部模块卡按前端（Flutter/Dart：共享界面、平台层）、端侧核心（Rust）、后端（server/）、工程与发布（tools/、.github/、installer/独立C++启动器）分组，列出代码目录、阶段与工具链；开会话前先查本卡属于哪一类。
- 模块卡每卡一个文件，命名 `S编号_卡号_分组.md`（分组：基座、引擎、界面、功能、账户、扩展、平台、发布）：`SADD/S0/` 放全部 S0 阶段卡；`SADD/core/` 放其余 CORE 卡（公共契约只在 CORE 卡定义）；`SADD/and/`、`SADD/win/` 放其余 AND、WIN 卡。三个文件夹的 `00-总览.md` 是原 01/02/03 中卡片以外的部分（依赖图、§2 实施阶段、§3 模块索引）。按卡号查找文件（如 `ls SADD/*/*_CORE-05_*`），引用卡片写卡号不写路径；布局说明见 `SADD/README.md` §7。
- 测试方案（各卡“验收标准”全文）放在 `SADD/Test/`，文件夹结构同上，命名 `S编号_卡号_TEST.md`（如 `SADD/Test/core/S1_CORE-05_TEST.md`）；卡片的“验收标准”字段只留引用行。编码时按该文件逐条写自动化测试；改卡片功能时同一提交同步改测试方案，卡片改名时测试文件同步改名（DTOcheck LAYOUT-06/07 检查）。
- 文档工具项（`tools/sadd/layout.mjs`、`split.mjs`、`split-tests.mjs`、`cardiff.mjs` 与 `tools/DTOcheck/`）不属于正式代码：不归任何模块卡、不计规模、不进产品构建，改动用 `chore(sadd)` 提交，清单见 `SADD/README.md` §7.1。
- `SADD/附录A-架构决策与评审记录.md`：ADR；`SADD/附录D-编码就绪检查记录.md`：逐卡就绪结论与遗留问题。

## 每次会话的材料（README §8.1）

1. 先运行 `node tools/sadd/pack.mjs <卡号> --file <将修改的已有实现>`（可重复 --file），读目标卡全文、完整直接依赖契约与 CORE-01/02；间接依赖只收录定义了所需符号的块（按符号传递收集，只提及不定义的说明块不收录，见 report.json 的 mentionOnly），contracts/ 与附录 A 只收录相关部分（README §8.1 第5项）。
2. 附正文引用的相关契约、本卡 [Rxx] 的 README §5 行、§6 影响本卡/正文引用的 Q 行、ADR 全行与补充章节。
3. 附 contracts/ 现有文件、锁定版本与已有实现；未创建文件明确标出。以 report.json 记录字符数、保留来源与 warning。
4. 复核先运行 `node tools/sadd/cardiff.mjs <卡号>`（对比基线 0773cd3 的旧三份文档，已按引用拼回 Test/ 验收标准，忽略章节标题、卡片标记与仅规模口径差异；`--all` 列出全部变化卡）。
5. 超过 80000 字符按无损 part-N.md 分段全部读完，在附录D登记总量/分段及处理方式，不静默省略。需要新的符号或文件时重生成；工具 warning 不能替代语义复核。

只实现本卡“范围/包含”中的内容，遵守“实现约束”；不修改依赖模块的接口，确需修改时停止并留下 README §8.4 契约变更单，由所有者修订、同步消费者、重生成材料并在D复检后继续。

## 规则（README §8.4）

- 模块编号全局唯一，不重排；撤销的卡在所在文档 §3 索引下注明，编号不复用。
- 一张卡的改动集中在它“规模”中列出的目录，约 500 行以内（规模不计测试代码与测试夹具，测试仍随本卡同一提交）；超出时先拆卡再编码。
- 修改公共契约必须先修订 01 中对应的卡，并检查所有引用它的平台卡；涉及决策的改动在附录 A 新增或修订 ADR。
- 需求与验收的对应关系以 README §5 为准；新增验收标准必须标注需求编号 [Rxx]。
- 新增错误码先写入 `contracts/errors/registry.yaml` 再生成代码（CORE-02）。

## 依赖方向（CORE-01）

1. `fml-ast` 不依赖解析器、存储与 UI；`fml-type` 只依赖 `fml-ast`、`fml-units`、`fml-notation`；`fml-eval` 只依赖 `fml-ast`、`fml-type`、`fml-units`；`fml-typeset` 不直接读字体文件。解析、绑定、校验与常数解析的编排由 CORE-56 的 fml-ffi 处理层完成，ConstantValue 是 CORE-05 的纯数据类型。通用例外：所有 crate 可依赖 `fml-error`；需要取消检查的 crate 可依赖 `fml-ast` 仅为使用 `CancelFlag`。
2. 领域 crate 无 I/O（不访问网络、文件、时钟与平台 API），时间、随机数与文件内容由调用方传入。
3. `fml-store` 可依赖领域 crate，反之不可。
4. `fml-ffi` 是唯一允许出现 `extern "C"` 的 crate。
5. Dart 分层：`app/lib/ui/<feature>/` 只放 Widget、绘制与路由视图，不 import `binding/`（仅 CORE-67 生成的纯数据 `binding/dto/*.g.dart` 可只读 import）、`platform/` 或发起 HTTP；`app/lib/<feature>/` 放 ViewModel、用例、Controller、Worker 与 DTO，可持有 CoreBinding；`composition/` 构造与注入服务，平台实现只经端口调用；共享界面不得判断平台。
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
C++ / CMake（installer/windows/launcher/，WIN-16 启动器，仅 Windows）
  cmake -S installer/windows/launcher -B build/launcher
  cmake --build build/launcher --config Release
  ctest --test-dir build/launcher -C Release --output-on-failure
```

为验收标准中的每一条写出自动化测试；无法自动化的手动步骤写成 checklist 放在 PR 描述中。工具链版本见 `rust-toolchain.toml`、`app/.flutter-version` 与各 `toolchain.versions`（ADR-V5-15）。

## 会话流程与提交前全量检查

1. 查 README §8.6 主类，确认 D.10 当前等级与 D.12 整卡复核：仅 A/B 且复核通过的卡开编码会话；C 或未通过先修文档。按 §8.1 生成材料，使用 §8.2 模板；未创建文件、全部 warning 与超量不能当通过。
2. 按卡实现并逐条对照验收。材料缺符号或需改依赖接口时，按 §8.4 留契约变更单（目标卡/符号、旧新签名、理由、消费者、迁移风险、验收），由所有者修订、同步消费者、重生成材料并在 D 复检后继续。
3. 运行本主类检查与下面全量检查；未实现的脚本或缺工具链记录未执行/阻断，禁止报告通过。CORE-41 交付后 `python tools/ci/run_all.py` 为最终聚合入口，manual/content/pending 不能作为自动通过。
4. 将手动 checklist、证据、外部前提与未通过项写入 PR 描述；按本文件提交格式提交。一卡一提交，特性分支不超过 3 天，main 始终可构建。SADD 专项修订按其任务书分组提交，不能把该例外推广到业务编码。

领域 crate 使用 `#![forbid(unsafe_code)]`；仅 `fml-ffi`、`fml-imgproc`、`fml-recognize-local` 允许受审计 unsafe，每块按 CORE-74 要求写非空 `// SAFETY:`。Rust 公共项 `#![deny(missing_docs)]`，Dart 启用 `public_member_api_docs`；各 crate/特性 README、示例与错误条件按 CORE-01。

提交前（所涉工具链均锁版后）还须运行：

```text
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
cargo deny check
cargo llvm-cov --workspace --all-targets --lcov --output-path build/coverage/core.lcov
python tools/ci/maint_report.py --root . --out build/maint.md --lcov build/coverage/core.lcov --core-sources build/coverage/core-sources.json
python tools/ci/run_all.py
node --test tools/sadd/pack.test.mjs tools/sadd/current.test.mjs tools/sadd/reservations.test.mjs
node tools/sadd/stats.mjs --check
node tools/DTOcheck/run.mjs          # SADD/契约一致性（卡↔索引↔依赖图、DTO manifest/schema/示例、错误码登记）；改文档或 contracts/ 时必跑，无需工具链
node --test tools/DTOcheck/*.test.mjs
```

PowerShell 对第一条用 `$env:RUSTDOCFLAGS='-D warnings'` 后运行 cargo doc。core-sources.json由CORE-41按CORE-71的tracked领域源码集合协议生成；覆盖率阈值与延迟目标按 CORE-41/71，不能以命令退出 0 代替阈值检查。Flutter SDK 唯一来源是 `app/.flutter-version`，Dart 随该 SDK；NDK/AGP/MSVC/CMake 等分别读平台 `toolchain.versions`，不重复指定 Flutter 版本。锁文件尚未创建时，按 CORE-01 开工规则建立并回填 ADR-V5-15，不能临时猜版本。
