// 不背公式（BubeiGongshi）CORE-01：空壳界面可启动的最小 Widget 测试。

import 'package:bubeigongshi/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('空壳应用启动并显示标题与占位文案', (WidgetTester tester) async {
    await tester.pumpWidget(const FmlShellApp());

    expect(find.text('不背公式'), findsOneWidget);
    expect(find.text('公式背诵'), findsOneWidget);
    expect(find.text('界面骨架已就位'), findsOneWidget);
  });
}
