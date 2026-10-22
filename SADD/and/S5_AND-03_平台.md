### AND-03 相册、文件导入与导出

**目标**：用系统选择器从相册与文件管理器导入图片和文档（不申请存储权限）与导出文件能力；剪贴板迁至AND-14（下游说明，非契约）。

**范围**
- 包含：`ImagePicker`、`DocumentPicker`、`FileExporter`端口实现；Photo Picker / SAF 选择；HEIC/HEIF 转 JPEG；临时副本管理；Kotlin 侧 `ImportBridge.kt`。
- 不包含：图片探测、解码与预处理（CORE-30，由 CORE-40 调用）；裁剪与识别界面（CORE-40）；私有目录的位置（经注入的 CORE-04 `LocalFileStore` 接口取得，实现在 AND-06）；复制格式内容的生成（CORE-52）。

**依赖**：CORE-01、CORE-02、CORE-04、AND-15

**接口契约**

实现的端口与接缝（CORE-04，逐字摘录；`ImportedImage`、`PickedDocument` 定义见 CORE-04）：

```dart
/// 图片来源：系统选择器、文件管理器、拖拽、剪贴板、扫描。
abstract interface class ImagePicker {
  Future<List<ImportedImage>> pick({required int maxCount});  // maxCount 1–10，越界抛 ArgumentError；用户取消返回空列表
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

本卡实现（`app/lib/platform/android/picker/`）：

```dart
final class AndroidImagePicker implements ImagePicker { AndroidImagePicker(); }
final class AndroidFileExporter implements FileExporter { AndroidFileExporter(); }
final class AndroidDocumentPicker implements DocumentPicker { AndroidDocumentPicker(this.files); final LocalFileStore files; }
// ports_android.dart 中以 AndroidDocumentPicker(<AND-06 的 LocalFileStore 实例>) 组装
```

```text
MethodChannel "fml/android/import"（ImportBridge.kt）
  pickImages   {max}                    → [{name, mime, size, tmp_path?}]
               API 33+ 或有回移 Photo Picker 的设备max=1用PickVisualMedia；max≥2用PickMultipleVisualMedia(min(max,系统getPickImagesMaxLimit()))，否则 ACTION_OPEN_DOCUMENT（MIME image/jpeg、image/png、image/webp，
               API 28+ 另加 image/heic、image/heif；EXTRA_ALLOW_MULTIPLE，超过 max 时只取前 max 个）
               每项：size > 20 MiB → 不复制，tmp_path 缺省（readBytes 抛 PLATFORM_FILE_TOO_LARGE）；
                     HEIC/HEIF → ImageDecoder 解码（目标长边 ≤ 4096）后以 JPEG 质量 92 写出，mime 改为 image/jpeg；
                     其余原样复制到 cacheDir/tmp-import/picker/<UUID>
  createDocument {name, mime}           → content URI 字符串或 null（用户取消）
  writeChunk   {uri, bytes, append}     → null      Dart 按 64 KiB 分块推送；任一块失败抛 PLATFORM_IO 并删除已写文档
  openDocument {mimes}                  → {name, size, uri} 或 null
  copyDocument {uri, dest_path, max}    → null      超过 max 中止并删除目标，抛 PLATFORM_FILE_TOO_LARGE
扩展名 → MIME：fmlbackup → application/octet-stream；csv → text/csv；tex、txt → text/plain；json → application/json；png → image/png
DocumentPicker：按 MIME 打开；选中文件扩展名不在 extensions 中 → PLATFORM_FILE_TYPE_MISMATCH；
                复制到 root(StoreArea.staging)/<UUID>.<ext>，返回 PickedDocument
```

- 错误码：只使用 CORE-04 登记的 `PLATFORM_IO`、`PLATFORM_FILE_TOO_LARGE`、`PLATFORM_FILE_TYPE_MISMATCH`；本卡不新增错误码。

Photo Picker数量分支在返回结果后统一截断至maxCount并去重；即使SAF不遵守EXTRA_ALLOW_MULTIPLE或返回超限也不复制多余URI。maxCount=1不得构造PickMultipleVisualMedia，系统可用性检测失败走SAF；AndroidX版本及ActivityResult探针仍M0外部前提。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

产品约束追踪：见README §6 Q12；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 不申请存储权限，不调用 `takePersistableUriPermission`；读取一次即复制，不保存源 URI 与原文件路径。
- Dart/Kotlin 层除 HEIC 转换外不解码图片；HEIC 解码在原生侧降采样输出，不把全尺寸 Bitmap 交给 Dart。
- `ImportedImage.expiresAt` 为创建后 1 h；到期或CORE-04 定义的批次结束时删除副本；应用启动时清空 `cacheDir/tmp-import/picker/`（初始化Future完成清理后才允许首次pick；不在构造时启动悬空异步删除，不触碰camera/clipboard目录）。
- 只删除本应用创建的副本，绝不删除或修改相册与文件管理器中的原始文件；不向相册写入。

**验收标准**：测试方案全文见 [Test/and/S5_AND-03_TEST.md](../Test/and/S5_AND-03_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 570 行；`app/lib/platform/android/picker/`、`app/android/.../ImportBridge.kt`、`app/`。组件估算：Dart三端口封装与参数校验约 120 行，原生选择器与回调约 95 行，流式复制/限额/文档校验约 100 行，HEIC降采样转码约 50 行，导出分块/失败清理约 65 行，临时批次生命周期约 135 行，模块/端口接入约 5 行（清单审计只消费 AND-02 的 `tools/ci/check_android_manifest.py`，本卡不改该脚本、不计该脚本行数）。分阶段：① 选择器与文档复制约 300 行；② 导出、HEIC与生命周期约 270 行；各阶段以替身隔离后续能力，分别可构建、验收与提交，未交付阶段不声明通过。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。

