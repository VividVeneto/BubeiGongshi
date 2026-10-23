import 'package:flutter/foundation.dart';

import '../ports/platform_ports.dart';
import '../ports/unsupported/unsupported_ports.dart';

/// S0 deliberately wires only CORE-04 fallbacks; future owners replace slots.
PlatformPorts buildWindowsPorts() {
  for (final name in const [
    'keys',
    'files',
    'picker',
    'camera',
    'notifications',
    'clipboard',
    'runtime',
    'lifecycle',
    'http',
    'exporter',
    'documents',
  ]) {
    debugPrint('Windows port $name: Unsupported (pending platform card)');
  }
  return PlatformPorts(
    keys: UnsupportedSecureKeyValueStore(),
    files: UnsupportedLocalFileStore(),
    picker: UnsupportedImagePicker(),
    camera: UnsupportedCameraController(),
    notifications: UnsupportedNotificationScheduler(),
    clipboard: UnsupportedClipboardAdapter(),
    runtime: UnsupportedRuntimeInfo(),
    lifecycle: UnsupportedAppLifecycle(),
    http: UnsupportedHttpTransport(),
    exporter: UnsupportedFileExporter(),
    documents: UnsupportedDocumentPicker(),
    platformInstallers: const [],
  );
}
