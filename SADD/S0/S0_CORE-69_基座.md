### CORE-69 源文件词法与依赖隐私门禁

**目标**：为源码扫描提供同一词法层，并机械执行依赖与平台隔离规则。

**范围**
- 包含：从CORE-41拆出的common.py、source_scan.py、check_deps.py与check_privacy.py及其正反例；DEP-1～6、PRIV-1/2规则与配置错误的GATE-1通道。
- 不包含：ABI/unsafe/错误注册表检查（CORE-74，下游说明，非契约）、CI编排与度量报告。

**依赖**：CORE-01、CORE-02、CORE-03

**接口契约**
`python tools/ci/check_deps.py --root .` 与 `check_privacy.py --root .`：输入Cargo.toml、Dart import/源码和CORE-01定义的四份policies（dep-allow.yaml、dep6_symbols.txt、platform-check-patterns.json、network-construction.yaml），输出Finding，终端每行写 `path:line: RULE message`（文件级问题写 `path: RULE message`）；退出码0无Finding、1有Finding、2解析/配置/工具错误。四份policy的文件缺失、未知字段、版本非1、重复键或非法行一律报2，不因白名单缺失降级为0。退出2只有一个通道：GateError被捕获后不输出任何Finding（不打印半份报告），stderr写单行 `<path>: GATE-1 <message>`（与具体文件无关的参数或环境错误把path写成 `-`），stdout留空，退出码2；GATE-1是本卡所有退出2场景的统一规则号，具体原因只写在message里，调用方（CORE-41、CORE-74）按退出码与规则号转发，不解析message文本。common.py是Finding、Token、GateError、emit、run与规则号字面量的唯一定义处（CORE-74/CORE-71只导入，不复制类型）：
```python
@dataclass(frozen=True)
class Finding:
    path: str          # 仓库相对POSIX路径
    line: int | None   # 1基行号；None为文件级
    rule: str          # 取DEP-1～6、PRIV-1/2、GATE-1、UNSAFE-1/2、ABI-1、ERR-1～3之一
    message: str       # 不含源码内容（不加行列原文）

@dataclass(frozen=True)
class Token:
    text: str          # 原文切片；string含引号，comment含注释标记
    offset: int        # 0基UTF-8字节偏移
    line: int          # 1基行号；多行token取起始行
    kind: str          # 只取 code、string、comment 三值

class GateError(Exception):   # 配置非法或输入不可解析；唯一的退出2通道
    path: str | None          # None表示与具体文件无关的参数或环境错误
    message: str
    rule: str = "GATE-1"

def emit(findings: list[Finding]) -> int: ...          # 无Finding返回0，否则1
def run(argv: list[str]) -> tuple[int, str, str]: ...   # (退出码, stdout, stderr)；数组参数、不经shell，供CORE-41原样调用
def main(cli) -> int: ...                              # 打印Finding后收敛退出码：GateError→2（stderr单行GATE-1），其余取emit结果
```
source_scan.py提供 `tokens(path, language=None) -> list[Token]`（按出现顺序）与 `scan_tree(root, suffixes) -> list[tuple[str, Token]]`（元素为仓库相对POSIX路径与Token，按路径字典序、同一文件内按出现顺序）。language取 `rust`、`dart`、`cpp`，缺省时由 `LANGUAGE_BY_SUFFIX` 按后缀判定（`.rs`→rust，`.dart`→dart，`.h`/`.hpp`/`.c`/`.cc`/`.cpp`→cpp）；`suffixes` 是后缀集合，语言同样查该表；未登记后缀由GateError报2，不猜语言。去注释/字符串内容而保留import与字符串字面量边界，支持Rust/Dart/C++注释；无法解析的输入由GateError报2，不以正则误认完整AST。

