### CORE-69 源文件词法与依赖隐私门禁

**目标**：为源码扫描提供同一词法层，并机械执行依赖与平台隔离规则。

**范围**
- 包含：从CORE-41拆出的common.py、source_scan.py、check_deps.py与check_privacy.py及其正反例；DEP-1～6、PRIV-1/2规则。
- 不包含：ABI/unsafe/错误注册表检查（CORE-74，下游说明，非契约）、CI编排与度量报告。

**依赖**：CORE-01、CORE-02、CORE-03

**接口契约**
python tools/ci/check_deps.py --root . 与 check_privacy.py --root .：输入Cargo.toml、Dart import/源码和CORE-01定义的四份policies（dep-allow.yaml、dep6_symbols.txt、platform-check-patterns.json、network-construction.yaml），输出 Finding(path,line,rule,message)，终端为path:line: RULE message；0无违例、1有违例、2解析/配置错误。common.py提供Finding、emit(findings)、run(command)（数组参数、不经shell），source_scan.py提供tokens(path)→Token{text,line,kind}[]；去注释/字符串内容而保留import与字符串字面量边界，支持Rust/Dart/C++注释；无法解析的输入报2，不以正则误认完整AST。

DEP-1按dep-allow.yaml逐包核对Cargo普通/build/dev/target直接路径依赖与环；包alias按package真名解析，未实现的预留包不要求存在，已实现但无策略条目的包拒绝。DEP-3/4查Cargo依赖图及extern C声明；DEP-2查领域crate中的std::fs/net/time::SystemTime路径（含use别名）；DEP-5查ui/导入binding（只豁免binding/dto/*.g.dart）、platform、HTTP包，以及构造参数/字段中AppDeps/CoreBinding/PlatformPorts标识符；composition外的ports.http访问须通过词法变量绑定追踪，无法判定类型的.http仅warning并登记人工checklist，不对ctx.http误报error。DEP-6按dep6_symbols.txt扫描平台目录的领域op字面量和类型token/Cargo领域依赖；清单唯一归CORE-01，不匹配普通说明字符串。PRIV-1只准network-construction.yaml指定platform/net构造网络对象；PRIV-2按platform-check-patterns.json的import alias与成员符号检测ui平台判断。别名/跨函数间接封装不能证明时输出warning及人工审查项，不声称静态检查保证所有路径。

**实现约束**
- Python标准库与锁定PyYAML；扫描器不用网络，不输出敏感源代码；与CORE-28的no_direct_http_test读同一白名单。
- 逐组件实现估算：common/Finding65、source_scan词法层180、deps150、privacy85、附属聚合调用10，合计490；fixtures/tests不计。不实现完整Dart/Rust语义解析器，超出上述子集先报warning并申请拆卡。
- 外部前提：CORE-01锁定Python/PyYAML并创建policies；工具不存在前明确pending。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-69_TEST.md](../Test/S0/S0_CORE-69_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约490行；tools/ci/common.py、词法辅助、check_deps.py、check_privacy.py及本卡编写的聚合调用行；不计自测、夹具、规则纯数据与报告生成物。

