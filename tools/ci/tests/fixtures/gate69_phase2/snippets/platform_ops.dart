/// 平台层夹具：DEP-6 的 op 调用字符串与 type 标识符。
Object? send(String op, String symbol);
Object? emit(String op);

// 注释里的 engine.parse 不报。
const String kOp = 'engine.parse';

/// 反例：调用实参里的 op 字符串与领域类型标识符。
class PlatformAdapter {
  /// 调用平台 op。
  Object? parse() => send('op', 'engine.parse');

  /// 使用领域类型标注。
  Object? layout() => emit('typeset.layout');

  /// 领域类型字段。
  final FormulaNode? node = null;
}
