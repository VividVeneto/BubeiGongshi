### CORE-55 界面设计系统与主题

**目标**：为两端共享界面提供唯一的视觉与交互规范及其 Dart 实现：设计原则、设计令牌、5 套原创预设主题色与外观模式、按窗口尺寸的自适应布局、按输入方式的密度、核心组件、关键页面布局、流畅性与无障碍规则，以及平台卡（AND-13、WIN-15）注入输入方式、触感、动画缩放与设备偏好存储的接缝。

**范围**
- 包含：设计原则与令牌、五套主题及对比度、AppearanceController、LayoutInfo、输入方式/反馈/动效端口及规范。
- 不包含：组件、命令、布局容器、外观选择界面与预热实现，迁至 CORE-58（下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-28

**接口契约**

**a. 设计原则**（每条可判定；括号内为 README §2.2 2026-10-19 甲方要求的条目与需求编号）

| 编号 | 原则 | 判定方法 | 对应 |
| --- | --- | --- | --- |
| P1 | 一屏一事：学习流程（作答、反馈、自评、默写、小结）每屏至多 1 个主按钮（`FmlButtonVariant.primary`）；首页首屏直接显示今日任务与“开始学习” | Widget 测试统计每个学习状态与首页的主按钮数；首页首屏无需滚动即可见今日新学、复习、错题数与主按钮 | 要求 1，R42.a |
| P2 | 主操作在易及处：触摸输入时主操作位于屏幕下部 40%（竖屏）或右侧下半（矮高度）；触控目标不小于 48 dp，指针目标不小于 32 px 且相邻目标间距不小于 8 | Widget 测试检查主按钮的全局矩形与命中区尺寸 | 要求 2，R42.b |
| P3 | 反馈即时而克制：作答后判定结果在 CORE-01“作答到判定反馈”预算内出现，只用颜色、图标与文字，不用全屏弹窗、撒花或默认开启的音效；任何动效不超过 400 ms | 性能测试按预算行测量；Widget 测试断言判定期间无 `Dialog`、动画时长 ≤ `FmlMotion.max` | 要求 1、3，R42.a、R42.c |
| P4 | 永不阻塞：界面线程不做同步核心调用；等待超过 150 ms 显示骨架或进度，超过 2 s 的任务可取消；所有转场可被新操作打断 | 静态检查 `ui/` 不调用同步 op；Widget 测试用延迟 Fake 检查骨架出现时刻 | 要求 3，R42.c |
| P5 | 一套视觉、两种密度：两端使用同一套令牌、组件与布局；差异只来自宽度分档与 `InputModality`，`ui/` 中不出现平台判断 | 设计测试 `no_platform_check_test.dart` 扫描 `app/lib/ui/` 不含 `Platform.`、`defaultTargetPlatform` 与 `RuntimeSnapshot.os`（无例外）；黄金图在固定主机/字体验证；两端同尺寸同输入方式的布局语义对照归 AND-12/WIN-13 | 要求 4，R42.d |
| P6 | 尺寸决定布局，方向不受限：布局只由窗口宽高决定，横竖屏都可用；旋转与改变窗口尺寸不重建页面、不丢输入与滚动位置 | Widget 测试改变 `MediaQuery.size` 前后比较 `State` 对象、文本与滚动偏移 | 补充一、二，R42.e |

视觉识别（原创，与原型的区别）：只借鉴不背单词“一屏一事、主操作醒目、首页即今日任务、判对判错即时而克制”的交互模式；不使用原型的任何配色、取色、截图、图标、插画、吉祥物、文案、音效、商标或版式细节（README §2.2“功能近似”条款）。本应用的识别要素：默认主色“群青”与另外 4 套取自中国传统颜料名的主题色（色值本卡自定）；“公式台面”——公式总放在带 1 dp 描边、大圆角的抬升面上居中显示，四周留白不少于 24 dp；线性图标（24 网格、2 dp 描边、圆头，基础图标取自 Material Symbols Rounded〔Apache-2.0〕，公式、量纲、推导、手写等学科图标按同一风格自绘）；中文用系统黑体、数字用等宽数字、公式用 CORE-12 数学字体包的三层字体搭配；界面无整屏背景图与插画。

**b. 设计令牌**（`app/lib/ui/design/tokens.dart`；均为 `ThemeExtension<T>`，`copyWith`/`lerp` 齐全，经 `FmlTheme.of(context)` 读取）

