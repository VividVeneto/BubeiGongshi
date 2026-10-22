### CORE-41 CI 门禁与可维护性度量

**目标**：把格式、静态检查、测试、依赖许可、ABI、迁移、资源包、隐私与文档追踪等检查固化为 CI 门禁，并持续度量可维护性。

**范围**
- 包含：`tools/ci/` 下的检查脚本与公共库；CI 工作流定义 `.github/workflows/ci.yml` 与 `weekly.yml`（附属，只编排脚本，不含检查逻辑）；`CODEOWNERS`。门禁阈值配置 `tools/ci/thresholds.yaml` 归 CORE-71（见下表），本卡只读取。本卡对 `tools/sadd/` 与 `tools/DTOcheck/` 只编排其既有入口：这些工具按 README §7.1 属文档工具项，不归本卡、不计本卡规模、不做整卡复核，改动由维护者按 `chore(sadd)` 提交。
- 不包含：发布打包与签名（CORE-42 与平台卡）；性能基准的测量程序本身（AND-12、WIN-13 与各卡测试）；鸿蒙冒烟工程（CORE-44，本卡只编排其编译任务）（下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-69、CORE-70、CORE-71、CORE-74、CORE-57、CORE-75、CORE-76

**接口契约**

门禁实现归属（本卡只编排，不重复实现）：

| 所有者 | 唯一实现与规则 | 规模 |
| --- | --- | --- |
| CORE-69 | common/source_scan/check_deps/check_privacy，DEP/PRIV | 见该卡 |
| CORE-74 | check_unsafe/check_abi/check_errors，UNSAFE/ABI/ERR | 见该卡 |
| CORE-70 | SADD-1～12、acceptance_jobs与D统计校验 | 见该卡 |
| CORE-71 | maint_report与thresholds，复杂度/LCOV覆盖率门禁及annotation | 见该卡 |
| CORE-57 | pack材料选择与契约收集 | 见该卡 |
| CORE-76 | current/stats/audit评级与独立证据核对 | 见该卡 |

本卡CLI：`python tools/ci/run_all.py [--root .] [--manifest tools/ci/manifest.json] [--out build/ci] [--release] [--only <id>]… [--step-timeout <秒>]`。manifest固定`{version:1,steps:[{id,owner,kind?,target?,argv,release_args?}]}`：id唯一并按数组顺序执行；`owner`为现行卡号；`kind`取`card`（默认，卡片自有的门禁规则）或`docs-tool`（README §7.1 文档工具项，`owner`必须写`SADD`，只编排、不计任何卡规模、不做整卡复核）；`target`可省略，省略时按“步骤目标存在性”段推定；`argv`为字符串数组且`argv[0]`只取python或node（解析为锁定解释器），其余参数原样传递，不经shell拼接、不展开通配（`*`、`?`、`{a,b}`、`[a]`等一律作为字面字符传给子进程）；`release_args`仅--release时追加；版本非1、id重复、`argv[0]`非法、`kind`非法、`docs-tool`的owner不是`SADD`、`card`步骤owner为`SADD`退出2。初始steps依次为reservations（CORE-75 design）、check-deps与check-privacy（CORE-69）、check-unsafe/check-abi/check-errors（CORE-74）、check-sadd（CORE-70，release_args为--release）、sadd-stats（CORE-76，`node tools/sadd/stats.mjs --check`）、sadd-audit（CORE-76，`node tools/sadd/audit.mjs --sadd SADD --out build/sadd/audit.json`）、sadd-selftest（docs-tool，`node --test`后逐个列`tools/sadd/pack.test.mjs`、`tools/sadd/current.test.mjs`、`tools/sadd/reservations.test.mjs`、`tools/sadd/cardiff.test.mjs`）、dtocheck（docs-tool，`node tools/DTOcheck/run.mjs --strict`）、dtocheck-selftest（docs-tool，`node --test`后逐个列`tools/DTOcheck/cards.test.mjs`、`tools/DTOcheck/dto.test.mjs`、`tools/DTOcheck/layout.test.mjs`、`tools/DTOcheck/xref.test.mjs`）、core-sources（本卡）、maint-report（CORE-71），共14步；一个入口一步一条argv，不把两条命令塞进同一步、也不新增包装脚本；新增测试文件时由维护者把文件名逐条加进对应argv（manifest是数据，不计本卡规模）。各脚本参数以所有者卡为准，脚本尚未创建记pending-target，不记通过。每步记录`{id,owner,exit,duration_ms,error_kind,stdout_tail,stderr_tail}`：`exit`为子进程退出码，未正常启动或超时为null；`error_kind`取null、`timeout`或`unavailable`（解释器缺失）。各脚本的Finding行（path:line: RULE message）原文归档不改写；任一步`error_kind`非null，或`exit`不在0/1/2之内，则总退出2，否则任一1则1，否则0；--release时存在pending也退出1。产物build/ci/run_all.json（steps按manifest顺序，忽略时间字段后字节稳定）与build/ci/pending.json（`{version:1,items:[{card,target,reason}]}`），终端最后一行`run_all: <n> steps, <e> error, <f> fail, <p> pending`。--only只供本地复现，CI不得使用。

