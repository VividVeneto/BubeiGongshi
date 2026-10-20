# AND-03 测试方案

> 来源卡：[S5_AND-03_平台.md](../../and/S5_AND-03_平台.md)（相册、文件导入与导出）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R38] 手动：分别通过 Photo Picker 与 SAF 选择图片，均返回 `ImportedImage`；全程未出现存储权限请求。
- [R38] 选择 11 张时只返回 10 个；CORE-04 定义的批次结束后 `cacheDir/tmp-import/picker/` 为空。
- [R31] 选择一张 25 MiB 的图片：`byteLength` 正确，`readBytes` 抛 `PLATFORM_FILE_TOO_LARGE`，未产生副本；在 API 28+ 选择 HEIC 照片得到 `image/jpeg`。
- [R36] 导入并完成识别后，原始相册图片的哈希与修改时间不变。
- [R27] `saveAs` 经 SAF 保存 50 MiB 流后文件哈希与源一致；`DocumentPicker.pick(extensions: ['fmlbackup'])` 选中 `.txt` 文件时抛 `PLATFORM_FILE_TYPE_MISMATCH`。
- [R01] CORE-04 的 `ImagePicker`、`FileExporter`、`DocumentPicker` 契约套件在真机通过（选择器步骤用 UI Automator 驱动）。

- [R38] 相机已有有效批次时初始化picker及连续两次pick，只删除picker旧批次；首次pick必须等待启动清理，返回文件仍可读。

- [R38] 主机/假ActivityResult分别以max=1、2、10验证单选/多选分支；SAF返回11张仅复制前10张，取消返回[]。真机选择器由AND-15框架（下游说明，非契约）在S7集中执行。
