// ignore_for_file: public_member_api_docs
// Test-only fixtures. No product source may import this library.
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:bubeigongshi/binding/core_binding.dart';
import 'package:bubeigongshi/binding/errors.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

final class FakeSecureKeyValueStore implements SecureKeyValueStore {
  final invalidAliases = <String>{};
  final _records = <String, Map<String, Uint8List>>{};
  var _serial = 0;
  void _check(String alias) {
    if (!RegExp(r'^[a-z0-9_.-]{1,64}$').hasMatch(alias))
      throw ArgumentError('Invalid alias');
    if (invalidAliases.contains(alias))
      throw FmlException('PLATFORM_KEY_UNAVAILABLE');
  }

  @override
  Future<Uint8List> wrap(String alias, Uint8List secret) async {
    _check(alias);
    final token = Uint8List.fromList([
      ++_serial >> 24,
      _serial >> 16,
      _serial >> 8,
      _serial & 255,
      ...secret.map((b) => b ^ 0xa5),
    ]);
    (_records[alias] ??= {})[token.join(',')] = Uint8List.fromList(secret);
    return token;
  }

  @override
  Future<Uint8List> unwrap(String alias, Uint8List wrapped) async {
    _check(alias);
    final value = _records[alias]?[wrapped.join(',')];
    if (value == null) throw FmlException('PLATFORM_KEY_UNAVAILABLE');
    return Uint8List.fromList(value);
  }

  @override
  Future<void> delete(String alias) async {
    _check(alias);
    _records.remove(alias);
  }

  @override
  Future<KeySecurityLevel> securityLevel(String alias) async {
    _check(alias);
    if (!_records.containsKey(alias))
      throw FmlException('PLATFORM_KEY_UNAVAILABLE');
    return KeySecurityLevel.software;
  }
}

final class FakeLocalFileStore implements LocalFileStore {
  final Directory privateRoot = Directory.systemTemp.createTempSync(
    'fml-core04-',
  );
  final excluded = <String>{};
  int availableBytes = 1024 * 1024 * 1024;
  Future<String> _inside(Directory dir) async {
    final root = await privateRoot.resolveSymbolicLinks();
    final target = await dir.resolveSymbolicLinks();
    if (target != root && !target.startsWith(root + Platform.pathSeparator)) {
      throw ArgumentError('Directory outside private root');
    }
    return target;
  }

  @override
  Future<Directory> root(StoreArea area) async {
    final dir = Directory.fromUri(privateRoot.uri.resolve('${area.name}/'));
    if (!await dir.exists()) await dir.create();
    await _inside(dir);
    return dir.absolute;
  }

  @override
  Future<int> freeBytes() async => availableBytes;
  @override
  Future<void> excludeFromSystemBackup(Directory dir) async =>
      excluded.add(await _inside(dir));
  Future<void> dispose() async => privateRoot.delete(recursive: true);
}

final class FakeImportedImage implements ImportedImage {
  FakeImportedImage(
    Uint8List bytes, {
    this.displayName = 'contract.png',
    this.mimeType = 'image/png',
    DateTime? expiresAt,
    DateTime Function()? now,
  }) : _bytes = Uint8List.fromList(bytes),
       _now = now ?? DateTime.now,
       expiresAt =
           expiresAt ?? (now ?? DateTime.now)().add(const Duration(hours: 1));
  final Uint8List _bytes;
  final DateTime Function() _now;
  bool ended = false;
  @override
  final String displayName;
  @override
  final String mimeType;
  @override
  int get byteLength => _bytes.length;
  @override
  final DateTime expiresAt;
  FakeImportedImage copyForBatch() => FakeImportedImage(
    _bytes,
    displayName: displayName,
    mimeType: mimeType,
    expiresAt: expiresAt,
    now: _now,
  );
  @override
  Future<Uint8List> readBytes() async {
    if (ended || !_now().isBefore(expiresAt)) throw FmlException('PLATFORM_IO');
    if (byteLength > 20 * 1024 * 1024)
      throw FmlException('PLATFORM_FILE_TOO_LARGE');
    return Uint8List.fromList(_bytes);
  }
}

final class _Batch {
  final images = <FakeImportedImage>[];
  void end() {
    for (final i in images) {
      i.ended = true;
    }
    images.clear();
  }

  FakeImportedImage take(FakeImportedImage template) {
    final image = template.copyForBatch();
    images.add(image);
    return image;
  }
}

final class FakeImagePicker implements ImagePicker {
  List<FakeImportedImage> images = [];
  final _batch = _Batch();
  @override
  Future<List<ImportedImage>> pick({required int maxCount}) async {
    _batch.end();
    if (maxCount < 1 || maxCount > 10) throw ArgumentError('Invalid maxCount');
    return images.take(maxCount).map(_batch.take).toList();
  }
}

