### WIN-04 文件导入、拖拽与导出

**目标**：通过文件对话框与拖放导入图片和文档，通过保存对话框导出文件；导入不冻结界面、不改动原文件、不残留临时副本。

**范围**
- 包含：`ImagePicker`、`DocumentPicker`、`FileExporter`、`CameraController`（不支持）端口实现；`ImageDropSource`（CORE-50 定义）实现与登记；拖入文件夹的一层扫描与确认；HEIC/HEIF 经 WIC 转 JPEG；临时副本管理。
- 不包含：图片探测、解码与预处理（CORE-30，由 CORE-40 调用）；裁剪与识别界面（CORE-40、CORE-50）；资源包安装（CORE-51 经 `DocumentPicker` 选文件后调用 CORE-15）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-50、WIN-01、WIN-17

**接口契约**

实现的端口与接缝（逐字摘录，定义见 CORE-04、CORE-50；`ImportedImage`、`PickedDocument` 见 CORE-04）：

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
/// 非图片文件选择（备份恢复 CORE-27、公式批量导入 CORE-14）：由系统选择器选取后复制到 StoreArea.staging。
abstract interface class DocumentPicker {
  Future<PickedDocument?> pick({required List<String> extensions, required int maxBytes});
  // extensions 为小写、不含点（如 ['fmlbackup']、['csv', 'tex', 'txt']）；用户取消返回 null；超过 maxBytes 抛 PLATFORM_FILE_TOO_LARGE
}
abstract interface class ImageDropSource {          // 平台卡经 platformInstallers 登记（WIN-04）；未登记时识别页不响应拖放
  Stream<DroppedImages> drops({Future<bool> Function(int count, int bytes, int other)? confirmFolder}); }
```

本卡实现（`app/lib/platform/windows/picker/`）：

```dart
final class WindowsImagePicker implements ImagePicker { WindowsImagePicker(this.files); final LocalFileStore files; }
final class WindowsDocumentPicker implements DocumentPicker { WindowsDocumentPicker(this.files); final LocalFileStore files; }
final class WindowsFileExporter implements FileExporter { const WindowsFileExporter(); }
final class WindowsCamera implements CameraController { const WindowsCamera(); }   // capture() 恒抛 FmlException(PLATFORM_UNSUPPORTED)
final class WindowsImageDrop implements ImageDropSource { WindowsImageDrop(this.files); final LocalFileStore files; }
void installWindowsImport(CompositionContext ctx);   // 登记 ImageDropSource；追加到 ports_windows.dart 的 platformInstallers（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
// files 为 WIN-07 的 WindowsFileStore 实例，在 ports_windows.dart 中注入
```

```text
MethodChannel "fml/windows/files"（app/windows/runner/file_dialog.cpp；对话框在 UI 线程以 IFileDialog 模态显示，复制与转码在工作线程）
  openImages {max}            → [{name, size, path}] 或 []   IFileOpenDialog，FOS_ALLOWMULTISELECT | FOS_FILEMUSTEXIST | FOS_FORCEFILESYSTEM，
                                过滤器 “图片 (*.png;*.jpg;*.jpeg;*.webp;*.heic;*.heif)”；选中超过 max 时只取前 max 个并在结果附 truncated: true
  openDocument {exts}         → {name, size, path} 或 null    过滤器由 exts 生成（“*.fmlbackup” 等）
  saveDocument {name, ext}    → path 或 null                  IFileSaveDialog，默认文件夹 FOLDERID_Documents，FOS_OVERWRITEPROMPT
  copyImage {src, dest_dir, max_bytes} → {mime, size, path}
                                size > max_bytes → 不复制，返回 {mime, size}（无 path）；
                                .heic/.heif → IWICImagingFactory 解码（长边 ≤ 4096）后以 JPEG 质量 92 写出，mime 为 image/jpeg；
                                创建解码器或GetFrame/CopyPixels任一步失败→抛PLATFORM_UNSUPPORTED；其余按扩展名定 mime 并复制
  copyDocument {src, dest_path, max_bytes} → null             超过 max_bytes 抛 PLATFORM_FILE_TOO_LARGE
  scanFolder {path}           → {images: [path], other: int, bytes: int}   只扫描一层，不跟随符号链接与连接点
  Dart 收到的调用：dropped {paths: [string]}                    WM_DROPFILES（DragAcceptFiles(hwnd, TRUE)）→ DragQueryFileW 全部路径

