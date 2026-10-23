import 'port_dtos.dart';
export 'port_dtos.dart';

/// 每次pick开始结束前批；图片一小时过期，已接管文件不清理。
abstract interface class ImagePicker {
  /// 数量1–10，否则ArgumentError；取消返回空列表。
  Future<List<ImportedImage>> pick({required int maxCount});
}
