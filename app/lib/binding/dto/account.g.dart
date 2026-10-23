// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=account.close_profile.schema.json, account.create_guest.schema.json, account.create_registered.schema.json, account.delete_profile.schema.json, account.get_blob.schema.json, account.local_setting.schema.json, account.open_profile.schema.json, account.profiles.schema.json, account.put_blob.schema.json, account.set_local_setting.schema.json, account.set_logged_out.schema.json, account.set_sync_enabled.schema.json, account.state.schema.json, account.touch_last_used.schema.json
// dart format off

import 'dart:convert';
import 'dart:typed_data';
import 'types.g.dart';

/// AccountCloseProfileOk：不可变值对象；wire 键见各字段。
final class AccountCloseProfileOk {
  /// 由 wire 字段构造。
  const AccountCloseProfileOk({
    required this.state,
  });

  /// wire 键 state。
  final AccountState state;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountCloseProfileOk.fromJson(Map<String, Object?> json) {
    return AccountCloseProfileOk(
      state: readEnum(json, 'state', AccountState.fromWire),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'state': state.wire,
    };
  }

  @override
  String toString() {
    return 'AccountCloseProfileOk(state: $state)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountCloseProfileOk &&
        dtoEquals(state, other.state);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(state),
  ]);
}

/// AccountCloseProfileRequest：不可变值对象；wire 键见各字段。
final class AccountCloseProfileRequest {
  /// 由 wire 字段构造。
  const AccountCloseProfileRequest({
    required this.lock,
  });

  /// wire 键 lock。
  final bool lock;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountCloseProfileRequest.fromJson(Map<String, Object?> json) {
    return AccountCloseProfileRequest(
      lock: readBool(json, 'lock'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'lock': lock,
    };
  }

  @override
  String toString() {
    return 'AccountCloseProfileRequest(lock: $lock)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountCloseProfileRequest &&
        dtoEquals(lock, other.lock);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(lock),
  ]);
}

/// AccountCreateGuestOk：不可变值对象；wire 键见各字段。
final class AccountCreateGuestOk {
  /// 由 wire 字段构造。
  const AccountCreateGuestOk({
    required this.dbKey,
    required this.profile,
  });

  /// wire 键 db_key。
  final Uint8List dbKey;

  /// wire 键 profile。
  final Profile profile;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountCreateGuestOk.fromJson(Map<String, Object?> json) {
    return AccountCreateGuestOk(
      dbKey: readBytes(json, 'db_key'),
      profile: readObject(json, 'profile', Profile.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'db_key': base64Encode(dbKey),
      'profile': profile.toJson(),
    };
  }

  @override
  String toString() {
    return 'AccountCreateGuestOk(dbKey: <redacted>, profile: $profile)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountCreateGuestOk &&
        dtoEquals(dbKey, other.dbKey) &&
        dtoEquals(profile, other.profile);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(dbKey),
    dtoHash(profile),
  ]);
}

/// AccountCreateGuestRequest：不可变值对象；wire 键见各字段。
final class AccountCreateGuestRequest {
  /// 无 wire 字段的空对象。
  const AccountCreateGuestRequest();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountCreateGuestRequest.fromJson(Map<String, Object?> json) {
    return const AccountCreateGuestRequest();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'AccountCreateGuestRequest()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is AccountCreateGuestRequest;
  }

  @override
  int get hashCode => 0;
}

/// AccountCreateRegisteredOk：不可变值对象；wire 键见各字段。
final class AccountCreateRegisteredOk {
  /// 由 wire 字段构造。
  const AccountCreateRegisteredOk({
    required this.dbKey,
    required this.profile,
  });

  /// wire 键 db_key。
  final Uint8List dbKey;

  /// wire 键 profile。
  final Profile profile;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountCreateRegisteredOk.fromJson(Map<String, Object?> json) {
    return AccountCreateRegisteredOk(
      dbKey: readBytes(json, 'db_key'),
      profile: readObject(json, 'profile', Profile.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'db_key': base64Encode(dbKey),
      'profile': profile.toJson(),
    };
  }

  @override
  String toString() {
    return 'AccountCreateRegisteredOk(dbKey: <redacted>, profile: $profile)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountCreateRegisteredOk &&
        dtoEquals(dbKey, other.dbKey) &&
        dtoEquals(profile, other.profile);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(dbKey),
    dtoHash(profile),
  ]);
}

