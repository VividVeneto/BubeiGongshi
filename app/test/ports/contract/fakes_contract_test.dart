import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

import '../../fakes/platform_fakes.dart';
import 'secure_key_value_store_contract.dart';
import 'local_file_store_contract.dart';
import 'image_picker_contract.dart';
import 'camera_controller_contract.dart';
import 'notification_scheduler_contract.dart';
import 'clipboard_adapter_contract.dart';
import 'runtime_info_contract.dart';
import 'app_lifecycle_contract.dart';
import 'http_transport_contract.dart';
import 'file_exporter_contract.dart';
import 'document_picker_contract.dart';

void main() {
  FakeImportedImage image() => FakeImportedImage(Uint8List.fromList([1, 2, 3]));
  runSecureKeyValueStoreContract(FakeSecureKeyValueStore.new);
  runLocalFileStoreContract(() {
    final p = FakeLocalFileStore();
    addTearDown(p.dispose);
    return p;
  });
  runImagePickerContract(() => FakeImagePicker()..images = [image()]);
  runCameraControllerContract(() => FakeCameraController()..image = image());
  runNotificationSchedulerContract(() {
    final p = FakeNotificationScheduler();
    addTearDown(p.dispose);
    return p;
  });
  runClipboardAdapterContract(FakeClipboardAdapter.new);
  runRuntimeInfoContract(
    () => FakeRuntimeInfo(
      RuntimeSnapshot(
        os: 'windows',
        osVersion: '10.0.17763',
        locale: 'zh-CN',
        availMemBytes: 42,
        dpiScale: 1.25,
        abi: 'x64',
        gpuAvailable: false,
      ),
    ),
  );
  runAppLifecycleContract(() {
    final p = FakeAppLifecycle();
    addTearDown(p.dispose);
    return p;
  });
  runHttpTransportContract(
    () => FakeHttpTransport()
      ..fixtures[(
        HttpMethod.get,
        Uri.parse('https://example.invalid/core04'),
      )] = HttpResult(
        status: 503,
        headers: {'X-Contract': 'yes'},
        body: Uint8List.fromList([1, 2, 3]),
        receivedBytes: 3,
      ),
  );
  runFileExporterContract(FakeFileExporter.new);
  runDocumentPickerContract(() {
    final files = FakeLocalFileStore();
    addTearDown(files.dispose);
    final staging = Directory.fromUri(files.privateRoot.uri.resolve('staging/'))
      ..createSync();
    final file = File.fromUri(staging.uri.resolve('contract.txt'))
      ..writeAsBytesSync([1, 2, 3]);
    return FakeDocumentPicker()
      ..document = PickedDocument(
        file: file,
        displayName: 'contract.txt',
        byteLength: 3,
      );
  });
}
