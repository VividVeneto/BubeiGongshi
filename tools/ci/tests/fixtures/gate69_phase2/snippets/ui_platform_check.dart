import 'dart:io';
import 'package:flutter/foundation.dart';

/// 反例：ui 内判断平台。
class PlatformCheckPage extends Object {
  /// 是否 Android。
  bool isAndroidUi() => Platform.isAndroid;

  /// 是否 Web。
  bool isWebUi() => kIsWeb;

  /// 是否 Windows。
  bool isWindowsUi() => defaultTargetPlatform == TargetPlatform.windows;
}