/// AccountCreateRegisteredRequest：不可变值对象；wire 键见各字段。
final class AccountCreateRegisteredRequest {
  /// 由 wire 字段构造。
  const AccountCreateRegisteredRequest({
    required this.accountId,
    required this.emailMasked,
  });

  /// wire 键 account_id。
  final String accountId;

  /// wire 键 email_masked。
  final String emailMasked;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountCreateRegisteredRequest.fromJson(Map<String, Object?> json) {
    return AccountCreateRegisteredRequest(
      accountId: readString(json, 'account_id'),
      emailMasked: readString(json, 'email_masked'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'account_id': accountId,
      'email_masked': emailMasked,
    };
  }

  @override
  String toString() {
    return 'AccountCreateRegisteredRequest(accountId: $accountId, emailMasked: $emailMasked)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountCreateRegisteredRequest &&
        dtoEquals(accountId, other.accountId) &&
        dtoEquals(emailMasked, other.emailMasked);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(accountId),
    dtoHash(emailMasked),
  ]);
}

/// AccountDeleteProfileOk：不可变值对象；wire 键见各字段。
final class AccountDeleteProfileOk {
  /// 无 wire 字段的空对象。
  const AccountDeleteProfileOk();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountDeleteProfileOk.fromJson(Map<String, Object?> json) {
    return const AccountDeleteProfileOk();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'AccountDeleteProfileOk()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is AccountDeleteProfileOk;
  }

  @override
  int get hashCode => 0;
}

/// AccountDeleteProfileRequest：不可变值对象；wire 键见各字段。
final class AccountDeleteProfileRequest {
  /// 由 wire 字段构造。
  const AccountDeleteProfileRequest({
    required this.profileId,
  });

  /// wire 键 profile_id。
  final String profileId;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountDeleteProfileRequest.fromJson(Map<String, Object?> json) {
    return AccountDeleteProfileRequest(
      profileId: readString(json, 'profile_id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'profile_id': profileId,
    };
  }

  @override
  String toString() {
    return 'AccountDeleteProfileRequest(profileId: $profileId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountDeleteProfileRequest &&
        dtoEquals(profileId, other.profileId);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(profileId),
  ]);
}

/// AccountGetBlobOk：不可变值对象；wire 键见各字段。
final class AccountGetBlobOk {
  /// 由 wire 字段构造。
  const AccountGetBlobOk({
    this.wrapped,
  });

  /// wire 键 wrapped。
  final Uint8List? wrapped;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountGetBlobOk.fromJson(Map<String, Object?> json) {
    return AccountGetBlobOk(
      wrapped: readBytesOrNull(json, 'wrapped'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'wrapped': wrapped == null ? null : base64Encode(wrapped!),
    };
  }

  @override
  String toString() {
    return 'AccountGetBlobOk(wrapped: $wrapped)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountGetBlobOk &&
        dtoEquals(wrapped, other.wrapped);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(wrapped),
  ]);
}

/// AccountGetBlobRequest：不可变值对象；wire 键见各字段。
final class AccountGetBlobRequest {
  /// 由 wire 字段构造。
  const AccountGetBlobRequest({
    required this.kind,
    required this.profileId,
  });

  /// wire 键 kind。
  final AccountGetBlobRequestKind kind;

  /// wire 键 profile_id。
  final String profileId;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountGetBlobRequest.fromJson(Map<String, Object?> json) {
    return AccountGetBlobRequest(
      kind: readEnum(json, 'kind', AccountGetBlobRequestKind.fromWire),
      profileId: readString(json, 'profile_id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'kind': kind.wire,
      'profile_id': profileId,
    };
  }

  @override
  String toString() {
    return 'AccountGetBlobRequest(kind: $kind, profileId: $profileId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountGetBlobRequest &&
        dtoEquals(kind, other.kind) &&
        dtoEquals(profileId, other.profileId);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(kind),
    dtoHash(profileId),
  ]);
}

/// 枚举 AccountGetBlobRequestKind：wire 取值为 [wire]。
enum AccountGetBlobRequestKind {
  /// wire 取值 db_key。
  dbKey('db_key'),
  /// wire 取值 refresh_token。
  refreshToken('refresh_token');

