### WIN-05 剪贴板与多格式复制

**目标**：只在用户显式操作时访问剪贴板；支持粘贴文本与图片；复制公式时一次写入多种 Windows 常见剪贴板格式，由粘贴目标自动选用（README §6 Q12）。

**范围**
- 包含：`ClipboardAdapter` 端口实现（文本经 Flutter `Clipboard`，图片经原生通道）；`WindowsFormulaClipboard`（实现 CORE-52 `FormulaClipboardWriter`）与登记；CF_HTML 包装。
- 不包含：各格式内容的生成（CORE-52）；复制按钮与“复制为”菜单（CORE-59）；粘贴文本的解析与安全预算（CORE-59 粘贴 → CORE-06）；粘贴图片后的裁剪（CORE-40/50）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-52、WIN-04、WIN-17

**接口契约**

实现的端口与接缝（逐字摘录，定义见 CORE-04、CORE-52）：

```dart
abstract interface class ClipboardAdapter {
  Future<String?> readText();
  Future<void> writeText(String text);
  Future<ImportedImage?> readImage();                         // 剪贴板无图片或平台不支持时返回 null
}
abstract interface class FormulaClipboardWriter {  // 平台卡经 PlatformPorts.platformInstallers 登记（WIN-05、AND-14）
  Future<bool> write(FormulaClipboardPayload payload);   // 平台不支持的字段忽略；返回 true 表示系统已显示复制反馈（如 Android 13+）
}
```

本卡实现（`app/lib/platform/windows/clipboard/`）：

```dart
final class WindowsClipboard implements ClipboardAdapter { WindowsClipboard(this.files); final LocalFileStore files; }
final class WindowsFormulaClipboard implements FormulaClipboardWriter { const WindowsFormulaClipboard(); }   // write 恒返回 false（由应用显示“已复制”）
void installWindowsClipboard(CompositionContext ctx) =>
    ctx.features.register<FormulaClipboardWriter>(const WindowsFormulaClipboard());
// 追加到 ports_windows.dart 的 platformInstallers（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
```

```text
MethodChannel "fml/windows/clipboard"（app/windows/runner/clipboard_channel.cpp）
  readImage {dest_dir}  → {mime: "image/png", size, path} 或 null
                         依次尝试注册格式 "PNG"、CF_DIBV5、CF_DIB；DIB 经 WIC 编码为 PNG；写入 dest_dir\<UUID>.png；
                         像素数 > 4000 万 → 不写文件，返回 {mime, size: 0}（readBytes 抛 PLATFORM_FILE_TOO_LARGE）
  setFormula {text?, latex?, mathml?, html?, svg?, png?} → null      （png 为字节；其余为字符串；缺省字段不写）
                         OpenClipboard（失败时每 50 ms 重试，最多 5 次）→ EmptyClipboard → 依次 SetClipboardData：
                           mathml → 注册格式 "MathML Presentation"、"MathML"、"application/mathml+xml"（UTF-8，无 BOM）
                           html   → 注册格式 "HTML Format"（CF_HTML：Version/StartHTML/EndHTML/StartFragment/EndFragment 头 + UTF-8）
                           svg    → 注册格式 "image/svg+xml"（UTF-8）
                           png    → 注册格式 "PNG" = 原字节；CF_DIB = 合成到白底后的 32 位 DIB
                           text   → CF_UNICODETEXT
                           latex  → 注册格式 "text/x-latex"（UTF-8）
                         → CloseClipboard；任一步失败 → 抛 PLATFORM_IO
WindowsClipboard：readText、writeText 用 Flutter Clipboard.getData/setData('text/plain')；
                  readImage 的 dest_dir = root(staging)\tmp-import\clipboard\<batch_id>（仅清理本适配器批次，初始化完成后接请求），返回的 ImportedImage 有效期 1 h
```

- 粘贴目标的选用（由目标程序决定，本卡只保证格式齐全）：

