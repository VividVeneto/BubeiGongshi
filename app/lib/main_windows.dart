import 'dart:io';

import 'binding/core_binding.dart';
import 'composition/entry.dart';
import 'composition/ports_windows.dart';
import 'composition/windows_launch.dart';

/// Windows process entry. ABI validation precedes construction of any ports.
Future<void> main(List<String> args) async {
  const crash = bool.fromEnvironment('FML_TEST_CRASH_ON_FIRST_START');
  const testBuild = bool.fromEnvironment('FML_TEST_BUILD');
  if (crash && !testBuild) {
    throw StateError('Crash injection requires FML_TEST_BUILD');
  }
  if (crash && args.any((arg) => arg.startsWith('--update-nonce'))) {
    exit(3);
  }
  setWindowsLaunchArguments(args);
  await runPlatformApp(
    CoreLibrarySpec(appDirFile('fmlcore.dll')),
    buildWindowsPorts,
  );
}
