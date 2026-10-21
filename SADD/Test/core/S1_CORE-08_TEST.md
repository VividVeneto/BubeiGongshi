# CORE-08 测试方案

> 来源卡：[S1_CORE-08_引擎.md](../../core/S1_CORE-08_引擎.md)（量纲与单位）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

以下为编码验收计划，非当前Rust测试通过声明。全部最小单位/kind fixture在测试中显式构造，不依赖CORE-56（下游说明，非契约）尚未交付的资产；实现/fixture/测试同阶段交付。

## 阶段①：数值、量纲、serde和独立基表
- [R13] 编译期能力断言覆盖源卡全部数据类型与MemRegistry::Clone；Rational不要求PartialOrd/Ord，不能把1/2与1/3按num/den字典序排序。纯crate的依赖检查禁止parser/type/store/ffi及文件/时钟/随机API。
- [R13] Rational::new(2,-4)=-1/2、new(0,5)=0/1、new(MIN,MIN)=1/1；new(1,0)、new(MIN,-1)、new(MIN,1).checked_neg()、零checked_recip、交叉约分后仍溢出的checked_mul与checked_add均UNIT_OVERFLOW；先可约分的大数乘法成功（如MAX/2 × 2/MAX=1）。所有成功结果规范形；失败不以f64降级。
- [R13] DimensionFull::one、checked_mul/inverse/pow属性：d*inverse(d)==one；L^2的pow(1/2)=L、L的pow(1/2)=L^1/2，pseudo去零且Angle<Count；Angle/Count的is_dimensionless=false。指数运算可用分数，不与用户Unit.expr的“仅整数幂”混淆。
- [R13] parse/to_text：L M T^-2、L^1/2、1、T^-1 Angle逐字一致；M L T^-2规范为L M T^-2，L L^-1规范为1；空串、未知基、L^x、L^1/0、1 L及垃圾后缀UNIT_DIM_SYNTAX；合法词法但超i128 UNIT_OVERFLOW。随机规范量纲parse(to_text(d))==d。
- [R13] serde固定shape与拒绝：Rational仅num/den十进制字符串，拒绝number、+1、01、-0、分母0/负数、未约分2/4、零0/5、i128越界与未知/重复字段；Full恰7exps，pseudo恰二项tuple、无零项/重复/反序；UnitKind蛇形、offset None省略、null拒绝。对所有类型逐字节固定fixture+roundtrip，显式确认Dart大整数不经浮点。
- [R13] UNIT-X1～X3按源卡固定有理值无溢出构造；eV→J→eV精确往返，u的num=41513476723/den=25000000000000000000000000000000000000；N_A=602214076000000000000000/1。保持来源“SI exact”和“CODATA近似”的区别，不因存储有理数而升级物理精确性。
- [R14] from_parts最小fixture明确含si:m、si:s、si:K、si:rad、si:N、common:kN、common:dyn、common:deg、common:degC、common:delta_degC；N/kN/dyn为L M T^-2、scale分别1/1000/1/100000，其他量纲不相容。compatible_units只返回[common:dyn,common:kN,si:N]（ASCII字节序），空量纲无匹配返回[]。构造顺序打乱不改变结果；lookup未知None。
- [R13] QuantityKind fixture含Energy/Heat互为兼容、Torque同量纲但不兼容、Frequency=T^-1、AngularFrequency=T^-1 Angle、Temperature/Difference。quantity_kind逐字段取回、未知None；重复kind UNIT_DUPLICATE、兼容引用缺失UNIT_UNKNOWN、未双向声明UNIT_DIM_SYNTAX。from_parts验证Unit id/namespace/scale/dimension/offset：重复ID UNIT_DUPLICATE、坏ID或scale≤0 UNIT_DIM_SYNTAX、非点带offset/点非纯Θ UNIT_INVALID_OFFSET；构造不猜用户图。
- [R13] T-UNIT固定换算：common:degC kind=AffinePoint、scale1、offset5463/20；si:K kind=Absolute、scale1无offset；common:delta_degC kind=Difference、scale1无offset。20℃→K=5863/20，5863/20K→℃=20；Δ20℃→K=20且K→Δ℃=20；℃↔Δ℃直接UNIT_AFFINE_MISUSE，K↔K不加offset。K中性只准换算，不使表达式点算术合法。
- [R13] 角度按PI_RAT而非double黄金：180deg→rad=245850922/78256779，1rad→deg=7043110110/122925461，360deg→rad=491701844/78256779；上述往返按有理数精确相等。另用独立高精度π字符串/十进制参考验|PI_RAT-π|<1e-15，与有理golden断言分开；不得由被测convert生成期望。
- [R13] convert错误优先：from未知且to不相容/仿射时UNIT_UNKNOWN；to未知也UNIT_UNKNOWN；两端已知但量纲不同为UNIT_INCOMPATIBLE，随后才检查点↔差；同量纲点/差为UNIT_AFFINE_MISUSE；合法换算中数值不可表示UNIT_OVERFLOW。from==to也先检查ID存在，不能未知ID原值直返。
- [R13] 有理域内无溢出的随机可兼容单位和值：a→b→a精确相等，a→b→c与a→c相等；分别覆盖线性、点→点/中性基准，不生成被明确禁止的点↔差路径。insert(Unit)与remove独立原子表：插入可查、重复拒绝、删除后None、未知删除UNIT_UNKNOWN，Clone的owned数据修改不影响原表。
- [R13] DTO契约用2020-12 validator显式format检查contracts/dto/types.schema.json与units.compatible/convert.schema.json的request/ok/examples；完整合法/非法Rational/DimensionFull/Unit样本与serde结果一致。FFI错误参数/不可用snapshot由CORE-56（下游说明，非契约）消费者测试，分别FFI_BAD_ARG/ENGINE_UNAVAILABLE；本纯算法测试不假造已运行适配。

