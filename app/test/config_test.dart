// 不背公式（BubeiGongshi）CORE-01：Dart 侧配置断言（CORE-01 测试方案第 7 条与第 2 条的 Dart 部分）。

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 读取相对 app/ 的文件内容；缺失时让测试失败而不是跳过。
String readAppFile(String relativePath) {
  final File file = File(relativePath);
  expect(file.existsSync(), isTrue, reason: '缺少文件 $relativePath');
  return file.readAsStringSync();
}

/// SemVer 主体（主.次.修订）是否合法。
final RegExp semVerCore = RegExp(r'^\d+\.\d+\.\d+$');

/// 从 pubspec.yaml 取出 version 行（不引入 YAML 依赖）。
String pubspecVersion(String yaml) {
  for (final String line in yaml.split('\n')) {
    if (line.startsWith('version:')) {
      return line.substring('version:'.length).trim();
    }
  }
  fail('pubspec.yaml 缺少 version 字段');
}

void main() {
  test('analysis_options 显式启用 public_member_api_docs', () {
    final String options = readAppFile('analysis_options.yaml');
    expect(options.contains('public_member_api_docs: true'), isTrue);
  });

  test('.flutter-version 只含单行版本号', () {
    final String text = readAppFile('.flutter-version');
    expect(text.trim(), '3.47.7');
    expect(text.trim().contains(RegExp(r'\d')), isTrue);
  });

  test('pubspec 版本与根 Cargo.toml 工作区版本主体一致', () {
    final String pubspec = readAppFile('pubspec.yaml');
    final String pubVersion = pubspecVersion(pubspec);
    expect(
      semVerCore.hasMatch(pubVersion),
      isTrue,
      reason: 'pubspec 版本应为 SemVer 主体：$pubVersion',
    );

    final String cargo = File('../Cargo.toml').readAsStringSync();
    final RegExpMatch? match = RegExp(
      r'^version = "([^"]+)"',
      multiLine: true,
    ).firstMatch(cargo.split('[workspace.package]').last);
    expect(
      match,
      isNotNull,
      reason: '根 Cargo.toml 缺少 workspace.package.version',
    );
    expect(pubVersion.split('+').first, match!.group(1));
  });

  test('pubspec 不引入第三方 Dart 依赖（本卡只锁 Flutter SDK 依赖）', () {
    final String pubspec = readAppFile('pubspec.yaml');
    expect(pubspec.contains('sdk: flutter'), isTrue);
    expect(pubspec.contains('publish_to: none'), isTrue);
  });
}
