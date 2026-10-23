import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/binding/core_binding.dart';
import 'package:bubeigongshi/composition/entry.dart';
import 'package:bubeigongshi/composition/ports_windows.dart';
import 'package:bubeigongshi/ports/unsupported/unsupported_ports.dart';

void main() {
  test(
    'R01 all eleven Windows slots are explicit Unsupported with one log each',
    () {
      final messages = <String?>[];
      final old = debugPrint;
      debugPrint = (String? message, {int? wrapWidth}) => messages.add(message);
      try {
        final p = buildWindowsPorts();
        expect(p.keys, isA<UnsupportedSecureKeyValueStore>());
        expect(p.files, isA<UnsupportedLocalFileStore>());
        expect(p.picker, isA<UnsupportedImagePicker>());
        expect(p.camera, isA<UnsupportedCameraController>());
        expect(p.notifications, isA<UnsupportedNotificationScheduler>());
        expect(p.clipboard, isA<UnsupportedClipboardAdapter>());
        expect(p.runtime, isA<UnsupportedRuntimeInfo>());
        expect(p.lifecycle, isA<UnsupportedAppLifecycle>());
        expect(p.http, isA<UnsupportedHttpTransport>());
        expect(p.exporter, isA<UnsupportedFileExporter>());
        expect(p.documents, isA<UnsupportedDocumentPicker>());
        expect(p.platformInstallers, isEmpty);
        expect(messages.length, 11);
        expect(messages.toSet().length, 11);
        expect(messages.every((m) => m!.contains('Unsupported')), isTrue);
      } finally {
        debugPrint = old;
      }
    },
  );
  final release = Platform.environment['FML_WINDOWS_LIBRARY'];
  final bump = Platform.environment['FML_BUMP_LIBRARY'];
  testWidgets(
    'R01 actual Release DLL and Windows aggregate show ABI and pending runtime',
    (tester) async {
      late CoreBinding core;
      await runPlatformApp(
        CoreLibrarySpec(release!),
        buildWindowsPorts,
        open: (spec) => core = CoreBinding.open(spec),
      );
      addTearDown(core.dispose);
      await tester.pumpAndSettle();
      expect(find.text('ABI 1.0'), findsOneWidget);
      expect(find.text('运行时信息待平台卡实现'), findsOneWidget);
    },
    skip: release == null,
  );
  testWidgets('R18 real MAJOR bump never constructs Windows ports', (
    tester,
  ) async {
    var count = 0;
    await runPlatformApp(CoreLibrarySpec(bump!), () {
      count++;
      return buildWindowsPorts();
    });
    await tester.pumpAndSettle();
    expect(count, 0);
    expect(find.text('核心版本不匹配，请重新安装'), findsOneWidget);
    expect(find.byType(TextButton), findsOneWidget);
  }, skip: bump == null);
  testWidgets('R18 malformed DLL is contained without constructing ports', (
    tester,
  ) async {
    final directory = Directory.systemTemp.createTempSync('win01-bad-dll-');
    addTearDown(() => directory.deleteSync(recursive: true));
    final file = File('${directory.path}/fmlcore.dll')
      ..writeAsStringSync('not PE');
    var count = 0;
    await runPlatformApp(CoreLibrarySpec(file.path), () {
      count++;
      return buildWindowsPorts();
    });
    await tester.pumpAndSettle();
    expect(count, 0);
    expect(find.text('核心组件加载失败，请重新安装'), findsOneWidget);
    expect(find.byType(TextButton), findsOneWidget);
  });
  testWidgets('R18 absent DLL never constructs Windows ports', (tester) async {
    var count = 0;
    await runPlatformApp(
      CoreLibrarySpec(File('win01-absent.dll').absolute.path),
      () {
        count++;
        return buildWindowsPorts();
      },
    );
    await tester.pumpAndSettle();
    expect(count, 0);
    expect(find.text('核心组件加载失败，请重新安装'), findsOneWidget);
    expect(find.byType(TextButton), findsOneWidget);
  });
}
