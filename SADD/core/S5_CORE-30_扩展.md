### CORE-30 图片解码与预处理

**目标**：在 Rust 侧以内存安全的解码器和固定预算处理导入图片，输出供识别与上传使用的规范图，以及非阻断的质量提示。

**范围**
- 包含：格式识别（魔数）、头部预算检查、流式解码、EXIF 方向修正与元数据剥离、裁剪、长边规范化、灰度与光照归一、去噪、可选自适应二值化与旋转纠偏（透视暂不实现，见README §6 Q38待确认）、质量评分、上传图尺寸规整与哈希。
- 不包含：选图与拍照（平台卡：AND-03、AND-04、WIN-04、WIN-05）；HEIC 解码（上游平台系统解码器先转成 JPEG，本卡只接收字节；平台导入是下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05

**接口契约**

```rust
// crates/fml-imgproc/src/lib.rs
pub struct DecodeLimits { pub max_bytes: u64 /* 20 MiB */, pub max_pixels: u64 /* 40 MP，按头部判断，解码前拒绝 */ }
pub enum ImageFormat { Png, Jpeg, WebP }
pub struct ImageInfo { pub format: ImageFormat, pub width: u32, pub height: u32, pub bytes: u64, pub exif_orientation: u8 /* 1..=8，无则 1 */ }
pub struct WorkingImage { /* 已按方向旋转的 8 位 RGB 缓冲；不可序列化，只在一次 op 内存活 */ }
pub struct Crop { pub x: u32, pub y: u32, pub w: u32, pub h: u32, pub rotation_deg: f32 }
pub struct EnhanceOptions { pub denoise: bool, pub illumination: bool, pub local_contrast: bool, pub deskew: bool, pub binarize: bool /* 默认 false */ }
pub struct QualityReport { pub sharpness: f32 /* 拉普拉斯方差 */, pub too_dark: bool, pub overexposed: bool, pub shadow: f32,
                           pub tilt_deg: f32, pub region_ratio: f32, pub hints: Vec<String> /* 消息键 */ }
pub struct PreparedImage { pub png: Vec<u8>, pub width: u32, pub height: u32, pub sha256: [u8; 32] }
pub fn probe(bytes: &[u8], limits: &DecodeLimits, declared_ext: Option<&str> /* 小写、不含点；None 不比较 */) -> Result<ImageInfo, FmlError>;
pub fn decode_oriented(bytes: &[u8], limits: &DecodeLimits, cancel: &CancelFlag) -> Result<WorkingImage, FmlError>; // 修正方向、剥离全部元数据
pub fn prepare(img: &WorkingImage, crop: &Crop, opts: &EnhanceOptions, long_edge: u32 /* 1600..=2200 */, cancel: &CancelFlag) -> Result<(PreparedImage, QualityReport), FmlError>;
pub fn fit_for_upload(img: &PreparedImage, cancel: &CancelFlag) -> Result<PreparedImage, FmlError>;
// s = min(1, √(4×10⁶ ÷ (w·h)))，重新编码后 ≤ 4 MiB；之后才计算 sha256 并展示预览
```

