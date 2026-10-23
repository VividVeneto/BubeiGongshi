import 'dart:io';

/// Two clean production builds must produce identical core DLL bytes.
/// Pass the full path to the current MSVC dumpbin.exe as the only argument.
Future<void> main(List<String> args) async {
  if (args.length != 1) throw ArgumentError('Expected path to dumpbin.exe');
  final app = File.fromUri(Platform.script).parent.parent.parent;
  Future<void> flutter(List<String> command) async {
    final result = await Process.run(
      'flutter',
      command,
      workingDirectory: app.path,
      runInShell: Platform.isWindows,
    );
    stdout.write(result.stdout);
    stderr.write(result.stderr);
    if (result.exitCode != 0) throw StateError('flutter $command failed');
  }

  final dll = File('${app.path}/build/windows/x64/runner/Release/fmlcore.dll');
  List<int>? first;
  for (var run = 0; run < 2; run++) {
    await flutter(['clean']);
    await flutter([
      'build',
      'windows',
      '--release',
      '-t',
      'lib/main_windows.dart',
    ]);
    final bytes = await dll.readAsBytes();
    if (bytes.isEmpty) throw StateError('Empty core DLL');
    if (first != null) {
      if (first.length != bytes.length) throw StateError('DLL size changed');
      for (var i = 0; i < bytes.length; i++) {
        if (first[i] != bytes[i]) throw StateError('DLL changed at byte $i');
      }
    }
    first = bytes;
  }
  final imports = await Process.run(args.single, ['/DEPENDENTS', dll.path]);
  if (imports.exitCode != 0)
    throw StateError('dumpbin failed: ${imports.stderr}');
  final output = imports.stdout.toString().toLowerCase();
  stdout.write(imports.stdout);
  if (!output.contains('kernel32.dll') || output.contains('vcruntime140')) {
    throw StateError('Core DLL must use static CRT (not Flutter engine CRT)');
  }
  stdout.writeln(
    'R23: two clean DLL builds byte-identical; no dynamic CRT PASS',
  );
}
