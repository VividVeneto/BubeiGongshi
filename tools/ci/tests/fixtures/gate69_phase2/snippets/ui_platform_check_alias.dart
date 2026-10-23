import 'dart:io' as io;
import 'package:flutter/foundation.dart' as f;

/// 反例：ui 用 import 别名判断平台。
class AliasCheckPage extends Object {
  /// 是否 Windows。
  bool isWindowsUi() => io.Platform.isWindows;

  /// 是否 iOS。
  bool isIosUi() => f.defaultTargetPlatform == f.TargetPlatform.iOS;
}
