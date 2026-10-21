# CORE-29 测试方案

> 来源卡：[S5_CORE-29_扩展.md](../../core/S5_CORE-29_扩展.md)（识别契约与后端注册）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R07] 契约测试：Fake 本地后端注册后可替换；Fake 本地后端与 CORE-34 返回的 `RawOutput` 经同一后处理（CORE-31）。
- [R26] `available(Guest)` 不含任何 `networked = true` 的后端；游客传入远程后端 id 返回 `RECOG_BACKEND_NOT_ALLOWED`。
- [R22] CI 检查：主线源码与依赖树中不存在 `yolo-experiment` 与 YOLO 相关依赖。
- [R06] 墨迹规范渲染：`crates/fml-recognize/tests/fixtures/ink/` 中 20 组笔迹在 Android 与 Windows 上渲染的 PNG 字节一致，与提交的期望哈希相同。
- [R19] 识别模式向量：`contracts/vectors/recognition-mode.json` 的 values 与 RecognitionMode serde 双向逐项一致、invalid 全部反序列化失败；与 CORE-33 的 RecognitionModeWire 由同一文件测试。
- [R19] 错误表逐行测试：空墨迹、超限墨迹、暂存区外路径、未注册 id 各返回约定错误码。
- [R31] recog.run 图片输入：image_path 在 staging_root 外、经符号链接指向外部或缺 staging_root 均报 RECOG_INPUT_INVALID；墨迹输入不需要 staging_root。
