### CORE-75 共享写入点预分配门禁

**目标**：对共享错误码、安装点、路由、快捷键表与排序号建立唯一预分配和实现登记回执检查。

**范围**
- 包含：shared-writes.json验证与构建后extensions.json回执比对；不实现各特性安装点。
- 不包含：业务注册代码、错误码生成器或UI导航实现。

**依赖**：CORE-01、CORE-02、CORE-57

**接口契约**
node tools/sadd/reservations.mjs [--policy contracts/policies/shared-writes.json] [--actual build/extensions.json]。0表与回执有效/1违约/2输入解析错误；不传actual只校验设计预分配，输出mode=design不得当实现通过。policy固定{version:1,entries:[{kind,key,owner,point}]}，kind为error/file/route/installer/shortcut/startup/profile/firstFrame/settings，key/owner/point为非空字符串、owner必须现行有效卡。每种 kind 内规范化 key 唯一（route 的参数段先归一为 :param 再比较）；route 为以 / 开头的合法路径，段为 [a-z][a-z0-9_-]* 或 :param（参数名以字母起始），归属按最长匹配前缀解析、同长度优先静态段，根 / 仅匹配自身。route 的父子前缀允许分属不同卡（现存 /study 与 /study/stats 即父子），本卡只禁止同一 route key 委派给两个 owner，不要求跨 owner 前缀互异；CORE-36 现行措辞“禁止相同前缀不同 owner”（SADD/core/S2_CORE-36_界面.md，下游说明，非契约）与本规则冲突，已按 CO-43 开契约变更单待 CORE-36 所有者同步，检查器不得实现成跨 owner 前缀全互异（否则现表直接违约）。point 为非空字符串，按 kind 取闭式形式之一（CO-60，ADR-V5-62；不属下列任一类别所定形式的写法一律失败）：error 为 contracts/errors/registry.yaml（错误码唯一登记处）；file 为该文件自身的仓库相对路径，且与条目 key 逐字相同；installer 为登记该安装点的装配文件仓库相对路径，取值限定 app/lib/composition/installers.dart（特性与传输层安装点）、app/lib/composition/ports_windows.dart 与 app/lib/composition/ports_android.dart（平台安装点），不写各特性自己的 install.dart；route 为注册该路由的顶层路由表函数符号（形如 accountRoutes，即 List<GoRoute> xxxRoutes(...)），不写路由路径也不写文件路径；shortcut 为该卡声明快捷键表或命令表的符号，取顶层 const 或 Class/Class.member（形如 defaultKeymap、defaultStudyBindings、StudyCommand），不写文件路径；startup/firstFrame/settings/profile 为注册器符号 Class 或 Class.member（形如 FeatureRegistry.startupHooks）；profile 的 point 固定写作 ProfileHooks（CORE-36 的类名，下游说明，非契约），大小写或拼写不符即失败。point 只允许 ASCII 字母、数字、下划线、点与斜杠，禁止空白、冒号与 ..；带 .. 或超出仓库根即越界失败。error为CORE-02合法大写码；排序号为规范十进制0～999，同一序列唯一。 startup为进程一次序列，profile为每档案句柄序列（point固定ProfileHooks），firstFrame和settings同样独立；同order跨序列不冲突，不能把profile登记伪装成startup。profile具体调度是CORE-36（下游说明，非契约）的行为，本卡只定义声明格式与一致性检查。
actual由构建后注册器导出相同version/entries形状，只含本构建已注册项；每项必须存在同kind/key/owner/point预分配。未实现项允许不出现，不伪造回执。发布required-stage清单由CORE-70（下游说明，非契约）另检全部应启用项，不能用子集比对代替完整性。脚本只验证声明归属，不声称能证明源码没有绕过安装点；扫描或消费者人工确认仍需D.12。
CI checks作业先design验证，功能构建后对该平台actual再验。新增项先由对应文件单写维护者分配并修本机器表，其他会话提交片段，不直接重排共享文件。本表现行全部条目（CO-60 时为 323 条）已按上述闭式 point 规则一次性迁移完成（CO-60；2026-10-22 用户裁定 F-75-03 按迁移处理，不设遗留豁免名单）：迁移只做一次，此后新增或修改条目一律按闭式规则写，不回填历史写法；迁移后的 policy 数据属本卡交付的契约数据，按 README §8.4 的数据文件口径不计入本卡实现规模。
导出签名（tools/sadd/reservations.mjs，编码会话不得改名或调换形参）：validateReservations(value: unknown, cards: Map<string, {id: string}>): string[]（返回 EXT-<n>: 开头的错误串数组，空数组通过，不抛异常）、routeOwner(policy: {version: 1, entries: Entry[]}, route: string): Entry | null（按最长匹配前缀返回归属条目，无匹配返回 null）、compareActual(policy, actual: {version: 1, entries: Entry[]}, cards): string[]（回执子集与归属比对）。
CLI stdout 固定输出一个 JSON 对象 {mode: "design" | "implementation", entries: <条目数>, errors: string[]}：不给 --actual 时 mode 恒为 design，给了 --actual 时 mode 为 implementation 且 entries 为本构建已注册项数；errors 每条以 EXT-<n>: 开头（n=1 格式或取值、2 重复、3 未知 owner、4 回执与预分配不符）。退出码：0 无违约；1 有违约（errors 非空，仍写出 JSON）；2 输入解析失败（policy 或 actual 不可读、JSON 损坏），此时 stderr 输出一行 EXT-INPUT: <原因>，不写半份结构。contracts/policies/shared-writes.json 由本卡单写维护：其他卡提交条目片段，由本卡会话合并后跑门禁，任何其他卡或会话不得直接重排该文件；本卡编码材料必须收录 policy 全文（工具按 owner 过滤出的片段或 0 条不得视为已读，见 CO-60 交 CORE-57 的变更单）；错误码条目字段与 installer/route 条目措辞的归属分别以 CORE-02、CORE-36 为准（下游说明，非契约），本卡只按 CO-43 变更单提示同步，未获所有者确认前不改它们的卡。

route key允许根/及带:param的规范段；参数名以字母起始，参数段重命名不产生新分配（/a/:x与/a/:y重复）。回执路由以完整段匹配最长预分配前缀，同长度优先静态段；根/仅匹配自身，不能作为未知路由兜底。静态/study/books/new优先于/study/books/:bookId；/libraryx不匹配/library。实际路由owner/point必须等于该归属，其他kind仍精确key比对。

**实现约束**
- Node标准库，版本读CORE-01；现版本仅作设计工具先行，锁文件缺失前不视为整卡就绪。现值：tools/sadd/reservations.mjs 56 行已实现 kind/key/owner/order/重复与回执子集校验及 CLI 退出码，尚未实现 point 形式校验与 route 父子前缀的最长前缀归属校验（routeOwner 已导出但无断言）；编码会话补齐这两项与 CLI 退出码 1 的断言，规模仍按约 100 行。
- policy不分配整段AUTH等公共前缀，逐码owner以CORE-02标准定义表为依据；尚无标准表的历史码列未注册阻断，不靠猜测补登记。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-75_TEST.md](../Test/S0/S0_CORE-75_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约100行；分主包与附属两部分：tools/sadd/reservations.mjs 主包约85行（现值 56 行，补齐 point 闭式校验与 route 最长前缀归属断言，含 CLI 退出码 1），本卡在 tools/ci/manifest.json 与 CI 作业中的调用接入行约15行；不计自测、夹具、policy/schema/声明数据与生成报告（CO-60 迁移的 shared-writes 数据属本卡交付的契约数据，按 README §8.4 数据文件口径不计规模）。

