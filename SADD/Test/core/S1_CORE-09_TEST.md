# CORE-09 测试方案

> 来源卡：[S1_CORE-09_引擎.md](../../core/S1_CORE-09_引擎.md)（类型推断与量纲校验）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R13] 正反例集 `tests/fixtures/dimension/dx.yaml` 全部通过：DX-01 F = ma Verified；DX-02 F = m + a Invalid（定位 m + a）；DX-03 ∫dx/x = ln|x| + C 且 x 为长度 → `TYPE_LOG_DIMENSIONED`；DX-04 x 无量纲 → Verified；DX-05 ∫f(x)dx = F(x) + C → VerifiedPolymorphic，F 为 D_f·D_x；DX-06 泰勒公式、DX-07 拉格朗日中值、DX-08 det(AB) = det A·det B、DX-09 AA* = |A|E、DX-10 正态密度、DX-11 切比雪夫不等式 → VerifiedPolymorphic；DX-12 eˣ（x 为长度）Invalid；DX-13 sin(ωt) Verified、sin t（t 为秒）Invalid；DX-14 国内方案 pV = νRT 与 p = nkT Verified；DX-15 v = s/t 且 s 未声明 → Unresolved；DX-16 无底 log → Unresolved。此集冻结后只追加编号、不改既有期望；期望以“与给定结果同构（变量可重命名）”比较，不依赖具体变量编号。
- [R13] 规则表测试：积分变量未绑定、点积输出向量、二维叉积、能量与力矩、频率与角频率混用、温度点乘除、经验公式无标记均给出约定诊断。合一算法本身的单元与属性测试归 CORE-77，本卡只测规则选取与诊断映射（`UnifyError::DimConflict` → `TYPE_DIM_CONFLICT`，定位首个不可合一的子式；`Overflow` → `UNIT_OVERFLOW`）；`TYPE_DIM_CONFLICT` 的 left/right 参数为 CORE-77 文本化格式（如 `L` 与 `L T^-1`）。
- [R13] typed 规范形：DX-05 的 typed 中 F 节点类型为 resolve 后的形式（与 D_f·D_x 同构，不出现已绑定变量）；DX-05～DX-11 每例 typed 中出现的变量集合 ⊆ `VerifiedPolymorphic.vars`，且对每个 `TypeExpr.dimension` 再调一次 `resolve` 结果不变。
- [R14] 单元测试：录入时修改符号量纲声明后重新校验，诊断随之变化；修改已入库修订的声明产生新 RevisionId。
- [R13] 属性测试：等价表达式（交换律、结合律变形）推出相同量纲；错误路径不 panic。
- [R03] 性能：解析 + 量纲校验（≤256 节点）满足 CORE-01 预算。