  const AccountGetBlobRequestKind(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, AccountGetBlobRequestKind> byWire = <String, AccountGetBlobRequestKind>{
    'db_key': AccountGetBlobRequestKind.dbKey,
    'refresh_token': AccountGetBlobRequestKind.refreshToken,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static AccountGetBlobRequestKind fromWire(String wire) {
    final AccountGetBlobRequestKind? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 AccountGetBlobRequestKind wire 取值: $wire');
    }
    return found;
  }
}

/// AccountLocalSettingOk：不可变值对象；wire 键见各字段。
final class AccountLocalSettingOk {
  /// 由 wire 字段构造。
  const AccountLocalSettingOk({
    required this.setting,
  });

  /// wire 键 setting。
  final LocalSetting setting;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountLocalSettingOk.fromJson(Map<String, Object?> json) {
    return AccountLocalSettingOk(
      setting: readObject(json, 'setting', LocalSetting.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'setting': setting.toJson(),
    };
  }

  @override
  String toString() {
    return 'AccountLocalSettingOk(setting: $setting)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountLocalSettingOk &&
        dtoEquals(setting, other.setting);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(setting),
  ]);
}

/// AccountLocalSettingRequest：不可变值对象；wire 键见各字段。
final class AccountLocalSettingRequest {
  /// 无 wire 字段的空对象。
  const AccountLocalSettingRequest();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountLocalSettingRequest.fromJson(Map<String, Object?> json) {
    return const AccountLocalSettingRequest();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'AccountLocalSettingRequest()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is AccountLocalSettingRequest;
  }

  @override
  int get hashCode => 0;
}

/// AccountOpenProfileOk：不可变值对象；wire 键见各字段。
final class AccountOpenProfileOk {
  /// 由 wire 字段构造。
  const AccountOpenProfileOk({
    required this.handle,
    required this.profileId,
    required this.state,
  });

  /// wire 键 handle。
  final String handle;

  /// wire 键 profile_id。
  final String profileId;

  /// wire 键 state。
  final AccountState state;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountOpenProfileOk.fromJson(Map<String, Object?> json) {
    return AccountOpenProfileOk(
      handle: readString(json, 'handle'),
      profileId: readString(json, 'profile_id'),
      state: readEnum(json, 'state', AccountState.fromWire),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'handle': handle,
      'profile_id': profileId,
      'state': state.wire,
    };
  }

  @override
  String toString() {
    return 'AccountOpenProfileOk(handle: $handle, profileId: $profileId, state: $state)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountOpenProfileOk &&
        dtoEquals(handle, other.handle) &&
        dtoEquals(profileId, other.profileId) &&
        dtoEquals(state, other.state);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(handle),
    dtoHash(profileId),
    dtoHash(state),
  ]);
}

/// AccountOpenProfileRequest：不可变值对象；wire 键见各字段。
final class AccountOpenProfileRequest {
  /// 由 wire 字段构造。
  const AccountOpenProfileRequest({
    required this.dbKey,
    required this.profileId,
  });

  /// wire 键 db_key。
  final Uint8List dbKey;

  /// wire 键 profile_id。
  final String profileId;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountOpenProfileRequest.fromJson(Map<String, Object?> json) {
    return AccountOpenProfileRequest(
      dbKey: readBytes(json, 'db_key'),
      profileId: readString(json, 'profile_id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'db_key': base64Encode(dbKey),
      'profile_id': profileId,
    };
  }

  @override
  String toString() {
    return 'AccountOpenProfileRequest(dbKey: <redacted>, profileId: $profileId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountOpenProfileRequest &&
        dtoEquals(dbKey, other.dbKey) &&
        dtoEquals(profileId, other.profileId);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(dbKey),
    dtoHash(profileId),
  ]);
}

/// AccountProfilesOk：不可变值对象；wire 键见各字段。
final class AccountProfilesOk {
  /// 由 wire 字段构造。
  const AccountProfilesOk({
    required this.profiles,
  });

