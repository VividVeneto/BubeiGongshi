### CORE-71 可维护性度量与阈值报告

**目标**：把文件长度、圈复杂度、unsafe与FFI数量转为可复现的报告。

**范围**
- 包含：从CORE-41拆出的maint_report.py、thresholds.yaml读取、PR annotation与每周对比。
- 不包含：测试覆盖采集命令和CI作业编排（CORE-41，下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-69

**接口契约**
python tools/ci/maint_report.py --root . --out <maint.md> [--previous <maint.json>] [--annotations] --lcov <core.lcov> --core-sources <core-sources.json>；附同名JSON，缺previous输出baseline而非零退化。读取thresholds.yaml：file_max_lines=800、fn_max_ccn=15、core_line_coverage=0.80、dart_ccn_warn_only=true。生成物/*.g.dart排除并在报告列明；Rust函数复杂度用锁定lizard，Dart用CORE-69词法token近似（只用 `Token.kind` 为 `code` 的token，注释与字符串字面量不计入）：具名函数/方法/闭包初值1，if/for/while/非default case/catch/&&/||/?:各+1，do-while只计while，else/??/?.不计；嵌套闭包单独算。f(){if(a&&b)x();}为3。未知语法输出warning+人工项，不称精确CFG。文件超800/Rust复杂度超15退出1，Dart超15只warning；配置/工具错误退出2，其他0。annotations输出GitHub path/line/rule消息，不含源代码；JSON按path/line排序、忽略时间戳后字节稳定。

覆盖率协议：core-sources.json固定{version:1,paths:[仓库相对POSIX路径]}，按字节序去重。领域集合= CORE-01 领域 crate 表列出的13个crate（fml-ast、fml-latex、fml-notation、fml-units、fml-type、fml-eval、fml-derive、fml-typeset、fml-export、fml-srs、fml-grade、fml-study、fml-crypto）的`crates/<name>/src/`下已跟踪的`.rs`文件（含src/lib.rs），加`crates/fml-sync/src/merge.rs`（CORE-26 定义的 sync 纯合并唯一位置）；CORE-41逐crate以字面路径参数调用`git ls-files -- crates/<name>/src`（不使用shell花括号、不以通配参数展开），按字节序去重，排除任何路径分量tests/fixtures的文件与`*.g.rs`并报告排除清单；分母不因crate未创建而缩小（未创建的crate贡献0个文件），13+1个路径全无文件才是空集；CORE-01表新增或拆分领域crate时须同步本列表，两处集合不一致即文档不一致；集合为空为pending-target，仅开发聚合允许，发布失败。未创建crate不捏造零覆盖。LCOV依据LLVM导出协议（官方https://www.llvm.org/docs/CommandGuide/llvm-cov.html ，锁版时复核此参考入口），必须含SF及逐行DA记录，以end_of_record结束；绝对SF规范化到root内相对路径，越界/重复SF/重复DA/负计数或行号非法/格式损坏退出2，不静默合并。每个core-sources文件须有记录，缺任一、空报告或缺参数退出2；集合外文件列明排除，不参与比例。分母为集合内DA的唯一(path,line)总数，分子为count>0的行数；LF/LH如存在须等于逐行计算，分母0退出2。以整数5*hit >= 4*total判80%，恰80%通过、低于80%退出1，不四舍五入后比较。JSON输出hit/total/ratio与缺失文件，不把缺文件当0/0通过。

**实现约束**
- 不向PR发评论；PR checks运行本脚本，weekly只归档周报；lizard写tools/requirements.txt并供两作业使用。
- 逐组件实现估算：tracked集合/配置80（13 crate + sync merge 字面枚举与排除清单）、行数/复杂度及unsafe/FFI计数95、LCOV协议/覆盖率160、报告/注释85、周报对比35、附属CI调用20，合计475；正反例测试与夹具不计。
- 外部前提：锁定Python、PyYAML/lizard；不读或上传公式内容。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-71_TEST.md](../Test/S0/S0_CORE-71_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约475行；tools/ci/maint_report.py、周报比较辅助及本卡编写的CI聚合调用行；不计本卡自测、夹具、tracked集合/阈值等纯数据、LCOV/报告生成物。