```dart
final class FmlTokens {
  final FmlColors color; final FmlTypeScale type; final FmlSpacing space;
  final FmlRadii radius; final FmlElevation elevation; final FmlMotion motion;
  final FmlDensity density; final FmlSemanticColors semantic;
  const FmlTokens({required this.color, required this.type, required this.space,
    required this.radius, required this.elevation, required this.motion,
    required this.density, required this.semantic});
}
abstract final class FmlTheme {
  static FmlTokens of(BuildContext context);
}
// 用法：final tokens = FmlTheme.of(context); ColoredBox(color: tokens.color.surface);
```

of 读取最近 Theme.of(context) 的上述8个 ThemeExtension；返回非空聚合，字段为本表类型。themeFor 对每个预设/明暗都登记全8项；缺项（包括没有本项目主题的宿主）抛 StateError('FML_THEME_MISSING:<扩展类型>')，不返回null或临时自造配色（`FML_THEME_MISSING` 是程序错误标签，与 `assert` 文本同类，不是 CORE-02 错误码、不进注册表，CORE-41 ERR-2 不报）。主题变化触发依赖Widget重建；密度由InputModalityScope派生后在宿主Theme覆盖，不能全局缓存BuildContext的tokens。FmlTokens不是新的ThemeExtension，不需第二套主题状态。

| ThemeExtension | 字段 | 取值 |
| --- | --- | --- |
| `FmlTypeScale` | `display` / `headline` / `title` / `titleSmall` | 32/40、24/32、20/28、16/24（字号/行高 sp），字重 600 |
| `FmlTypeScale` | `body` / `bodySmall` / `label` / `caption` | 16/24 w400（中文正文）、14/20 w400、14/20 w500、12/16 w400 |
| `FmlTypeScale` | `numeralLarge` / `numeral` | 40/48 w600、16/24 w500，均启用 `FontFeature.tabularFigures()`（今日任务计数、倒计时、计算结果） |
| `FmlTypeScale` | `formulaHero` / `formulaBody` / `formulaInline` | 28（紧凑档 24）、20、与所在行正文同号（传给 下游公式 Widget（下游说明，非契约） 的 `fontSize`，逻辑像素） |
| `FmlTypeScale` | `fontFamilyFallback` | `['Noto Sans CJK SC', 'Noto Sans SC', 'Microsoft YaHei UI', 'sans-serif']`；不打包中文字体（R03） |
| `FmlSpacing` | `xs` `s` `m` `l` `xl` `xxl` `xxxl` | 4、8、12、16、24、32、48（4 dp 栅格，所有间距取自本行） |
| `FmlSpacing` | `pageMargin(WidthClass)` / `gutter(WidthClass)` | 紧凑 16 / 16，中等 24 / 24，宽 32 / 24；正文阅读宽度上限 `readingMax` = 720，页面内容上限 `contentMax` = 1200 |
| `FmlRadii` | `sm` `md` `lg` `full` | 6（输入框、标签块）、12（按钮、卡片、选项）、20（公式台面、底部弹层、对话框）、999（徽标） |
| `FmlElevation` | `level0`～`level3` | 0 页面底 `surface`；1 卡片与公式台面 `surfaceRaised` + 1 dp `outline` 40% 描边、无阴影；2 菜单与提示条：阴影 0/2/8 dp 黑 12%；3 对话框与底部弹层：阴影 0/8/24 dp 黑 16%；深色下阴影改为每级 `surfaceRaised` 叠加 `onSurface` 4% |
| `FmlMotion` | `fast` / `standard` / `emphasized` / `max` | 100 ms（悬停、按下、焦点）、200 ms（判定条、选项状态、组件进出）、300 ms（页面转场、布局切换）、400 ms（上限，任何动效不得超过） |
| `FmlMotion` | `standardCurve` / `enterCurve` / `exitCurve` | `Cubic(0.2, 0, 0, 1)`、`Cubic(0, 0, 0, 1)`、`Cubic(0.3, 0, 1, 1)` |
| `FmlMotion` | `Duration scaled(Duration d)` | “减少动效”开启（`MediaQuery.disableAnimations`）→ 位移与缩放为 0，只保留 ≤ 100 ms 的淡入淡出；否则 `d × MotionScaleSource.scale`（未登记为 1.0），结果不超过 `max` |
| `FmlDensity` | `controlHeight` / `minTarget` / `optionHeight` / `listRowHeight` | 触摸 48 / 48 / 56 / 64；指针 36 / 32 / 44 / 48；触控笔 44 / 44 / 52 / 56（dp 或逻辑像素） |
| `FmlDensity` | `showHoverHints` / `showShortcutHints` / `showDragHandles` | 触摸 否/否/是；指针 是/是/否；触控笔 是/否/是 |
| `FmlColors` | 见 c | 随预设与浅/深色变化 |
| `FmlSemanticColors` | 见 c | 固定，不随预设变化 |

**c. 主题色与外观模式**