- FFI op（图片字节不经 JSON 传递，输入输出都是 `StoreArea.staging` 下的文件路径）：`img.probe`（同步）`{ path }` → `ImageInfo`；`img.prepare`（长任务）`{ path, crop, options, long_edge, out_path }` → `{ out_path, width, height, sha256, quality }`（写出 PNG）；`img.fit_for_upload`（长任务）`{ prepared_path, out_path }` → `{ out_path, width, height, sha256, bytes }`。路径不在暂存区 → `IMG_PATH_INVALID`。
- 扩展名与取消（ADR-V5-46）：`CancelFlag` 取自 CORE-05 的 `fml-ast`（本卡新增依赖，仅用该类型）。纯函数不读文件名。扩展名比较归 fml-ffi 适配层：`img.probe` 与 `img.prepare` 从 `path` 取小写扩展名传给 `probe` 的 `declared_ext`（`png`→Png，`jpg`/`jpeg`→Jpeg，`webp`→WebP；`bin` 或无扩展名传 `None` 不比较；其他扩展名视为与任何格式都不符）；魔数格式与 `Some` 扩展名不符 → `IMG_FORMAT_UNSUPPORTED`。平台导入写暂存文件时使用与实际格式一致的扩展名，或统一使用 `.bin`。`CancelFlag` 检查点：解码每 64 行、方向旋转与裁剪每 64 行、去噪与光照归一每个分块、deskew 每个角度步、PNG 编码每个块之后；置位立即返回 `IMG_CANCELLED`。FFI 适配先写 `out_path.tmp` 再原子重命名，取消或失败时删除临时文件，不留半成品。
- 支持格式：PNG（image crate）、JPEG（zune-jpeg）、静态单帧 WebP（image-webp，不链接 libwebp）；不支持 SVG、PDF 与网页。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `IMG_FORMAT_UNSUPPORTED` | error | 否 | 魔数不是 PNG、JPEG、WebP；动画 WebP；调用方传入 `declared_ext` 且魔数格式与之不符 |
| `IMG_TOO_LARGE` | error | 否 | 文件 > `max_bytes` |
| `IMG_TOO_MANY_PIXELS` | error | 否 | 头部声明的宽 × 高 > `max_pixels`（解码前判断） |
| `IMG_CORRUPT` | error | 否 | 头部无法解析、数据截断或解码器报错 |
| `IMG_CROP_INVALID` | error | 否 | 裁剪框超出图像、宽或高 < 32 像素、旋转角不在 −45°..45°；`long_edge` 不在 1600..=2200 |
| `IMG_UPLOAD_TOO_LARGE` | error | 否 | 按公式缩放并以最高压缩级别编码后仍 > 4 MiB |
| `IMG_PATH_INVALID` | error | 否 | 输入或输出路径不在 `StoreArea.staging` 内，或为符号链接 |
| `IMG_CANCELLED` | info | 否 | `CancelFlag` 置位（`decode_oriented`、`prepare`、`fit_for_upload` 的检查点触发；`probe` 不取消） |

deskew：灰度缩至长边1024，阈值化后扫描-15°..15°步长0.5°，最大化水平行投影的方差，同分选绝对值小者再选负角；旋转采用双线性/白底，|角|<0.5°不转。无可靠峰（最高/中位<1.1）仅提示手动裁剪。质量初值：8位灰度3×3离散Laplacian方差<100提示模糊，均值<40偏暗，≥250像素比例>0.2过曝；作为提示不阻止导入，AND-12/WIN-13以100图标注集标定并版本化阈值。

**实现约束**
- 不在 Dart、Java/Kotlin 或 C# 侧解码全尺寸位图；平台层只传字节流或系统解码后的 PNG。
- 质量提示不阻断流程，低质量时提示重拍或调整；阈值在 M0 用样本标定后写入 `crates/fml-imgproc/thresholds.yaml`。
- 不强制锐化与二值化；保留灰度图与增强图供用户对照；切换增强选项会重新生成图片与哈希，原有上传授权作废。
- 只有基准测试证明必要时才引入 OpenCV（须经 ADR）。
- 外部前提：image（只启用 png 特性）、zune-jpeg、image-webp、kamadak-exif（读取方向）；cargo-fuzz 目标 `crates/fml-imgproc/fuzz/decode.rs` 由 CORE-41 夜间任务运行。
- 中间结果只在内存或 `StoreArea.staging` 中，会话结束立即清理；不写系统相册或公共目录。
- 单个活动解码/推理任务，排队有上限；一次导入最多 10 张图片。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-30_TEST.md](../Test/core/S5_CORE-30_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 615 行；主包 `crates/fml-imgproc/`（约 535，含取消检查点与扩展名比较），附属 `crates/fml-ffi/src/ops/img.rs`（img.probe、img.fit_for_upload、img.prepare 处理与暂存区路径/临时文件工具，约 80）；thresholds.yaml 为数据不计。分阶段：① 解码、几何与上传规整（探测与解码、方向、裁剪旋转、长边规整、PNG 编码与哈希、上传规整及两个 op，约 360）；② 图像增强与质量评分（prepare 编排、光照/去噪/局部对比度/二值化、deskew、质量评分与阈值加载、img.prepare，约 255）。

