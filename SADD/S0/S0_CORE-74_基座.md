### CORE-74 unsafe、ABI与错误注册表门禁

**目标**：检查unsafe边界、公开头文件兼容和生成错误码漂移。

**范围**
- 包含：从CORE-41拆出的UNSAFE-1/2、ABI-1、ERR-1～4及其测试；配置与环境错误经CORE-69的GATE-1通道上报（不另建退出2格式）。
- 不包含：词法共用层（CORE-69）、CI编排。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-69

**接口契约**
只导入CORE-69的 `Finding`、`GateError`、`emit`、`run`、`Token`、`tokens`、`scan_tree` 与 `LANGUAGE_BY_SUFFIX`（0/1/2退出码同此），不复制common类型、不另写词法器；rule取 `UNSAFE-1`、`UNSAFE-2`、`ABI-1`、`ERR-1`～`ERR-3`，配置或环境错误一律走GATE-1（stderr单行、退出2）。扫描语言与后缀口径全部来自CORE-69，本卡不另建映射，也不猜语言。

`check_unsafe.py --root .`：UNSAFE-1是unsafe白名单——只允许fml-ffi、fml-imgproc、fml-recognize-local，其他crate出现 `unsafe` 块、`unsafe fn`、`unsafe impl`、`unsafe extern` 或其他unsafe修饰报1。白名单的唯一规范源是CORE-01:133，本卡脚本持同一三名常量镜像、不读SADD；CORE-01增删该名单时由其所有者按README §8.4同批修订本卡常量与测试夹具（夹具断言恰好这三名，缺一或多一即测试失败）。UNSAFE-2是注释门禁——每处unsafe的起始行前3行内须有 `// SAFETY:`，缺失、注释内容为空、或去掉前缀与空白后不足8个非空白字符或不含字母报1。

`check_abi.py --header contracts/include/fmlcore.h [--base-ref <tag>] [--first-release]`：解析CORE-03固定C子集的函数名/参数类型文本/返回类型文本/struct字段名与类型文本顺序/`#define` 宏及 `FML_ABI_MAJOR`、`FML_ABI_MINOR`；只比较字段顺序与类型文本，不计算sizeof/offset/对齐（跨目标不可比）。基准取值顺序：显式 `--base-ref` 优先，否则自动取 `abi-v<MAJOR>.<MINOR>.<PATCH>` 标签中版本最高、且 `git merge-base --is-ancestor <tag> HEAD` 成立的一个；SADD文档标签（`sadd-v*`、`archive/*`）与其他标签不参与选择。显式 `--base-ref` 指向非 `abi-v*` 标签、ref不可解析、或不满足 `git merge-base --is-ancestor <tag> HEAD` 一律报2（基准必须是HEAD祖先，否则比较方向不确定）。基准头文本用 `git show <tag>:contracts/include/fmlcore.h` 读取（subprocess数组参数、不经shell）；git不可用、标签不存在、该文件在基准中缺失或非零退出报2。

ABI-1判定式（基准 (BMAJ,BMIN)、新头 (NMAJ,NMIN)）：
- 版本单调（任何情况）：`NMAJ < BMAJ` 报ABI-1；`NMAJ == BMAJ` 且 `NMIN < BMIN` 报ABI-1；`NMAJ > BMAJ` 时NMIN可任意取值，即MAJOR提升允许MINOR重置，此分支不受上一子句约束。
- 破坏性变化（删除函数或宏、改参数或返回类型文本、增删或重排struct字段）：要求 `NMAJ > BMAJ`，否则ABI-1。
- 纯新增（新增函数或宏、struct字段追加在末尾）：要求 `(NMAJ,NMIN)` 字典序大于 `(BMAJ,BMIN)`，否则ABI-1；只提MAJOR不动MINOR也满足。
- 无差异：不要求提升，但版本号仍受单调子句约束。

`--first-release` 只在没有任何可达 `abi-v*` 基准时合法：输出 `ABI baseline: first-release`，只做自包含baseline fixture校验并返回0，不声称历史兼容；与 `--base-ref` 同时给出、或已存在可达 `abi-v*` 标签时报2。首个基准标签命名为 `abi-v<NMAJ>.<NMIN>.0`（取当时 `fmlcore.h` 的宏值），由发布流程在首个通过ABI门禁的版本创建；标签一旦存在，发布流程须在同一变更内停用 `--first-release`，本卡只按“存在可达 `abi-v*` 即非法”判定，不代发布流程造标签。`git rev-parse --is-shallow-repository` 为true且未给 `--base-ref` 时报2并提示 `fetch-depth: 0` 或 `--first-release`；无基准、未标首发、非浅clone同样报2，不伪造比较通过。