步骤目标存在性（pending-target判定）：`target`为仓库相对POSIX路径；省略时按argv推定——python步骤首参数为`-m`时取其后模块名（按`mod.replace('.', '/') + '.py'`或包目录`__init__.py`在根下查找），python步骤首参数不以`-`开头时取该文件，node步骤首参数为`--test`时取其后所有不以`-`开头的参数为文件目标（全部存在才active），其余node步骤取首参数文件。任一目标不存在该步记pending-target（reason写缺失的目标路径，多个以`,`连接），写入pending.json且不执行；目标存在但退出1记fail，不得SKIP；`--release`时存在pending退出1。存在性判定只看字面路径，不展开通配、不遍历目录。

单步超时与终止：`--step-timeout <秒>`，默认900。900 s是工程常量而非产品政策：本卡清单中最慢的`cargo llvm-cov --workspace --all-targets`与`flutter test`在GitHub免费runner上通常10～20 min量级，取15 min留出余量，同时远小于Actions单作业6 h上限与weekly的10 min fuzz目标，失败能较快回传；CI用默认值，仅本地排障可调小。超时处理：子进程在新进程组启动（POSIX新session、Windows新进程组），到期先终止整棵进程树（terminate，宽限5 s后kill），该步写入`error_kind:"timeout"`、`exit:null`、实际`duration_ms`，并保留终止前已捕获的`stdout_tail`/`stderr_tail`；按未知退出计入error使总退出2，不得写pending.json、不得记SKIP或通过；`run_all.json`完整保留该步便于归档比对。解释器缺失记`error_kind:"unavailable"`、`exit:null`，同样计error。

工具链读取：`python tools/ci/toolchain.py --root . [--format env|json]` 读 `rust-toolchain.toml`、`app/.flutter-version`、`tools/toolchain.versions`，输出 RUST_VERSION、FLUTTER_VERSION、PYTHON_VERSION、NODE_VERSION、FUZZ_NIGHTLY、CARGO_FUZZ、CARGO_DENY、CARGO_AUDIT、CARGO_LLVM_COV（env 格式供工作流写入环境）；缺文件或缺必需键退出2，不回退默认版本。`cargo_deny=` 已由 CORE-01 验收首次使用时锁入 `tools/toolchain.versions`，本卡只读取、不重选；`cargo_audit=`、`cargo_llvm_cov=` 由本卡首次使用时按 ADR-V5-15 追加（CORE-01 允许后续所有者首用登记），lizard 由 CORE-71 写入 `tools/requirements.txt`。

