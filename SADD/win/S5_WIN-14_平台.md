### WIN-14 快捷键自定义

**目标**：在设置页提供快捷键自定义入口：查看全部快捷键（含 WIN-15 学习流程命令）、为命令录制新的组合键、检测冲突与保留键、恢复默认；自定义键位按设备保存（README §6 Q11）。

**范围**
- 包含：`KeymapPrefs`（键位的读取与保存，含学习命令）；把 WIN-15 `StudyCommand` 并入可自定义列表“学习”组；`KeymapEditorVm`（分配、冲突、清除与恢复默认）；设置区“快捷键”（order 60）与录制对话框；启动时加载自定义键位；安装点 `installWindowsKeymap`。
- 不包含：按键分发、默认键位表与保留键规则（WIN-08；学习命令的分发、默认键位与命令 ID 见 WIN-15）；键位方案的导入导出、多套预设方案与跨设备同步（V1 不做）；LaTeX 命令补全（CORE-53）与公式库批量操作（CORE-54）的按键（固定，经 WIN-08 表中“保留（固定）”行只读列出）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-36、WIN-06、WIN-08、WIN-15、CORE-28、WIN-17

**接口契约**

使用的上游类型（定义见 WIN-06、WIN-08、WIN-15、CORE-36）：`WindowsPrefs`（`get/set` 字符串偏好）；`ShortcutCommand`、`ShortcutScope`、`Keymap`、`defaultKeymap`、`isReservedChord`、`KeymapHolder`（WIN-08）；`KeyChord`、`StudyCommand`、`defaultStudyBindings`、`StudyKeymapHolder`、`WindowsKeyRouter`（WIN-15）；`SettingsSection`、`SettingsSections`。

```dart
// app/lib/platform/windows/keymap/
sealed class BindableCommand { const BindableCommand(); String get persistKey; String get titleKey; }
final class AppCommand extends BindableCommand { const AppCommand(this.command); final ShortcutCommand command; }       // persistKey = command.name
final class StudyKeyCommand extends BindableCommand { const StudyKeyCommand(this.command); final StudyCommand command; } // persistKey = command.id（如 "study.pause"）
final class KeymapSet {                             // 默认值 KeymapSet(defaultKeymap, defaultStudyBindings)
  const KeymapSet(this.app, this.study);
  final Keymap app; final Map<StudyCommand, List<KeyChord>> study;
}
final class KeymapPrefs {
  KeymapPrefs(this._prefs);                         // WindowsPrefs（WIN-06）
  Future<KeymapSet> load();                         // 读偏好 keymap.v1；缺失 → 默认；解析失败、含保留键或违反实现约束 ① ② → 默认并记 AppLog warning
  Future<void> save(KeymapSet s);                   // 只写与默认不同的命令；全部与默认相同时删除该偏好
}
sealed class AssignResult { const AssignResult(); }
final class Assigned extends AssignResult {}
final class Rejected extends AssignResult { final String reasonKey; }        // 见实现约束 ②
final class Conflict extends AssignResult { final BindableCommand other; }   // 该组合键已分配给 other
final class KeymapEditorVm extends ChangeNotifier {
  KeymapEditorVm(this._holder, this._study, this._router, this._prefs);   // KeymapHolder、StudyKeymapHolder、WindowsKeyRouter、KeymapPrefs
  List<BindableCommand> get commands;               // ShortcutCommand 声明顺序在前（按 scope 分组），其后 StudyCommand 声明顺序（“学习”组）
  List<KeyChord> chordsOf(BindableCommand c);
  bool isDefault(BindableCommand c);
  AssignResult tryAssign(BindableCommand c, KeyChord chord, {int slot = 0});  // slot 0 或 1；Assigned 时立即生效并保存
  Future<void> replace(BindableCommand c, KeyChord chord, {int slot = 0});    // 用户确认“替换”后：从原命令移除该键再分配
  Future<void> clear(BindableCommand c, int slot);
  Future<AssignResult> resetCommand(BindableCommand c); // 预检全部默认键；冲突不修改，返回首个Conflict
  Future<void> resetAll();                          // 需界面二次确认
}
void installWindowsKeymap(CompositionContext ctx);
// 登记 order 12 启动钩子：KeymapPrefs.load → KeymapHolder.value 与 StudyKeymapHolder.value；向 SettingsSections 加入 order 60 的“快捷键”区；追加到 platformInstallers（在 installWindowsEditing 之后）（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
```

