import 'dart:io';
import 'dart:typed_data';

/// 密钥保护级别。
enum KeySecurityLevel {
  /// strongBox。
  strongBox,

  /// tee。
  tee,

  /// software。
  software,

  /// dpapi。
  dpapi,
}

/// 应用私有存储分区。
enum StoreArea {
  /// database。
  database,

  /// packs。
  packs,

  /// recognition。
  recognition,

  /// staging。
  staging,

  /// drafts。
  drafts,

  /// exports。
  exports,

  /// logs。
  logs,
}

/// 生命周期事件。
enum LifecycleEvent {
  /// resumed。
  resumed,

  /// paused。
  paused,

  /// detached。
  detached,

  /// lowMemory。
  lowMemory,
}

/// 传输方法。
enum HttpMethod {
  /// get。
  get,

  /// post。
  post,

  /// put。
  put,

  /// delete。
  delete,
}

/// 网络用途，由CORE-28校验授权。
enum RequestPurpose {
  /// packDownload。
  packDownload,

  /// updateCheck。
  updateCheck,

  /// auth。
  auth,

  /// sync。
  sync,

  /// cloudRecognition。
  cloudRecognition,

  /// cloudControl。
  cloudControl,

  /// diagnostics。
  diagnostics,
}

/// 设备本地时区时刻；运行时检查而非发布可移除的assert。
final class LocalTime {
  /// 越界抛ArgumentError；Dart const构造无法承诺此运行时异常。
  LocalTime(this.hour, this.minute) {
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59) {
      throw ArgumentError('Invalid local time');
    }
  }

  /// 小时0–23。
  final int hour;

  /// 分钟0–59。
  final int minute;
}

/// 平台快照；仅验证纯数据，不探测宿主平台。
final class RuntimeSnapshot {
  /// 拒绝非法OS/ABI、负内存和非有限正dpiScale。
  RuntimeSnapshot({
    required this.os,
    required this.osVersion,
    required this.locale,
    required this.availMemBytes,
    required this.dpiScale,
    required this.abi,
    required this.gpuAvailable,
  }) {
    if (!{'android', 'windows'}.contains(os) ||
        osVersion.isEmpty ||
        !RegExp(r'^[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*$').hasMatch(locale) ||
        availMemBytes < 0 ||
        !dpiScale.isFinite ||
        dpiScale <= 0 ||
        !{'arm64-v8a', 'armeabi-v7a', 'x86_64', 'x64'}.contains(abi)) {
      throw ArgumentError('Invalid runtime snapshot');
    }
  }

  /// android或windows。
  final String os;

  /// 系统API级别或内部版本号。
  final String osVersion;

  /// BCP47语言标签。
  final String locale;

  /// 可用内存字节数。
  final int availMemBytes;

  /// 正有限缩放系数。
  final double dpiScale;

  /// 平台ABI名称。
  final String abi;

  /// 未知GPU能力时为false。
  final bool gpuAvailable;
}

/// 网络请求数据；不在此复制NetworkGuard的策略检查。
final class HttpRequestDto {
  /// body上限16MiB；rangeStart非负且必须有saveTo，timeout为正。
  HttpRequestDto({
    required this.method,
    required this.url,
    required this.purpose,
    Map<String, String> headers = const {},
    Uint8List? body,
    this.timeout = const Duration(seconds: 30),
    this.consentToken,
    this.saveTo,
    this.rangeStart,
  }) : headers = Map.unmodifiable(headers),
       body = body == null
           ? null
           : Uint8List.fromList(body).asUnmodifiableView() {
    if ((body?.length ?? 0) > 16 * 1024 * 1024 ||
        timeout <= Duration.zero ||
        (rangeStart != null && (rangeStart! < 0 || saveTo == null))) {
      throw ArgumentError('Invalid transport parameters');
    }
  }

  /// HTTP方法。
  final HttpMethod method;

  /// HTTPS与主机白名单由CORE-28检查。
  final Uri url;

  /// 必填用途。
  final RequestPurpose purpose;

  /// 不可变请求头；Cookie策略由CORE-28检查。
  final Map<String, String> headers;

  /// 不可变请求体副本，至多16MiB。
  final Uint8List? body;

  /// 包括落盘与纠错重发的总时限。
  final Duration timeout;

  /// 云识别同意令牌；由CORE-28消费校验。
  final String? consentToken;

  /// 平台负责验证staging归属并流式写入。
  final File? saveTo;

  /// 续传偏移；大于0时平台验证文件已存在且等长。
  final int? rangeStart;
}

/// HTTP响应；非2xx仍正常返回。
final class HttpResult {
  /// 复制body与头；统一头名为小写，拒绝重复规范头名或负接收数。
  HttpResult({
    required this.status,
    required Map<String, String> headers,
    required Uint8List body,
    required this.receivedBytes,
  }) : headers = Map.unmodifiable({
         for (final e in headers.entries) e.key.toLowerCase(): e.value,
       }),
       body = Uint8List.fromList(body).asUnmodifiableView() {
    if (status < 100 ||
        status > 599 ||
        receivedBytes < 0 ||
        this.headers.length != headers.length) {
      throw ArgumentError('Invalid HTTP result');
    }
  }

  /// HTTP状态码。
  final int status;

  /// 小写头名、不可修改。
  final Map<String, String> headers;

  /// 响应副本；成功saveTo传输时为空。
  final Uint8List body;

  /// 本次实际接收字节数。
  final int receivedBytes;
}

/// 当前导入批次的只读图片；过期清理不影响已接管的副本。
abstract interface class ImportedImage {
  /// 仅供显示，不记录日志。
  String get displayName;

  /// image/jpeg、image/png或image/webp；HEIC由平台转JPEG质量92。
  String get mimeType;

  /// 图片原始字节数。
  int get byteLength;

  /// 创建后一小时失效。
  DateTime get expiresAt;

  /// 有效期内可重复读取；到期/批次结束PLATFORM_IO，超过20MiB FILE_TOO_LARGE。
  Future<Uint8List> readBytes();
}

/// 系统选择后复制至staging的文件，调用方用完删除。
final class PickedDocument {
  /// 字节数不得为负；目录归属由平台适配器保证。
  PickedDocument({
    required this.file,
    required this.displayName,
    required this.byteLength,
  }) {
    if (byteLength < 0) throw ArgumentError('Negative document length');
  }

  /// 私有staging中的文件。
  final File file;

  /// 仅供显示的名称。
  final String displayName;

  /// 文件字节数。
  final int byteLength;
}