5 套原创预设（默认 `qunqing`）；外观模式 `system`（默认，跟随系统深浅色）/ `light` / `dark`。`FmlColors` 字段：

| 预设 `FmlPresetId` | 名称 | 模式 | primary | onPrimary | primaryContainer | onPrimaryContainer | surface | surfaceRaised | onSurface | onSurfaceMuted | outline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `qunqing` | 群青 | 浅色 | `#3949AB` | `#FFFFFF` | `#DFE2FF` | `#0F1A5E` | `#F7F7FB` | `#FFFFFF` | `#1A1B22` | `#4A4D5C` | `#7A7E8F` |
| `qunqing` | 群青 | 深色 | `#B6C0FF` | `#16226E` | `#2D3A8C` | `#DFE2FF` | `#121318` | `#1C1D24` | `#E4E4EC` | `#B3B5C4` | `#8A8D9E` |
| `shiqing` | 石青 | 浅色 | `#00658A` | `#FFFFFF` | `#C6E8F7` | `#002A3B` | `#F5F8FA` | `#FFFFFF` | `#171C1F` | `#45525A` | `#74828B` |
| `shiqing` | 石青 | 深色 | `#7FD0F2` | `#00354A` | `#004D69` | `#C6E8F7` | `#101416` | `#192024` | `#E0E5E8` | `#AFBCC4` | `#84939C` |
| `ziteng` | 紫藤 | 浅色 | `#6A4C9C` | `#FFFFFF` | `#EBDDFF` | `#25104E` | `#F9F7FC` | `#FFFFFF` | `#1C1A22` | `#4D4759` | `#7E778C` |
| `ziteng` | 紫藤 | 深色 | `#D4BCFF` | `#3A1F6C` | `#523985` | `#EBDDFF` | `#141218` | `#1E1B24` | `#E7E1EC` | `#BBB2C8` | `#8F879D` |
| `tanhe` | 檀褐 | 浅色 | `#8A4E22` | `#FFFFFF` | `#FBDCC6` | `#381804` | `#FBF8F5` | `#FFFFFF` | `#201A16` | `#54473E` | `#857469` |
| `tanhe` | 檀褐 | 深色 | `#FFB68A` | `#502404` | `#6D3912` | `#FBDCC6` | `#17120F` | `#221C18` | `#EDE0D8` | `#C9B6A9` | `#9A877B` |
| `mohui` | 墨灰 | 浅色 | `#3D4A57` | `#FFFFFF` | `#DAE2EA` | `#16202A` | `#F6F7F8` | `#FFFFFF` | `#1A1C1E` | `#484E55` | `#7A8087` |
| `mohui` | 墨灰 | 深色 | `#BAC7D4` | `#24303C` | `#3A4651` | `#DAE2EA` | `#121416` | `#1C1F22` | `#E2E3E5` | `#B3B9C0` | `#8C939A` |

语义色 `FmlSemanticColors`（所有预设共用，只分浅/深色；判定与掌握度在任何主题下含义与颜色不变）：

| 字段 | 含义 | 浅色 | 深色 |
| --- | --- | --- | --- |
| `correct` | 正确：文字与图标 | `#1B7A3A` | `#5CCF7F` |
| `correctContainer` | 正确：容器底 | `#DDF2E3` | `#123A20` |
| `onCorrectContainer` | 正确：容器上文字 | `#0A4520` | `#BDEFCB` |
| `wrong` | 错误：文字与图标 | `#C0262D` | `#FF8078` |
| `wrongContainer` | 错误：容器底 | `#FCE3E1` | `#4B1615` |
| `onWrongContainer` | 错误：容器上文字 | `#73111A` | `#FFD8D4` |
| `hint` | 提示：文字与图标 | `#875400` | `#F0BF4C` |
| `hintContainer` | 提示：容器底 | `#FCEDCC` | `#3E2E05` |
| `onHintContainer` | 提示：容器上文字 | `#4F3200` | `#FBE6AF` |
| `masteryUnlearned` | 掌握度·未学 | `#878D96` | `#8B93A0` |
| `masteryLearning` | 掌握度·学习中 | `#1F74C4` | `#6AA8EE` |
| `masteryMastered` | 掌握度·已掌握 | `#23874A` | `#5CCF7F` |
| `masteryReview` | 掌握度·需巩固 | `#C05A00` | `#F0A04B` |

