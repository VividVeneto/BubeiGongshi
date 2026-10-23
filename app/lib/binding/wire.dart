part of 'core_binding.dart';

const _ffiCodes = [
  'FFI_BAD_ARG',
  'FFI_UNKNOWN_OP',
  'FFI_VERSION_MISMATCH',
  'FFI_STALE_HANDLE',
  'FFI_PANIC',
  'FFI_BUSY',
];
final _random = Random.secure();
String _trace() {
  final bytes = List.generate(16, (_) => _random.nextInt(256));
  if (bytes.every((b) => b == 0)) bytes[15] = 1;
  return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
}

bool _traceValid(Object? value) =>
    value is String &&
    RegExp(r'^[0-9a-f]{32}$').hasMatch(value) &&
    value != '0' * 32;
String _u64(String value) {
  if (!RegExp(r'^[0-9]+$').hasMatch(value) ||
      BigInt.parse(value) > BigInt.parse('18446744073709551615')) {
    throw ArgumentError('Expected unsigned decimal u64');
  }
  return value;
}

FfiException _failure(int status, [String? trace]) => FfiException(
  status,
  code: status <= -1 && status >= -6 ? _ffiCodes[-status - 1] : null,
  traceId: trace,
);
Map<String, Object?> _decode(
  Uint8List bytes,
  int? status,
  void Function(String) emit,
) {
  try {
    final env = jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;
    if (env['v'] is! int ||
        env['v'] != 1 ||
        !_traceValid(env['trace_id']) ||
        env.containsKey('ok') == env.containsKey('error'))
      throw const FormatException();
    final generation = env['engine_generation'];
    if (env.containsKey('engine_generation')) _u64(generation as String);
    final error = env.containsKey('error')
        ? FmlException.fromJson({'error': env['error']})
        : null;
    if (error != null && error.traceId != env['trace_id'])
      throw const FormatException();
    if (error == null) {
      if ((status != null && status != 0) ||
          env['ok'] is! Map<String, dynamic>) {
        throw const FormatException();
      }
      // Reuse CORE-02 diagnostic validation and CORE-67's generated DTOs.
      FmlException.fromJson({
        'error': {
          'code': 'FFI_BAD_ARG',
          'domain': 'ffi',
          'retryable': false,
          'trace_id': env['trace_id'],
          'diagnostics': env['diagnostics'],
        },
      });
    } else if (status == 0 || (status != null && status > 1)) {
      throw const FormatException();
    }
    final index = error == null ? -1 : _ffiCodes.indexOf(error.code);
    if (error != null && status != null) {
      if ((index >= 0 && status != -index - 1) ||
          (status >= -6 && status < 0 && index < 0)) {
        throw const FormatException();
      }
    }
    // Only a fully validated envelope may publish metadata.
    if (generation != null) emit(generation as String);
    if (error != null) {
      if (status != null && status < 0) {
        throw FfiException(
          status,
          code: index < 0 ? null : error.code,
          traceId: error.traceId,
        );
      }
      if (index >= 0)
        throw FfiException(
          -index - 1,
          code: error.code,
          traceId: error.traceId,
        );
      throw error;
    }
    return Map<String, Object?>.from(env['ok'] as Map);
  } on FmlException {
    rethrow;
  } on FfiException {
    rethrow;
  } catch (_) {
    throw const FormatException('Invalid native response envelope');
  }
}

T _request<T>(
  String op,
  Map<String, Object?> body,
  String? profile,
  Duration? budget,
  String? generation,
  T Function(Pointer<Char>, Pointer<Uint8>, int) invoke,
) {
  if (op.isEmpty || op.contains('\u0000'))
    throw ArgumentError('Invalid operation name');
  final ms = budget?.inMilliseconds;
  if (budget != null && (budget.isNegative || ms! > 0xffffffff)) {
    throw ArgumentError('budget_ms outside u32');
  }
  final bytes = utf8.encode(
    jsonEncode({
      'v': 1,
      'trace_id': _trace(),
      'body': body,
      if (profile != null) 'profile_handle': profile,
      if (ms != null) 'budget_ms': ms,
      if (generation != null) 'expected_generation': _u64(generation),
    }),
  );
  Pointer<Uint8> request = nullptr;
  Pointer<Utf8> name = nullptr;
  try {
    if (bytes.length > 16 * 1024 * 1024)
      throw ArgumentError('Request exceeds 16 MiB');
    request = calloc<Uint8>(bytes.length);
    request.asTypedList(bytes.length).setAll(0, bytes);
    name = op.toNativeUtf8();
    return invoke(name.cast(), request, bytes.length);
  } finally {
    if (request != nullptr) {
      request.asTypedList(bytes.length).fillRange(0, bytes.length, 0);
      calloc.free(request);
    }
    bytes.fillRange(0, bytes.length, 0);
    if (name != nullptr) calloc.free(name);
  }
}
