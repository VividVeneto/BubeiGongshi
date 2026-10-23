import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import '../../windows/build_core.dart' show validateBuildDefines;

void main() {
  String encode(List<String> values) =>
      values.map((v) => base64.encode(utf8.encode(v))).join(',');
  test('R18 production rejects every test define, including false', () {
    for (final value in [
      'FML_TEST_BUILD=true',
      'FML_TEST_BUILD=false',
      'FML_TEST_CRASH_ON_FIRST_START=true',
      'FML_TEST_UNKNOWN=false',
    ]) {
      expect(
        () => validateBuildDefines({
          'DART_DEFINES': encode([value]),
        }),
        throwsStateError,
      );
    }
    validateBuildDefines({
      'DART_DEFINES': encode(['FML_API_HOST=host', 'FML_PACK_HOST=host']),
    });
  });
  test(
    'R18 explicit test build requires true marker and known boolean switches',
    () {
      final env = {
        'FML_WINDOWS_TEST_BUILD': '1',
        'DART_DEFINES': encode([
          'FML_TEST_BUILD=true',
          'FML_TEST_CRASH_ON_FIRST_START=true',
        ]),
      };
      validateBuildDefines(env);
      for (final invalid in [
        ['FML_TEST_BUILD=false'],
        ['FML_TEST_BUILD=true', 'FML_TEST_OTHER=true'],
        ['FML_TEST_BUILD=true', 'FML_TEST_CRASH_ON_FIRST_START=1'],
        ['FML_TEST_BUILD=true', 'FML_TEST_BUILD=false'],
        ['missing-equals'],
      ]) {
        expect(
          () => validateBuildDefines({...env, 'DART_DEFINES': encode(invalid)}),
          throwsStateError,
        );
      }
      expect(
        () => validateBuildDefines({'DART_DEFINES': '!'}),
        throwsFormatException,
      );
    },
  );
}
