import '../binding/core_binding.dart' show CancelToken;
import 'port_dtos.dart';
export 'port_dtos.dart';

/// 纯传输；HTTPS/主机/Cookie/用途与同意检查唯一归CORE-28。
abstract interface class HttpTransport {
  /// 总时限含落盘及至多一次纠错重发；取消抛FfiCancelled。
  /// rangeStart>0须文件等长；200截断，合法identity 206续写，其他状态不写文件。
  /// 非法206关闭后一次无Range重下；内存响应上限16MiB。
  Future<HttpResult> send(HttpRequestDto req, {CancelToken? cancel});
}
