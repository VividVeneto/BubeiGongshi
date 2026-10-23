import 'dart:async';
import 'dart:convert';
import 'dart:ffi';
import 'dart:isolate';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' show RootIsolateToken;

import 'package:ffi/ffi.dart';

import 'errors.dart';
import 'fmlcore.g.dart';
part 'ffi_core_binding.dart';
part 'wire.dart';

/// Process-lifetime native library location, supplied by the platform owner.
final class CoreLibrarySpec {
  /// Does not load or validate the path.
  const CoreLibrarySpec(this.path);

  /// Dynamic library path; never inferred from the host platform.
  final String path;
}

/// Cooperative, idempotent cancellation; native draining is asynchronous.
final class CancelToken {
  bool _cancelled = false;
  final _listeners = <void Function()>{};

  /// Whether cancellation has been requested.
  bool get isCancelled => _cancelled;

  /// Requests cancellation of all submissions using this token.
  void cancel() {
    _cancelled = true;
    for (final listener in _listeners.toList()) {
      listener();
    }
  }
}

/// ABI failure, separate from domain DTO errors; never includes raw payloads.
final class FfiException implements Exception {
  /// Carries the native status and optional validated wire metadata.
  const FfiException(this.status, {this.code, this.traceId});

  /// Native status, including unregistered future negative values.
  final int status;

  /// Registered wire code when available.
  final String? code;

  /// Nonzero validated wire trace when available.
  final String? traceId;
  @override
  String toString() =>
      'FfiException(status: $status, code: $code, traceId: $traceId)';
}

/// Submission cancelled; a late native result is still drained by the owner.
final class FfiCancelled implements Exception {}

/// JSON transport only; business callers use CORE-67 generated DTOs.
abstract interface class CoreBinding {
  /// Opens without swallowing loader errors or enforcing the platform ABI UI.
  static CoreBinding open(CoreLibrarySpec spec) => FfiCoreBinding(spec);

  /// Rejects new work and drains owned jobs before unregistering the listener.
  Future<void> dispose();

  /// Returns an immutable profile view, not a Store owner.
  CoreBinding scopedTo(String profileHandle);

  /// Shareable library location for background synchronous callers.
  CoreLibrarySpec get spec;

  /// Packed ABI major/minor, compared by platform composition.
  int abiVersion();

  /// Generation metadata, emitted before delivering its result or error.
  Stream<String> get engineGenerations;

  /// Executes a short operation; returns only the business ok object.
  Map<String, Object?> call(
    String op,
    Map<String, Object?> body, {
    Duration? budget,
    String? expectedGeneration,
  });

  /// Submits on the root isolate; background isolates must not own callbacks.
  Future<Map<String, Object?>> submit(
    String op,
    Map<String, Object?> body, {
    CancelToken? cancel,
    String? expectedGeneration,
  });
}
