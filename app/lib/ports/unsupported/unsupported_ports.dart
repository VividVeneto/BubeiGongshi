import 'dart:io';
import 'dart:typed_data';

import '../../binding/core_binding.dart' show CancelToken;
import '../../binding/errors.dart';
import '../platform_ports.dart';

Never _unsupported() => throw FmlException('PLATFORM_UNSUPPORTED');

/// 未接入平台密钥能力；绝不以可逆Fake保护产品密钥。
final class UnsupportedSecureKeyValueStore implements SecureKeyValueStore {
  @override
  Future<Uint8List> wrap(String alias, Uint8List secret) async =>
      _unsupported();
  @override
  Future<Uint8List> unwrap(String alias, Uint8List wrapped) async =>
      _unsupported();
  @override
  Future<void> delete(String alias) async => _unsupported();
  @override
  Future<KeySecurityLevel> securityLevel(String alias) async => _unsupported();
}

/// 未接入私有存储，不创建目录。
final class UnsupportedLocalFileStore implements LocalFileStore {
  @override
  Future<Directory> root(StoreArea area) async => _unsupported();
  @override
  Future<int> freeBytes() async => _unsupported();
  @override
  Future<void> excludeFromSystemBackup(Directory dir) async => _unsupported();
}

/// 未接入图片选择；参数错误仍是ArgumentError。
final class UnsupportedImagePicker implements ImagePicker {
  @override
  Future<List<ImportedImage>> pick({required int maxCount}) async {
    if (maxCount < 1 || maxCount > 10) throw ArgumentError('Invalid maxCount');
    return _unsupported();
  }
}

/// 未接入相机。
final class UnsupportedCameraController implements CameraController {
  @override
  Future<ImportedImage?> capture() async => _unsupported();
}

/// 未接入提醒；点击流为空。
final class UnsupportedNotificationScheduler implements NotificationScheduler {
  @override
  Future<bool> requestPermission() async => _unsupported();
  @override
  Future<void> scheduleDailyReminder(LocalTime time, String body) async =>
      _unsupported();
  @override
  Future<void> cancelAll() async => _unsupported();
  @override
  Stream<void> taps() => const Stream.empty();
}

/// 未接入剪贴板；图片不支持按接口返回null。
final class UnsupportedClipboardAdapter implements ClipboardAdapter {
  @override
  Future<String?> readText() async => _unsupported();
  @override
  Future<void> writeText(String text) async => _unsupported();
  @override
  Future<ImportedImage?> readImage() async => null;
}

/// 未接入运行信息，不返回虚构快照。
final class UnsupportedRuntimeInfo implements RuntimeInfo {
  @override
  Future<RuntimeSnapshot> snapshot() async => _unsupported();
}

/// 未接入生命周期；空流可重复订阅。
final class UnsupportedAppLifecycle implements AppLifecycle {
  @override
  Stream<LifecycleEvent> events() => const Stream.empty();
}

/// 未接入传输，不构造网络客户端。
final class UnsupportedHttpTransport implements HttpTransport {
  @override
  Future<HttpResult> send(HttpRequestDto req, {CancelToken? cancel}) async =>
      _unsupported();
}

/// 未接入文件导出，不消费用户流。
final class UnsupportedFileExporter implements FileExporter {
  @override
  Future<bool> saveAs(String suggestedName, Stream<List<int>> bytes) async =>
      _unsupported();
}

/// 未接入文档选择，不访问文件。
final class UnsupportedDocumentPicker implements DocumentPicker {
  @override
  Future<PickedDocument?> pick({
    required List<String> extensions,
    required int maxBytes,
  }) async => _unsupported();
}
