import 'port_dtos.dart';
export 'port_dtos.dart';

/// 非图片文档复制至staging，由调用方删除。
abstract interface class DocumentPicker {
  /// extensions为小写无点扩展名；取消null，超限FILE_TOO_LARGE，错类型FILE_TYPE_MISMATCH。
  Future<PickedDocument?> pick({
    required List<String> extensions,
    required int maxBytes,
  });
}
