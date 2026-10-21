# WIN-04 测试方案

> 来源卡：[S5_WIN-04_平台.md](../../win/S5_WIN-04_平台.md)（文件选择、复制与导出）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R37] 手动：经文件对话框选择 1 张与 10 张图片均进入裁剪页；选择 12 张时只导入前 10 张。
- [R36] 导入并完成识别后 本次picker批次目录为空，其他适配器仍有效，原文件哈希与修改时间不变；`WindowsCamera.capture()` 抛 `PLATFORM_UNSUPPORTED`。
- [R27] 经保存对话框导出 50 MiB 备份：默认位于“文档”，文件哈希与源一致；取消返回 false 且无 `.fmlpart` 残留；`DocumentPicker.pick(extensions: ['fmlbackup'])` 选中 `.txt` 抛 `PLATFORM_FILE_TYPE_MISMATCH`。
- [R01] CORE-04 的 `ImagePicker`、`DocumentPicker`、`FileExporter`、`CameraController` 契约套件（对话框步骤以 显式FML_TEST_BUILD构建中的FML_TEST_DIALOG_RESULT编译期define注入预设路径；默认入口为空；正式发布CI拒绝FML_TEST_*，非测试构建发现非空define在运行时抛StateError）在 Windows 10 与 11 上通过。

- [R19][R36] 交错启动picker清理与clipboard.readImage：初始化完成后首个pick才复制；活动clipboard批次在picker构造、选择、结束及到期清理后仍可读；结束A只删A目录，原文件哈希/mtime不变。