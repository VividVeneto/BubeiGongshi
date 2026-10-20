# CORE-30 测试方案

> 来源卡：[S5_CORE-30_扩展.md](../../core/S5_CORE-30_扩展.md)（图片解码与预处理）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R32] 样本集（`tests/fixtures/images/`：暗光、阴影、倾斜、模糊、纸张纹理各 ≥ 20 张）经 `prepare` 后，质量提示命中率与人工标注一致性 ≥ 90%；增强前后对照图可在界面展示（CORE-40）。
- [R31] 解码预算：20 MiB 以上、40 MP 以上、魔数与扩展名不符、截断文件均被拒绝并给出约定错误码；解码入口 cargo-fuzz 累计 24 小时无崩溃（发布前门槛）。
- [R40] `fit_for_upload` 输出 ≤ 4 MiB 且 ≤ 4 MP；输出不含 EXIF 等元数据（逐字节检查）。
- [R31] 取消与扩展名：20 MP 样本在 `decode_oriented`、`prepare`（含 deskew）、`fit_for_upload` 各阶段中途置位 `CancelFlag`，在固定上限（测试机 200 ms）内返回 `IMG_CANCELLED`，`out_path` 与 `.tmp` 均不存在；`declared_ext` 为 `Some("png")` 而内容是 JPEG 报 `IMG_FORMAT_UNSUPPORTED`，`None` 与 `.bin` 不比较并按魔数通过；`.gif`/`.heic` 扩展名被拒绝。
- [R03] 性能：12 MP 照片 `img.prepare` 满足 CORE-01 预算表“图片预处理”行；连续导入 20 张 12 MP 图片满足“连续 20 张 12 MP 图片”行（基准 `crates/fml-imgproc/benches/prepare.rs`，真机数据由 AND-12、WIN-13 采集）。