DEP-1按dep-allow.yaml逐包核对Cargo普通/build/dev/target直接路径依赖与环。包身份按 `[package].name` 判定，不靠目录名或依赖键名推断：仓库内任一 `Cargo.toml` 的 `[package].name` 等于该名即视为已实现（`crates/<域>/Cargo.toml` 与 `server/Cargo.toml` 都由这条解析）。`dep = { workspace = true }` 取键名本身作为包名（workspace 继承只影响版本与features），`alias = { path = "crates/x", package = "fml-x" }` 取 `package` 真名，alias 不能绕过。路径依赖指向仓库外目录报GATE-1（2），不静默放行；registry与git依赖不参与本表判定（仍归锁文件）。`[dependencies]`、`[dev-dependencies]`、`[build-dependencies]` 及 `[target.…]` 下的普通/dev/build 变体全部检查；本仓库直接依赖未登记在允许表→DEP-1；策略表中出现尚未实现的包名不报（CORE-01:96 允许预留）；已实现包名没有策略条目→GATE-1（2，与 CORE-01:96 的未知已实现包名属同类配置错误）；本地直接依赖图出现环→DEP-1。DEP-3是Cargo依赖图的独立方向判定：领域crate不得依赖fml-store与fml-ffi（CORE-01 规则3，以及规则4把 fml-ffi 限定在处理层的分层结论）。领域crate集合固定为CORE-01:46列出的13个包 fml-ast、fml-latex、fml-notation、fml-units、fml-type、fml-eval、fml-derive、fml-typeset、fml-export、fml-srs、fml-grade、fml-study、fml-crypto，加 fml-sync（其合并逻辑同属无I/O领域）；本卡只持这一名单的常量镜像，规范源是CORE-01:46，改名或增删须由CORE-01所有者按README §8.4同批修订本卡常量，检查器不读SADD。同一条边同时命中DEP-1与DEP-3时只报DEP-3，一条边只报一码（DEP-1负责策略条目缺失、未登记包与环）；即使该边已登记在dep-allow.yaml也报DEP-3——允许表只是上界，不覆盖CORE-01的规则2～4。fml-pack→fml-store不属DEP-3（pack不是领域crate），其允许性由DEP-1按表判定（CORE-01:124 仅限 PackCatalog 只读适配）。DEP-4只判 `extern "C"`（含 `unsafe extern "C"`、`extern "C" { … }` 块与 `extern "C" fn`）出现在 `crates/fml-ffi/src/` 之外：扫描对象是 `crates/**/*.rs`，不含 `.h`/`.hpp`/`.c`/`.cc`/`.cpp`（`contracts/include/fmlcore.h` 本身就是C边界，C++启动器 installer/ 不在本卡范围），字符串与注释内的同名文本由词法层排除。DEP-2查同一领域名单在 `crates/<域>/**/*.rs` 中的 `std::fs`、`std::net`、`std::time::SystemTime`：全限定路径与同文件 `use std::fs…`/`use std::net…`/`use std::time::SystemTime` 导入都判，`use … as` 别名按同文件别名解析；`std::time::Instant/Duration` 不判（CORE-01:124 只禁 SystemTime）。DEP-5分两段，作用域与CORE-01规则5、:91对齐。(a) `app/lib/ui/**/*.dart`（任意深度）：导入 `binding/`（只豁免CORE-67生成的 `binding/dto/*.g.dart`）、导入 `platform/`、导入HTTP包（字面量集合固定为 `package:http`、`package:dio`，`package:` 与相对写法都判），以及构造参数或字段初始化中出现 `AppDeps`、`CoreBinding`、`PlatformPorts` 标识符→DEP-5。(b) `app/lib/**/*.dart` 中除 `app/lib/composition/**` 以外的文件：读取 `PlatformPorts` 的 `http` 字段→DEP-5；判定只认能证明的接收者类型——同文件内存在 `PlatformPorts` 的类型标注（参数、字段或局部声明），或经同文件赋值链追到该标注时才报error，类型不可判定时只报warning并登记人工checklist，因此 `AppDeps.http` 一类非 PlatformPorts 字段不误报error。ui文件同时受(a)(b)约束；同一条token（同path同offset）只报一条。网络构造的豁免目录只读network-construction.yaml的allow（初始为 `app/lib/platform/{android,windows}/net/**/*.dart`，与CORE-28的no_direct_http_test同一文件；CORE-28属下游说明，非契约），不另建包名单。DEP-6按dep6_symbols.txt扫描 `app/lib/platform/**/*.dart`：`op:` 行只比对调用表达式实参中的字符串token，`type:` 行只比对类型标注与标识符token，均按词法精确相等，注释与普通说明字符串不命中；Cargo侧无可扫对象（平台层没有Cargo工程，Rust侧领域算法由DEP-2/DEP-3与代码评审管），本卡不据此另设规则。PRIV-1只准network-construction.yaml的allow构造网络对象（HttpClient/Socket）与导入网络包；与DEP-5去重精确到token：同一(path, offset)的import或构造同时命中两条时只报DEP-5，PRIV-1抑制该token；不同token（如同文件另一处构造）各自报一条，不整文件抑制。PRIV-2按platform-check-patterns.json的import alias与成员符号检测ui内的平台判断。别名或跨函数间接封装不能证明时输出warning及人工审查项，不声称静态检查保证所有路径。