领域源码集合：`python tools/ci/core_sources.py --root . --out build/coverage/core-sources.json` 按 CORE-71 覆盖率协议的领域集合定义生成——CORE-01 领域 crate 表列出的13个crate逐个以字面路径调用`git ls-files -- crates/<name>/src`（不使用shell花括号、不以通配参数展开），再加`crates/fml-sync/src/merge.rs`；结果按字节序去重，排除任何路径分量`tests/fixtures`的文件与`*.g.rs`，排除清单写到 stderr。集合为空时写空 paths、退出0并在 pending.json 登记 core-sources 的 pending-target；非 git 仓库或 git 不可用退出2；分母即该集合，不因crate未创建而缩小。

ci.yml：lint（cargo fmt/clippy、dart format/flutter analyze、cargo doc文档告警）→test（cargo test/llvm-cov、flutter test，上传core.lcov）→checks（core_sources.py、run_all.py与maint_report --annotations）→build（ubuntu APK/鸿蒙、Windows Flutter/CMake/CTest）→deny（cargo deny check）；needs链固定，各作业先运行toolchain.py安装锁定版本，YAML不写版本字面量与检查逻辑。ci.yml是共享文件，本卡为单写维护者（contracts/policies/shared-writes.json登记）；他卡不直接编辑该文件，而以契约变更单提交完整作业片段（YAML job键、needs、steps、所需环境/缓存与secrets），由本卡合入。合入前置校验：job键不得与现有作业重复、needs只能引用已存在作业、作业内步骤须先经toolchain.py或显式说明免锁原因；任一不满足则不合入，按变更单回退给提交卡并在pending.json记pending-target，不得静默改名或删除对方作业。CORE-44的ohos-smoke即此类片段（下游说明，非契约）；合入后与lint/test/checks/build/deny同为required checks（仓库设置manual checklist，脚本不伪称通过）。weekly.yml（每周schedule与workflow_dispatch）归档maint_report周对比（build/maint.md与同名JSON，--previous取上周构件）、cargo audit JSON与各fuzz目标10分钟的崩溃输入目录；fuzz崩溃使作业失败并保存输入。CODEOWNERS为crates/fml-crypto/、crates/fml-sync/、contracts/各列至少两名所有者；两人评审由分支保护（required approvals=2、要求CODEOWNERS审阅、required checks为lint/test/checks/build/deny）落实，属仓库设置的manual checklist，脚本不伪称通过；无合格第二评审时PR不能合入。

**验收执行环境索引（H7）**
`tools/ci/acceptance_jobs.json` 由本卡创建为 `{version:1,rows:[]}`（容器格式与唯一键归 CORE-70），rows 每行 `{card, requirement, criterion, stage, environment, target, status}`；criterion 为卡内验收序号，environment 只取 host-rust/host-widget/android-host/windows-host/manual/content；status 为 active/pending-target。CORE-70编写清单解析及正反例，本卡只聚合运行；业务卡实现时补自己的 target（文件/作业名），CI 逐条核对，缺行失败。既不把 manual 当自动通过，也不把 pending-target 当运行成功。
- 纯算法/格式/DTO/仓储用 host-rust；Widget交互/黄金图用 host-widget，固定Linux镜像digest、SDK和字体文件哈希，禁止用待测实现生成期望值。
- 真机性能、墨迹延迟、旋转/杀进程/通知/回滚演练分别为 android-host/windows-host，由 AND-12/WIN-13 主机进程执行，Flutter进程不得负责杀死自己后继续断言。integration_test只执行进程存活期间的脚本，发布Release指标来自主机日志/trace（AND-12/WIN-13为下游说明，非契约）。
- 原卡真机/手动验收保留可追溯条款，执行责任集中到AND-12/WIN-13；人工视觉/硬件项形成带步骤、预期、设备、构建哈希、证据与执行者的checklist；未运行就是未验收（下游说明，非契约）。
- S0仅验收作业定义、清单与fixture。业务目标未创建时打印`SKIP pending <card>: <target>`并归档pending；目标存在但测试失败不得SKIP。发布作业 required_stage=S7 的判定归 CORE-70：`check_sadd.py --release` 在结构校验后固定按 S7 检查 acceptance_jobs.json（缺 stage=S7 的发布验收行、任一行 status=pending-target、active 行 target 不存在均退出1），本卡只以 release_args 追加 `--release` 并聚合退出码，不重复实现解析；无设备、缺发布凭据与人工签字属发布 checklist（manual，由发布执行人核对并归档证据），脚本不读取、不得记为通过。鸿蒙消费者在CORE-44实现后启用，S0不能要求其通过（下游说明，非契约）。

