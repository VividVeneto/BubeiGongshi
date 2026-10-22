### WIN-04 文件选择、复制与导出

**目标**：通过文件对话框导入图片和文档，通过保存对话框导出文件；导入不冻结界面、不改动原文件、不残留临时副本。

**范围**
- 包含：`ImagePicker`、`DocumentPicker`、`FileExporter`、`CameraController`（不支持）端口实现；HEIC/HEIF 经 WIC 转 JPEG；临时副本管理。
- 不包含：图片探测、解码与预处理（CORE-30，由 CORE-40 调用）；裁剪与识别界面（CORE-40、CORE-50）；资源包安装（CORE-51 经 `DocumentPicker` 选文件后调用 CORE-15）。

**依赖**：CORE-01、CORE-02、CORE-04、WIN-01、WIN-17

**接口契约**

实现的端口与接缝（逐字摘录，定义见 CORE-04；`ImportedImage`、`PickedDocument` 见 CORE-04）：

```dart
/// 图片来源：系统选择器、文件管理器、拖拽、剪贴板、扫描。
abstract interface class ImagePicker {
  Future<List<ImportedImage>> pick({required int maxCount});  // maxCount 1–10，越界抛 ArgumentError；用户取消返回空列表
}
abstract interface class CameraController {
  Future<ImportedImage?> capture();                           // 用户取消返回 null；只写应用私有目录
}
abstract interface class FileExporter {
  Future<bool> saveAs(String suggestedName, Stream<List<int>> bytes); // 由用户选择保存位置；用户取消返回 false
}
/// 非图片文件选择（备份恢复 CORE-84、公式批量导入 CORE-79）：由系统选择器选取后复制到 StoreArea.staging。
abstract interface class DocumentPicker {
  Future<PickedDocument?> pick({required List<String> extensions, required int maxBytes});
  // extensions 为小写、不含点（如 ['fmlbackup']、['csv', 'tex', 'txt']）；用户取消返回 null；超过 maxBytes 抛 PLATFORM_FILE_TOO_LARGE
}
```

本卡实现（`app/lib/platform/windows/picker/`）：

```dart
final class WindowsImagePicker implements ImagePicker { WindowsImagePicker(this.files); final LocalFileStore files; }
final class WindowsDocumentPicker implements DocumentPicker { WindowsDocumentPicker(this.files); final LocalFileStore files; }
final class WindowsFileExporter implements FileExporter { const WindowsFileExporter(); }
final class WindowsCamera implements CameraController { const WindowsCamera(); }   // capture() 恒抛 FmlException(PLATFORM_UNSUPPORTED)
// files 为 WIN-07 的 WindowsFileStore 实例，在 ports_windows.dart 中注入
```

```text
MethodChannel "fml/windows/files"（app/windows/runner/file_dialog.cpp；对话框在 UI 线程以 IFileDialog 模态显示，复制与转码在工作线程）
  openImages {max}            → {items: [{name, size, path}], truncated: bool}   IFileOpenDialog，FOS_ALLOWMULTISELECT | FOS_FILEMUSTEXIST | FOS_FORCEFILESYSTEM，
                                过滤器 “图片 (*.png;*.jpg;*.jpeg;*.webp;*.heic;*.heif)”；选中超过 max 时 items 只取前 max 个并置 truncated: true；无选中（用户取消）返回 {items: [], truncated: false}
  openDocument {exts}         → {name, size, path} 或 null    过滤器由 exts 生成（“*.fmlbackup” 等）
  saveDocument {name, ext}    → path 或 null                  IFileSaveDialog，默认文件夹 FOLDERID_Documents，FOS_OVERWRITEPROMPT
  copyImage {src, dest_dir, max_bytes} → {mime, size, path}
                                size > max_bytes → 不复制，返回 {mime, size}（无 path）；
                                .heic/.heif → IWICImagingFactory 解码（长边 ≤ 4096）后以 JPEG 质量 92 写出，mime 为 image/jpeg；
                                创建解码器或GetFrame/CopyPixels任一步失败→抛PLATFORM_UNSUPPORTED；其余按扩展名定 mime 并复制
  copyDocument {src, dest_path, max_bytes} → null             超过 max_bytes 抛 PLATFORM_FILE_TOO_LARGE

规则：
  ImagePicker.pick：openImages → {items, truncated}；只为 items 逐个 copyImage(dest_dir = root(staging)\tmp-import\picker\<batch_id>, max_bytes = 20 MiB) 并按返回副本构造 ImportedImage；无 path 的项其 readBytes 抛 PLATFORM_FILE_TOO_LARGE；truncated 只用于本卡调试日志与 WIN-17 主机验收断言，不改变复制数量，CORE-04 的 ImagePicker.pick 签名不变（不新增返回值）
  DocumentPicker.pick：openDocument → 扩展名（小写）不在 extensions → PLATFORM_FILE_TYPE_MISMATCH；size > maxBytes → PLATFORM_FILE_TOO_LARGE；
                       否则 copyDocument 到 root(staging)\<UUID>.<ext>
  FileExporter.saveAs：saveDocument → null 返回 false；否则写入 <path>.fmlpart（64 KiB 分块，Dart 侧 IOSink），完成后改名覆盖目标；失败删除 .fmlpart，抛 PLATFORM_IO
```

