### CORE-75 共享写入点预分配门禁

**目标**：对共享错误码、安装点、路由、快捷键表与排序号建立唯一预分配和实现登记回执检查。

**范围**
- 包含：shared-writes.json验证与构建后extensions.json回执比对；不实现各特性安装点。
- 不包含：业务注册代码、错误码生成器或UI导航实现。

**依赖**：CORE-01、CORE-02

**接口契约**
node tools/sadd/reservations.mjs [--policy contracts/policies/shared-writes.json] [--actual build/extensions.json]。0表与回执有效/1违约/2输入解析错误；不传actual只校验设计预分配，输出mode=design不得当实现通过。policy固定{version:1,entries:[{kind,key,owner,point}]}，kind为error/file/route/installer/shortcut/startup/firstFrame/settings，key/owner/point为非空字符串、owner必须现行有效卡。每种kind内key唯一；route合法绝对路径，同前缀唯一、按最长段前缀解析。error为CORE-02合法大写码；排序号为规范十进制0～999，同一序列唯一。
actual由构建后注册器导出相同version/entries形状，只含本构建已注册项；每项必须存在同kind/key/owner/point预分配。未实现项允许不出现，不伪造回执。发布required-stage清单由CORE-70（下游说明，非契约）另检全部应启用项，不能用子集比对代替完整性。脚本只验证声明归属，不声称能证明源码没有绕过安装点；扫描或消费者人工确认仍需D.12。
CI checks作业先design验证，功能构建后对该平台actual再验。新增项先由对应文件单写维护者分配并修本机器表，其他会话提交片段，不直接重排共享文件。

route key允许根/及带:param的规范段；参数名以字母起始，参数段重命名不产生新分配（/a/:x与/a/:y重复）。回执路由以完整段匹配最长预分配前缀，同长度优先静态段；根/仅匹配自身，不能作为未知路由兜底。静态/study/books/new优先于/study/books/:bookId；/libraryx不匹配/library。实际路由owner/point必须等于该归属，其他kind仍精确key比对。

**实现约束**
- Node标准库，版本读CORE-01；现版本仅作设计工具先行，锁文件缺失前不视为整卡就绪。
- policy不分配整段AUTH等公共前缀，逐码owner以CORE-02标准定义表为依据；尚无标准表的历史码列未注册阻断，不靠猜测补登记。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-75_TEST.md](../Test/S0/S0_CORE-75_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约115行；tools/sadd/reservations.mjs及本卡编写的CI调用行；不计自测、夹具、policy/schema/声明数据与生成报告。

