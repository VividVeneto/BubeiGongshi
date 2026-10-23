import 'dart:io';
import 'package:http/http.dart' as http;

/// 反例：白名单目录外的网络构造与网络包导入。
class NetClient {
  /// 创建客户端。
  NetClient();

  /// 构造 HttpClient。
  Object build() => HttpClient();

  /// 返回网络包符号。
  Object? pkg() => http.Client();
}
