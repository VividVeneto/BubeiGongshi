// 不背公式（BubeiGongshi）CORE-01：Dart 侧配置断言（CORE-01 测试方案第 7、5、2 条的 Dart 部分）。

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

/// 正例源码：公开项均有文档注释；负例由它删掉 `///` 行得到，两者只差这些行。
const String documentedDartSource = '''
/// 返回入参加一。
int bump(int value) {
  return value + 1;
}

/// 公开类，公开成员均有文档。
class Counter {
  /// 以零计数构造。
  Counter(this.count);

  /// 当前计数。
  final int count;

  /// 返回两倍计数。
  int doubled() => count * 2;
}
''';

/// 删除源码中的文档注释行；负例与正例因此只差“公开项是否有文档”。
String withoutDocComments(String source) {
  final List<String> kept = <String>[];
  int removed = 0;
  for (final String line in source.split('\n')) {
    if (line.trimLeft().startsWith('///')) {
      removed++;
      continue;
    }
    kept.add(line);
  }
  expect(removed, greaterThanOrEqualTo(4), reason: '正例必须含公开项文档注释');
  return kept.join('\n');
}

/// 找到真实的 Dart 可执行文件：优先 Flutter SDK 自带的，其次 PATH 上的 dart。
String dartExecutable() {
  final String? flutterRoot = Platform.environment['FLUTTER_ROOT'];
  if (flutterRoot != null && flutterRoot.isNotEmpty) {
    for (final String candidate in <String>[
      '$flutterRoot/bin/dart.bat',
      '$flutterRoot/bin/dart',
    ]) {
      if (File(candidate).existsSync()) {
        return candidate;
      }
    }
  }
  return 'dart';
}

/// 在给定目录运行 Dart 命令（Windows 下 .bat 需经 shell 解析）。
ProcessResult runDart(String dart, List<String> arguments, Directory cwd) {
  return Process.runSync(
    dart,
    arguments,
    workingDirectory: cwd.path,
    runInShell: Platform.isWindows,
  );
}

/// 写一个一次性 Dart 包：真实 analysis_options（取自 app/）+ 指定 lib 源码。
void writeDartPackage(Directory dir, String analysisOptions, String source) {
  dir.createSync(recursive: true);
  File('${dir.path}/pubspec.yaml').writeAsStringSync(
    'name: fml_doc_lint_fixture\n'
    'publish_to: none\n'
    'environment:\n'
    '  sdk: ">=3.0.0 <4.0.0"\n',
  );
  File('${dir.path}/analysis_options.yaml').writeAsStringSync(analysisOptions);
  Directory('${dir.path}/lib').createSync();
  File('${dir.path}/lib/public_api.dart').writeAsStringSync(source);
}

void main() {
  test('analysis_options 显式启用 public_member_api_docs', () {
    final String options = readAppFile('analysis_options.yaml');
    expect(options.contains('public_member_api_docs: true'), isTrue);
  });

  test('public_member_api_docs 真实拒绝缺文档的公开成员（临时包 + dart analyze）', () {
    final Directory temp = Directory.systemTemp.createTempSync(
      'fml_doc_lints_',
    );
    try {
      final String options = readAppFile('analysis_options.yaml');
      final String negativeSource = withoutDocComments(documentedDartSource);
      expect(negativeSource, isNot(documentedDartSource));

      final Directory positiveDir = Directory('${temp.path}/positive');
      final Directory negativeDir = Directory('${temp.path}/negative');
      writeDartPackage(positiveDir, options, documentedDartSource);
      writeDartPackage(negativeDir, options, negativeSource);

      final String dart = dartExecutable();
      // 分析器只在解析过依赖的包内启用 lint（缺 package_config 时 public_member_api_docs
      // 完全不报），故正负例都走真实 pub 解析；夹具无第三方依赖，--offline 即可完成。
      for (final Directory dir in <Directory>[positiveDir, negativeDir]) {
        final ProcessResult pub = runDart(dart, <String>[
          'pub',
          'get',
          '--offline',
        ], dir);
        expect(
          pub.exitCode,
          0,
          reason: 'dart pub get --offline 失败：\n${pub.stdout}\n${pub.stderr}',
        );
      }

      final ProcessResult positive = runDart(dart, <String>[
        'analyze',
        '--fatal-infos',
        '--fatal-warnings',
        '.',
      ], positiveDir);
      expect(
        positive.exitCode,
        0,
        reason: '含文档的正例不应报 lint：\n${positive.stdout}\n${positive.stderr}',
      );
      expect('${positive.stdout}', isNot(contains('public_member_api_docs')));

      final ProcessResult negative = runDart(dart, <String>[
        'analyze',
        '--fatal-infos',
        '--fatal-warnings',
        '.',
      ], negativeDir);
      final String output = '${negative.stdout}\n${negative.stderr}';
      expect(negative.exitCode, isNot(0), reason: '缺文档负例必须非零退出：\n$output');
      expect(output, contains('public_member_api_docs'));
      expect(output, contains('Missing documentation for a public member'));
    } finally {
      temp.deleteSync(recursive: true);
    }
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
