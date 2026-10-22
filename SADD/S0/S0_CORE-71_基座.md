### CORE-71 可维护性度量与阈值报告

**目标**：把文件长度、圈复杂度、unsafe与FFI数量转为可复现的报告。

**范围**
- 包含：从CORE-41拆出的maint_report.py（下游说明，非契约）、创建并读取tools/ci/thresholds.yaml、PR annotation与每周对比。
- 不包含：测试覆盖采集命令和CI作业编排（CORE-41，下游说明，非契约）；阈值化的unsafe/ABI门禁（CORE-74）。

**依赖**：CORE-01、CORE-69

**接口契约**
python tools/ci/maint_report.py --root . --out <maint.md> [--previous <maint.json>] [--annotations] --lcov <core.lcov> --core-sources <core-sources.json>；附同名JSON，字段固定为`{version:1, files:[{path,lines,max_ccn,generated}], unsafe:{blocks,safety_missing,files}, ffi:{extern_c_blocks,exported_symbols,files}, coverage:{hit,total,ratio,missing}, violations:[{rule,path,line,message}]}`，忽略时间字段后字节稳定。unsafe/FFI数量只入报告与周报对比，不参与退出码与阈值（门禁归CORE-74的UNSAFE/ABI，下游说明，非契约），本卡不复制其判据。

阈值文件tools/ci/thresholds.yaml由本卡创建并读取（CORE-41只读取、不定义；下游说明，非契约）：顶层只允许`file_max_lines`（int>0，默认800）、`fn_max_ccn`（int>0，默认15）、`core_line_coverage`（0<x≤1，默认0.80）、`dart_ccn_warn_only`（bool，默认true）四个键；未知键、缺键、类型或范围不符、YAML解析失败一律退出2，不静默取默认值。

生成物`*.g.dart`与`crates/fml-error/src/codes.rs`参与文件长度与复杂度计算，并在报告中记generated:true（排除项只有前者）。Rust函数复杂度用锁定lizard，Dart用CORE-69词法token近似（只消费`Token.kind`为code的token，注释与字符串字面量不计入；kind取值域由CORE-69定义，本卡只按code/comment/string三类消费）：具名函数/方法/闭包初值1，if/for/while/非default case/catch/&&/||/?:各+1，do-while只计while，else/??/?.不计；嵌套闭包单独算。函数头判定：kind=code的token中，`{`前紧邻`)`且该括号对之间只有参数（可空）时视为函数体起点，`=>`视为箭头函数或闭包，无法判定函数头一律输出warning并列入人工项，不称精确CFG；`f(){if(a&&b)x();}`为3。文件超file_max_lines、Rust复杂度超fn_max_ccn退出1；Dart超fn_max_ccn时dart_ccn_warn_only为true只warning、为false退出1；配置/工具错误退出2，其他0。`--previous`文件不存在时输出baseline标记而非零退化，文件损坏、version非1或缺必需字段退出2。annotations输出GitHub path/line/rule消息，不含源代码；JSON按path/line排序、忽略时间戳后字节稳定。

覆盖率协议：core-sources.json固定`{version:1,paths:[仓库相对POSIX路径]}`，按字节序去重。领域集合=CORE-01领域crate表列出的13个crate（fml-ast、fml-latex、fml-notation、fml-units、fml-type、fml-eval、fml-derive、fml-typeset、fml-export、fml-srs、fml-grade、fml-study、fml-crypto）的`crates/<name>/src/`下已跟踪的`.rs`文件（含src/lib.rs），加`crates/fml-sync/src/merge.rs`（同步纯合并唯一位置）；排除任何路径分量tests/fixtures的文件与`*.g.rs`，排除清单随报告输出。本卡只定义集合内容，生成方式（逐crate调用git、参数展开与退出码）归CORE-41的core_sources.py（下游说明，非契约），本卡不重复其操作句。本卡列表是CORE-01领域crate表在v5.3.4的可读快照，运行时唯一来源是CORE-01表；两处不一致时以CORE-01为准并修本卡文案，属开发者的manual核对项，本卡不声称机器检查。分母不因crate未创建而缩小（未创建的crate贡献0个文件），13+1个路径全无文件才是空集；集合为空为pending-target，仅开发聚合允许，发布失败；未创建crate不捏造零覆盖。LCOV依据LLVM导出协议（官方https://www.llvm.org/docs/CommandGuide/llvm-cov.html ，锁版时复核此参考入口），必须含SF及end_of_record；绝对SF规范化到root内相对路径，越界/重复SF/重复DA/负计数或行号非法/格式损坏退出2，不静默合并。每个core-sources文件必须存在SF记录；SF存在但无DA视为0可执行行，不参与分子与分母、也不判失败。缺任一SF、空报告或缺参数退出2；集合外文件列明排除，不参与比例。分母为集合内DA的唯一(path,line)总数，分子为count>0的行数；LF/LH如存在须等于逐行计算，分母0退出2。以`hit*den >= num*total`判通过，`num/den`由core_line_coverage化简而来（默认0.80=4/5），恰达阈值通过、低于阈值退出1，不四舍五入后比较。JSON输出hit/total/ratio与缺失文件，不把缺文件当0/0通过。

**实现约束**
- 不向PR发评论；PR checks运行本脚本，weekly只归档周报；lizard写tools/requirements.txt并供两作业使用。
- 周报比较辅助是本脚本的`--previous`分支，不另建脚本；unsafe/FFI计数与CORE-74门禁取同源数据（下游说明，非契约），但本卡只报告、不判定。
- 逐组件实现估算：集合与阈值配置80（含thresholds.yaml创建）、行数/复杂度及unsafe/FFI计数95、LCOV协议与覆盖率160、报告与注解85、周报对比35、附属CI调用片段20；正反例测试与夹具不计。
- 外部前提：锁定Python、PyYAML/lizard；不读或上传公式内容。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-71_TEST.md](../Test/S0/S0_CORE-71_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约475行；主包 `tools/ci/maint_report.py` 约455行（集合与阈值配置80、行数与复杂度及unsafe/FFI计数95、LCOV与覆盖率160、报告与注解85、周报对比35），附属 `ci.yml` 调用片段约20行（按 §8.4 共享写入点由 CORE-41 合入、本卡不编辑该文件；下游说明，非契约）；thresholds.yaml、requirements条目与LCOV/报告生成物为数据，自测与夹具不计。
