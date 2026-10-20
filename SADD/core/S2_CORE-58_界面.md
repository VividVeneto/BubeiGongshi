### CORE-58 设计组件、命令与外观入口

**目标**：设计组件、命令与外观入口，与原卡分开实施与验收。

**范围**
- 包含：核心组件、命令接缝、外观选择、预热与样例；接收 CORE-55 f/j 及布局容器实现。
- 不包含：依赖卡已定义的业务算法、存储与平台能力；不修改其契约。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-28、CORE-55

**接口契约**

```dart
class AdaptiveScaffold extends StatefulWidget {      // 按 LayoutInfo 切换底栏 / rail / 侧栏；body 子树用同一 GlobalKey 挂载，切换不重建
  const AdaptiveScaffold({super.key, required this.destinations, required this.selected, required this.onSelect, required this.body});
}
class TwoPane extends StatelessWidget {              // panes = 2 时并排，否则只显示 detail（非空）或 list；两栏状态由路由参数表达
  const TwoPane({super.key, required this.list, this.detail, this.listWidth = 360, this.placeholder});
}

// 平台无关命令接缝：页面声明当前可用命令，平台按键处理器（WIN-15）按命令 ID 调用；共享界面不感知按键
class FmlCommandScope extends StatefulWidget {      // commands 中值为 null 表示当前不可用；当前路由内最内层已挂载的 scope 生效
  const FmlCommandScope({super.key, required this.commands, required this.child});
  final Map<String, VoidCallback?> commands; final Widget child;
}
abstract final class FmlCommands {                  // 无已挂载 scope、命令未声明或为 null → 返回 false，不抛错
  static bool invoke(String id); static bool isAvailable(String id);
}
abstract interface class ShortcutLabelSource { String? labelOf(String commandId); Listenable get changes; }   // 可选（WIN-15 登记，键位变化时通知）；未登记时 ShortcutHint 不显示

class AppearancePicker extends StatelessWidget {     // 5 个色块（名称 + 浅深示意）+ 外观模式三段选择；本卡S2独立/settings/appearance路由承载，CORE-47只链接
  const AppearancePicker({super.key, required this.controller}); final AppearanceController controller;
}

```

**f. 核心组件**（`app/lib/ui/design/components/`；以 Material 3 组件加 `themeFor` 中的组件主题实现——按钮、卡片、输入装饰、提示条、导航栏/rail/抽屉均只配主题与薄封装，只有作答选项状态、公式台面渐隐与骨架闪光自绘；所有状态色取自令牌，状态层为 `onSurface` 或 `onPrimary` 叠加：悬停 8%、按下 12%、拖动 16%）