- 热力图 5 档 `heat`（`List<Color>`，学习量由少到多）：浅色 `#E6E8EC`、`#BBD3EE`、`#7FAEE0`、`#3F82C9`、`#1F5FA8`；深色 `#23262B`、`#1E3A5C`、`#2D5C91`、`#4A86C8`、`#7DB4F5`。各档另有图例文字与悬停/长按数值，浅档不承担单独表意。
- 对比度（WCAG 2.1 相对亮度公式计算；门槛：正文与次要文字 ≥ 4.5，`onSurface` 正文本卡另要求 ≥ 7，描边、图标与图形 ≥ 3）。语义容器上文字（浅色 / 深色）：正确 9.49 / 9.91，错误 9.44 / 11.25，提示 10.13 / 10.66。各预设：

| 预设 | 模式 | onPrimary / primary | onPrimaryContainer / primaryContainer | onSurface / surface、surfaceRaised（较小者） | onSurfaceMuted（较小者） | primary 作文字（较小者） | outline（较小者） | 正确、错误、提示文字（最小） | 掌握度四段与热力最深档（最小） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 群青 | 浅色 | 7.73 | 12.38 | 16.06 | 7.84 | 7.24 | 3.77 | 5.05 | 3.13 |
| 群青 | 深色 | 8.05 | 7.86 | 13.28 | 8.25 | 9.57 | 5.11 | 6.89 | 5.42 |
| 石青 | 浅色 | 6.50 | 11.68 | 16.11 | 7.55 | 6.10 | 3.71 | 5.06 | 3.14 |
| 石青 | 深色 | 7.59 | 7.19 | 12.99 | 8.49 | 9.59 | 5.21 | 6.76 | 5.32 |
| 紫藤 | 浅色 | 6.72 | 12.92 | 16.18 | 8.36 | 6.31 | 4.02 | 5.07 | 3.14 |
| 紫藤 | 深色 | 7.81 | 7.15 | 13.24 | 8.34 | 10.05 | 4.95 | 6.96 | 5.48 |
| 檀褐 | 浅色 | 6.58 | 12.42 | 16.26 | 8.45 | 6.21 | 4.22 | 5.10 | 3.16 |
| 檀褐 | 深色 | 7.72 | 7.20 | 13.03 | 8.62 | 9.87 | 4.91 | 6.90 | 5.43 |
| 墨灰 | 浅色 | 9.07 | 12.59 | 15.93 | 7.84 | 8.46 | 3.72 | 5.03 | 3.12 |
| 墨灰 | 深色 | 7.81 | 7.38 | 12.89 | 8.37 | 9.62 | 5.33 | 6.79 | 5.34 |

- 设计规则：预设主色避开语义色的绿、红色相，使“正确/错误”不与主按钮混淆；今后新增或修改预设时须重新跑 c 的对比度测试。高对比度（`MediaQuery.highContrast` 为真）时：`onSurfaceMuted` 改用 `onSurface`，描边改为 2 dp `onSurface`，焦点环 3 dp。

```dart
// app/lib/design/appearance.dart
enum FmlPresetId { qunqing, shiqing, ziteng, tanhe, mohui }
enum AppearanceMode { system, light, dark }
final class AppearancePref {
  const AppearancePref({this.mode = AppearanceMode.system, this.preset = FmlPresetId.qunqing, this.haptics = true});
  final AppearanceMode mode; final FmlPresetId preset;
  final bool haptics;                                // 触感反馈开关（甲方要求“可在设置中关闭”）；只在登记了 UiFeedbackSink 时有意义
  String encode();                                   // {"v":1,"mode":"system","preset":"qunqing","haptics":true}；旧值缺 haptics 时按 true 读取
  static AppearancePref decode(String? json);        // null、JSON 损坏、v ≠ 1 或未知取值 → 默认值（不抛错）
}
abstract interface class DevicePrefStore {           // 设备级偏好：不进档案库、不同步、不进备份
  Future<String?> read(String key); Future<void> write(String key, String value);   // key 匹配 ^[a-z0-9_.]{1,64}$
}
final class FileDevicePrefStore implements DevicePrefStore {   // 默认实现：root(StoreArea.database)/device_prefs/<key>.json，写临时文件后原子改名
  FileDevicePrefStore(LocalFileStore files);
}
final class ResolvedAppearance { final Brightness brightness; final FmlPresetId preset; final FmlColors colors; }
final class AppearanceController extends ChangeNotifier {
  static const prefKey = 'appearance.v1';
  AppearanceController(FeatureRegistry features, LocalFileStore files);   // load 时取 features.get<DevicePrefStore>()，取不到用 FileDevicePrefStore(files)，files由installDesign的ctx.ports.files注入
  AppearancePref get pref; ResolvedAppearance get resolved;
  Stream<ResolvedAppearance> get resolvedChanges;    // 偏好或系统深浅色变化时发出（平台卡据此改系统栏与标题栏）
  Future<void> load();                               // 读失败或超过 50 ms → 默认值，之后到达的结果仍应用
  Future<void> set(AppearancePref p);                // 先 notifyListeners（同帧生效），再异步写盘；写盘失败只记 CORE-28 `AppLog`
  ThemeData themeFor(Brightness b, {required bool highContrast});   // 含全部 ThemeExtension；useMaterial3，不用动态取色
}
// app/lib/ui/design/appearance_picker.dart
```