**实现约束**
- Python标准库与锁定PyYAML；扫描器不用网络，不输出敏感源代码；与CORE-28的no_direct_http_test读同一白名单（CORE-28属下游说明，非契约）。
- 词法子集（tokens契约，CORE-71与CORE-74按此消费）：Token.kind只取 `code`、`string`、`comment` 三种，本卡是这三个字面量的唯一定义处，不为标识符/关键字细分；text为原文切片（string含引号，comment含注释标记）；offset为0基UTF-8字节偏移、line为1基行号，多行token的line取其起始行；源文件按UTF-8严格解码，解码失败由GateError报2（不用替换字符降级），offset在同一遍扫掠里记录字节位置，不用文本索引反推；计行只认 `\n`，`\r\n` 只增一行（`\r` 归前一行行尾），单独的 `\r` 不计行，U+2028/U+2029 不计行（与Rust/Dart词法一致，作为已知边界登记，不做归一化）；Dart的单引号一律是字符串，Rust中单引号后紧跟标识符字符且其后没有闭合单引号时判为生命周期（kind=code），否则判字符字面量（kind=string，含转义与 `\u{…}` 形式）；支持 `//`、`///`、`//!`、`/* */`、`/** */` 与Rust嵌套块注释，Dart三引号字符串与raw字符串（r前缀），Rust/C++的raw字符串（`r#"…"#`、`R"delim(…)delim"`）；字符串与注释不互相吞并（字符串内的 `//` 不是注释，注释内的引号不开启字符串）；只做词法不做语法树，括号/花括号不平衡不报错，未闭合的字符串或块注释视为不可解析报2。
- 语义依赖：CORE-02划定 `app/lib/binding/`（error_codes.g.dart、errors.dart）与错误码命名空间，DEP-5的binding豁免面以它为准；CORE-03定义 `contracts/include/fmlcore.h`、`fml_close_handle` 与 `CoreBinding`，是DEP-5的CoreBinding字面量与DEP-4的 `extern "C"` 边界对象来源；CORE-04定义 `PlatformPorts`、CORE-36定义 `AppDeps`（CORE-04、CORE-36属下游说明，非契约）。本卡不读SADD、不推断类型，只持 `AppDeps`、`CoreBinding`、`PlatformPorts` 三个字面量加领域crate名单；这些符号改名、移动或职责变化时，其所有者须按README §8.4提契约变更单，并与CORE-69同批修订本卡清单与测试夹具，不接受文档已改名而脚本未改的状态；本卡不调用其运行时代码。
- 逐组件实现估算：common（Finding/Token/GateError/emit/run）与GATE-1通道70、source_scan词法层185、check_deps（DEP-1～6）175、check_privacy（PRIV-1/2）105、规则号表与入口收敛10，合计545；fixtures与tests不计。超过约500行，按ADR-V5-52分两阶段：阶段1约270行（common与词法层，可独立构建并跑词法/Token/GATE-1测试），阶段2约275行（两个检查脚本、DEP-1～6与PRIV-1/2规则、规则号表与入口）；两阶段各自提交、各自复核。
- 入口与单写边界：本卡编写的入口调用行指 `tools/ci/check_deps.py`、`tools/ci/check_privacy.py`、`tools/ci/source_scan.py` 的 `main` 与参数解析，以及 `tools/ci/common.py` 的退出码收敛，不新建 `tools/ci/__main__.py`；`tools/ci/manifest.json` 与 `.github/workflows/ci.yml` 属 CORE-41 的单写区，本卡只提交步骤片段（步骤id/owner/argv），由 CORE-41 所有者合入。
- 外部前提：CORE-01锁定Python/PyYAML并创建policies；工具不存在前明确pending。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-69_TEST.md](../Test/S0/S0_CORE-69_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约545行，分阶段（ADR-V5-52）：阶段1约270行（common.py的Finding/Token/GateError/emit/run、GATE-1通道、source_scan.py词法层），阶段2约275行（check_deps.py、check_privacy.py、DEP-1～6与PRIV-1/2规则、规则号表与入口收敛）；tools/ci/common.py、词法辅助、check_deps.py、check_privacy.py及本卡编写的入口调用行；不计自测、夹具、规则纯数据与报告生成物。
