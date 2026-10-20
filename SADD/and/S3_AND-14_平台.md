### AND-14 剪贴板与公式多格式复制

**目标**：实现用户触发的剪贴板读写与公式图文复制，从导入卡独立验收。

**范围**
- 包含：ClipboardAdapter、FormulaClipboardWriter、ClipboardBridge.kt、FileProvider与临时clip目录。
- 不包含：公式格式生成（CORE-52）、图片/文档选择与文件导出（AND-03，下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-52、AND-01、AND-02、AND-15

**接口契约**
```dart
abstract interface class ClipboardAdapter {
  Future<String?> readText();
  Future<void> writeText(String text);
  Future<ImportedImage?> readImage();                         // 剪贴板无图片或平台不支持时返回 null
}
abstract interface class FormulaClipboardWriter {  // 平台卡经 PlatformPorts.platformInstallers 登记（WIN-05、AND-14）
  Future<bool> write(FormulaClipboardPayload payload);   // 平台不支持的字段忽略；返回 true 表示系统已显示复制反馈（如 Android 13+）
}
final class AndroidClipboard implements ClipboardAdapter { AndroidClipboard(); }      // 文本经 Flutter Clipboard；图片经通道
final class AndroidFormulaClipboard implements FormulaClipboardWriter { const AndroidFormulaClipboard(); }   // API 33+ 返回 true（系统显示复制预览）
void installAndroidClipboard(CompositionContext ctx) => ctx.features.register<FormulaClipboardWriter>(const AndroidFormulaClipboard());
```
ports_android.dart将clipboard字段替换为本卡实现并追加安装点；Dart路径app/lib/platform/android/clipboard/。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
```text
MethodChannel fml/android/clipboard（ClipboardBridge.kt，实现AND-01 AndroidChannelModule）
  clipboardImage → {name,mime,size,tmp_path}或null；复制image/* URI到私有tmp-clipboard批目录，ImportedImage按CORE-04生命周期。
  setFormula   {text?, html?, png?}     → {system_feedback: bool}
               png 写入 cacheDir/clip/<UUID>.png（先删除该目录中旧文件，只保留最近一次），经 FileProvider（authority ${applicationId}.clip）取 content URI；
               ClipData(ClipDescription("公式", [text 有 → text/plain，html 有 → text/html，png 有 → image/png]),
                        ClipData.Item(text, html, null, pngUri))；只有 png 时用 ClipData.newUri（复制为图片）；
               ClipboardManager.setPrimaryClip；system_feedback = SDK_INT ≥ 33；mathml、svg、latex 字段 Android 不写（无通用接收方）
```
只复用CORE-04 PLATFORM_IO/PLATFORM_FILE_TOO_LARGE，不新增错误码。

图片读取只接受实际解码格式JPEG/PNG/WebP并返回对应image/jpeg、image/png、image/webp；先检查可知长度>20MiB则拒绝，未知长度流式复制到20MiB+1即停止删除副本并抛PLATFORM_FILE_TOO_LARGE；GIF/HEIC/SVG及其他image/*返回PLATFORM_UNSUPPORTED，不只改后缀或MIME冒充支持。Clipboard外部URI必须持临时读取授权；失效返回PLATFORM_IO。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

**实现约束**
- 只在用户粘贴/复制时访问，不后台监听、不写私有MIME、不自动清空剪贴板；系统API33+复制反馈返回true。
- provider条目由AND-02合并清单主体维护，本卡只追加：androidx.core.content.FileProvider，authority=${applicationId}.clip，exported=false/grantUriPermissions=true；res/xml/clip_paths.xml仅cache-path name=clip path=clip/；白名单追加一行。
- 仅删除自有clip文件，copy目录保留最后一次；外部接收方URI临时授权能力为M0实测前提，微信/QQ/便签结果记D，失败退text/plain。

**验收标准**
- [R08] 仪器测试：以 CORE-52 夹具负载 `write` 后读回主剪贴项：描述含 text/plain、text/html、image/png，`coerceToText` 为 LaTeX 源码，`htmlText` 等于负载 html，URI 可经 `ContentResolver` 读出与负载相同的 PNG；连续复制两次后 `cacheDir/clip/` 只剩 1 个文件；“复制为图片”只有 image/png。
- [R08] 手动矩阵（结果记入附录 D）：“复制公式”后在系统便签/备忘录粘贴得到 LaTeX 或图片、在微信输入框粘贴得到 LaTeX 文本、“复制为 → 图片”后在支持图片粘贴的聊天应用得到公式图片。
- [R08] 单元测试：长度已知 20 MiB+1 的图片直接抛 `PLATFORM_FILE_TOO_LARGE`；长度未知的流复制到 20 MiB+1 字节即停止、删除副本并抛同一码；GIF、HEIC、SVG 返回 `PLATFORM_UNSUPPORTED`；PNG 的 MIME 按实际解码结果为 image/png，扩展名改为 .jpg 也不变。
- [R01] CORE-04 ClipboardAdapter契约套件通过；读取无图片返回null，下一次readImage即结束上一批，已复制到业务staging的文件不被清理。

**规模**：约 240 行；app/lib/platform/android/clipboard/、app/android/.../ClipboardBridge.kt与res/xml/clip_paths.xml（同app构建单元），附属清单与审计白名单追加行。