- 错误码：只使用 CORE-04 登记的 `PLATFORM_UNSUPPORTED`、`PLATFORM_IO`、`PLATFORM_FILE_TOO_LARGE`、`PLATFORM_FILE_TYPE_MISMATCH`；本卡不新增错误码。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-18汇总（下游说明，非契约）。

picker仅拥有staging/tmp-import/picker/<batch_id>/；drop目录、订阅与登记归WIN-19，clipboard归WIN-05。batch_id为每次操作新UUID；平台工厂发布本端口前await唯一init Future，重入等待同一Future。批次归属判据：每个批次目录写 `.owner`（UTF-8 文本，含 pid 与进程启动时刻）；启动清理只删能确认上次进程已退出的批次——`.owner` 可解析、且其 pid 已不存在，或该 pid 已被复用（登记的启动时刻与现存进程启动时刻不一致）；pid 仍存活即跳过；`.owner` 缺失、不可解析或查询进程失败无法确认（含权限/IO 错误）一律保守跳过并保留目录，不以“启动时刻早于本进程”单独作为删除依据；当前 batch_id 永不删除；清理只在初始化 Future 内做一次，不实现常驻进程巡检或退出清理。到期/结束先关闭本批句柄再删除，仅结束自己的上批；错误留待下次启动重试，不递归清空共用根。

**实现约束**
- WIN-19 通过本卡已有 `fml/windows/files.copyImage` 受限复制/转码方法复用读取实现；该方法由本卡唯一拥有，调用者只传自己的drop批次目录，不接管picker状态。
- 读取一次即复制；不保存原文件路径（含识别历史），不删除、不修改、不加锁用户原文件；复制失败时删除已写部分。
- Dart 层除 HEIC 转换外不解码图片；HEIC 转换在原生工作线程降采样输出，主线程只等待通道结果。
- `ImportedImage.expiresAt` 为创建后 1 h；到期或导入会话结束删除副本；WindowsImagePicker首次请求前await唯一初始化Future，只清理按 `.owner` 判定为上次进程已退出或 pid 已被复用的 picker 批次目录（判据见上），无法确认时跳过不删；构造器不启动悬空异步删除，不触碰clipboard目录。删除前确保本卡打开的句柄已关闭；删除失败的副本留待下次启动清空。
- 外部前提：HEIC/HEIF的WIC编解码能力取决于系统、HEIF图像扩展与可能需要的HEVC视频扩展（含授权）；1809/11组合须M0实测。任一解码步骤失败提示“当前系统无法解码，请检查HEIF/HEVC扩展或转换为JPEG”，不保证安装某一扩展必然成功。

**验收标准**：测试方案全文见 [Test/win/S5_WIN-04_TEST.md](../Test/win/S5_WIN-04_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 510 行；`app/lib/platform/windows/picker/` 与 `app/windows/runner/file_dialog.cpp`。分阶段：① Dart端口、文件对话框与文档/导出约315行；② WIC/受限复制及picker生命周期约195行；两阶段以替身隔离未交付转码，分别构建与验收。数据/自测不计，包含本卡端口构造接入行。
