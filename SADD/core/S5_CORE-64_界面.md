### CORE-64 墨迹控制器与手写画布

**目标**：墨迹控制器与手写画布，与原卡分开实施与验收。

**范围**
- 包含：InkController、InkInputPolicy、DefaultInkInputPolicy、InkCanvas 与限额。
- 不包含：依赖卡已定义的业务算法、存储与平台能力；不修改其契约。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-29、CORE-55、CORE-58

**接口契约**

```dart
// app/lib/ui/recognition/ink/ink_canvas.dart
class InkCanvas extends StatefulWidget {
  const InkCanvas({super.key, required this.controller, this.policy = const DefaultInkInputPolicy()});
  final InkController controller; final InkInputPolicy policy;   // 页面传 features.get<InkInputPolicy>() ?? const DefaultInkInputPolicy()
}
// app/lib/recognition/ink/ink_input.dart（接缝与控制器；平台卡与 CORE-39 只 import 此文件，不 import ui/）
abstract interface class InkInputPolicy {          // 平台卡经 PlatformPorts.platformInstallers 登记（AND-07、WIN-08）
  bool accept(PointerDownEvent e, {required bool stylusSeen});   // false = 整笔丢弃（防手掌误触）；stylusSeen = 本画布清空后出现过触控笔
  double? pressureOf(PointerEvent e);                            // 0..1；null = 不记录压力
  bool isEraser(PointerEvent e);                                 // true = 该笔为擦除（触及的笔画整笔删除）
}
final class DefaultInkInputPolicy implements InkInputPolicy {
  const DefaultInkInputPolicy();   // accept 恒为 true；pressureOf：stylus 取 e.pressure 归一化，其余 null；isEraser：kind == invertedStylus
}
final class InkController extends ChangeNotifier {
  InkStrokesDto get strokes; bool get isEmpty;
  void onPointer(PointerEvent e);                          // 平台卡可从原生笔事件转 PointerEvent 后调用
  void undoStroke(); void clear();                         // 超过 500 笔或 20000 点时拒绝新笔画并提示
}
```
InkStrokesDto 为 CORE-29 InkStrokes 的 CORE-03 生成映射（跨语言消费者只引用）。

**实现约束**
- 采样按指针 id 分笔；清空后重置 stylusSeen；超过500笔/20000点拒绝新笔，仅显示本地输入上限提示，不抛未登记错误码、不触发识别。
- 撤销与整笔擦除仅改变本地墨迹，不触发网络或创建识别会话；输入方式及控件取 CORE-55/58。
- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-64_TEST.md](../Test/core/S5_CORE-64_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 230 行；主包 `app/lib/recognition/ink/`、`app/lib/ui/recognition/ink/`。