```text
偏好 keymap.v1（WindowsPrefs，HKCU\Software\BubeiGongshi\Prefs 下的字符串值）：
  {"v": 1, "bindings": {"fraction": ["ctrl+shift+0x00000000066"], "sqrt": [], "study.pause": ["ctrl+shift+0x00000000071"]}}
  键为 BindableCommand.persistKey；只含与默认不同的命令；值为 0–2 个 KeyChord.encode() 字符串，空数组表示该命令不分配按键；
  未知命令名忽略（向前兼容）；"v" 不为 1 时整体按默认处理
设置区“快捷键”：
  分“编辑器”“全局”“学习”三组（“学习”组按 WIN-15 a 表，组说明“数字与字母键只在焦点不在文本框时生效”），每行：命令名称 | 组合键 1 | 组合键 2 | “更改”“清除”“恢复默认”（与默认不同时显示）
  组底部列出 WIN-08 表中的“保留（固定）”按键作说明，不可编辑；顶部“全部恢复默认”
录制对话框：
  打开时 KeymapHolder.suspended 与 WindowsKeyRouter.suspended 均为 true，关闭时恢复；显示“请按下新的组合键”，捕获下一次非修饰键的 KeyDownEvent
  Esc 取消；Rejected 显示原因并等待重按；Conflict 显示“已被『<命令名>』使用”与“替换”“取消”
```

- 错误码：无（偏好无效时回退默认并记日志，不向用户报错）。

BindableCommand必须按具体子类型与枚举值实现==/hashCode：AppCommand(x)==AppCommand(x)，StudyKeyCommand(x)==StudyKeyCommand(x)，跨子类型不等；持久化键仅使用声明的唯一ID，不以显示标题比较。KeyChord严格复用WIN-15规范格式，不接受短位宽旧示例。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

产品约束追踪：见README §6 Q28、Q29；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

单项恢复默认是原子的预检+提交：按默认组合键声明顺序，在App/Study全部其他命令查占用；发现冲突返回Conflict(other)，不修改holder与偏好，界面显示现有冲突文案，并提示先更改/清除占用键，不能静默覆盖。全部空闲才恢复，返回Assigned并保存；保存失败沿用约束③的内存生效与提示。resetAll按现有二次确认整体恢复已验证无冲突的两组默认，不复用单项逐个恢复。

**实现约束**
- ① 一个组合键在全部命令中只能出现一次（不分范围，含“学习”组）：全局命令先于页面收到按键，若与编辑器命令同键，编辑器命令永远不会触发。
- ② 拒绝的组合键：`isReservedChord` 为 true（显示“系统或输入法使用该组合键”）；不含 Ctrl 或 Alt 且不是 F2～F12（显示“需要包含 Ctrl 或 Alt”）；Shift+字符（显示“会与正常输入冲突”）。例外：`unmodifiedAllowed` 为 true 的学习命令（WIN-15）另允许不带修饰的字母 A～Z 与数字 0～9（仍先查 `isReservedChord`），因 WIN-15 在焦点位于文本框时不分发这类按键。
- ③ 修改即时生效：每次成功分配、清除或恢复后写 `KeymapHolder.value` 并调用 `KeymapPrefs.save`；保存失败时保留内存中的键位并提示“快捷键未能保存，重启后将恢复为上次保存的设置”。
- ④ 设置区与帮助只读取 `defaultKeymap`、`KeymapHolder` 与 `ShortcutCommand.titleKey`，不复制键位表；新增编辑器或全局命令时只改 WIN-08，新增学习命令时只改 WIN-15（命令 ID 先在 CORE-58 `StudyCommand` 登记）。
- ⑤ 只在 Windows 登记；共享界面不出现平台判断（设置区经 CORE-36 `SettingsSections` 接入）。
- 外部前提：无新增第三方库。

**验收标准**：测试方案全文见 [Test/win/S5_WIN-14_TEST.md](../Test/win/S5_WIN-14_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 510 行；`app/lib/platform/windows/keymap/`。组件估算：命令值对象/偏好验证和差异保存约 120 行，VM冲突/原子reset与保存失败约 170 行，设置区/录制弹窗/焦点和suspend恢复约 190 行，安装/启动读取/共享接入约 30 行。分阶段：① 模型与VM约 290 行；② 界面与安装约 220 行；各阶段以替身隔离后续能力，分别可构建、验收与提交，未交付阶段不声明通过。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。

