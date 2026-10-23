import 'dart:io';

import 'port_dtos.dart';
export 'port_dtos.dart';

/// 应用私有目录接缝。
abstract interface class LocalFileStore {
  /// 创建并返回私有子目录；staging绝对路径供staging_root使用，重复调用不删文件。
  Future<Directory> root(StoreArea area);

  /// 私有根所在卷可用字节数。
  Future<int> freeBytes();

  /// 解析符号链接后须位于私有根内；越界ArgumentError且不修改目标。
  Future<void> excludeFromSystemBackup(Directory dir);
}