`check_errors.py --registry contracts/errors/registry.yaml [--root .]`：ERR-1不重复CORE-02的五投影实现——脚本以数组参数子进程调用 `python tools/ci/gen_errors.py --check --registry <path>`，其0无Finding、1按ERR-1报、2按GATE-1报2（含缺PyYAML、registry或arb不可解析）；本卡只转发结果，不另写比对器，也不在依赖未交付时用本地副本兜底。ERR-2是未注册字面量：扫描 `crates/`、`server/`、`app/lib/` 下的 `.rs` 与 `.dart`，排除 `/tests/`、`/benches/`、`/examples/`、`/fixtures/`、`build/`、`contracts/`、`SADD/`、`installer/`、生成的 `*.g.dart` 与 `crates/fml-error/src/codes.rs`（五投影归ERR-1）；候选判据只来自registry自身——取registry每个code的首段（第一个 `_` 前的全大写词）组成领域前缀集合，字符串字面量整体呈全大写下划线形式、首段属于该集合、且完整code不在registry时报ERR-2；`FML_*` 宏与 `FML_THEME_MISSING` 一类资源键因首段不在集合内不报，注释与普通说明字符串不命中。ERR-3只判registry内部重复（同code多条、同message_key多码），不判生成物与registry一致性（属ERR-1），也不判owner与ownership.yaml投影不一致（同属ERR-1）。ERR-4只在registry不存在阶段核对SADD唯一定义并输出“实现注册表未启用”，退出2（不记产品门禁通过、不假过）；SADD文档侧错误码一致性（多卡重复定义、owner与shared-writes投影不符）唯一归DTOcheck的XREF-01～05，本卡不重复实现，registry按CORE-02创建且生成器 `--check` 跑通后ERR-4关闭。消费卡错误表仅三列引用/所有者/本卡处理，定义表按CORE-02四列（服务端加HTTP）。

**实现约束**
- 不维护第二前缀表（前缀与登记唯一来自CORE-02），也不维护第二份unsafe白名单（唯一源CORE-01:133，本卡只镜像三名）；ABI解析只支持公共头所用语法；版本主变更仍需BREAKING CHANGE及ADR。
- 逐组件实现估算：unsafe70、ABI180、errors150、公共入口接入25（各脚本main、参数解析与退出码收敛），合计425；正反例测试与夹具不计，词法层复用CORE-69且不重复计。
- 与CORE-41的单写边界：`tools/ci/manifest.json` 的三个步骤行与 `.github/workflows/ci.yml` 的ABI作业行属CORE-41单写文件，本卡只提交片段（步骤id/owner/argv、`fetch-depth: 0`），由CORE-41所有者合入；`contracts/policies/shared-writes.json` 也不由本卡写，manifest作业类别与条目登记须由CORE-41按README §8.4变更单落卡，本卡不自行登记。规模只计本卡三个脚本文件内的代码，公共入口接入指各脚本的main、参数解析与退出码收敛。
- 外部前提：锁定Python/PyYAML，基准Git标签（`abi-v*` 由发布流程创建，首个基准标签的命名与创建时机见接口契约）；尚无标签时只有自包含基准fixture通过，不声称历史ABI兼容。
- Python自测：本卡测试文件为 `tools/ci/tests/test_gate74_*.py`，本地与PR证据用 `python -m unittest discover -s tools/ci/tests -p "test_gate74_*.py"`；CORE-41的 `run_all.py` 交付后以其步骤条目为唯一CI入口，本卡只提交步骤片段，CORE-41未交付前该命令记为“未接入聚合、未执行”，不得报告通过。除三个脚本与这些测试文件外不新建产品文件；`tools/ci/tests/` 与夹具不计规模。
- 消费方与同步义务：CORE-03改 `contracts/include/fmlcore.h`、改ABI宏值或调整 `FML_ABI_*` 语义时，须同批检查ABI-1判定式与 `abi-v*` 制标签时机，并把该义务写进CORE-03卡片与测试方案；此项属README §8.4契约变更单，待CORE-03所有者签认，本卡不代改其正文。CORE-41的CI ABI作业取 `fetch-depth: 0` 并原样转发本卡退出码；CORE-42的兼容矩阵引用同一 `FML_ABI_MAJOR/MINOR`（CORE-42属下游说明，非契约）；CORE-69提供词法层与GATE-1通道。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-74_TEST.md](../Test/S0/S0_CORE-74_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约425行（未超500，不分阶段）；tools/ci/check_unsafe.py、check_abi.py、check_errors.py及本卡编写的公共入口接入行（各脚本main、参数解析与退出码收敛）；不计自测、夹具、registry/schema数据、生成头文件与报告；复用CORE-69公共词法而不重复计。
