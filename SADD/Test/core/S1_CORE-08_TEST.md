# CORE-08 测试方案

> 来源卡：[S1_CORE-08_引擎.md](../../core/S1_CORE-08_引擎.md)（量纲与单位）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R13] T-UNIT：20 ℃ → 293.15 K、Δ20 ℃ → 20 K、温度点相加被拒；rad 与 deg 换算；ω = 2πf 显式；ω = f 报 QuantityKind 不一致（由 CORE-09 使用本卡数据）。
- [R15] 自定义单位：等价换算成功；循环定义与非法 offset 被拒（`UNIT_CYCLE`、`UNIT_INVALID_OFFSET`）。
- [R13] 属性测试：换算满足结合性与往返一致（a→b→a 精确相等）。
- [R14] 单元测试：`compatible_units` 对力的量纲只返回 N、kN、dyn 等相容单位。
- [R13] 量纲文本：`L M T^-2`、`L^1/2`、`1`、`T^-1 Angle` 解析后 `to_text` 原样返回；`M L T^-2` 规范化为 `L M T^-2`；`L^x` 返回 `UNIT_DIM_SYNTAX`。

- [R13] 指数运算单测：`Rational::new(1, 0)`、`Rational::new(i128::MIN, 1).checked_neg()`、零的 `checked_recip`、先交叉约分后仍溢出的 `checked_mul`、`checked_add` 溢出均返回 `UNIT_OVERFLOW`；`new(2, -4)` 规范为 `-1/2`、`new(0, 5)` 规范为 `0/1`；`DimensionFull::one()` 为单位元，`checked_mul` 与 `inverse` 结果去零指数且 pseudo 按 Angle < Count 排序，`pow(1/2)` 后 `L^2` 得 `L`，`d.checked_mul(&d.inverse()?)? == one()`；`is_dimensionless` 对 `Angle` 为 false。
- [R13] UNIT-X1～X3 可无溢出表示；eV 往返为精确有理数，i128 边界外返回 UNIT_OVERFLOW，JSON 往返无 Dart 浮点损失。
