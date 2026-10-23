/// 用户选择位置的流式导出。
abstract interface class FileExporter {
  /// 取消返回false，系统中断可抛PLATFORM_CANCELLED。
  Future<bool> saveAs(String suggestedName, Stream<List<int>> bytes);
}