**d. 自适应布局**（`app/lib/ui/design/adaptive.dart`；只读 `MediaQuery.sizeOf`，以当前窗口而非整块屏幕计，分屏与小窗同样适用）

| 条件 | 判定（逻辑像素 / dp） | 导航形态 | 列数与布局 |
| --- | --- | --- | --- |
| 紧凑 `compact` | 宽 < 600 | 底部导航栏（4 项，图标 + 文字，高 64 + 底部安全区） | 1 列；详情、编辑与学习会话为全屏推入页 |
| 中等 `medium` | 600 ≤ 宽 < 960 | 侧边导航栏 rail（宽 80，图标 + 文字） | 1 列居中（内容 ≤ `readingMax`）；公式库与设置为列表 → 推入详情 |
| 宽 `expanded` | 宽 ≥ 960 | 常驻侧栏（宽 240，图标 + 文字，可收起为 rail） | 2 栏：列表 360（≥ 1280 时 400）+ 详情自适应；学习页公式区 + 信息区 320 |
| 矮高度 `shortHeight` | 高 < 480（与宽度档叠加） | 侧边导航栏 rail（宽 72，只图标、悬停或长按显示文字）；顶部栏压缩为 48 | 学习、计算与识别页改左右排列：左侧内容区、右侧操作区，主操作在右下；软键盘弹出时输入区上移保持可见 |
| 大字号降档 | `textScaler` 缩放 ≥ 1.5 | 按低一档的导航形态 | 宽档按中等档布局，中等档按紧凑档布局，保证 200% 字号不截断 |

| 设备与状态 | 典型窗口（dp） | 落在 | 导航 | 布局要点 |
| --- | --- | --- | --- | --- |
| 手机竖屏 | 360～430 × 640～932 | 紧凑 | 底部导航 | 单列；主操作底部通栏 |
| 手机横屏 | 640～932 × 360～430 | 中等（或宽）+ 矮高度 | 窄 rail | 内容左、操作右；顶部栏 48；主操作右下拇指区 |
| 平板竖屏（最短边 ≥ 600） | 600～900 × 960～1366 | 中等（宽 ≥ 960 时为宽） | rail | 单列居中；公式库列表 → 详情推入 |
| 平板横屏（最短边 ≥ 600） | 960～1366 × 600～900 | 宽 | 常驻侧栏 | 公式库列表 + 详情；学习页公式区 + 信息区；设置列表 + 子页 |
| 平板分屏或小窗 | 按当前窗口 | 按上两表 | 按上两表 | 与手机同档同布局 |
| Windows 最小窗口 | 600 × 500（WIN-15 设定） | 中等 | rail | 单列 |
| Windows 默认窗口 | 1280 × 800（WIN-06） | 宽 | 常驻侧栏 | 双栏 |
| Windows 半屏贴靠 | 约 960 × 1032（1920×1080 @100%） | 宽 | 常驻侧栏 | 双栏（列表 360） |
| Windows 最大化 | ≥ 1366 × 700 | 宽 | 常驻侧栏 | 双栏；内容总宽 ≤ `contentMax` 居中 |

```dart
enum WidthClass { compact, medium, expanded }
enum NavForm { bottomBar, rail, sidebar, hidden }    // hidden：学习会话、相机与全屏编辑页
final class LayoutInfo {
  final WidthClass width; final bool shortHeight; final bool largeScreen /* 最短边 ≥ 600 */; final NavForm nav; final int panes;
  static LayoutInfo fromSize(Size size, {double textScale = 1.0, bool immersive = false});
  static LayoutInfo of(BuildContext context);
}
final class FmlDestination { final String location; final IconData icon; final String labelKey; }
```

**e. 输入方式与密度**