  /// wire 键 profiles。
  final List<Profile> profiles;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountProfilesOk.fromJson(Map<String, Object?> json) {
    return AccountProfilesOk(
      profiles: readList(json, 'profiles', (Object? value) => Profile.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'profiles': encodeList(profiles, (Profile item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'AccountProfilesOk(profiles: $profiles)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountProfilesOk &&
        dtoEquals(profiles, other.profiles);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(profiles),
  ]);
}

/// AccountProfilesRequest：不可变值对象；wire 键见各字段。
final class AccountProfilesRequest {
  /// 无 wire 字段的空对象。
  const AccountProfilesRequest();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountProfilesRequest.fromJson(Map<String, Object?> json) {
    return const AccountProfilesRequest();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'AccountProfilesRequest()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is AccountProfilesRequest;
  }

  @override
  int get hashCode => 0;
}

/// AccountPutBlobOk：不可变值对象；wire 键见各字段。
final class AccountPutBlobOk {
  /// 无 wire 字段的空对象。
  const AccountPutBlobOk();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountPutBlobOk.fromJson(Map<String, Object?> json) {
    return const AccountPutBlobOk();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'AccountPutBlobOk()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is AccountPutBlobOk;
  }

  @override
  int get hashCode => 0;
}

/// AccountPutBlobRequest：不可变值对象；wire 键见各字段。
final class AccountPutBlobRequest {
  /// 由 wire 字段构造。
  const AccountPutBlobRequest({
    required this.kind,
    required this.profileId,
    required this.wrapped,
  });

  /// wire 键 kind。
  final AccountPutBlobRequestKind kind;

  /// wire 键 profile_id。
  final String profileId;

  /// wire 键 wrapped。
  final Uint8List wrapped;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountPutBlobRequest.fromJson(Map<String, Object?> json) {
    return AccountPutBlobRequest(
      kind: readEnum(json, 'kind', AccountPutBlobRequestKind.fromWire),
      profileId: readString(json, 'profile_id'),
      wrapped: readBytes(json, 'wrapped'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'kind': kind.wire,
      'profile_id': profileId,
      'wrapped': base64Encode(wrapped),
    };
  }

  @override
  String toString() {
    return 'AccountPutBlobRequest(kind: $kind, profileId: $profileId, wrapped: $wrapped)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountPutBlobRequest &&
        dtoEquals(kind, other.kind) &&
        dtoEquals(profileId, other.profileId) &&
        dtoEquals(wrapped, other.wrapped);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(kind),
    dtoHash(profileId),
    dtoHash(wrapped),
  ]);
}

/// 枚举 AccountPutBlobRequestKind：wire 取值为 [wire]。
enum AccountPutBlobRequestKind {
  /// wire 取值 db_key。
  dbKey('db_key'),
  /// wire 取值 refresh_token。
  refreshToken('refresh_token');

  const AccountPutBlobRequestKind(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, AccountPutBlobRequestKind> byWire = <String, AccountPutBlobRequestKind>{
    'db_key': AccountPutBlobRequestKind.dbKey,
    'refresh_token': AccountPutBlobRequestKind.refreshToken,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static AccountPutBlobRequestKind fromWire(String wire) {
    final AccountPutBlobRequestKind? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 AccountPutBlobRequestKind wire 取值: $wire');
    }
    return found;
  }
}

/// AccountSetLocalSettingOk：不可变值对象；wire 键见各字段。
final class AccountSetLocalSettingOk {
  /// 无 wire 字段的空对象。
  const AccountSetLocalSettingOk();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountSetLocalSettingOk.fromJson(Map<String, Object?> json) {
    return const AccountSetLocalSettingOk();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'AccountSetLocalSettingOk()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is AccountSetLocalSettingOk;
  }

  @override
  int get hashCode => 0;
}

/// AccountSetLocalSettingRequest：不可变值对象；wire 键见各字段。
final class AccountSetLocalSettingRequest {
  /// 由 wire 字段构造。
  const AccountSetLocalSettingRequest({
    required this.setting,
  });

  /// wire 键 setting。
  final LocalSetting setting;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountSetLocalSettingRequest.fromJson(Map<String, Object?> json) {
    return AccountSetLocalSettingRequest(
      setting: readObject(json, 'setting', LocalSetting.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'setting': setting.toJson(),
    };
  }

  @override
  String toString() {
    return 'AccountSetLocalSettingRequest(setting: $setting)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountSetLocalSettingRequest &&
        dtoEquals(setting, other.setting);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(setting),
  ]);
}

/// AccountSetLoggedOutOk：不可变值对象；wire 键见各字段。
final class AccountSetLoggedOutOk {
  /// 无 wire 字段的空对象。
  const AccountSetLoggedOutOk();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountSetLoggedOutOk.fromJson(Map<String, Object?> json) {
    return const AccountSetLoggedOutOk();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'AccountSetLoggedOutOk()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is AccountSetLoggedOutOk;
  }

  @override
  int get hashCode => 0;
}

/// AccountSetLoggedOutRequest：不可变值对象；wire 键见各字段。
final class AccountSetLoggedOutRequest {
  /// 由 wire 字段构造。
  const AccountSetLoggedOutRequest({
    required this.loggedOut,
    required this.profileId,
  });

  /// wire 键 logged_out。
  final bool loggedOut;

  /// wire 键 profile_id。
  final String profileId;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountSetLoggedOutRequest.fromJson(Map<String, Object?> json) {
    return AccountSetLoggedOutRequest(
      loggedOut: readBool(json, 'logged_out'),
      profileId: readString(json, 'profile_id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'logged_out': loggedOut,
      'profile_id': profileId,
    };
  }

  @override
  String toString() {
    return 'AccountSetLoggedOutRequest(loggedOut: $loggedOut, profileId: $profileId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountSetLoggedOutRequest &&
        dtoEquals(loggedOut, other.loggedOut) &&
        dtoEquals(profileId, other.profileId);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(loggedOut),
    dtoHash(profileId),
  ]);
}

/// AccountSetSyncEnabledOk：不可变值对象；wire 键见各字段。
final class AccountSetSyncEnabledOk {
  /// 无 wire 字段的空对象。
  const AccountSetSyncEnabledOk();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountSetSyncEnabledOk.fromJson(Map<String, Object?> json) {
    return const AccountSetSyncEnabledOk();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'AccountSetSyncEnabledOk()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is AccountSetSyncEnabledOk;
  }

  @override
  int get hashCode => 0;
}

/// AccountSetSyncEnabledRequest：不可变值对象；wire 键见各字段。
final class AccountSetSyncEnabledRequest {
  /// 由 wire 字段构造。
  const AccountSetSyncEnabledRequest({
    required this.enabled,
    required this.profileId,
  });

  /// wire 键 enabled。
  final bool enabled;

  /// wire 键 profile_id。
  final String profileId;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountSetSyncEnabledRequest.fromJson(Map<String, Object?> json) {
    return AccountSetSyncEnabledRequest(
      enabled: readBool(json, 'enabled'),
      profileId: readString(json, 'profile_id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'enabled': enabled,
      'profile_id': profileId,
    };
  }

  @override
  String toString() {
    return 'AccountSetSyncEnabledRequest(enabled: $enabled, profileId: $profileId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountSetSyncEnabledRequest &&
        dtoEquals(enabled, other.enabled) &&
        dtoEquals(profileId, other.profileId);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(enabled),
    dtoHash(profileId),
  ]);
}

/// AccountStateOk：不可变值对象；wire 键见各字段。
final class AccountStateOk {
  /// 由 wire 字段构造。
  const AccountStateOk({
    this.profileId,
    required this.state,
  });

  /// wire 键 profile_id。
  final String? profileId;

  /// wire 键 state。
  final AccountState state;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountStateOk.fromJson(Map<String, Object?> json) {
    return AccountStateOk(
      profileId: readStringOrNull(json, 'profile_id'),
      state: readEnum(json, 'state', AccountState.fromWire),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'profile_id': profileId,
      'state': state.wire,
    };
  }

  @override
  String toString() {
    return 'AccountStateOk(profileId: $profileId, state: $state)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountStateOk &&
        dtoEquals(profileId, other.profileId) &&
        dtoEquals(state, other.state);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(profileId),
    dtoHash(state),
  ]);
}

/// AccountStateRequest：不可变值对象；wire 键见各字段。
final class AccountStateRequest {
  /// 由 wire 字段构造。
  const AccountStateRequest({
    this.profileId,
  });

  /// wire 键 profile_id。
  final String? profileId;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountStateRequest.fromJson(Map<String, Object?> json) {
    return AccountStateRequest(
      profileId: readStringOrNull(json, 'profile_id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'profile_id': profileId,
    };
  }

  @override
  String toString() {
    return 'AccountStateRequest(profileId: $profileId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountStateRequest &&
        dtoEquals(profileId, other.profileId);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(profileId),
  ]);
}

/// AccountTouchLastUsedOk：不可变值对象；wire 键见各字段。
final class AccountTouchLastUsedOk {
  /// 无 wire 字段的空对象。
  const AccountTouchLastUsedOk();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountTouchLastUsedOk.fromJson(Map<String, Object?> json) {
    return const AccountTouchLastUsedOk();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'AccountTouchLastUsedOk()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is AccountTouchLastUsedOk;
  }

  @override
  int get hashCode => 0;
}

/// AccountTouchLastUsedRequest：不可变值对象；wire 键见各字段。
final class AccountTouchLastUsedRequest {
  /// 由 wire 字段构造。
  const AccountTouchLastUsedRequest({
    required this.nowMs,
    required this.profileId,
  });

  /// wire 键 now_ms。
  final int nowMs;

  /// wire 键 profile_id。
  final String profileId;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory AccountTouchLastUsedRequest.fromJson(Map<String, Object?> json) {
    return AccountTouchLastUsedRequest(
      nowMs: readInt(json, 'now_ms'),
      profileId: readString(json, 'profile_id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'now_ms': nowMs,
      'profile_id': profileId,
    };
  }

  @override
  String toString() {
    return 'AccountTouchLastUsedRequest(nowMs: $nowMs, profileId: $profileId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is AccountTouchLastUsedRequest &&
        dtoEquals(nowMs, other.nowMs) &&
        dtoEquals(profileId, other.profileId);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(nowMs),
    dtoHash(profileId),
  ]);
}

/// 把 JSON 值收成对象。
Map<String, Object?> asObject(Object? value) {
  if (value is Map<String, Object?>) return value;
  throw const FormatException('元素应为 object');
}

/// 递归值相等：列表逐项、映射逐键，其余用 ==。
bool dtoEquals(Object? a, Object? b) {
  if (identical(a, b)) {
    return true;
  }
  if (a is List && b is List) {
    if (a.length != b.length) {
      return false;
    }
    for (int index = 0; index < a.length; index++) {
      if (!dtoEquals(a[index], b[index])) {
        return false;
      }
    }
    return true;
  }
  if (a is Map && b is Map) {
    if (a.length != b.length) {
      return false;
    }
    for (final Object? key in a.keys) {
      if (!b.containsKey(key) || !dtoEquals(a[key], b[key])) {
        return false;
      }
    }
    return true;
  }
  return a == b;
}

/// 与 [dtoEquals] 一致的递归哈希：列表有序、映射无序。
int dtoHash(Object? value) {
  if (value is List) {
    final List<int> hashes = <int>[];
    for (final Object? item in value) {
      hashes.add(dtoHash(item));
    }
    return Object.hashAll(hashes);
  }
  if (value is Map) {
    final List<int> hashes = <int>[];
    for (final Object? key in value.keys) {
      hashes.add(Object.hash(dtoHash(key), dtoHash(value[key])));
    }
    return Object.hashAllUnordered(hashes);
  }
  return value.hashCode;
}

/// 把列表逐项编码成 JSON 值。
List<Object?> encodeList<T>(List<T> values, Object? Function(T) encode) {
  return values.map<Object?>(encode).toList(growable: false);
}

/// 严格读取 bool 字段。
bool readBool(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is bool) return value;
  throw FormatException('字段 ' + key + ' 应为 bool');
}

/// 严格读取 base64 字节字段。
Uint8List readBytes(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  final String? text = value is String ? value : null;
  if (text != null) return base64Decode(text);
  throw FormatException('字段 ' + key + ' 应为 base64 字符串');
}

/// 读取可空 base64 字节字段。
Uint8List? readBytesOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  final String? text = value is String ? value : null;
  if (text != null) return base64Decode(text);
  throw FormatException('字段 ' + key + ' 应为 base64 字符串或 null');
}

/// 严格读取枚举字段（wire 字符串）。
T readEnum<T>(
  Map<String, Object?> json,
  String key,
  T Function(String) fromWire,
) {
  final Object? value = json[key];
  if (value is String) return fromWire(value);
  throw FormatException('字段 ' + key + ' 应为字符串枚举');
}

/// 严格读取 int 字段。
int readInt(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is int) return value;
  throw FormatException('字段 ' + key + ' 应为 int');
}

/// 严格读取数组字段并逐个解码。
List<T> readList<T>(
  Map<String, Object?> json,
  String key,
  T Function(Object?) decode,
) {
  final Object? value = json[key];
  if (value is List<Object?>) {
    return List<T>.unmodifiable(value.map<T>(decode));
  }
  throw FormatException('字段 ' + key + ' 应为数组');
}

/// 严格读取对象字段并解码。
T readObject<T>(
  Map<String, Object?> json,
  String key,
  T Function(Map<String, Object?>) decode,
) {
  final Object? value = json[key];
  if (value is Map<String, Object?>) return decode(value);
  throw FormatException('字段 ' + key + ' 应为 object');
}

/// 严格读取 string 字段。
String readString(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string');
}

/// 读取可空 string 字段。
String? readStringOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string 或 null');
}
