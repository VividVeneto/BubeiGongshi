import 'port_dtos.dart';
export 'port_dtos.dart';

/// 私有目录拍照；每次capture开始结束前批，过期清理不删已接管文件。
abstract interface class CameraController {
  /// 取消返回null；不支持抛PLATFORM_UNSUPPORTED。
  Future<ImportedImage?> capture();
}