## 阶段②：定义图与原子用户单位操作
- [R15] with_user_definitions借用①from_parts的稳定base，defs含user:km2="1000 si:m"、user:minute="1/60 si:s"、user:force="si:kg si:m si:s^-2"；base fixture补si:kg，验证单位比例/量纲与原定义一一对应；时间例语义是si:s/60，不能误写为60秒。正整数幂/负幂/有理系数/有限小数合法；定义结果namespace=user、version=1，symbol只保留定义元数据而非lookup别名。
- [R15] 全集前向引用user:a→user:b、user:b→si:m成功；自环user:a→user:a、间接a→b→a均UNIT_CYCLE；非环缺失user:b或si:missing为UNIT_UNKNOWN；重复定义ID/与base冲突UNIT_DUPLICATE。defs输入顺序不改变查找/换算结果，来源依赖来自expr图而非扁平scale。
- [R15] insert_definition/define_user_unit委派原子入口：注册a后插b引用a，remove(a)为UNIT_IN_USE；先删b再删a成功。先记录registry lookup/compatible/图可观察状态，尝试重复/未知/环/坏offset/溢出插入后逐项不变；不能先写Unit再在记录graph失败时留下半条。普通insert仅原子Unit，不提供定义删除安全证据。
- [R15] 非法定义矩阵逐项断言：user名超长/首数字、symbol空/17个标量/控制字符、空expr、括号、运算符*/+、科学记数、指数1/2、未知幂词法、最终系数≤0均UNIT_DIM_SYNTAX；未知但合法unitId为UNIT_UNKNOWN。量纲parse的分数指数仍合法，User.expr分数幂不支持必须明确拒绝。
- [R15] offset：非点携offset、offset="abc"、非Θ点UNIT_INVALID_OFFSET；合法数字超i128 UNIT_OVERFLOW；引用common:degC作为因子UNIT_AFFINE_MISUSE；从si:K定义点且offset=5463/20成功，20点→si:K=5863/20。AffinePoint不准乘积/非1幂，不准借点作差。
- [R15] 生命周期/Clone编译测试：借用base的registry不能逃逸base作用域；克隆共享只读base但owned用户图独立；删除只操作owned，借用base-only ID返回UNIT_UNKNOWN且base未改变；base含User的错误用法属于调用前置条件，不能通过dyn clone/强转绕过。API文档示例须在deny(missing_docs)下构建。
- [R14] 跨卡接线验收由CORE-14（下游说明，非契约）补齐：事务内取当前定义全集+候选构造/修改图，UNIT_IN_USE时数据库定义与引擎层均不变；删除成功再以新全集重建/发布，旧borrow退出后才更新快照。CORE-56（下游说明，非契约）从snapshot合成Unit/Kind构造from_parts只读表，不将其用于用户定义删除检查。新trait入口/生命周期/错误触发变化必须非作者复核与实际消费者确认，未完成时保留门禁。
- [R13] 下游语义跟踪（非本卡独立通过项）：CORE-09（下游说明，非契约）的ω=2πf显式成立、ω=f报TYPE_QK_MISMATCH及点+点/乘除/幂报TYPE_AFFINE_MISUSE；本卡只提供kind/PI_RAT单位数据契约，无表达式算术API。CORE-56（下游说明，非契约）资产中的deg比例、K/点/差kind和QuantityKind关系需与本fixture一致；未实现资产/适配/锁文件时记录未执行。
