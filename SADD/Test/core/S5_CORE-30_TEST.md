# CORE-30 测试方案

> 来源卡：[S5_CORE-30_扩展.md](../../core/S5_CORE-30_扩展.md)（图片解码与预处理）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R32] 样本集（`tests/fixtures/images/`：暗光、阴影、倾斜、模糊、纸张纹理各 20 张，来源与标注见卡片外部前提）按固定种子分为标定集与验证集各 50 张：阈值只在标定集上调整，验证集上质量提示与人工标注一致性 ≥ 90%（避免用同一批样本标定又验收）；开启任一增强时 `img.prepare` 写出 `gray_out_path` 对照图且其字节与 `PrepareOutput.gray` 相同，全部增强关闭时不写对照图（界面展示由 CORE-40 测试）。
- [R31] 解码预算：20 MiB 以上、40 MP 以上、魔数与扩展名不符、截断文件均被拒绝并给出约定错误码；解码入口 cargo-fuzz 累计 24 小时无崩溃（发布前门槛）。
- [R40] `fit_for_upload` 输出 ≤ 4 MiB 且 ≤ 4 MP；输出不含 EXIF 等元数据（逐字节检查）。
- [R31] 取消与扩展名：20 MP 样本在 `decode_oriented`、`prepare`（含 deskew）、`fit_for_upload` 各阶段中途置位 `CancelFlag`（用计数型测试 CancelFlag 在第 k 次检查时置位），置位后至返回之间最多再处理一个检查点单元（64 行 / 一个分块 / 一个角度步 / 一个 PNG 块，以处理单元计数断言，不用绝对毫秒）并返回 `IMG_CANCELLED`，适配层测试中 `out_path` 与 `.tmp` 均不存在；`declared_ext` 为 `Some("png")` 而内容是 JPEG 报 `IMG_FORMAT_UNSUPPORTED`，`None` 与 `.bin` 不比较并按魔数通过；`.gif`/`.heic` 扩展名被拒绝。
- [R03] 性能：12 MP 照片 `img.prepare` 满足 CORE-01 预算表“图片预处理”行；连续导入 20 张 12 MP 图片满足“连续 20 张 12 MP 图片”行（基准 `crates/fml-imgproc/benches/prepare.rs`，真机数据由 AND-12、WIN-13 采集）。
- [R31] 方向与元数据：EXIF 方向 1–8 各一张 3×2 彩色块夹具，decode_oriented 后像素排列与期望逐像素相同；含 EXIF/XMP/ICC/文本块的 JPEG、PNG、WebP 输入经 prepare 与 fit_for_upload 输出都只含 IHDR/IDAT/IEND（逐块检查）。
- [R31] 边界：文件恰为 20 MiB 通过、+1 字节 IMG_TOO_LARGE；头部恰 40 MP 通过、多 1 像素 IMG_TOO_MANY_PIXELS（解码前，分配计数为 0）；动画 WebP 与 GIF 魔数报 IMG_FORMAT_UNSUPPORTED；IMG_CROP_INVALID 各条件（越界、w 或 h = 31、旋转 ±45.5°、long_edge 1599/2201）逐条触发，32 像素、±45°、1600/2200 通过。
- [R40] 上传：构造按公式缩放后最高压缩仍 > 4 MiB 的噪声图报 IMG_UPLOAD_TOO_LARGE；sha256 等于最终输出字节的 SHA-256；同一输入在 Linux/Windows/Android CI 产物上 prepare 与 fit_for_upload 的 PNG 字节与 sha256 相同（跨平台向量文件）。
- [R32] 流水线与质量：合成图验证裁剪→旋转→缩小次序（已知坐标标记点位置）、长边小于 long_edge 时不放大、输出为 8 位灰度 PNG；旋转 5°、−7.5° 的文本合成图 deskew 检出角误差 ≤ 0.5°，均匀噪声图无可靠峰给出 quality.deskew_unreliable 且 tilt_deg = 0；七项指标各一张合成图触发对应消息键且 hints 顺序固定；thresholds.yaml 解析成功且含全部七个键。
- [R31] 路径：path/out_path 在 staging_root 外、经符号链接或重解析点指向外部、父目录不存在均报 IMG_PATH_INVALID；staging_root 为相对路径或不存在报 FFI_BAD_ARG。
