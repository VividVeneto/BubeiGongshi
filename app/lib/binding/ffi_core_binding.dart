part of 'core_binding.dart';

/// Native transport. Only the root isolate owns the process completion slot.
final class FfiCoreBinding implements CoreBinding {
  /// Loads the library; ABI mismatch remains a platform startup decision.
  FfiCoreBinding(this.spec)
    : _native = FmlCoreBindings(DynamicLibrary.open(spec.path)),
      _root = null,
      _profile = null {
    if (RootIsolateToken.instance != null) {
      if (_owner != null)
        throw StateError('A completion owner is already open');
      final listener = NativeCallable<FmlCompletionFunction>.listener(
        _complete,
      );
      final status = _native.fml_register_completion(
        listener.nativeFunction,
        nullptr,
      );
      if (status != 0) {
        listener.close();
        throw _failure(status);
      }
      _listener = listener;
      _owner = this;
    }
  }
  FfiCoreBinding._view(FfiCoreBinding root, this._profile)
    : _root = root,
      spec = root.spec,
      _native = root._native;
  static FfiCoreBinding? _owner;
  final FmlCoreBindings _native;
  final FfiCoreBinding? _root;
  final String? _profile;
  final _generations = StreamController<String>.broadcast(sync: true);
  final _jobs = <int, _Job>{};
  final _cancelling = <Future<void>>{};
  NativeCallable<FmlCompletionFunction>? _listener;
  bool _closed = false;
  Future<void>? _disposing;
  FfiCoreBinding get _transport => _root ?? this;
  @override
  final CoreLibrarySpec spec;
  @override
  int abiVersion() => _native.fml_abi_version();
  @override
  Stream<String> get engineGenerations => _transport._generations.stream;
  void _check() {
    if (_closed || _transport._closed) throw StateError('Binding disposed');
  }

  @override
  CoreBinding scopedTo(String profileHandle) {
    _check();
    _u64(profileHandle);
    if (_profile != null && _profile != profileHandle)
      throw StateError('Profile view is immutable');
    return FfiCoreBinding._view(_transport, profileHandle);
  }

  Uint8List _take(FmlBuf buf) {
    try {
      return Uint8List.fromList(buf.ptr.asTypedList(buf.len));
    } finally {
      if (buf.ptr != nullptr) _native.fml_free_buffer(buf);
    }
  }

  @override
  Map<String, Object?> call(
    String op,
    Map<String, Object?> body, {
    Duration? budget,
    String? expectedGeneration,
  }) {
    _check();
    return _request(op, body, _profile, budget, expectedGeneration, (
      name,
      req,
      len,
    ) {
      final out = calloc<FmlBuf>();
      try {
        final status = _native.fml_call(name, req, len, out);
        if (out.ref.ptr == nullptr) {
          if (status < 0) throw _failure(status);
          throw const FormatException('Missing native response');
        }
        return _decode(_take(out.ref), status, _transport._generations.add);
      } finally {
        calloc.free(out);
      }
    });
  }

  @override
  Future<Map<String, Object?>> submit(
    String op,
    Map<String, Object?> body, {
    CancelToken? cancel,
    String? expectedGeneration,
  }) {
    _check();
    final owner = _transport;
    if (owner._listener == null)
      throw StateError('Submit requires root isolate');
    if (cancel?.isCancelled ?? false) return Future.error(FfiCancelled());
    return _request(op, body, _profile, null, expectedGeneration, (
      name,
      req,
      len,
    ) {
      final id = calloc<Uint64>();
      try {
        final status = _native.fml_submit(name, req, len, id);
        if (status != 0)
          return Future<Map<String, Object?>>.error(_failure(status));
        final job = _Job(cancel);
        owner._jobs[id.value] = job;
        final jobId = id.value;
        job.onCancel = () => owner._cancel(jobId, job);
        cancel?._listeners.add(job.onCancel!);
        return job.done.future;
      } finally {
        calloc.free(id);
      }
    });
  }

  void _finish(int id, _Job job, {Map<String, Object?>? value, Object? error}) {
    _jobs.remove(id);
    job.token?._listeners.remove(job.onCancel);
    if (job.cancelled) error = FfiCancelled();
    if (error != null) {
      job.done.completeError(error);
    } else {
      job.done.complete(value!);
    }
  }

  void _complete(int id, FmlBuf buf, Pointer<Void> userData) {
    final job = _jobs[id];
    try {
      final bytes = _take(
        buf,
      ); // Even unknown/late jobs relinquish the buffer once.
      if (job != null)
        _finish(id, job, value: _decode(bytes, null, _generations.add));
    } catch (error) {
      if (job != null && !job.done.isCompleted) _finish(id, job, error: error);
    }
  }

  void _cancel(int id, _Job job) {
    if (job.cancelled || job.done.isCompleted) return;
    job.cancelled = true;
    final task = _cancelNative(id, job);
    _cancelling.add(task);
    task.whenComplete(() => _cancelling.remove(task));
  }

  Future<void> _cancelNative(int id, _Job job) async {
    try {
      // Capture only transferable values; never block the completion listener.
      final path = spec.path;
      final status = await Isolate.run(() => _cancelAt(path, id));
      if (!job.done.isCompleted && status != 1) {
        _finish(
          id,
          job,
          error: status == 0 || status == -4
              ? FfiCancelled()
              : _failure(status),
        );
      }
    } catch (error) {
      if (!job.done.isCompleted) _finish(id, job, error: error);
    }
  }

  @override
  Future<void> dispose() {
    _closed = true;
    return _disposing ??= _drain();
  }

  Future<void> _drain() async {
    if (_root == null && _listener != null) {
      final jobs = _jobs.entries.toList();
      final drained = Future.wait(
        jobs.map(
          (entry) => entry.value.done.future.then<void>(
            (_) {},
            onError: (Object _) {},
          ),
        ),
      );
      for (final entry in jobs) {
        _cancel(entry.key, entry.value);
      }
      await drained;
      await Future.wait(_cancelling.toList());
      while (true) {
        final status = _native.fml_register_completion(nullptr, nullptr);
        if (status == 0) break;
        if (status != -6)
          throw _failure(status); // Keep listener alive on failure.
        await Future<void>.delayed(Duration.zero);
      }
      _listener!.close();
      _listener = null;
      _owner = null;
    }
    await _generations.close();
  }
}

int _cancelAt(String path, int id) =>
    FmlCoreBindings(DynamicLibrary.open(path)).fml_cancel(id);

final class _Job {
  _Job(this.token);
  final CancelToken? token;
  final done = Completer<Map<String, Object?>>();
  void Function()? onCancel;
  bool cancelled = false;
}