| 组件 | 尺寸（触摸 / 指针 / 触控笔） | 状态与表现 | 说明 |
| --- | --- | --- | --- |
| `FmlButton(variant: primary · secondary · tertiary · destructive, label, icon?, onPressed, loading)` | 高 48 / 36 / 44；最小宽 88 / 64 / 80；水平内距 24 / 16 / 20；圆角 `md` | 默认；悬停、按下状态层；焦点 2 dp `primary` 环、外距 2；禁用：内容 38%、容器 12%；加载：转圈替换文字、宽度不变、不可再点 | primary 实底 `primary`；secondary 实底 `primaryContainer`；tertiary 无底；destructive 文字 `wrong` |
| `FmlCard` | 内距 16 / 12 / 16；圆角 `md`；`level1` | 可点击时有悬停、按下、焦点态 | 列表项、今日任务卡、统计卡 |
| `AnswerOption(index, child, state, commandId?)` | 高 ≥ 56 / 44 / 52，内容超出时增高；全宽；左侧序号徽标 A～D（指针时经 `ShortcutLabelSource` 显示 `commandId` 的键位） | `idle`、悬停、按下、焦点、`disabled`（提交中）、`selected`、`correct`（`correctContainer` + ✓ 图标 + “正确”）、`wrong`（`wrongContainer` + ✕ 图标 + “错误”）、`revealedCorrect`（`correct` 2 dp 描边 + ✓） | 状态变化 `standard` 时长淡变，不抖动 |
| `FormulaStage(child, caption?, size: hero · body)` | 内距 24（紧凑 16）；最小高 120；圆角 `lg`；`level1` | 过宽时先降为 `formulaBody`，仍过宽则水平滚动并在边缘渐隐；不缩小到 `formulaBody` 以下 | 学习题干、反馈标准答案、详情页、计算器 |
| `FmlInputArea(child, error?, helper?)` | 最小高 = `controlHeight`，1～5 行自增，超出内滚；圆角 `sm` | 默认 1 dp `outline`；焦点 2 dp `primary`；错误 2 dp `wrong` + 下方错误文字与图标；禁用 38% | 包裹 CORE-59 编辑器与文本框；获得焦点时 `ensureVisible` 到软键盘之上 |
| `ActionBar(primary?, secondary)` | 高 72（含内距，另加底部安全区）；至多 1 个主按钮 + 2 个次按钮 | 主按钮在右（紧凑档为通栏）；滚动内容不遮挡；矮高度时变为 `SidePanel` 的底部 | 学习、计算、识别、编辑页 |
| `SidePanel(child, width = 320)` | 宽 320（矮高度 280）；`level1` | 可滚动；矮高度时主操作固定在面板底部 | 宽档信息区、矮高度操作区 |
| `VerdictBanner(verdict, message)` | 高 ≥ 48；圆角 `md` | 正确、错误、自评、提示四种：对应容器色 + 图标 + 文字，进入用 `standard` 淡入 + 8 dp 上移 | 判定结果的唯一呈现方式 |
| `showFmlToast(context, message, {action, duration})` | 宽 ≤ 560；至多 2 行；`level2` | 默认 4 s，带操作 10 s（CORE-54 撤销）；出现在 `ActionBar` 之上，不遮挡主操作；新提示替换旧提示 | 非阻断提示；错误需用户处理时用页面内提示而非提示条 |
| `EmptyState(icon, title, message, action?)` | 图标 48；最多 1 个主按钮 | — | 无数据、无结果、功能不可用（如未登记手写） |
| `LoadingState` / `Skeleton(lines)` | 骨架块高同正文行高，圆角 `sm` | 等待 > 150 ms 才显示；骨架闪光周期 1.2 s，减少动效时静止；> 1 s 的任务显示进度，> 2 s 显示“取消” | 列表首屏、详情、计算结果 |
| `ShortcutHint(commandId)` | 字号 `caption`，`outline` 描边圆角 `sm` | 只在 `showShortcutHints` 为真时显示 | 按钮与选项旁的键位提示；文本取可选接缝 `ShortcutLabelSource.labelOf(commandId)`（WIN-15 登记），取不到或返回 null 时不显示 |

**j. 预热与设计样例页**

```dart
// app/lib/ui/design/warmup.dart
abstract final class DesignWarmup {
  // 在 ui.PictureRecorder 上依次绘制：level1 卡片描边、level2/level3 阴影、lg 圆角裁剪、FormulaStage 边缘渐隐遮罩、透明层与淡入转场各一次，
  // toImage(64, 64) 后丢弃；进程内只执行一次（再次调用立即返回）；累计超过 budget 即停止；任何异常只记 CORE-28 AppLog，不抛出
  static Future<void> run(ThemeData theme, {Duration budget = const Duration(milliseconds: 200)});
}
// app/test/ui/design/gallery/design_gallery.dart（测试夹具，不进发布包，与其他测试夹具一样不计入规模）
enum GallerySample { list, input, detail, form, task }
class DesignGallery extends StatefulWidget {   // 以 AdaptiveScaffold（4 个假导航项）+ FmlCommandScope 包裹所选样例；不依赖 CoreBinding 与任何特性目录
  const DesignGallery({super.key, required this.sample, this.pref = const AppearancePref()});
  final GallerySample sample; final AppearancePref pref;
}
```