| 粘贴目标 | 预期取用的格式 | 得到 |
| --- | --- | --- |
| 记事本、VS Code、终端、聊天输入框的纯文本 | CF_UNICODETEXT | LaTeX 源码 |
| Word / PowerPoint / OneNote（Microsoft 365） | MathML 格式（优先）或 PNG | 可编辑公式（不认 MathML 时为图片） |
| 浏览器富文本编辑框、邮件客户端 | HTML Format | 公式图片（alt 为 LaTeX） |
| 画图、截图标注、QQ/微信图片粘贴 | PNG 或 CF_DIB | 公式图片 |
| Inkscape 等矢量软件 | image/svg+xml | 矢量公式 |

- 错误码：只使用 CORE-04 登记的 `PLATFORM_IO`、`PLATFORM_FILE_TOO_LARGE`；本卡不新增错误码。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

**实现约束**
- 只在用户按 Ctrl+V / Ctrl+C 或点击“粘贴”“复制公式”时访问剪贴板；不注册剪贴板监听（`AddClipboardFormatListener`），不读取剪贴板历史。
- 一次复制在同一次 `OpenClipboard` 内写完全部格式，先写信息量大的格式（顺序见上）；不使用延迟渲染（`SetClipboardData(fmt, NULL)`），应用退出后内容仍可粘贴。
- 不写应用私有格式；不设置“复制后自动清空”；不设置 `ExcludeClipboardContentFromMonitorProcessing` 等隐藏标记（剪贴板历史由用户的系统设置决定）。
- 剪贴板内容与复制的公式不写入日志（CORE-28 日志规则）。
- 粘贴的图片只返回 `ImportedImage`，是否进入裁剪由调用方决定（CORE-50 先进入裁剪预览，不直接识别）。
- 外部前提：Office 识别的 MathML 剪贴板格式名（"MathML Presentation"、"MathML"）与可编辑公式转换行为在 M0 用 Microsoft 365 当前通道验证并记入附录 D；不识别时 Word 退回 PNG，不影响其余目标。

**验收标准**
- [R37] 手动：用截图工具复制公式区域，在识别页按 Ctrl+V 进入裁剪预览；从画图复制（仅 CF_DIB）同样可粘贴。
- [R10] 粘贴含 `\input` 的 LaTeX 文本到编辑器，显示 `PARSE_FORBIDDEN_COMMAND` 并定位（经 CORE-59 编辑控制器的粘贴处理）。
- [R08] 集成测试：以 CORE-52 夹具负载调用 `setFormula` 后用 `EnumClipboardFormats` 读回，九个注册/标准格式名（三种 MathML 名、HTML Format、image/svg+xml、PNG、CF_DIB、CF_UNICODETEXT、text/x-latex）全部存在；PNG等于原png字节；三种MathML、SVG和LaTeX去格式终止符后按UTF-8解码等于对应输入；CF_UNICODETEXT以UTF-16LE解码并去末尾NUL后等于text；CF_HTML按UTF-8字节偏移取片段等于html；CF_DIB检查32位头/尺寸与白底合成后的像素黄金文件，不要求等于PNG字节；CF_HTML 头中的偏移指向的片段等于 `html`；“复制为图片”负载只有 PNG、CF_DIB 与 SVG，无 CF_UNICODETEXT。
- [R08] 手动矩阵（结果记入附录 D）：在公式详情点“复制公式”后，记事本得到 LaTeX 源码；Word 得到可编辑公式或清晰图片；画图得到图片；浏览器富文本框得到图片；“复制为 → Unicode 文本”在记事本得到 Unicode 文本。
- [R20] 粘贴与复制后检查 `logs\`，不含剪贴板文本与公式源码。
- [R01] CORE-04 `ClipboardAdapter` 契约套件在 Windows 上通过；剪贴板为空时 `readImage` 返回 null。

- [R08][R19] 使用含中文、非BMP符号、半透明像素的固定负载，分别断言UTF-8/UTF-16往返、CF_HTML字节偏移和DIB白底合成像素；未知格式不写，输入缺text时不产生CF_UNICODETEXT。

**规模**：约 320 行；`app/lib/platform/windows/clipboard/` 与 `app/windows/runner/clipboard_channel.cpp`（同属 `app/` 构建单元）。

