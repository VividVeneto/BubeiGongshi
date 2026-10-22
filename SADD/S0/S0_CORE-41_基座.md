### CORE-41 CI 门禁与可维护性度量

**目标**：把格式、静态检查、测试、依赖许可、ABI、迁移、资源包、隐私与文档追踪等检查固化为 CI 门禁，并持续度量可维护性。

**范围**
- 包含：`tools/ci/` 下的检查脚本与公共库；CI 工作流定义 `.github/workflows/ci.yml` 与 `weekly.yml`（附属，只编排脚本，不含检查逻辑）；`CODEOWNERS`。门禁阈值配置 `tools/ci/thresholds.yaml` 归 CORE-71（见下表），本卡只读取。
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

本卡CLI：`python tools/ci/run_all.py [--root .] [--manifest tools/ci/manifest.json] [--out build/ci] [--release] [--only <id>]…`。manifest固定`{version:1,steps:[{id,owner,argv,release_args?}]}`：id唯一并按数组顺序执行，owner为现行卡号，argv为字符串数组且argv[0]只取python或node（解析为锁定解释器），其余参数原样传递，不经shell拼接、不展开通配；release_args仅--release时追加；版本非1、id重复、argv[0]非法退出2。初始steps依次为reservations（CORE-75 design）、check-deps与check-privacy（CORE-69）、check-unsafe/check-abi/check-errors（CORE-74）、check-sadd（CORE-70，release_args为--release）、sadd-stats（CORE-76 stats --check与audit）、sadd-selftest（node --test tools/sadd/*.test.mjs）、dtocheck（node tools/DTOcheck/run.mjs及其自测）、core-sources（本卡）、maint-report（CORE-71）；各脚本参数以所有者卡为准，脚本尚未创建记pending-target，不记通过。每步记录{id,owner,exit,duration_ms,stdout_tail,stderr_tail}，各脚本的Finding行（path:line: RULE message）原文归档不改写；任一步退出2或出现未知退出（非0/1/2、超时、解释器缺失）则总退出2，否则任一1则1，否则0；--release时存在pending也退出1。产物build/ci/run_all.json（steps按manifest顺序，忽略时间字段后字节稳定）与build/ci/pending.json（`{version:1,items:[{card,target,reason}]}`），终端最后一行`run_all: <n> steps, <e> error, <f> fail, <p> pending`。--only只供本地复现，CI不得使用。

工具链读取：`python tools/ci/toolchain.py --root . [--format env|json]` 读 `rust-toolchain.toml`、`app/.flutter-version`、`tools/toolchain.versions`，输出 RUST_VERSION、FLUTTER_VERSION、PYTHON_VERSION、NODE_VERSION、FUZZ_NIGHTLY、CARGO_FUZZ、CARGO_DENY、CARGO_AUDIT、CARGO_LLVM_COV（env 格式供工作流写入环境）；缺文件或缺必需键退出2，不回退默认版本。`cargo_deny=`、`cargo_audit=`、`cargo_llvm_cov=` 由本卡首次使用时按 ADR-V5-15 追加到 `tools/toolchain.versions`（CORE-01 允许后续所有者首用登记），lizard 由 CORE-71 写入 `tools/requirements.txt`。

领域源码集合：`python tools/ci/core_sources.py --root . --out build/coverage/core-sources.json` 按 CORE-71 覆盖率协议用 git ls-files 生成并把排除清单写到 stderr；集合为空时写空 paths、退出0并在 pending.json 登记 core-sources 的 pending-target；非 git 仓库或 git 不可用退出2。

ci.yml：lint（cargo fmt/clippy、dart format/flutter analyze、cargo doc文档告警）→test（cargo test/llvm-cov、flutter test，上传core.lcov）→checks（core_sources.py、run_all.py与maint_report --annotations）→build（ubuntu APK/鸿蒙、Windows Flutter/CMake/CTest）→deny（cargo deny check）；needs链固定，各作业先运行toolchain.py安装锁定版本，YAML不写版本字面量与检查逻辑。ci.yml是共享文件，本卡为单写维护者（contracts/policies/shared-writes.json登记），其他卡的作业以片段提交由本卡合入；CORE-44的ohos-smoke即此类片段（下游说明，非契约）。weekly.yml（每周schedule与workflow_dispatch）归档maint_report周对比（build/maint.md与同名JSON，--previous取上周构件）、cargo audit JSON与各fuzz目标10分钟的崩溃输入目录；fuzz崩溃使作业失败并保存输入。CODEOWNERS为crates/fml-crypto/、crates/fml-sync/、contracts/各列至少两名所有者；两人评审由分支保护（required approvals=2、要求CODEOWNERS审阅、required checks为lint/test/checks/build/deny）落实，属仓库设置的manual checklist，脚本不伪称通过；无合格第二评审时PR不能合入。

**验收执行环境索引（H7）**
`tools/ci/acceptance_jobs.json` 由本卡创建为 `{version:1,rows:[]}`（容器格式与唯一键归 CORE-70），rows 每行 `{card, requirement, criterion, stage, environment, target, status}`；criterion 为卡内验收序号，environment 只取 host-rust/host-widget/android-host/windows-host/manual/content；status 为 active/pending-target。CORE-70编写清单解析及正反例，本卡只聚合运行；业务卡实现时补自己的 target（文件/作业名），CI 逐条核对，缺行失败。既不把 manual 当自动通过，也不把 pending-target 当运行成功。
- 纯算法/格式/DTO/仓储用 host-rust；Widget交互/黄金图用 host-widget，固定Linux镜像digest、SDK和字体文件哈希，禁止用待测实现生成期望值。
- 真机性能、墨迹延迟、旋转/杀进程/通知/回滚演练分别为 android-host/windows-host，由 AND-12/WIN-13 主机进程执行，Flutter进程不得负责杀死自己后继续断言。integration_test只执行进程存活期间的脚本，发布Release指标来自主机日志/trace（AND-12/WIN-13为下游说明，非契约）。
- 原卡真机/手动验收保留可追溯条款，执行责任集中到AND-12/WIN-13；人工视觉/硬件项形成带步骤、预期、设备、构建哈希、证据与执行者的checklist；未运行就是未验收（下游说明，非契约）。
- S0仅验收作业定义、清单与fixture。业务目标未创建时打印`SKIP pending <card>: <target>`并归档pending；目标存在但测试失败不得SKIP。发布作业 required_stage=S7：pending/无设备/缺凭据/无人工签字任一存在都拒绝发布。鸿蒙消费者在CORE-44实现后启用，S0不能要求其通过（下游说明，非契约）。

PRIV-2与no_platform_check_test规则及反例见CORE-69；本卡只验证检查作业调用和退出码聚合。

P2按门禁族拆为CORE-69/70/71/74；本卡依赖上述S0卡后再实现聚合器与工作流。源扫描与度量规则只在其所有者定义。逐文件估算（不含测试，2026-10-22 复核修订）：run_all与manifest/退出码聚合120、pending与发布阶段清单处理50、toolchain.py 40、core_sources.py 40、ci.yml/weekly/CODEOWNERS/manifest.json 170，合计420；不再用480行承担全部门禁。后续业务卡仍是延迟目标，不成为S0编译依赖。

checks中调用CORE-75共享写入点design校验；业务构建后按平台actual回执再校验，required-stage完整性归CORE-70清单，缺实现不当门禁通过。

覆盖率采集由test作业执行cargo llvm-cov --workspace --all-targets --lcov --output-path build/coverage/core.lcov；checks的maint_report必须传--lcov build/coverage/core.lcov --core-sources build/coverage/core-sources.json。core-sources按CORE-71协议从tracked领域源码生成，不能从LCOV已出现的文件反推集合。maint-report步骤argv固定包含这两个参数，run_all原样透传；缺输入与低覆盖都不得SKIP，主线未创建领域实现前明确pending-target，发布拒绝pending。

**实现约束**
- 主干必须始终可构建；PR 需全部 error 级门禁通过才能合并；`fml-crypto`、`fml-sync` 与 `contracts/` 的改动需两人评审。
- Python/Node与cargo-deny/cargo-audit/cargo-llvm-cov版本统一经toolchain.py读取锁文件；lizard用于PR及周报。每门禁卡提供自己的正反例，本卡用替身命令验证聚合行为。
- 工作流只调用 `tools/ci/` 脚本与官方工具，不在 YAML 中写检查逻辑，便于本地 `python tools/ci/run_all.py` 复现（`run_all.py` 依次运行全部检查并汇总退出码）。
- 提交信息遵循 Conventional Commits（带模块卡编号，如 `feat(core-19): …`）；发布使用签名标签。
- 属性测试与模糊测试发现的失败样例保存为回归用例（weekly崩溃输入构件由发现者转入对应卡的回归夹具）；模型权重不进 Git（发布产物或 LFS，并记录哈希）。
- 外部前提：GitHub Actions（或等价 CI，迁移时只替换 `.github/workflows/`）；`cargo-deny`、`cargo-audit`、`cargo-llvm-cov`、`lizard`；OpenHarmony SDK 的 Rust 目标（CORE-44）；Windows 构建机的 CMake/CTest 与 MSVC 工具集（WIN-16 启动器）；版本按 ADR-V5-15 锁定（cargo-deny/cargo-audit/cargo-llvm-cov 写 tools/toolchain.versions，lizard 写 tools/requirements.txt）；鸿蒙目标与 WIN-16 启动器工具为下游说明，非契约。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-41_TEST.md](../Test/S0/S0_CORE-41_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 420 行；主包 `tools/ci/`（run_all/manifest 聚合、pending/发布阶段、toolchain.py 与 core_sources.py，约 250 行），附属 `.github/workflows/ci.yml`、`weekly.yml` 与 `CODEOWNERS`（约 170 行，只编排）。