```dart
// app/lib/ui/design/modality.dart
enum InputModality { touch, pointer, stylus }
abstract interface class InputModalitySource {       // 平台登记（AND-13：touch；WIN-15：pointer，平板模式或触摸时 touch）；未登记时 initial = touch
  InputModality get initial; Stream<InputModality> get changes;
}
class InputModalityScope extends StatefulWidget {     // 宿主根部；合并平台源与根部 Listener 看到的 PointerDeviceKind
  const InputModalityScope({super.key, required this.child});
  static InputModality of(BuildContext context);       // 依赖它的组件随之重建
  static FmlDensity densityOf(BuildContext context);
}
enum UiFeedbackKind { tap, selection, correct, wrong, warning }
abstract interface class UiFeedbackSink { void emit(UiFeedbackKind kind); }   // 可选（AND-13 触感）；未登记为空操作；共享界面统一经 FmlFeedback.emit(context, kind) 调用，pref.haptics 为 false 时不转发
abstract final class FmlFeedback { static void emit(BuildContext context, UiFeedbackKind kind); }   // 取 UiFeedbackSink 与 AppearanceController；未登记或 haptics=false 时为空操作
abstract interface class MotionScaleSource { double get scale; Stream<double> get changes; }   // 可选（AND-13 系统动画时长缩放），取值 0～10
// app/lib/design/install.dart
void installDesign(CompositionContext ctx);          // 只登记 AppearanceController；featureInstallers 第一项
```

- 切换规则：收到 `PointerDeviceKind.touch` 按下 → `touch`；`mouse` 或 `trackpad` 的移动或按下 → `pointer`；`stylus`/`invertedStylus` → `stylus`；平台源事件优先。300 ms 内只切换一次，切换只改密度与提示，不改布局档、不移动焦点。
- 各方式的交互提示：`pointer` 显示悬停态、悬停提示（500 ms 后出现）、右键菜单与 `ShortcutHint`；`touch` 不显示悬停与快捷键，所有长按与滑动都有可见按钮等价（如“更多”菜单按钮、选择模式按钮）；`stylus` 同触摸密度，额外显示悬停态，手写区内不触发滚动。

**g. 关键页面布局**（各页功能不变，只规定呈现与主操作位置；“主操作”即该屏唯一的 primary 按钮）

| 页面 | 紧凑（手机竖屏） | 矮高度（手机横屏） | 中等（平板竖屏、Windows 窄窗） | 宽（平板横屏、Windows 默认） |
| --- | --- | --- | --- | --- |
| 账户入口 `/`、`/account/*` | 单列表单（≤ 400 居中）：应用名、三个入口（游客、注册、登录）；主操作“开始使用（游客）”在底部 | 表单可滚动，主操作随表单底部；软键盘弹出时当前输入框可见 | 居中卡片 440 宽 | 同中等；不加插画 |
| 首页（今日任务）`/study` | 顶部日期与考试倒计时；今日卡：新学 / 复习 / 错题三个 `numeralLarge` 计数；主操作“开始学习”（有未完会话时为“继续上次”）底部通栏；次要入口：书架、统计 | 左侧今日卡，右侧主操作与次要入口 | 今日卡 + 主操作居中（≤ `readingMax`），下方书本进度 | 左栏今日卡与主操作；右栏近 7 天学习量与书本进度（CORE-49 组件） |
| 学习页·辨识 `/study/session/:id`（命令 study.option1～4 的选择题布局） | 隐藏导航；顶部栏：进度 n/总数、暂停；上部 `FormulaStage`（题干，考试标签在上方）；下部 2～4 个 `AnswerOption`，点选即提交 | 左 55% 题干，右侧选项纵列，暂停在右上 | 单列居中（≤ `readingMax`） | 左：题干 + 选项（≤ 720）；右 `SidePanel`：本组进度、书名与章节 |
| 学习页·输入与默写（命令 study.primary 的输入与默写布局） | 题干在上，`FmlInputArea` 在中，主操作“提交”在 `ActionBar`；默写每屏 1 题，底部“上一题 / 下一题”，末题主操作“提交默写” | 左题干、右输入区与提交；软键盘弹出时题干缩为 1 行摘要 | 单列居中 | 左题干与输入区，右侧默写题号列表（可跳转） |
| 学习页·反馈（反馈与自评布局命令） | `VerdictBanner` 在题干下；`FormulaStage` 显示标准答案与“将在本组稍后重现”；易混公式列表；主操作“下一题”在底部，“记错了”为 tertiary 按钮；自评页主操作为两个等宽按钮“会 / 不会”（视为一组主操作） | 左标准答案，右判定条、“下一题”与“记错了” | 单列居中 | 左标准答案；右 `SidePanel` 判定条、易混与派生公式 |
| 公式库 `/library`、`/library/:itemId` | 列表全屏（搜索框在顶部栏，筛选为底部弹层）；点按推入详情；“新建”浮动按钮右下 | 列表单列，顶部栏 48；详情推入 | 列表行加宽显示学科与掌握度；详情推入 | 双栏容器（CORE-58，下游说明，非契约）：左列表、右详情；无选中时右侧为空状态 |
| 计算器 `/calc` | 上部公式与目标选择，中部输入行列表，结果固定在底部 `ActionBar` 上方，主操作“计算”；无 `revision` 参数时显示空状态“从公式库选择一个公式”（主操作跳转 `/library`） | 左输入行，右结果与“计算” | 单列居中 | 左输入行，右结果、单位、有效数字与所用常数 |
| 识别 `/recognize` | 入口页：手写、拍照、相册、文件四个大卡片；画布页全屏，候选在底部弹层，主操作“采用” | 画布左、候选与“采用”在右 | 画布居中（宽 ≤ 720），候选在下 | 左画布或图片，右候选与校正 |
| 设置 `/settings` | 分组列表 → 推入子页；外观子页 `/settings/appearance` 放 外观选择器（CORE-58，下游说明，非契约） | 同紧凑 | 同紧凑，内容 ≤ `readingMax` | 双栏容器（CORE-58，下游说明，非契约）：左分组列表 240～360，右子页 |