PRIV-2与no_platform_check_test规则及反例见CORE-69；本卡只验证检查作业调用和退出码聚合。

P2按门禁族拆为CORE-69/70/71/74；本卡依赖上述S0卡后再实现聚合器与工作流。源扫描与度量规则只在其所有者定义。逐文件估算（不含测试，2026-10-22 修订）：run_all（manifest解析、目标存在性、单步超时与进程树终止、退出码聚合、run_all.json/pending.json归档）145、pending与发布阶段清单处理50、toolchain.py 40、core_sources.py 40、ci.yml 120/weekly.yml 30/CODEOWNERS 20（附属合计170），合计445；`tools/ci/manifest.json`、`acceptance_jobs.json`、thresholds与锁文件为数据，不计规模；不再用480行承担全部门禁。后续业务卡仍是延迟目标，不成为S0编译依赖。

checks中调用CORE-75共享写入点design校验；业务构建后按平台actual回执再校验，required_stage 完整性、发布门禁与 `--release` 语义归 CORE-70 清单，缺实现不当门禁通过。

覆盖率采集由test作业执行cargo llvm-cov --workspace --all-targets --lcov --output-path build/coverage/core.lcov；checks的maint_report必须传--lcov build/coverage/core.lcov --core-sources build/coverage/core-sources.json。core-sources按CORE-71协议从tracked领域源码生成，不能从LCOV已出现的文件反推集合。maint-report步骤argv固定包含这两个参数，run_all原样透传；缺输入与低覆盖都不得SKIP，主线未创建领域实现前明确pending-target，发布拒绝pending。

**实现约束**
- 主干必须始终可构建；PR 需全部 error 级门禁通过才能合并；`fml-crypto`、`fml-sync` 与 `contracts/` 的改动需两人评审。
- Python/Node与cargo-deny/cargo-audit/cargo-llvm-cov版本统一经toolchain.py读取锁文件；lizard用于PR及周报。每门禁卡提供自己的正反例，本卡用替身命令验证聚合行为。
- 工作流只调用 `tools/ci/` 脚本与官方工具，不在 YAML 中写检查逻辑，便于本地 `python tools/ci/run_all.py` 复现（`run_all.py` 依次运行全部检查并汇总退出码）。
- 提交信息遵循 Conventional Commits（带模块卡编号，如 `feat(core-19): …`）；发布使用签名标签。
- 属性测试与模糊测试发现的失败样例保存为回归用例（weekly崩溃输入构件由发现者转入对应卡的回归夹具）；模型权重不进 Git（发布产物或 LFS，并记录哈希）。
- 外部前提：GitHub Actions（或等价 CI，迁移时只替换 `.github/workflows/`）；`cargo-deny`、`cargo-audit`、`cargo-llvm-cov`、`lizard`；OpenHarmony SDK 的 Rust 目标（CORE-44）；Windows 构建机的 CMake/CTest 与 MSVC 工具集（WIN-16 启动器）；版本按 ADR-V5-15 锁定（cargo-deny/cargo-audit/cargo-llvm-cov 写 tools/toolchain.versions，lizard 写 tools/requirements.txt）；鸿蒙目标与 WIN-16 启动器工具为下游说明，非契约。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-41_TEST.md](../Test/S0/S0_CORE-41_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 445 行；主包 `tools/ci/`（run_all 的 manifest 解析/目标存在性/单步超时与终止/退出码聚合、pending 与发布阶段、toolchain.py 与 core_sources.py，约 275 行），附属 `.github/workflows/ci.yml`、`weekly.yml` 与 `CODEOWNERS`（约 170 行，只编排）；manifest.json、acceptance_jobs.json 与锁文件为数据，不计。

