# WIN-05 测试方案

> 来源卡：[S5_WIN-05_平台.md](../../win/S5_WIN-05_平台.md)（剪贴板与多格式复制）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R37] 手动：用截图工具复制公式区域，在识别页按 Ctrl+V 进入裁剪预览；从画图复制（仅 CF_DIB）同样可粘贴。
- [R10] 粘贴含 `\input` 的 LaTeX 文本到编辑器，显示 `PARSE_FORBIDDEN_COMMAND` 并定位（经 CORE-59 编辑控制器的粘贴处理）。
- [R08] 集成测试：以 CORE-52 夹具负载调用 `setFormula` 后用 `EnumClipboardFormats` 读回，九个注册/标准格式名（三种 MathML 名、HTML Format、image/svg+xml、PNG、CF_DIB、CF_UNICODETEXT、text/x-latex）全部存在；PNG等于原png字节；三种MathML、SVG和LaTeX去格式终止符后按UTF-8解码等于对应输入；CF_UNICODETEXT以UTF-16LE解码并去末尾NUL后等于text；CF_HTML按UTF-8字节偏移取片段等于html；CF_DIB检查32位头/尺寸与白底合成后的像素黄金文件，不要求等于PNG字节；CF_HTML 头中的偏移指向的片段等于 `html`；“复制为图片”负载只有 PNG、CF_DIB 与 SVG，无 CF_UNICODETEXT。
- [R08] 手动矩阵（结果记入附录 D）：在公式详情点“复制公式”后，记事本得到 LaTeX 源码；Word 得到可编辑公式或清晰图片；画图得到图片；浏览器富文本框得到图片；“复制为 → Unicode 文本”在记事本得到 Unicode 文本。
- [R20] 粘贴与复制后检查 `logs\`，不含剪贴板文本与公式源码。
- [R01] CORE-04 `ClipboardAdapter` 契约套件在 Windows 上通过；剪贴板为空时 `readImage` 返回 null。

- [R08][R19] 使用含中文、非BMP符号、半透明像素的固定负载，分别断言UTF-8/UTF-16往返、CF_HTML字节偏移和DIB白底合成像素；未知格式不写，输入缺text时不产生CF_UNICODETEXT。