规则：
  ImagePicker.pick：openImages → 逐个 copyImage(dest_dir = root(staging)\tmp-import\picker\<batch_id>, max_bytes = 20 MiB)；无 path 的项其 readBytes 抛 PLATFORM_FILE_TOO_LARGE
  DocumentPicker.pick：openDocument → 扩展名（小写）不在 extensions → PLATFORM_FILE_TYPE_MISMATCH；size > maxBytes → PLATFORM_FILE_TOO_LARGE；
                       否则 copyDocument 到 root(staging)\<UUID>.<ext>
  FileExporter.saveAs：saveDocument → null 返回 false；否则写入 <path>.fmlpart（64 KiB 分块，Dart 侧 IOSink），完成后改名覆盖目标；失败删除 .fmlpart，抛 PLATFORM_IO
  ImageDropSource.drops：dropped 路径按扩展名分为图片与其他；某路径为文件夹 → scanFolder，调用drops的confirmFolder(count,bytes,other)，共享界面负责确认框；回调缺失按取消，平台不创建业务确认UI；
                       取消则整批丢弃；图片取前 10 张 copyImage，其余计入 skippedOverLimit，非图片计入 skippedNotImage；
                       0 张图片时仍发送批次以便提示（images 为空的批次不进入识别流程，由 CORE-50 只显示提示）
```

- 错误码：只使用 CORE-04 登记的 `PLATFORM_UNSUPPORTED`、`PLATFORM_IO`、`PLATFORM_FILE_TOO_LARGE`、`PLATFORM_FILE_TYPE_MISMATCH`；本卡不新增错误码。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

picker与drop分别拥有staging/tmp-import/picker/<batch_id>/和drop/<batch_id>/，batch_id为每次操作新UUID；同一适配器后续操作只按CORE-04结束自己的上批，不使clipboard等其他批次失效。平台工厂在发布端口前await picker/drop/clipboard各自init，重入请求等待同一Future；启动恢复只清理已确认上次进程的批次，当前活动集合中的目录永不删除。到期/批次结束关闭本批句柄后删除本批目录；错误保留待下次启动，不递归清空共用根。

**实现约束**
- 读取一次即复制；不保存原文件路径（含识别历史），不删除、不修改、不加锁用户原文件；复制失败时删除已写部分。
- Dart 层除 HEIC 转换外不解码图片；HEIC 转换在原生工作线程降采样输出，主线程只等待通道结果。
- `ImportedImage.expiresAt` 为创建后 1 h；到期或导入会话结束删除副本；WindowsImagePicker首次请求前await唯一初始化Future，只清理上次进程遗留的picker/drop批次目录；构造器不启动悬空异步删除，不触碰clipboard目录。删除前确保本卡打开的句柄已关闭；删除失败的副本留待下次启动清空。
- 拖放只在识别页订阅期间生效（CORE-50）；其他页面拖入时 `drops` 无订阅者，事件被丢弃且不复制文件。
- 外部前提：HEIC/HEIF的WIC编解码能力取决于系统、HEIF图像扩展与可能需要的HEVC视频扩展（含授权）；1809/11组合须M0实测。任一解码步骤失败提示“当前系统无法解码，请检查HEIF/HEVC扩展或转换为JPEG”，不保证安装某一扩展必然成功。

**验收标准**
- [R37] 手动：经文件对话框选择 1 张与 10 张图片均进入裁剪页；选择 12 张时只导入前 10 张。
- [R37] 拖入 3 张图片与 1 个 txt：识别页进入裁剪，提示跳过 1 个非图片文件；拖入含 200 张图片的文件夹先显示数量与大小确认框，取消后无副本产生。
- [R31] 拖入 25 MiB 图片：不复制，`readBytes` 抛 `PLATFORM_FILE_TOO_LARGE` 并提示；导入 1200 万像素 JPEG 期间界面无超过 100 ms 的帧卡顿（DevTools 时间线）。
- [R36] 导入并完成识别后 本次picker/drop批次目录为空，其他适配器仍有效，原文件哈希与修改时间不变；`WindowsCamera.capture()` 抛 `PLATFORM_UNSUPPORTED`。
- [R27] 经保存对话框导出 50 MiB 备份：默认位于“文档”，文件哈希与源一致；取消返回 false 且无 `.fmlpart` 残留；`DocumentPicker.pick(extensions: ['fmlbackup'])` 选中 `.txt` 抛 `PLATFORM_FILE_TYPE_MISMATCH`。
- [R01] CORE-04 的 `ImagePicker`、`DocumentPicker`、`FileExporter`、`CameraController` 契约套件（对话框步骤以 显式FML_TEST_BUILD构建中的FML_TEST_DIALOG_RESULT编译期define注入预设路径；默认入口为空；正式发布CI拒绝FML_TEST_*，非测试构建发现非空define在运行时抛StateError）在 Windows 10 与 11 上通过。

- [R19][R36] 交错启动picker清理与clipboard.readImage：初始化完成后首个pick才复制；活动clipboard批次在picker/drop构造、选择、结束及到期清理后仍可读；结束A只删A目录，原文件哈希/mtime不变。

**规模**：约 450 行；`app/lib/platform/windows/picker/` 与 `app/windows/runner/file_dialog.cpp`（同属 `app/` 构建单元）。

