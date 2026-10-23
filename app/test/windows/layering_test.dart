import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('R41 existing shared UI contains no platform probes or imports', () {
    // S0 renders here; ui/ is a future feature directory.
    final files = [File('lib/main.dart'), File('lib/composition/entry.dart')];
    final ui = Directory('lib/ui');
    if (ui.existsSync()) {
      files.addAll(
        ui
            .listSync(recursive: true)
            .whereType<File>()
            .where((f) => f.path.endsWith('.dart')),
      );
    }
    final probe = RegExp(
      r'Platform\.is[A-Z]|defaultTargetPlatform|TargetPlatform\.',
    );
    for (final file in files) {
      final source = file.readAsStringSync();
      expect(probe.hasMatch(source), isFalse, reason: file.path);
      final directives = source
          .split('\n')
          .where(
            (line) =>
                line.trimLeft().startsWith('import ') ||
                line.trimLeft().startsWith('export '),
          );
      expect(
        directives.any((line) => line.contains('platform/')),
        isFalse,
        reason: file.path,
      );
    }
  });
}
