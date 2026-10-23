// WIN-01 build glue: invoked by CMake, not part of the application isolate.
import 'dart:convert';
import 'dart:io';

/// Rejects test switches before any production build can start Cargo.
void validateBuildDefines(Map<String, String> environment) {
  final defines = <String, String>{};
  for (final encoded in (environment['DART_DEFINES'] ?? '').split(',')) {
    if (encoded.isEmpty) continue;
    final value = utf8.decode(base64.decode(encoded));
    final separator = value.indexOf('=');
    if (separator < 1) throw StateError('Malformed Dart define');
    final key = value.substring(0, separator);
    if (defines.containsKey(key)) throw StateError('Duplicate Dart define');
    defines[key] = value.substring(separator + 1);
  }
  final testKeys = defines.keys.where((key) => key.startsWith('FML_TEST_'));
  final allowTests = environment['FML_WINDOWS_TEST_BUILD'] == '1';
  if (testKeys.isNotEmpty &&
      (!allowTests || defines['FML_TEST_BUILD'] != 'true')) {
    throw StateError('Production build rejects FML_TEST_* defines');
  }
  for (final key in testKeys) {
    if (!const {
          'FML_TEST_BUILD',
          'FML_TEST_CRASH_ON_FIRST_START',
        }.contains(key) ||
        !const {'true', 'false'}.contains(defines[key])) {
      throw StateError('Unknown or malformed test define');
    }
  }
}

/// Builds the production C ABI DLL using the repository-pinned Rust toolchain.
Future<void> main(List<String> args) async {
  if (args.length != 1) throw ArgumentError('Expected Cargo output directory');
  validateBuildDefines(Platform.environment);
  final root = File.fromUri(Platform.script).parent.parent.parent.path;
  final flags = [
    '-C',
    'target-feature=+crt-static',
    '--remap-path-prefix=$root=/src',
    '-C',
    'link-arg=/Brepro',
    '-C',
    'link-arg=/PDBALTPATH:%_PDB%',
  ].join(String.fromCharCode(31));
  final process = await Process.start(
    'cargo',
    [
      'build',
      '--locked',
      '-p',
      'fml-ffi',
      '--release',
      '--target',
      'x86_64-pc-windows-msvc',
      '--target-dir',
      args.single,
    ],
    workingDirectory: root,
    mode: ProcessStartMode.inheritStdio,
    environment: {
      'CARGO_ENCODED_RUSTFLAGS': flags,
      'CARGO_PROFILE_RELEASE_DEBUG': 'line-tables-only',
      'CARGO_PROFILE_RELEASE_INCREMENTAL': 'false',
      'SOURCE_DATE_EPOCH': '0',
    },
  );
  exitCode = await process.exitCode;
}
