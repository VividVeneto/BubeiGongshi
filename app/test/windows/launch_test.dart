import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/composition/windows_launch.dart';

void main() {
  test(
    'R19 exe-adjacent path rejects traversal and ignores current directory',
    () {
      final original = Directory.current;
      final temporary = Directory.systemTemp.createTempSync('win01-cwd-');
      try {
        Directory.current = temporary;
        final expected = File(Platform.resolvedExecutable).parent.uri
            .resolve('fmlcore.dll')
            .toFilePath();
        expect(appDirFile('fmlcore.dll'), expected);
        expect(File(appDirFile('fmlcore.dll')).isAbsolute, isTrue);
        for (final bad in [
          '../fmlcore.dll',
          r'C:\evil.dll',
          '/evil.dll',
          'https://evil/dll',
        ]) {
          expect(() => appDirFile(bad), throwsArgumentError);
        }
      } finally {
        Directory.current = original;
        temporary.deleteSync();
      }
    },
  );
  test(
    'R18 launch args copied once, immutable, no VM argument substitution',
    () {
      expect(() => windowsLaunchArguments, throwsStateError);
      final args = ['--update-nonce=abc', '中文 空格'];
      setWindowsLaunchArguments(args);
      args.clear();
      expect(windowsLaunchArguments, ['--update-nonce=abc', '中文 空格']);
      expect(() => windowsLaunchArguments.add('bad'), throwsUnsupportedError);
      expect(() => setWindowsLaunchArguments([]), throwsStateError);
    },
  );
}
