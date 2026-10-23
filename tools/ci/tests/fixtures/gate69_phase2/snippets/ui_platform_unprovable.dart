/// 反例：ui 内出现平台判断成员但无法证明来源，只输出 warning。
class UnprovablePage extends Object {
  /// 是否 Android（未导入 dart:io，无法证明）。
  bool isAndroidUi() => Platform.isAndroid;
}
