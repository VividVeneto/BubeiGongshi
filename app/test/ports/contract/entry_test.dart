import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/binding/core_binding.dart';
import 'package:bubeigongshi/binding/errors.dart';
import 'package:bubeigongshi/binding/fmlcore.g.dart' show FML_ABI_MAJOR;
import 'package:bubeigongshi/composition/entry.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

import '../../fakes/composition_fakes.dart';
import '../../fakes/platform_fakes.dart';

void main() {
  const spec = CoreLibrarySpec('unused');
  testWidgets('loader failure never builds ports; fixed copy and only exit', (
    tester,
  ) async {
    var built = false;
    await runPlatformApp(spec, () {
      built = true;
      return portsWith();
    }, open: (_) => throw ArgumentError('secret/path'));
    await tester.pumpAndSettle();
    expect(built, isFalse);
    expect(find.text('核心组件加载失败，请重新安装'), findsOneWidget);
    expect(find.textContaining('secret'), findsNothing);
    expect(find.byType(TextButton), findsOneWidget);
    final methods = <String>[];
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform,
      (call) async {
        methods.add(call.method);
        return null;
      },
    );
    addTearDown(
      () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        null,
      ),
    );
    await tester.tap(find.text('退出'));
    await tester.pump();
    expect(methods, contains('SystemNavigator.pop'));
  });
  testWidgets(
    'major mismatch disposes before returning and never builds ports',
    (tester) async {
      final core = FakeCoreBinding(version: (FML_ABI_MAJOR + 1) << 16);
      var built = false;
      await runPlatformApp(spec, () {
        built = true;
        return portsWith();
      }, open: (_) => core);
      await tester.pumpAndSettle();
      expect(built, isFalse);
      expect(core.disposed, isTrue);
      expect(find.text('核心版本不匹配，请重新安装'), findsOneWidget);
      expect(find.byType(TextButton), findsOneWidget);
    },
  );
  testWidgets(
    'minor compatible and Unsupported snapshot does not fabricate fields',
    (tester) async {
      final core = FakeCoreBinding(version: FML_ABI_MAJOR << 16 | 42);
      var calls = 0;
      await runPlatformApp(spec, () {
        calls++;
        return portsWith();
      }, open: (_) => core);
      await tester.pumpAndSettle();
      expect(calls, 1);
      expect(core.disposed, isFalse);
      expect(find.text('ABI $FML_ABI_MAJOR.42'), findsOneWidget);
      expect(find.text('运行时信息待平台卡实现'), findsOneWidget);
      expect(find.textContaining('osVersion:'), findsNothing);
    },
  );
  testWidgets('smoke shows every injected runtime field and ABI', (
    tester,
  ) async {
    final runtime = FakeRuntimeInfo(
      RuntimeSnapshot(
        os: 'windows',
        osVersion: '26100',
        locale: 'zh-CN',
        availMemBytes: 123,
        dpiScale: 1.25,
        abi: 'x64',
        gpuAvailable: true,
      ),
    );
    await smokeEntry(portsWith(runtime: runtime), FakeCoreBinding());
    await tester.pumpAndSettle();
    expect(find.text('ABI $FML_ABI_MAJOR.0'), findsOneWidget);
    for (final field in [
      'os: windows',
      'osVersion: 26100',
      'locale: zh-CN',
      'availMemBytes: 123',
      'dpiScale: 1.25',
      'abi: x64',
      'gpuAvailable: true',
    ]) {
      expect(find.textContaining(field), findsOneWidget);
    }
  });
  testWidgets(
    'non-Unsupported runtime failures propagate and close owned binding',
    (tester) async {
      final core = FakeCoreBinding();
      final runtime = FakeRuntimeInfo(null)..errorCode = 'PLATFORM_IO';
      await expectLater(
        runPlatformApp(
          spec,
          () => portsWith(runtime: runtime),
          open: (_) => core,
        ),
        throwsA(
          isA<FmlException>().having((e) => e.code, 'code', 'PLATFORM_IO'),
        ),
      );
      expect(core.disposed, isTrue);
      await expectLater(
        runPlatformApp(
          spec,
          portsWith,
          open: (_) => throw StateError('unclassified'),
        ),
        throwsStateError,
      );
    },
  );
  testWidgets(
    'real missing DLL default loader rejects without constructing ports',
    (tester) async {
      var built = false;
      await runPlatformApp(
        const CoreLibrarySpec('core04-nonexistent-library.dll'),
        () {
          built = true;
          return portsWith();
        },
      );
      await tester.pumpAndSettle();
      expect(built, isFalse);
      expect(find.text('核心组件加载失败，请重新安装'), findsOneWidget);
    },
  );
  final native = Platform.environment['FML_TEST_LIBRARY'];
  final bumped = Platform.environment['FML_BUMP_LIBRARY'];
  testWidgets(
    'real default loader accepts normal ABI and releases after builder failure',
    (tester) async {
      var built = false;
      await expectLater(
        runPlatformApp(CoreLibrarySpec(native!), () {
          built = true;
          throw StateError('fixture-builder');
        }),
        throwsStateError,
      );
      expect(built, isTrue);
      final reopened = CoreBinding.open(CoreLibrarySpec(native));
      expect(reopened.abiVersion() >> 16, FML_ABI_MAJOR);
      await reopened.dispose();
    },
    skip: native == null,
  );
  testWidgets(
    'real default loader rejects bumped ABI without constructing ports',
    (tester) async {
      var built = false;
      await runPlatformApp(CoreLibrarySpec(bumped!), () {
        built = true;
        return portsWith();
      });
      await tester.pumpAndSettle();
      expect(built, isFalse);
      expect(find.text('核心版本不匹配，请重新安装'), findsOneWidget);
      final reopened = CoreBinding.open(CoreLibrarySpec(bumped));
      await reopened.dispose();
    },
    skip: bumped == null,
  );
  testWidgets('real library smoke displays ABI with Unsupported runtime', (
    tester,
  ) async {
    late CoreBinding core;
    await runPlatformApp(
      CoreLibrarySpec(native!),
      portsWith,
      open: (s) => core = CoreBinding.open(s),
    );
    addTearDown(() => core.dispose());
    await tester.pumpAndSettle();
    final abi = core.abiVersion();
    expect(
      find.text(
        'ABI @@major.@@minor'
            .replaceAll('@@major', (abi >> 16).toString())
            .replaceAll('@@minor', (abi & 0xffff).toString()),
      ),
      findsOneWidget,
    );
    expect(find.text('运行时信息待平台卡实现'), findsOneWidget);
  }, skip: native == null);
}