```text
紧凑·学习页（辨识）          矮高度·学习页（辨识）
┌──────────────────┐        ┌──────────────────────────────────┐
│ 3/10        暂停 │        │ 3/10                        暂停 │
│ [考试标签]       │        │ ┌────────────────┐ ┌──────────┐ │
│ ┌──────────────┐ │        │ │                │ │ A 选项   │ │
│ │  公式台面    │ │        │ │   公式台面     │ │ B 选项   │ │
│ └──────────────┘ │        │ │                │ │ C 选项   │ │
│ ┌ A 选项 ──────┐ │        │ └────────────────┘ │ D 选项   │ │
│ ┌ B 选项 ──────┐ │        │                    └──────────┘ │
│ ┌ C 选项 ──────┐ │        └──────────────────────────────────┘
│ ┌ D 选项 ──────┐ │
└──────────────────┘
```

- 主导航顺序：学习（`/study`，首页）、公式库、识别、设置；完成账户入口后落在 `/study`。计算器、统计与资源包不进主导航，从详情页、首页与设置页进入。

**h. 流畅性规范**
- 界面线程不做同步核心调用：`ui/` 只调用 CORE-03 的异步 op；单帧内的同步计算（排版缓存命中除外）不超过 4 ms，超过的放入后台 isolate 或核心长任务。
- 等待显示：≤ 150 ms 不显示任何占位（避免闪烁）；150 ms～1 s 骨架；> 1 s 进度；> 2 s 可取消。乐观更新只用于本地可逆操作（选中、切换），其余等结果。
- 动效：时长取 b 中令牌并不超过 `max`；所有动效由 `AnimationController` 或隐式动画驱动，可被新输入打断并从当前值继续；页面转场 `emphasized`，学习会话内题目切换 `standard` 淡变 + 16 dp 平移；“减少动效”与 `MotionScaleSource` 按 `FmlMotion.scaled` 处理。
- 旋转与改变窗口尺寸：不重建路由与页面 `State`（自适应宿主（CORE-58，下游说明，非契约） 用 `GlobalKey` 保持 body；页面布局切换用同一 `State` 内的 `LayoutBuilder`）；文本控制器与表单状态在视图模型中；可滚动区域设 `PageStorageKey`；切换时焦点保持在原控件；不在尺寸变化时触发核心调用。
- 列表：超过 50 条一律用 `ListView.builder`/`SliverList` 懒构建并给出 `itemExtent` 或 `prototypeItem`；禁止对长列表 `shrinkWrap`；图片与公式缩略按可见项加载。
- 首帧与着色器：首帧只渲染外壳与当前路由的骨架；下游 CORE-58 在启动钩子 order 90 空闲时预热组件（下游说明，非契约）离屏绘制一次核心组件与转场用到的阴影、圆角裁剪、渐隐遮罩与透明层，使 Skia 后端的首次转场满足 CORE-01“转场与动效”行；Impeller 后端同样执行（成本低于预算，不按渲染后端或平台分支）。
- 性能指标见 CORE-01 全局资源预算表“点击到可见反馈”“作答到判定反馈”“转场与动效”“旋转与窗口尺寸变化”“主题切换”行（ADR-V5-25）。

**i. 无障碍**（接收并细化 CORE-36 原基线）
- 所有可交互控件有 `Semantics` 标签与角色；公式控件朗读 CORE-12 `semantic_text`；判定条朗读“正确/错误”及标准答案，以 `liveRegion` 播报。
- 系统字号放大到 200%（`textScaler` 2.0）时，各档（含矮高度）内容不截断、不重叠：文本容器不设固定高度，按 d 的大字号降档规则布局，必要时整页滚动。
- 颜色之外有第二提示：判定用图标 + 文字；掌握度四段与热力档有文字图例与数值；错误输入有文字说明；焦点环在键盘操作时可见（`FocusHighlightMode.traditional`）。
- 文字对比度满足 c 的门槛；高对比度模式按 c 的规则调整。

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/design/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/design/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

