/// 正例：普通说明字符串与注释里的符号不报。
const String kDoc = 'engine.parse 与 FormulaNode 只是说明文字';

// calc.evaluate 只在注释里出现。
Object? describe() => kDoc;