final class FakeCameraController implements CameraController {
  FakeImportedImage? image;
  final _batch = _Batch();
  @override
  Future<ImportedImage?> capture() async {
    _batch.end();
    return image == null ? null : _batch.take(image!);
  }
}

final class FakeClipboardAdapter implements ClipboardAdapter {
  String? text;
  FakeImportedImage? image;
  final _batch = _Batch();
  @override
  Future<String?> readText() async => text;
  @override
  Future<void> writeText(String text) async {
    this.text = text;
  }

  @override
  Future<ImportedImage?> readImage() async {
    _batch.end();
    return image == null ? null : _batch.take(image!);
  }
}

final class FakeNotificationScheduler implements NotificationScheduler {
  FakeNotificationScheduler() {
    _taps = StreamController<void>.broadcast(
      onListen: () {
        if (_pending) {
          _pending = false;
          _taps.add(null);
        }
      },
    );
  }
  bool permission = true;
  (LocalTime, String)? reminder;
  bool _pending = false;
  late final StreamController<void> _taps;
  void simulateTap() {
    if (_taps.hasListener) {
      _taps.add(null);
    } else {
      _pending = true;
    }
  }

  @override
  Future<bool> requestPermission() async => permission;
  @override
  Future<void> scheduleDailyReminder(LocalTime time, String body) async {
    if (!permission) throw FmlException('PLATFORM_PERMISSION_DENIED');
    reminder = (time, body);
  }

  @override
  Future<void> cancelAll() async {
    reminder = null;
  }

  @override
  Stream<void> taps() => _taps.stream;
  Future<void> dispose() => _taps.close();
}

final class FakeRuntimeInfo implements RuntimeInfo {
  FakeRuntimeInfo(this.value);
  RuntimeSnapshot? value;
  String? errorCode;
  @override
  Future<RuntimeSnapshot> snapshot() async {
    if (errorCode != null) throw FmlException(errorCode!);
    return value ?? (throw StateError('Missing runtime fixture'));
  }
}

final class FakeAppLifecycle implements AppLifecycle {
  final _events = StreamController<LifecycleEvent>.broadcast();
  void emit(LifecycleEvent event) => _events.add(event);
  @override
  Stream<LifecycleEvent> events() => _events.stream;
  Future<void> dispose() => _events.close();
}

final class FakeHttpTransport implements HttpTransport {
  final fixtures = <(HttpMethod, Uri), Object>{};
  final requests = <HttpRequestDto>[];
  final cancellations = <CancelToken?>[];
  @override
  Future<HttpResult> send(HttpRequestDto req, {CancelToken? cancel}) async {
    requests.add(req);
    cancellations.add(cancel);
    if (cancel?.isCancelled ?? false) throw FfiCancelled();
    final offset = req.rangeStart ?? 0;
    if (offset > 0 &&
        (!await req.saveTo!.exists() || await req.saveTo!.length() != offset)) {
      throw ArgumentError('Range does not match file');
    }
    final value = fixtures[(req.method, req.url)];
    if (value == null) throw StateError('Missing HTTP fixture');
    if (value is String) throw FmlException(value);
    if (value is! HttpResult) throw StateError('Invalid HTTP fixture');
    // Scripted responses only: no network or transport protocol emulation.
    return value;
  }
}

final class FakeFileExporter implements FileExporter {
  bool cancelled = false;
  String? suggestedName;
  Uint8List? savedBytes;
  @override
  Future<bool> saveAs(String suggestedName, Stream<List<int>> bytes) async {
    this.suggestedName = suggestedName;
    if (cancelled) return false;
    final builder = BytesBuilder(copy: true);
    await for (final chunk in bytes) {
      builder.add(chunk);
    }
    savedBytes = builder.takeBytes();
    return true;
  }
}

final class FakeDocumentPicker implements DocumentPicker {
  PickedDocument? document;
  @override
  Future<PickedDocument?> pick({
    required List<String> extensions,
    required int maxBytes,
  }) async {
    if (maxBytes < 0 ||
        extensions.isEmpty ||
        extensions.any((e) => !RegExp(r'^[a-z0-9]+$').hasMatch(e))) {
      throw ArgumentError('Invalid document constraints');
    }
    final d = document;
    if (d == null) return null;
    if (d.byteLength > maxBytes) throw FmlException('PLATFORM_FILE_TOO_LARGE');
    if (!extensions.contains(d.displayName.split('.').last.toLowerCase())) {
      throw FmlException('PLATFORM_FILE_TYPE_MISMATCH');
    }
    return d;
  }
}
