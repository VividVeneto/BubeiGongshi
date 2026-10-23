import 'port_dtos.dart';
export 'port_dtos.dart';

/// 剪贴板接缝；图片批次由适配器独立管理。
abstract interface class ClipboardAdapter {
  /// 无文字返回null。
  Future<String?> readText();

  /// 写入文字，不记录用户内容。
  Future<void> writeText(String text);

  /// 无图片或不支持图片返回null。
  Future<ImportedImage?> readImage();
}
