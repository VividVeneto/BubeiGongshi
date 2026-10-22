### CORE-69 源文件词法与依赖隐私门禁

**目标**：为源码扫描提供同一词法层，并机械执行依赖与平台隔离规则。

**范围**
- 包含：从CORE-41拆出的common.py、source_scan.py、check_deps.py与check_privacy.py及其正反例；DEP-1～6、PRIV-1/2规则。
- 不包含：ABI/unsafe/错误注册表检查（CORE-74，下游说明，非契约）、CI编排与度量报告。

**依赖**：CORE-01、CORE-02、CORE-03

**接口契约**
`python tools/ci/check_deps.py --root .` 与 `check_privacy.py --root .`：输入Cargo.toml、Dart import/源码和CORE-01定义的四份policies（dep-allow.yaml、dep6_symbols.txt、platform-check-patterns.json、network-construction.yaml），输出Finding，终端每行写 `path:line: RULE message`（文件级问题写 `path: RULE message`）；退出码0无Finding、1有Finding、2解析/配置/工具错误。四份policy的文件缺失、未知字段、版本非1、重复键或非法行一律报2，不因白名单缺失降级为0。common.py是Finding、Token、GateError、emit、run与规则号字面量的唯一定义处（CORE-74/CORE-71只导入，不复制类型）：
```python
@dataclass(frozen=True)
class Finding:
    path: str          # 仓库相对POSIX路径
    line: int | None   # 1基行号；None为文件级
    rule: str          # 取DEP-1～6、PRIV-1/2、UNSAFE-1/2、ABI-1、ERR-1～3之一
    message: str       # 不含源码内容（不加行列原文）

class Token: ...       # text/offset/line/kind，kind取值域见实现约束
class GateError(Exception):   # 配置非法或输入不可解析
    path: str | None
    message: str

def emit(findings: list[Finding]) -> int: ...          # 无Finding返回0，否则1
def run(argv: list[str]) -> tuple[int, str, str]: ...   # (退出码, stdout, stderr)；数组参数、不经shell，供CORE-41原样调用
def main(cli) -> int: ...                              # 打印Finding后收敛退出码：GateError→2，其余取emit结果
```
source_scan.py提供 `tokens(path) -> list[Token]`（按出现顺序）与 `scan_tree(root, suffixes) -> list[Token]`；去注释/字符串内容而保留import与字符串字面量边界，支持Rust/Dart/C++注释；无法解析的输入由GateError报2，不以正则误认完整AST。

DEP-1按dep-allow.yaml逐包核对Cargo普通/build/dev/target直接路径依赖与环；包alias按package真名解析，未实现的预留包不要求存在，已实现但无策略条目的包拒绝。DEP-3是Cargo依赖图的独立方向判定：领域crate不得依赖fml-store与fml-ffi（CORE-01依赖方向2/3），领域crate集合取dep-allow.yaml的crates键去掉fml-store、fml-ffi，不另持名单；同一条边同时命中DEP-1与DEP-3时只报DEP-3，一条边只报一码（DEP-1负责策略条目缺失、未登记包与环）。DEP-4只判 `extern "C"` 声明出现在fml-ffi之外。DEP-2查领域crate中的std::fs/net/time::SystemTime路径（含use别名）。DEP-5的路径前缀固定 `app/lib/ui/`，查导入 `binding/`（只豁免CORE-67生成的 `binding/dto/*.g.dart`）、`platform/` 与HTTP包；HTTP包字面量集合固定为 `package:http`、`package:dio`，网络构造的豁免目录只读network-construction.yaml的allow（初始为`app/lib/platform/{android,windows}/net/**/*.dart`，与CORE-28的no_direct_http_test同一文件），不另建包名单；构造参数/字段中出现AppDeps、CoreBinding、PlatformPorts标识符（CORE-36/CORE-04定义的类型名，按字面量清单，不由扫描器推断）报1；composition外的ports.http访问须通过词法变量绑定追踪，无法判定类型的.http仅warning并登记人工checklist，不对ctx.http误报error。DEP-6按dep6_symbols.txt扫描平台目录的领域op字面量和类型token/Cargo领域依赖；清单唯一归CORE-01，不匹配普通说明字符串。PRIV-1只准network-construction.yaml指定platform/net构造网络对象；PRIV-2按platform-check-patterns.json的import alias与成员符号检测ui平台判断。别名/跨函数间接封装不能证明时输出warning及人工审查项，不声称静态检查保证所有路径。

**实现约束**
- Python标准库与锁定PyYAML；扫描器不用网络，不输出敏感源代码；与CORE-28的no_direct_http_test读同一白名单。
- 词法子集（tokens契约，CORE-71与CORE-74按此消费）：Token.kind只取 `code`、`string`、`comment` 三种，不为标识符/关键字细分；text为原文切片（string含引号，comment含注释标记）；offset为0基字节偏移、line为1基行号，多行token的line取其起始行；支持 `//`、`///`、`//!`、`/* */`、`/** */` 与Rust嵌套块注释，Dart `'''`/`"""` 与raw `r''`/`r""` 字符串，Rust/C++ raw字符串 `r#"…"#`；字符串与注释不互相吞并（字符串内的`//`不是注释，注释内的引号不开启字符串）；只做词法不做语法树，括号/花括号不平衡不报错，未闭合的字符串或块注释视为不可解析报2。
- 语义依赖：CORE-02划定 `app/lib/binding/`（error_codes.g.dart、errors.dart）与错误码命名空间，DEP-5的binding豁免面以它为准；CORE-03定义 `contracts/include/fmlcore.h` 与 `CoreBinding`，是DEP-5的CoreBinding字面量与DEP-4的 `extern "C"` 边界对象来源；本卡不调用其运行时代码。
- 逐组件实现估算：common/Finding65、source_scan词法层180、deps150、privacy85、附属聚合调用10，合计490；fixtures/tests不计。不实现完整Dart/Rust语义解析器，超出上述子集先报warning并申请拆卡。
- 外部前提：CORE-01锁定Python/PyYAML并创建policies；工具不存在前明确pending。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-69_TEST.md](../Test/S0/S0_CORE-69_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约490行；tools/ci/common.py、词法辅助、check_deps.py、check_privacy.py及本卡编写的聚合调用行；不计自测、夹具、规则纯数据与报告生成物。
