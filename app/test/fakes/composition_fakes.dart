// ignore_for_file: public_member_api_docs
import 'package:bubeigongshi/binding/core_binding.dart';
import 'package:bubeigongshi/binding/fmlcore.g.dart' show FML_ABI_MAJOR;
import 'package:bubeigongshi/composition/composition.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';
import 'package:bubeigongshi/ports/unsupported/unsupported_ports.dart';

final class FakeCoreBinding implements CoreBinding {
  FakeCoreBinding({this.version = FML_ABI_MAJOR << 16});
  int version;
  bool disposed = false;
  @override
  final spec = const CoreLibrarySpec('fixture-not-a-library');
  @override
  int abiVersion() => version;
  @override
  Future<void> dispose() async {
    disposed = true;
  }

  @override
  Stream<String> get engineGenerations => const Stream.empty();
  @override
  CoreBinding scopedTo(String profileHandle) =>
      throw StateError('Not used by CORE04');
  @override
  Map<String, Object?> call(
    String op,
    Map<String, Object?> body, {
    Duration? budget,
    String? expectedGeneration,
  }) => throw StateError('Not used by CORE04');
  @override
  Future<Map<String, Object?>> submit(
    String op,
    Map<String, Object?> body, {
    CancelToken? cancel,
    String? expectedGeneration,
  }) async => throw StateError('Not used by CORE04');
}

PlatformPorts portsWith({
  RuntimeInfo? runtime,
  List<Installer> installers = const [],
}) => PlatformPorts(
  keys: UnsupportedSecureKeyValueStore(),
  files: UnsupportedLocalFileStore(),
  picker: UnsupportedImagePicker(),
  camera: UnsupportedCameraController(),
  notifications: UnsupportedNotificationScheduler(),
  clipboard: UnsupportedClipboardAdapter(),
  runtime: runtime ?? UnsupportedRuntimeInfo(),
  lifecycle: UnsupportedAppLifecycle(),
  http: UnsupportedHttpTransport(),
  exporter: UnsupportedFileExporter(),
  documents: UnsupportedDocumentPicker(),
  platformInstallers: installers,
);