| 样例 | 内容（Key 供测试查找） | 主按钮 |
| --- | --- | --- |
| `list` | `ListView.builder` 200 行 `FmlCard`，`itemExtent` = `listRowHeight`，`PageStorageKey('gallery.list')`；宽档为 `TwoPane`，右侧 `EmptyState` | 无 |
| `input` | `FormulaStage(size: hero)` + `FmlInputArea` 包裹 `TextField(key: Key('gallery.input'))` + `ActionBar` | “提交” |
| `detail` | `TwoPane`：左 20 行列表并选中第 3 行，右 `FormulaStage` + `VerdictBanner(correct)` + 掌握度四段图例；tertiary“复制” | 无 |
| `form` | 3 个 `FmlInputArea`（`gallery.form.title` / `subject` / `tags`），第 2 个带错误文字；tertiary“取消” | “保存” |
| `task` | 3 个 `numeralLarge` 计数（12 / 30 / 3）+ 倒计时 + `ActionBar`，secondary“书架”“统计” | “开始学习” |


路由工厂`List<GoRoute> designComponentRoutes(AppearanceController controller)`只构造AppearancePicker页面及触感反馈开关（仅存在UiFeedbackSink时显示，写AppearancePref.haptics）（controller由composition从features.require<AppearanceController>()取得后显式传入；Widget只接收controller）；由宿主在路由聚合表挂载/settings/appearance。安装点 `installDesignComponents(CompositionContext ctx)`：登记 order 90 预热；S2 注册 `/settings/appearance` 为独立路由，CORE-47（下游说明，非契约）设置首页仅链接该路由，不重复提供页面。学习命令 ID 字符串 `study.primary`、`study.option1`～`study.option4`、`study.rateKnew`、`study.rateForgot`、`study.skip`、`study.pause`、`study.appeal`、`study.prevQuestion`、`study.nextQuestion` 唯一归本卡 `app/lib/design/commands.dart`，不依赖 S4 页面。

```dart
// app/lib/design/commands.dart
enum StudyCommand {                                 // 顺序即设置页“学习”组显示顺序；唯一 ID 定义，WIN-14 持久化键
  primary('study.primary'), option1('study.option1'), option2('study.option2'), option3('study.option3'),
  option4('study.option4'), rateKnew('study.rateKnew'), rateForgot('study.rateForgot'), skip('study.skip'),
  pause('study.pause'), appeal('study.appeal'), prevQuestion('study.prevQuestion'), nextQuestion('study.nextQuestion');
  const StudyCommand(this.id); final String id;
  bool get unmodifiedAllowed;                       // option1～4、rateKnew、rateForgot 为 true：可用不带修饰的字母或数字键
  String get titleKey;                              // 本地化键 shortcut.study.<name>
}
```

LibraryBatchCommands唯一命令字符串前缀library.batch.；无参动作toggle/selectAll/clear/open/trash/editTags/menu/undo；方向动作以独立ID表达：move.up、move.down、move.home、move.end、move.pageUp、move.pageDown及对应extend.up/down/home/end/pageUp/pageDown。全部通过现有VoidCallback和invoke(id)执行，不另传未定义载荷。页面将各ID分别绑定到选择模型；pageUp/pageDown按当前可见行数（至少1），home/end到首/末项；无目标项时不可用。

**实现约束**
- 组件只消费 CORE-55 令牌与端口；不读绑定或平台。入口是本卡声明的独立路由，S2假宿主直接注册并从导航链接进入；真实壳在CORE-36注册designComponentRoutes，不取SettingsSections避免反向依赖。
- 按 CORE-55 a/g/h/i 的视觉、布局、动效与无障碍规范实现。
- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-58_TEST.md](../Test/core/S2_CORE-58_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 430 行；主包 `app/lib/ui/design/components/`、`app/lib/ui/design/warmup.dart`、`app/lib/design/{commands,routes}.dart`（含测试与必要的同构建单元接缝）。

