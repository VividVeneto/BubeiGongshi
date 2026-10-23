import '../composition/composition.dart' show Installer;
import 'secure_key_value_store.dart';
export 'secure_key_value_store.dart';
import 'local_file_store.dart';
export 'local_file_store.dart';
import 'image_picker.dart';
export 'image_picker.dart';
import 'camera_controller.dart';
export 'camera_controller.dart';
import 'notification_scheduler.dart';
export 'notification_scheduler.dart';
import 'clipboard_adapter.dart';
export 'clipboard_adapter.dart';
import 'runtime_info.dart';
export 'runtime_info.dart';
import 'app_lifecycle.dart';
export 'app_lifecycle.dart';
import 'http_transport.dart';
export 'http_transport.dart';
import 'file_exporter.dart';
export 'file_exporter.dart';
import 'document_picker.dart';
export 'document_picker.dart';
export 'port_dtos.dart';

/// 平台构造的完整端口集合，无平台探测或默认Fake。
final class PlatformPorts {
  /// 安装点复制为只读列表，在featureInstallers之后由CORE-36逐项await。
  PlatformPorts({
    required this.keys,
    required this.files,
    required this.picker,
    required this.camera,
    required this.notifications,
    required this.clipboard,
    required this.runtime,
    required this.lifecycle,
    required HttpTransport http,
    required this.exporter,
    required this.documents,
    List<Installer> platformInstallers = const [],
  }) : http = http,
       platformInstallers = List.unmodifiable(platformInstallers);

  /// SecureKeyValueStore端口。
  final SecureKeyValueStore keys;

  /// LocalFileStore端口。
  final LocalFileStore files;

  /// ImagePicker端口。
  final ImagePicker picker;

  /// CameraController端口。
  final CameraController camera;

  /// NotificationScheduler端口。
  final NotificationScheduler notifications;

  /// ClipboardAdapter端口。
  final ClipboardAdapter clipboard;

  /// RuntimeInfo端口。
  final RuntimeInfo runtime;

  /// AppLifecycle端口。
  final AppLifecycle lifecycle;

  /// HttpTransport端口。
  final HttpTransport http;

  /// FileExporter端口。
  final FileExporter exporter;

  /// DocumentPicker端口。
  final DocumentPicker documents;

  /// 平台专属安装点，默认空。
  final List<Installer> platformInstallers;
}
