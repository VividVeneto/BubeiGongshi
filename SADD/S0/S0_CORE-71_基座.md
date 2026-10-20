### CORE-71 可维护性度量与阈值报告

**目标**：把文件长度、圈复杂度、unsafe与FFI数量转为可复现的报告。

**范围**
- 包含：从CORE-41拆出的maint_report.py、thresholds.yaml读取、PR annotation与每周对比。
- 不包含：测试覆盖采集命令和CI作业编排（CORE-41，下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-69

**接口契约**
python tools/ci/maint_report.py --root . --out <maint.md> [--previous <maint.json>] [--annotations] --lcov <core.lcov> --core-sources <core-sources.json>；附同名JSON，缺previous输出baseline而非零退化。读取thresholds.yaml：file_max_lines=800、fn_max_ccn=15、core_line_coverage=0.80、dart_ccn_warn_only=true。生成物/*.g.dart排除并在报告列明；Rust函数复杂度用锁定lizard，Dart用CORE-69词法token近似：具名函数/方法/闭包初值1，if/for/while/非default case/catch/&&/||/?:各+1，do-while只计while，else/??/?.不计；嵌套闭包单独算。f(){if(a&&b)x();}为3。未知语法输出warning+人工项，不称精确CFG。文件超800/Rust复杂度超15退出1，Dart超15只warning；配置/工具错误退出2，其他0。annotations输出GitHub path/line/rule消息，不含源代码；JSON按path/line排序、忽略时间戳后字节稳定。

覆盖率协议：core-sources.json固定{version:1,paths:[仓库相对POSIX路径]}，按字节序去重。CORE-41使用git ls-files枚举crates/fml-{ast,notation,units,type,eval,derive,typeset,study}/src/**/*.rs中已创建的源码（含src/lib.rs），排除任何路径分量tests/fixtures与*.g.rs并报告排除清单；集合为空为pending-target，仅开发聚合允许，发布失败。未创建crate不捏造零覆盖。LCOV依据LLVM导出协议（官方https://www.llvm.org/docs/CommandGuide/llvm-cov.html ，锁版时复核此参考入口），必须含SF及逐行DA记录，以end_of_record结束；绝对SF规范化到root内相对路径，越界/重复SF/重复DA/负计数或行号非法/格式损坏退出2，不静默合并。每个core-sources文件须有记录，缺任一、空报告或缺参数退出2；集合外文件列明排除，不参与比例。分母为集合内DA的唯一(path,line)总数，分子为count>0的行数；LF/LH如存在须等于逐行计算，分母0退出2。以整数5*hit >= 4*total判80%，恰80%通过、低于80%退出1，不四舍五入后比较。JSON输出hit/total/ratio与缺失文件，不把缺文件当0/0通过。

**实现约束**
- 不向PR发评论；PR checks运行本脚本，weekly只归档周报；lizard写tools/requirements.txt并供两作业使用。
- 逐文件估算：聚合/阈值80、Dart近似70、LCOV与核心集合100、报告50、正反例160，合计460。
- 外部前提：锁定Python、PyYAML/lizard；不读或上传公式内容。

**验收标准**
- [R18][R20] 注释/字符串/嵌套闭包/三元表达式夹具给固定期望复杂度，文件与Rust阈值反例返回1，Dart阈值只warning；PR有annotation、weekly有对比、两者均不发评论。
- [R18] 相同输入重复运行结果字节一致；缺上周报告只标baseline，损坏配置失败2。

- [R18][R20] LCOV夹具4/5=80%通过、3/5退出1；缺核心SF、空报告、缺参数、DA重复/负计数、LF/LH不符、越界路径退出2；集合外高覆盖文件不抬高比例，零分母拒绝；重跑稳定。领域源码集合为空必须pending，--release失败。

**规模**：约 460 行；主包 `tools/ci/maint_report.py`与`tools/ci/tests/test_maint.py`。

