// 不背公式（BubeiGongshi）Flutter 共享界面最小空壳（CORE-01）。
//
// 本文件只负责让应用在没有 FFI、没有核心绑定、没有平台工程的条件下可启动：
// 不含 CoreBinding、不 import platform/、不判断平台、不含业务逻辑。
// 核心绑定由 CORE-56/CORE-67 接入，平台原生工程由 AND-01/WIN-01 生成。

import 'package:flutter/material.dart';

/// 应用根 Widget：只装配主题与首页空壳，不判断平台、不访问核心绑定。
class FmlShellApp extends StatelessWidget {
  /// 创建空壳应用。
  const FmlShellApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '不背公式',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: const Color(0xFF3F51B5)),
      home: const FmlShellHomePage(),
    );
  }
}

/// 首页空壳：只显示占位文案；公式列表、作答与排程由后续界面卡实现。
class FmlShellHomePage extends StatelessWidget {
  /// 创建首页空壳。
  const FmlShellHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('不背公式')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Text('公式背诵', style: theme.textTheme.headlineMedium),
            const SizedBox(height: 12),
            Text('界面骨架已就位', style: theme.textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }
}

/// 应用入口：启动空壳界面。
void main() {
  runApp(const FmlShellApp());
}