installDesign使用ctx.features和ctx.ports.files构造AppearanceController，先登记再由mainCommon.load等待；平台DevicePrefStore在load时延迟查找，不在构造时固定fallback。设计路由由composition将同一个controller显式传给CORE-58路由工厂。

产品约束追踪：见README §6 Q17、Q18、Q20、Q25；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 顶部栏：`themeFor` 生成的 `AppBarTheme` 背景取当前主题 `surface`（滚动下沉时同为 `surface` 加色调，不改亮度方向），并设 `systemOverlayStyle` 与 `surface` 的亮度一致，使 Flutter 经 `AnnotatedRegion` 自动设置的状态栏图标明暗与 平台系统栏接缝（下游说明，非契约） 的结果相同；页面不得自行指定状态栏样式。
- 本卡只提供令牌、组件、布局与接缝，不包含业务页面；页面卡按 g 呈现。组件只读 `FmlTheme`、`LayoutInfo`、`InputModalityScope`，不读 `RuntimeSnapshot`、不判断平台（CORE-01 依赖规则 5）。
- 组件中的颜色、间距、圆角、字号与时长只能取自令牌；`app/lib/ui/` 其他目录中出现颜色字面量或时长字面量由本卡的设计测试 `token_literal_test.dart` 报告（`design/` 目录除外）。
- 组装：`installDesign` 放在 CORE-36 `featureInstallers` 第一项；`mainCommon` 在 `composeApp` 之后、`runApp` 之前 `await AppearanceController.load()`（上限 50 ms）；宿主外壳（CORE-36，下游说明，非契约） 以 `themeFor` 生成 `theme`/`darkTheme`、按 `pref.mode` 设 `themeMode`，并在 `builder` 中包裹 `InputModalityScope`。平台卡只经 `InputModalitySource`、`UiFeedbackSink`、`MotionScaleSource`、`DevicePrefStore` 四个接缝与 `resolvedChanges` 接入。
- 外观偏好按设备保存：键 `appearance.v1`，值 `{"v":1,"mode":"system|light|dark","preset":"<FmlPresetId 名>","haptics":true|false}`；不写入档案库、不进 outbox、不进备份（README §6 Q19）；版本升级时新增 `appearance.v2` 并在读取时迁移。
- 切换主题与外观即时生效、不重启、不重建路由：只替换 `ThemeData`，主题插值用 `fast` 时长（减少动效时为 0）。
- 不使用 Android 系统动态取色与平台原生控件风格（ADR-V5-24）。
- 外部前提：只用 Flutter SDK（Material 3 组件作为底层实现）；Material Symbols Rounded 字体按 Apache-2.0 随应用打包并只保留用到的字形；不新增第三方包。
- 产品取舍（2026-10-19 甲方确认）：主导航顺序 README §6 Q21、高对比度跟随系统 Q22、不提供作答音效 Q23、Windows 最小窗口 600×500 Q24、矮高度主操作在右侧 Q27。

**验收标准**
- [R42.f] 单元测试（`app/test/ui/design/contrast_test.dart`）：按 WCAG 2.1 公式对 5 套预设 × 浅/深色计算 c 中各项对比度，全部达到门槛，且与 c 表数值误差 ≤ 0.01；语义色在 5 套预设中取值相同。
- [R42.f] Widget 测试：`AppearanceController.set` 切换预设与外观模式后同一帧内 `Theme.of` 已变化，路由栈与页面 `State` 不变；用 Fake `DevicePrefStore` 断言写入键 `appearance.v1` 与 `{"v":1,…}`；重新 `load` 后恢复；写入损坏 JSON 或 `"v":2` 时得到默认值（`system`、`qunqing`）；偏好不出现在 outbox 与备份范围中。
- [R42.e] Widget 测试：`LayoutInfo.fromSize` 对 d 表每一行的典型尺寸（360×800、800×360、800×1280、1280×800、600×500、960×1032、1920×1080）得到表中的档位、矮高度与导航形态；`textScale` 2.0 时宽档降为中等档。
- [R42.c] 性能：两端真机按 CORE-01 全局资源预算表“点击到可见反馈”“转场与动效”“主题切换”行测量（AND-12、WIN-13 执行），满足预算。

- [R42.d] of(context)返回FmlTokens，5预设×2明暗字段齐全且与ThemeExtension是同一对象；嵌套Theme读最近值；缺少任一扩展抛FML_THEME_MISSING而非空指针；切主题后color随新Theme更新。


**规模**：约 360 行；主包 `app/lib/design/`、`app/lib/ui/design/`（不含 components/、warmup.dart）。

