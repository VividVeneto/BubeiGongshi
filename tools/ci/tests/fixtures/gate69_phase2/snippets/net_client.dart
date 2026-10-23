import 'dart:io';
import 'package:http/http.dart' as http;

/// 白名单目录内的网络构造：不报 PRIV-1。
class NetClient {
  /// 创建客户端。
  NetClient();

  /// 构造 HttpClient 与 Socket。
  Object build() => HttpClient();

  /// 返回网络包符号。
  Object? pkg() => http.Client();
}
