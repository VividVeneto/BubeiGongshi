import 'dart:typed_data';

import 'port_dtos.dart';
export 'port_dtos.dart';

/// 平台密钥包装，不要求用户认证。
abstract interface class SecureKeyValueStore {
  /// 包装密钥；alias须匹配 ^[a-z0-9_.-]{1,64}$。
  Future<Uint8List> wrap(String alias, Uint8List secret);

  /// 解包；别名失效或密文篡改抛 PLATFORM_KEY_UNAVAILABLE。
  Future<Uint8List> unwrap(String alias, Uint8List wrapped);

  /// 删除别名；不存在时成功。
  Future<void> delete(String alias);

  /// 返回别名保护级别。
  Future<KeySecurityLevel> securityLevel(String alias);
}
