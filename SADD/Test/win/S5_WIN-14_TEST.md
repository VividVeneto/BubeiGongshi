# WIN-14 测试方案

> 来源卡：[S5_WIN-14_平台.md](../../win/S5_WIN-14_平台.md)（快捷键自定义）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R08] 单元测试：把分式改为 Ctrl+Shift+F 后 `KeymapHolder.value` 立即生效；重新 `load` 后保持；偏好中只含 `fraction` 一项；`resetCommand` 后偏好被删除。
- [R08] 单元测试：把根号设为 Ctrl+/ 返回 `Conflict(fraction)`；`replace` 后分式不再有该键、根号有；把新建公式（全局）设为 Ctrl+R 返回 `Conflict(sqrt)`。
- [R08] 单元测试：为编辑器或全局命令录制 Ctrl+C、Ctrl+Space、Ctrl+.、Alt+F4、Ctrl+Alt+E、单独字母 A、Shift+A 均返回 `Rejected`；F5 与 Alt+Shift+M 返回 `Assigned`。
- [R19] 单元测试：`keymap.v1` 为非法 JSON、`"v": 2` 或含保留键时 `load` 返回默认（`defaultKeymap` 与 `defaultStudyBindings`）且不抛异常；`resetAll` 后两组键位都等于默认且偏好被删除。
- [R08] Widget 测试：设置页“快捷键”区按 WIN-08 默认表列出全部命令与按键；录制对话框打开期间按 Ctrl+1 不导航、按 Ctrl+/ 不插入分式、按 Ctrl+Enter 不触发学习主操作；修改后的键位在列表中显示并标记可“恢复默认”。
- [R42.b] 单元测试：把 `study.pause` 改为 Ctrl+Shift+Q 后 `StudyKeymapHolder.value` 与 WIN-15 `WindowsShortcutLabels.labelOf('study.pause')` 立即更新，重新 `load` 后保持且偏好 `bindings` 只含 `"study.pause"`；为 `study.option1` 录制单独字母 Q 返回 `Assigned`，为 `study.skip` 录制单独字母 Q 返回 `Rejected`；为 `study.rateKnew` 录制 Ctrl+F 返回 `Conflict(AppCommand(findInLibrary))`；为全局命令 `goStudy` 录制 Ctrl+Enter 返回 `Conflict(StudyKeyCommand(primary))`。
- [R42.b] 单元测试（键位冲突）：`defaultStudyBindings` 中任一组合键 `isReservedChord` 为 false，且与 `defaultKeymap` 全部组合键无交集；`KeymapPrefs.load` 读入的默认 `KeymapSet` 满足实现约束 ① ②。
- [R42.b] Widget 测试：设置页“学习”组按 WIN-15 a 表顺序列出 12 个命令与默认按键；“全部恢复默认”后学习键位等于 `defaultStudyBindings`。
- [R08] 手动：开启微软拼音输入法时录制 Ctrl+Space 被拒绝并提示原因；修改“下标”为 Ctrl+Shift+- 后在编辑器中立即可用，重启应用后仍然有效。

- [R42.d] 将本卡完整keymap JSON示例作为fixture，decode全部成功且encode返回逐字相同的11位hex规范串。

- [R08][R42.b] 根号经replace占用分式默认键后resetCommand(fraction)返回Conflict(sqrt)，两组与偏好均不变；清除占用后恢复成功。App/Study跨组同样预检，保存失败内存仍保持无冲突并提示，resetAll不因单项预检留半成品。
