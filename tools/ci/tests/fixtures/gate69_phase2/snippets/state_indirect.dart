Object? pick();

/// 反例：接收者类型不可判定，只输出 warning 与人工项。
Object? readIndirect() {
  final port = pick();
  return port.http;
}
