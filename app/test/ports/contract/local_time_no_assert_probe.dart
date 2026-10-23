// Standalone Dart probe: dart run test/ports/contract/local_time_no_assert_probe.dart
import '../../../lib/ports/port_dtos.dart';

/// Proves release-mode validation is not an assert-only check.
void main() {
  var assertsEnabled = false;
  assert(() {
    assertsEnabled = true;
    return true;
  }());
  if (assertsEnabled) throw StateError('Run without --enable-asserts');
  for (final value in [(-1, 0), (24, 0), (0, -1), (0, 60)]) {
    try {
      LocalTime(value.$1, value.$2);
    } on ArgumentError {
      continue;
    }
    throw StateError('Invalid time accepted');
  }
  for (final hour in [0, 23]) {
    for (final minute in [0, 59]) {
      final time = LocalTime(hour, minute);
      if (time.hour != hour || time.minute != minute)
        throw StateError('Value changed');
    }
  }
  print(
    'CORE04 LocalTime: assertions disabled; 4 invalid and 4 valid boundaries passed',
  );
}
