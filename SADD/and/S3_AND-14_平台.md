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

**验收标准**：测试方案全文见 [Test/and/S3_AND-14_TEST.md](../Test/and/S3_AND-14_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 305 行；。组件估算：Dart剪贴板/批次ImportedImage约 80 行，原生图文写入与FileProvider URI约 85 行，原生格式识别/限额复制与自有清理约 130 行，安装/模块/审计接入约 10 行。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。

