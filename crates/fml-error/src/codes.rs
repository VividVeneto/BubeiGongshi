//! 由 `tools/ci/gen_errors.py` 从 `contracts/errors/registry.yaml` 生成的错误码表。
//!
//! 请勿手工编辑：先改注册表，再运行 `python tools/ci/gen_errors.py`。

use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::Severity;

/// 注册表中不存在的错误码：解析失败时返回，不 panic、不回退、不丢未知值。
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct UnknownErrorCode;

#[rustfmt::skip]
impl fmt::Display for UnknownErrorCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { f.write_str("错误码未在 registry.yaml 中登记") }
}

impl std::error::Error for UnknownErrorCode {}

/// 一条错误码在注册表中的元数据。
struct Meta {
    code: &'static str,
    domain: &'static str,
    severity: Severity,
    retryable: bool,
    message_key: &'static str,
    fix_hint: bool,
    surface: &'static str,
    http_status: Option<u16>,
}

/// 注册表元数据，按 `code` 升序，与 `ErrorCode` 的声明顺序一致。
#[rustfmt::skip]
static META: &[Meta] = &[
    Meta { code: "AST_JSON_INVALID", domain: "ast", severity: Severity::Error, retryable: false, message_key: "err.ast.json_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "AUTH_EMAIL_CODE_EXPIRED", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.email_code_expired", fix_hint: false, surface: "server", http_status: Some(400) },
    Meta { code: "AUTH_EMAIL_CODE_INVALID", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.email_code_invalid", fix_hint: false, surface: "server", http_status: Some(400) },
    Meta { code: "AUTH_EMAIL_SEND_FAILED", domain: "auth", severity: Severity::Error, retryable: true, message_key: "err.auth.email_send_failed", fix_hint: false, surface: "server", http_status: Some(503) },
    Meta { code: "AUTH_EMAIL_TAKEN", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.email_taken", fix_hint: false, surface: "server", http_status: Some(409) },
    Meta { code: "AUTH_GUEST_EXISTS", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.guest_exists", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "AUTH_INVALID_CREDENTIALS", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.invalid_credentials", fix_hint: false, surface: "server", http_status: Some(401) },
    Meta { code: "AUTH_LOCKED", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.locked", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "AUTH_NO_PROFILE", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.no_profile", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "AUTH_PASSWORD_WEAK", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.password_weak", fix_hint: false, surface: "server", http_status: Some(400) },
    Meta { code: "AUTH_PROFILE_EXISTS", domain: "auth", severity: Severity::Warning, retryable: false, message_key: "err.auth.profile_exists", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "AUTH_RATE_LIMITED", domain: "auth", severity: Severity::Error, retryable: true, message_key: "err.auth.rate_limited", fix_hint: false, surface: "server", http_status: Some(429) },
    Meta { code: "AUTH_REAUTH_REQUIRED", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.reauth_required", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "AUTH_RECENT_LOGIN_REQUIRED", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.recent_login_required", fix_hint: false, surface: "server", http_status: Some(401) },
    Meta { code: "AUTH_REFRESH_REVOKED", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.refresh_revoked", fix_hint: false, surface: "server", http_status: Some(401) },
    Meta { code: "AUTH_SETTING_INVALID", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.setting_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "AUTH_TOKEN_EXPIRED", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.token_expired", fix_hint: false, surface: "server", http_status: Some(401) },
    Meta { code: "AUTH_TOKEN_INVALID", domain: "auth", severity: Severity::Error, retryable: false, message_key: "err.auth.token_invalid", fix_hint: false, surface: "server", http_status: Some(401) },
    Meta { code: "AUTH_UPLOAD_RECONFIRM_REQUIRED", domain: "auth", severity: Severity::Warning, retryable: false, message_key: "err.auth.upload_reconfirm_required", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "BACKUP_CANCELLED", domain: "backup", severity: Severity::Info, retryable: false, message_key: "err.backup.cancelled", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "BACKUP_CORRUPT", domain: "backup", severity: Severity::Error, retryable: false, message_key: "err.backup.corrupt", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "BACKUP_DISK_FULL", domain: "backup", severity: Severity::Error, retryable: true, message_key: "err.backup.disk_full", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "BACKUP_PROTECTION_UNAVAILABLE", domain: "backup", severity: Severity::Error, retryable: false, message_key: "err.backup.protection_unavailable", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "BACKUP_REPLACE_BLOCKED_BY_SYNC", domain: "backup", severity: Severity::Error, retryable: false, message_key: "err.backup.replace_blocked_by_sync", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "BACKUP_SCHEMA_TOO_NEW", domain: "backup", severity: Severity::Error, retryable: false, message_key: "err.backup.schema_too_new", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "BACKUP_SCOPE_INVALID", domain: "backup", severity: Severity::Error, retryable: false, message_key: "err.backup.scope_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "BACKUP_TOKEN_UNKNOWN", domain: "backup", severity: Severity::Error, retryable: false, message_key: "err.backup.token_unknown", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "BACKUP_WRONG_SECRET", domain: "backup", severity: Severity::Error, retryable: true, message_key: "err.backup.wrong_secret", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_BUDGET_BREAKER", domain: "cloud", severity: Severity::Error, retryable: true, message_key: "err.cloud.budget_breaker", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_CONSENT_INVALID", domain: "cloud", severity: Severity::Error, retryable: false, message_key: "err.cloud.consent_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_HASH_MISMATCH", domain: "cloud", severity: Severity::Error, retryable: false, message_key: "err.cloud.hash_mismatch", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_IDEMPOTENCY_CONFLICT", domain: "cloud", severity: Severity::Error, retryable: false, message_key: "err.cloud.idempotency_conflict", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_IMAGE_TOO_LARGE", domain: "cloud", severity: Severity::Error, retryable: false, message_key: "err.cloud.image_too_large", fix_hint: true, surface: "client", http_status: None },
    Meta { code: "CLOUD_JOB_NOT_FOUND", domain: "cloud", severity: Severity::Error, retryable: false, message_key: "err.cloud.job_not_found", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_NOT_ELIGIBLE", domain: "cloud", severity: Severity::Error, retryable: false, message_key: "err.cloud.not_eligible", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_OUTPUT_REJECTED", domain: "cloud", severity: Severity::Warning, retryable: false, message_key: "err.cloud.output_rejected", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_PREVIEW_STALE", domain: "cloud", severity: Severity::Warning, retryable: false, message_key: "err.cloud.preview_stale", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_PROVIDER_ERROR", domain: "cloud", severity: Severity::Error, retryable: true, message_key: "err.cloud.provider_error", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_PROVIDER_TIMEOUT", domain: "cloud", severity: Severity::Error, retryable: true, message_key: "err.cloud.provider_timeout", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_QUOTA_EXCEEDED", domain: "cloud", severity: Severity::Warning, retryable: true, message_key: "err.cloud.quota_exceeded", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_TOKEN_EXPIRED", domain: "cloud", severity: Severity::Warning, retryable: false, message_key: "err.cloud.token_expired", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CLOUD_UNKNOWN_OUTCOME", domain: "cloud", severity: Severity::Warning, retryable: false, message_key: "err.cloud.unknown_outcome", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CONTENT_DUPLICATE", domain: "content", severity: Severity::Error, retryable: false, message_key: "err.content.duplicate", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CONTENT_FIELD_INVALID", domain: "content", severity: Severity::Error, retryable: false, message_key: "err.content.field_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CONTENT_FIELD_MISSING", domain: "content", severity: Severity::Error, retryable: false, message_key: "err.content.field_missing", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CONTENT_LICENSE_FORBIDDEN", domain: "content", severity: Severity::Error, retryable: false, message_key: "err.content.license_forbidden", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CONTENT_LICENSE_MISSING", domain: "content", severity: Severity::Error, retryable: false, message_key: "err.content.license_missing", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CONTENT_NOT_VERIFIED", domain: "content", severity: Severity::Error, retryable: false, message_key: "err.content.not_verified", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CONTENT_REVIEW_INVALID", domain: "content", severity: Severity::Error, retryable: false, message_key: "err.content.review_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CRYPTO_DECRYPT_FAILED", domain: "crypto", severity: Severity::Error, retryable: false, message_key: "err.crypto.decrypt_failed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CRYPTO_KDF_MEMORY", domain: "crypto", severity: Severity::Error, retryable: false, message_key: "err.crypto.kdf_memory", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CRYPTO_KEY_VERSION_UNKNOWN", domain: "crypto", severity: Severity::Error, retryable: false, message_key: "err.crypto.key_version_unknown", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CRYPTO_PARAM_INVALID", domain: "crypto", severity: Severity::Error, retryable: false, message_key: "err.crypto.param_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CRYPTO_PASSPHRASE_WEAK", domain: "crypto", severity: Severity::Warning, retryable: false, message_key: "err.crypto.passphrase_weak", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CRYPTO_RECOVERY_CODE_FORMAT", domain: "crypto", severity: Severity::Warning, retryable: false, message_key: "err.crypto.recovery_code_format", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "CRYPTO_RNG_FAILED", domain: "crypto", severity: Severity::Error, retryable: true, message_key: "err.crypto.rng_failed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "DERIVE_CROSS_KIND_UNCONFIRMED", domain: "derive", severity: Severity::Error, retryable: false, message_key: "err.derive.cross_kind_unconfirmed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "DERIVE_CYCLE", domain: "derive", severity: Severity::Error, retryable: false, message_key: "err.derive.cycle", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "DERIVE_DEPTH_EXCEEDED", domain: "derive", severity: Severity::Error, retryable: false, message_key: "err.derive.depth_exceeded", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "DERIVE_NODE_LIMIT", domain: "derive", severity: Severity::Error, retryable: false, message_key: "err.derive.node_limit", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "DERIVE_NOT_VERIFIED", domain: "derive", severity: Severity::Error, retryable: false, message_key: "err.derive.not_verified", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "DERIVE_READ_ONLY", domain: "derive", severity: Severity::Error, retryable: false, message_key: "err.derive.read_only", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "DERIVE_TYPE_MISMATCH", domain: "derive", severity: Severity::Error, retryable: false, message_key: "err.derive.type_mismatch", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "ENGINE_DATA_CONFLICT", domain: "engine", severity: Severity::Error, retryable: false, message_key: "err.engine.data_conflict", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "ENGINE_DATA_INVALID", domain: "engine", severity: Severity::Error, retryable: false, message_key: "err.engine.data_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "ENGINE_UNAVAILABLE", domain: "engine", severity: Severity::Error, retryable: true, message_key: "err.engine.unavailable", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EVAL_DIV_ZERO", domain: "eval", severity: Severity::Error, retryable: false, message_key: "err.eval.div_zero", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EVAL_DOMAIN", domain: "eval", severity: Severity::Error, retryable: false, message_key: "err.eval.domain", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EVAL_LIMIT_EXCEEDED", domain: "eval", severity: Severity::Error, retryable: false, message_key: "err.eval.limit_exceeded", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EVAL_MULTI_BRANCH", domain: "eval", severity: Severity::Info, retryable: false, message_key: "err.eval.multi_branch", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EVAL_NAN_OR_INF", domain: "eval", severity: Severity::Error, retryable: false, message_key: "err.eval.nan_or_inf", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EVAL_NEEDS_INTERVAL", domain: "eval", severity: Severity::Error, retryable: false, message_key: "err.eval.needs_interval", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EVAL_NOT_COMPUTABLE", domain: "eval", severity: Severity::Error, retryable: false, message_key: "err.eval.not_computable", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EVAL_NO_CONVERGE", domain: "eval", severity: Severity::Error, retryable: false, message_key: "err.eval.no_converge", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EVAL_OVERFLOW", domain: "eval", severity: Severity::Error, retryable: false, message_key: "err.eval.overflow", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EVAL_TIMEOUT", domain: "eval", severity: Severity::Error, retryable: true, message_key: "err.eval.timeout", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EXPORT_NOT_RENDERABLE", domain: "export", severity: Severity::Warning, retryable: false, message_key: "err.export.not_renderable", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "EXPORT_TOO_LARGE", domain: "export", severity: Severity::Warning, retryable: false, message_key: "err.export.too_large", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "FFI_BAD_ARG", domain: "ffi", severity: Severity::Error, retryable: false, message_key: "err.ffi.bad_arg", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "FFI_BUSY", domain: "ffi", severity: Severity::Error, retryable: true, message_key: "err.ffi.busy", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "FFI_PANIC", domain: "ffi", severity: Severity::Error, retryable: false, message_key: "err.ffi.panic", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "FFI_STALE_HANDLE", domain: "ffi", severity: Severity::Error, retryable: false, message_key: "err.ffi.stale_handle", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "FFI_UNKNOWN_OP", domain: "ffi", severity: Severity::Error, retryable: false, message_key: "err.ffi.unknown_op", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "FFI_VERSION_MISMATCH", domain: "ffi", severity: Severity::Error, retryable: false, message_key: "err.ffi.version_mismatch", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "GRADE_PARSE_FAILED", domain: "grade", severity: Severity::Error, retryable: false, message_key: "err.grade.parse_failed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "GRADE_TIMEOUT", domain: "grade", severity: Severity::Warning, retryable: false, message_key: "err.grade.timeout", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "GRADE_UNSUPPORTED", domain: "grade", severity: Severity::Warning, retryable: false, message_key: "err.grade.unsupported", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "IMG_CANCELLED", domain: "img", severity: Severity::Info, retryable: false, message_key: "err.img.cancelled", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "IMG_CORRUPT", domain: "img", severity: Severity::Error, retryable: false, message_key: "err.img.corrupt", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "IMG_CROP_INVALID", domain: "img", severity: Severity::Error, retryable: false, message_key: "err.img.crop_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "IMG_FORMAT_UNSUPPORTED", domain: "img", severity: Severity::Error, retryable: false, message_key: "err.img.format_unsupported", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "IMG_PATH_INVALID", domain: "img", severity: Severity::Error, retryable: false, message_key: "err.img.path_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "IMG_TOO_LARGE", domain: "img", severity: Severity::Error, retryable: false, message_key: "err.img.too_large", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "IMG_TOO_MANY_PIXELS", domain: "img", severity: Severity::Error, retryable: false, message_key: "err.img.too_many_pixels", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "IMG_UPLOAD_TOO_LARGE", domain: "img", severity: Severity::Error, retryable: false, message_key: "err.img.upload_too_large", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_BATCH_CANCELLED", domain: "lib", severity: Severity::Info, retryable: false, message_key: "err.lib.batch_cancelled", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_BATCH_TOO_LARGE", domain: "lib", severity: Severity::Error, retryable: false, message_key: "err.lib.batch_too_large", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_DRAFT_INVALID", domain: "lib", severity: Severity::Error, retryable: false, message_key: "err.lib.draft_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_IMPORT_ROW_INVALID", domain: "lib", severity: Severity::Error, retryable: false, message_key: "err.lib.import_row_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_IMPORT_TOO_LARGE", domain: "lib", severity: Severity::Error, retryable: false, message_key: "err.lib.import_too_large", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_META_INVALID", domain: "lib", severity: Severity::Error, retryable: false, message_key: "err.lib.meta_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_NOT_FOUND", domain: "lib", severity: Severity::Error, retryable: false, message_key: "err.lib.not_found", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_NOT_VERIFIED", domain: "lib", severity: Severity::Error, retryable: false, message_key: "err.lib.not_verified", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_READ_ONLY", domain: "lib", severity: Severity::Error, retryable: false, message_key: "err.lib.read_only", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_TAGS_LIMIT", domain: "lib", severity: Severity::Warning, retryable: false, message_key: "err.lib.tags_limit", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "LIB_TRASHED", domain: "lib", severity: Severity::Error, retryable: false, message_key: "err.lib.trashed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "NET_HOST_NOT_ALLOWED", domain: "net", severity: Severity::Error, retryable: false, message_key: "err.net.host_not_allowed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "NET_OFFLINE", domain: "net", severity: Severity::Error, retryable: true, message_key: "err.net.offline", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "NET_TIMEOUT", domain: "net", severity: Severity::Error, retryable: true, message_key: "err.net.timeout", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "NET_TLS", domain: "net", severity: Severity::Error, retryable: false, message_key: "err.net.tls", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "NOTATION_AMBIGUOUS", domain: "notation", severity: Severity::Warning, retryable: false, message_key: "err.notation.ambiguous", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "NOTATION_CONSTANT_CONFLICT", domain: "notation", severity: Severity::Info, retryable: false, message_key: "err.notation.constant_conflict", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "NOTATION_LOG_BASE", domain: "notation", severity: Severity::Warning, retryable: false, message_key: "err.notation.log_base", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "NOTATION_UNBOUND", domain: "notation", severity: Severity::Error, retryable: false, message_key: "err.notation.unbound", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_DEP_MISSING", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.dep_missing", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_DOWNGRADE", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.downgrade", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_DOWNLOAD_INCOMPLETE", domain: "pack", severity: Severity::Warning, retryable: true, message_key: "err.pack.download_incomplete", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_EPOCH_ROLLBACK", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.epoch_rollback", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_FORBIDDEN_ENTRY", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.forbidden_entry", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_HASH_MISMATCH", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.hash_mismatch", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_INCOMPATIBLE", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.incompatible", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_KEY_UNKNOWN", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.key_unknown", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_LIMIT_EXCEEDED", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.limit_exceeded", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_METADATA_EXPIRED", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.metadata_expired", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_SIG_INVALID", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.sig_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_STORAGE_LOW", domain: "pack", severity: Severity::Warning, retryable: true, message_key: "err.pack.storage_low", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PACK_UNSAFE_PATH", domain: "pack", severity: Severity::Error, retryable: false, message_key: "err.pack.unsafe_path", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PARSE_FORBIDDEN_COMMAND", domain: "parse", severity: Severity::Error, retryable: false, message_key: "err.parse.forbidden_command", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PARSE_HOLE_UNFILLED", domain: "parse", severity: Severity::Error, retryable: false, message_key: "err.parse.hole_unfilled", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PARSE_LIMIT_EXCEEDED", domain: "parse", severity: Severity::Error, retryable: false, message_key: "err.parse.limit_exceeded", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PARSE_SYNTAX", domain: "parse", severity: Severity::Error, retryable: false, message_key: "err.parse.syntax", fix_hint: true, surface: "client", http_status: None },
    Meta { code: "PARSE_TIMEOUT", domain: "parse", severity: Severity::Error, retryable: true, message_key: "err.parse.timeout", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PARSE_UNICODE_NOT_EXPORTABLE", domain: "parse", severity: Severity::Warning, retryable: false, message_key: "err.parse.unicode_not_exportable", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PARSE_UNSUPPORTED_COMMAND", domain: "parse", severity: Severity::Error, retryable: false, message_key: "err.parse.unsupported_command", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_CANCELLED", domain: "platform", severity: Severity::Info, retryable: false, message_key: "err.platform.cancelled", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_FILE_TOO_LARGE", domain: "platform", severity: Severity::Error, retryable: false, message_key: "err.platform.file_too_large", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_FILE_TYPE_MISMATCH", domain: "platform", severity: Severity::Error, retryable: false, message_key: "err.platform.file_type_mismatch", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_IO", domain: "platform", severity: Severity::Error, retryable: true, message_key: "err.platform.io", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_KEY_UNAVAILABLE", domain: "platform", severity: Severity::Error, retryable: false, message_key: "err.platform.key_unavailable", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_PERMISSION_DENIED", domain: "platform", severity: Severity::Error, retryable: true, message_key: "err.platform.permission_denied", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_UNSUPPORTED", domain: "platform", severity: Severity::Error, retryable: false, message_key: "err.platform.unsupported", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_UPDATE_DISK_FULL", domain: "platform", severity: Severity::Error, retryable: true, message_key: "err.platform.update_disk_full", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_UPDATE_HASH_MISMATCH", domain: "platform", severity: Severity::Error, retryable: true, message_key: "err.platform.update_hash_mismatch", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_UPDATE_ROLLED_BACK", domain: "platform", severity: Severity::Warning, retryable: false, message_key: "err.platform.update_rolled_back", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PLATFORM_UPDATE_SIG_INVALID", domain: "platform", severity: Severity::Error, retryable: false, message_key: "err.platform.update_sig_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PRIVACY_CONSENT_MISSING", domain: "privacy", severity: Severity::Error, retryable: false, message_key: "err.privacy.consent_missing", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PRIVACY_DIAGNOSTICS_DISABLED", domain: "privacy", severity: Severity::Info, retryable: false, message_key: "err.privacy.diagnostics_disabled", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PRIVACY_REPRO_FAILED", domain: "privacy", severity: Severity::Error, retryable: true, message_key: "err.privacy.repro_failed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "PRIVACY_REQUEST_BLOCKED", domain: "privacy", severity: Severity::Error, retryable: false, message_key: "err.privacy.request_blocked", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_ACTIVE_TASK_EXISTS", domain: "recog", severity: Severity::Warning, retryable: true, message_key: "err.recog.active_task_exists", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_ALL_CANDIDATES_INVALID", domain: "recog", severity: Severity::Warning, retryable: false, message_key: "err.recog.all_candidates_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_BACKEND_NOT_ALLOWED", domain: "recog", severity: Severity::Error, retryable: false, message_key: "err.recog.backend_not_allowed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_BACKEND_REMOTE", domain: "recog", severity: Severity::Info, retryable: false, message_key: "err.recog.backend_remote", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_BACKEND_UNAVAILABLE", domain: "recog", severity: Severity::Error, retryable: false, message_key: "err.recog.backend_unavailable", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_CANCELLED", domain: "recog", severity: Severity::Info, retryable: false, message_key: "err.recog.cancelled", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_HISTORY_KEY_UNAVAILABLE", domain: "recog", severity: Severity::Error, retryable: true, message_key: "err.recog.history_key_unavailable", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_IMAGE_LOST", domain: "recog", severity: Severity::Warning, retryable: false, message_key: "err.recog.image_lost", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_INPUT_INVALID", domain: "recog", severity: Severity::Error, retryable: false, message_key: "err.recog.input_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_KEEP_LAST_OUT_OF_RANGE", domain: "recog", severity: Severity::Error, retryable: false, message_key: "err.recog.keep_last_out_of_range", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_MODEL_INCOMPATIBLE", domain: "recog", severity: Severity::Error, retryable: false, message_key: "err.recog.model_incompatible", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_MODEL_NOT_INSTALLED", domain: "recog", severity: Severity::Error, retryable: false, message_key: "err.recog.model_not_installed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_MODEL_OOM", domain: "recog", severity: Severity::Error, retryable: true, message_key: "err.recog.model_oom", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_MODEL_TIMEOUT", domain: "recog", severity: Severity::Warning, retryable: true, message_key: "err.recog.model_timeout", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_NO_CANDIDATE", domain: "recog", severity: Severity::Warning, retryable: true, message_key: "err.recog.no_candidate", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_OUTPUT_REJECTED", domain: "recog", severity: Severity::Warning, retryable: false, message_key: "err.recog.output_rejected", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_OUTPUT_TOO_LARGE", domain: "recog", severity: Severity::Error, retryable: false, message_key: "err.recog.output_too_large", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_QUOTA_EXCEEDED", domain: "recog", severity: Severity::Warning, retryable: false, message_key: "err.recog.quota_exceeded", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_SESSION_NOT_FOUND", domain: "recog", severity: Severity::Error, retryable: false, message_key: "err.recog.session_not_found", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_SPAN_INVALID", domain: "recog", severity: Severity::Error, retryable: false, message_key: "err.recog.span_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "RECOG_TRANSITION_INVALID", domain: "recog", severity: Severity::Error, retryable: false, message_key: "err.recog.transition_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SERVER_CLIENT_TOO_OLD", domain: "server", severity: Severity::Error, retryable: false, message_key: "err.server.client_too_old", fix_hint: false, surface: "server", http_status: Some(426) },
    Meta { code: "SERVER_UNAVAILABLE", domain: "server", severity: Severity::Error, retryable: true, message_key: "err.server.unavailable", fix_hint: false, surface: "server", http_status: Some(503) },
    Meta { code: "STORE_BUSY", domain: "store", severity: Severity::Warning, retryable: true, message_key: "err.store.busy", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STORE_CORRUPT", domain: "store", severity: Severity::Error, retryable: false, message_key: "err.store.corrupt", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STORE_DISK_FULL", domain: "store", severity: Severity::Error, retryable: true, message_key: "err.store.disk_full", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STORE_KEY_INVALID", domain: "store", severity: Severity::Error, retryable: false, message_key: "err.store.key_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STORE_MIGRATION_FAILED", domain: "store", severity: Severity::Error, retryable: false, message_key: "err.store.migration_failed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STORE_SCHEMA_TOO_NEW", domain: "store", severity: Severity::Error, retryable: false, message_key: "err.store.schema_too_new", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_BOOK_READ_ONLY", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.book_read_only", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_CARD_NOT_FOUND", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.card_not_found", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_CARD_PENDING_CHOICE", domain: "study", severity: Severity::Warning, retryable: false, message_key: "err.study.card_pending_choice", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_DAY_INVALID", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.day_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_INPUT_INVALID", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.input_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_K_OUT_OF_RANGE", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.k_out_of_range", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_NO_CARDS", domain: "study", severity: Severity::Info, retryable: false, message_key: "err.study.no_cards", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_PARAMS_NO_PREVIOUS", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.params_no_previous", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_PARAMS_VERSION_STALE", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.params_version_stale", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_PLAN_INVALID", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.plan_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_RETENTION_OUT_OF_RANGE", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.retention_out_of_range", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_REVISION_NOT_VERIFIED", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.revision_not_verified", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_SESSION_EXPIRED", domain: "study", severity: Severity::Warning, retryable: false, message_key: "err.study.session_expired", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "STUDY_STATS_RANGE_INVALID", domain: "study", severity: Severity::Error, retryable: false, message_key: "err.study.stats_range_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_AAD_MISMATCH", domain: "sync", severity: Severity::Warning, retryable: false, message_key: "err.sync.aad_mismatch", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_BATCH_INVALID", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.batch_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_BATCH_UNKNOWN", domain: "sync", severity: Severity::Warning, retryable: false, message_key: "err.sync.batch_unknown", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_CHOICE_INVALID", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.choice_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_CURSOR_INVALID", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.cursor_invalid", fix_hint: false, surface: "server", http_status: Some(400) },
    Meta { code: "SYNC_DECRYPT_FAILED", domain: "sync", severity: Severity::Warning, retryable: false, message_key: "err.sync.decrypt_failed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_DISABLED", domain: "sync", severity: Severity::Info, retryable: false, message_key: "err.sync.disabled", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_ENVELOPE_INVALID", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.envelope_invalid", fix_hint: false, surface: "server", http_status: Some(400) },
    Meta { code: "SYNC_EPOCH_STALE", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.epoch_stale", fix_hint: false, surface: "server", http_status: Some(409) },
    Meta { code: "SYNC_HASH_MISMATCH", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.hash_mismatch", fix_hint: false, surface: "server", http_status: Some(400) },
    Meta { code: "SYNC_KEY_MISSING", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.key_missing", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_KEY_VERSION_REJECTED", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.key_version_rejected", fix_hint: false, surface: "server", http_status: Some(409) },
    Meta { code: "SYNC_MERGE_CONFLICT", domain: "sync", severity: Severity::Warning, retryable: false, message_key: "err.sync.merge_conflict", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_NOT_AVAILABLE", domain: "sync", severity: Severity::Info, retryable: false, message_key: "err.sync.not_available", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_NOT_FOUND", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.not_found", fix_hint: false, surface: "server", http_status: Some(404) },
    Meta { code: "SYNC_PATH_INVALID", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.path_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_PAYLOAD_TOO_LARGE", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.payload_too_large", fix_hint: false, surface: "server", http_status: Some(413) },
    Meta { code: "SYNC_QUARANTINED", domain: "sync", severity: Severity::Warning, retryable: false, message_key: "err.sync.quarantined", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_QUOTA_EXCEEDED", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.quota_exceeded", fix_hint: false, surface: "server", http_status: Some(507) },
    Meta { code: "SYNC_SNAPSHOT_CORRUPT", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.snapshot_corrupt", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_SNAPSHOT_INCOMPLETE", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.snapshot_incomplete", fix_hint: false, surface: "server", http_status: Some(409) },
    Meta { code: "SYNC_UPGRADE_IN_PROGRESS", domain: "sync", severity: Severity::Warning, retryable: true, message_key: "err.sync.upgrade_in_progress", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_UPGRADE_KEY_FAILED", domain: "sync", severity: Severity::Error, retryable: true, message_key: "err.sync.upgrade_key_failed", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_UPGRADE_NOT_ABANDONABLE", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.upgrade_not_abandonable", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "SYNC_UPGRADE_STEP_INVALID", domain: "sync", severity: Severity::Error, retryable: false, message_key: "err.sync.upgrade_step_invalid", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPESET_DEPTH_EXCEEDED", domain: "typeset", severity: Severity::Error, retryable: false, message_key: "err.typeset.depth_exceeded", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPESET_MISSING_GLYPH", domain: "typeset", severity: Severity::Error, retryable: false, message_key: "err.typeset.missing_glyph", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPESET_NO_FONT", domain: "typeset", severity: Severity::Error, retryable: false, message_key: "err.typeset.no_font", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPE_AFFINE_MISUSE", domain: "type", severity: Severity::Error, retryable: false, message_key: "err.type.affine_misuse", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPE_CROSS_DIM", domain: "type", severity: Severity::Error, retryable: false, message_key: "err.type.cross_dim", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPE_DIM_CONFLICT", domain: "type", severity: Severity::Error, retryable: false, message_key: "err.type.dim_conflict", fix_hint: true, surface: "client", http_status: None },
    Meta { code: "TYPE_EMPIRICAL_COEFF", domain: "type", severity: Severity::Warning, retryable: false, message_key: "err.type.empirical_coeff", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPE_FUNC_ARG_DIMENSIONED", domain: "type", severity: Severity::Error, retryable: false, message_key: "err.type.func_arg_dimensioned", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPE_LOG_DIMENSIONED", domain: "type", severity: Severity::Error, retryable: false, message_key: "err.type.log_dimensioned", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPE_MATHKIND_MISMATCH", domain: "type", severity: Severity::Error, retryable: false, message_key: "err.type.mathkind_mismatch", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPE_QK_MISMATCH", domain: "type", severity: Severity::Warning, retryable: false, message_key: "err.type.qk_mismatch", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "TYPE_UNKNOWN_DIM", domain: "type", severity: Severity::Warning, retryable: false, message_key: "err.type.unknown_dim", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "UNIT_AFFINE_MISUSE", domain: "unit", severity: Severity::Error, retryable: false, message_key: "err.unit.affine_misuse", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "UNIT_CYCLE", domain: "unit", severity: Severity::Error, retryable: false, message_key: "err.unit.cycle", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "UNIT_DIM_SYNTAX", domain: "unit", severity: Severity::Error, retryable: false, message_key: "err.unit.dim_syntax", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "UNIT_DUPLICATE", domain: "unit", severity: Severity::Error, retryable: false, message_key: "err.unit.duplicate", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "UNIT_INCOMPATIBLE", domain: "unit", severity: Severity::Error, retryable: false, message_key: "err.unit.incompatible", fix_hint: true, surface: "client", http_status: None },
    Meta { code: "UNIT_INVALID_OFFSET", domain: "unit", severity: Severity::Error, retryable: false, message_key: "err.unit.invalid_offset", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "UNIT_IN_USE", domain: "unit", severity: Severity::Error, retryable: false, message_key: "err.unit.in_use", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "UNIT_OVERFLOW", domain: "unit", severity: Severity::Error, retryable: false, message_key: "err.unit.overflow", fix_hint: false, surface: "client", http_status: None },
    Meta { code: "UNIT_UNKNOWN", domain: "unit", severity: Severity::Error, retryable: false, message_key: "err.unit.unknown", fix_hint: false, surface: "client", http_status: None },
];

/// 全部已登记错误码，按注册表 `code` 升序。
#[rustfmt::skip]
static ALL: &[ErrorCode] = &[
    ErrorCode::AstJsonInvalid,
    ErrorCode::AuthEmailCodeExpired,
    ErrorCode::AuthEmailCodeInvalid,
    ErrorCode::AuthEmailSendFailed,
    ErrorCode::AuthEmailTaken,
    ErrorCode::AuthGuestExists,
    ErrorCode::AuthInvalidCredentials,
    ErrorCode::AuthLocked,
    ErrorCode::AuthNoProfile,
    ErrorCode::AuthPasswordWeak,
    ErrorCode::AuthProfileExists,
    ErrorCode::AuthRateLimited,
    ErrorCode::AuthReauthRequired,
    ErrorCode::AuthRecentLoginRequired,
    ErrorCode::AuthRefreshRevoked,
    ErrorCode::AuthSettingInvalid,
    ErrorCode::AuthTokenExpired,
    ErrorCode::AuthTokenInvalid,
    ErrorCode::AuthUploadReconfirmRequired,
    ErrorCode::BackupCancelled,
    ErrorCode::BackupCorrupt,
    ErrorCode::BackupDiskFull,
    ErrorCode::BackupProtectionUnavailable,
    ErrorCode::BackupReplaceBlockedBySync,
    ErrorCode::BackupSchemaTooNew,
    ErrorCode::BackupScopeInvalid,
    ErrorCode::BackupTokenUnknown,
    ErrorCode::BackupWrongSecret,
    ErrorCode::CloudBudgetBreaker,
    ErrorCode::CloudConsentInvalid,
    ErrorCode::CloudHashMismatch,
    ErrorCode::CloudIdempotencyConflict,
    ErrorCode::CloudImageTooLarge,
    ErrorCode::CloudJobNotFound,
    ErrorCode::CloudNotEligible,
    ErrorCode::CloudOutputRejected,
    ErrorCode::CloudPreviewStale,
    ErrorCode::CloudProviderError,
    ErrorCode::CloudProviderTimeout,
    ErrorCode::CloudQuotaExceeded,
    ErrorCode::CloudTokenExpired,
    ErrorCode::CloudUnknownOutcome,
    ErrorCode::ContentDuplicate,
    ErrorCode::ContentFieldInvalid,
    ErrorCode::ContentFieldMissing,
    ErrorCode::ContentLicenseForbidden,
    ErrorCode::ContentLicenseMissing,
    ErrorCode::ContentNotVerified,
    ErrorCode::ContentReviewInvalid,
    ErrorCode::CryptoDecryptFailed,
    ErrorCode::CryptoKdfMemory,
    ErrorCode::CryptoKeyVersionUnknown,
    ErrorCode::CryptoParamInvalid,
    ErrorCode::CryptoPassphraseWeak,
    ErrorCode::CryptoRecoveryCodeFormat,
    ErrorCode::CryptoRngFailed,
    ErrorCode::DeriveCrossKindUnconfirmed,
    ErrorCode::DeriveCycle,
    ErrorCode::DeriveDepthExceeded,
    ErrorCode::DeriveNodeLimit,
    ErrorCode::DeriveNotVerified,
    ErrorCode::DeriveReadOnly,
    ErrorCode::DeriveTypeMismatch,
    ErrorCode::EngineDataConflict,
    ErrorCode::EngineDataInvalid,
    ErrorCode::EngineUnavailable,
    ErrorCode::EvalDivZero,
    ErrorCode::EvalDomain,
    ErrorCode::EvalLimitExceeded,
    ErrorCode::EvalMultiBranch,
    ErrorCode::EvalNanOrInf,
    ErrorCode::EvalNeedsInterval,
    ErrorCode::EvalNotComputable,
    ErrorCode::EvalNoConverge,
    ErrorCode::EvalOverflow,
    ErrorCode::EvalTimeout,
    ErrorCode::ExportNotRenderable,
    ErrorCode::ExportTooLarge,
    ErrorCode::FfiBadArg,
    ErrorCode::FfiBusy,
    ErrorCode::FfiPanic,
    ErrorCode::FfiStaleHandle,
    ErrorCode::FfiUnknownOp,
    ErrorCode::FfiVersionMismatch,
    ErrorCode::GradeParseFailed,
    ErrorCode::GradeTimeout,
    ErrorCode::GradeUnsupported,
    ErrorCode::ImgCancelled,
    ErrorCode::ImgCorrupt,
    ErrorCode::ImgCropInvalid,
    ErrorCode::ImgFormatUnsupported,
    ErrorCode::ImgPathInvalid,
    ErrorCode::ImgTooLarge,
    ErrorCode::ImgTooManyPixels,
    ErrorCode::ImgUploadTooLarge,
    ErrorCode::LibBatchCancelled,
    ErrorCode::LibBatchTooLarge,
    ErrorCode::LibDraftInvalid,
    ErrorCode::LibImportRowInvalid,
    ErrorCode::LibImportTooLarge,
    ErrorCode::LibMetaInvalid,
    ErrorCode::LibNotFound,
    ErrorCode::LibNotVerified,
    ErrorCode::LibReadOnly,
    ErrorCode::LibTagsLimit,
    ErrorCode::LibTrashed,
    ErrorCode::NetHostNotAllowed,
    ErrorCode::NetOffline,
    ErrorCode::NetTimeout,
    ErrorCode::NetTls,
    ErrorCode::NotationAmbiguous,
    ErrorCode::NotationConstantConflict,
    ErrorCode::NotationLogBase,
    ErrorCode::NotationUnbound,
    ErrorCode::PackDepMissing,
    ErrorCode::PackDowngrade,
    ErrorCode::PackDownloadIncomplete,
    ErrorCode::PackEpochRollback,
    ErrorCode::PackForbiddenEntry,
    ErrorCode::PackHashMismatch,
    ErrorCode::PackIncompatible,
    ErrorCode::PackKeyUnknown,
    ErrorCode::PackLimitExceeded,
    ErrorCode::PackMetadataExpired,
    ErrorCode::PackSigInvalid,
    ErrorCode::PackStorageLow,
    ErrorCode::PackUnsafePath,
    ErrorCode::ParseForbiddenCommand,
    ErrorCode::ParseHoleUnfilled,
    ErrorCode::ParseLimitExceeded,
    ErrorCode::ParseSyntax,
    ErrorCode::ParseTimeout,
    ErrorCode::ParseUnicodeNotExportable,
    ErrorCode::ParseUnsupportedCommand,
    ErrorCode::PlatformCancelled,
    ErrorCode::PlatformFileTooLarge,
    ErrorCode::PlatformFileTypeMismatch,
    ErrorCode::PlatformIo,
    ErrorCode::PlatformKeyUnavailable,
    ErrorCode::PlatformPermissionDenied,
    ErrorCode::PlatformUnsupported,
    ErrorCode::PlatformUpdateDiskFull,
    ErrorCode::PlatformUpdateHashMismatch,
    ErrorCode::PlatformUpdateRolledBack,
    ErrorCode::PlatformUpdateSigInvalid,
    ErrorCode::PrivacyConsentMissing,
    ErrorCode::PrivacyDiagnosticsDisabled,
    ErrorCode::PrivacyReproFailed,
    ErrorCode::PrivacyRequestBlocked,
    ErrorCode::RecogActiveTaskExists,
    ErrorCode::RecogAllCandidatesInvalid,
    ErrorCode::RecogBackendNotAllowed,
    ErrorCode::RecogBackendRemote,
    ErrorCode::RecogBackendUnavailable,
    ErrorCode::RecogCancelled,
    ErrorCode::RecogHistoryKeyUnavailable,
    ErrorCode::RecogImageLost,
    ErrorCode::RecogInputInvalid,
    ErrorCode::RecogKeepLastOutOfRange,
    ErrorCode::RecogModelIncompatible,
    ErrorCode::RecogModelNotInstalled,
    ErrorCode::RecogModelOom,
    ErrorCode::RecogModelTimeout,
    ErrorCode::RecogNoCandidate,
    ErrorCode::RecogOutputRejected,
    ErrorCode::RecogOutputTooLarge,
    ErrorCode::RecogQuotaExceeded,
    ErrorCode::RecogSessionNotFound,
    ErrorCode::RecogSpanInvalid,
    ErrorCode::RecogTransitionInvalid,
    ErrorCode::ServerClientTooOld,
    ErrorCode::ServerUnavailable,
    ErrorCode::StoreBusy,
    ErrorCode::StoreCorrupt,
    ErrorCode::StoreDiskFull,
    ErrorCode::StoreKeyInvalid,
    ErrorCode::StoreMigrationFailed,
    ErrorCode::StoreSchemaTooNew,
    ErrorCode::StudyBookReadOnly,
    ErrorCode::StudyCardNotFound,
    ErrorCode::StudyCardPendingChoice,
    ErrorCode::StudyDayInvalid,
    ErrorCode::StudyInputInvalid,
    ErrorCode::StudyKOutOfRange,
    ErrorCode::StudyNoCards,
    ErrorCode::StudyParamsNoPrevious,
    ErrorCode::StudyParamsVersionStale,
    ErrorCode::StudyPlanInvalid,
    ErrorCode::StudyRetentionOutOfRange,
    ErrorCode::StudyRevisionNotVerified,
    ErrorCode::StudySessionExpired,
    ErrorCode::StudyStatsRangeInvalid,
    ErrorCode::SyncAadMismatch,
    ErrorCode::SyncBatchInvalid,
    ErrorCode::SyncBatchUnknown,
    ErrorCode::SyncChoiceInvalid,
    ErrorCode::SyncCursorInvalid,
    ErrorCode::SyncDecryptFailed,
    ErrorCode::SyncDisabled,
    ErrorCode::SyncEnvelopeInvalid,
    ErrorCode::SyncEpochStale,
    ErrorCode::SyncHashMismatch,
    ErrorCode::SyncKeyMissing,
    ErrorCode::SyncKeyVersionRejected,
    ErrorCode::SyncMergeConflict,
    ErrorCode::SyncNotAvailable,
    ErrorCode::SyncNotFound,
    ErrorCode::SyncPathInvalid,
    ErrorCode::SyncPayloadTooLarge,
    ErrorCode::SyncQuarantined,
    ErrorCode::SyncQuotaExceeded,
    ErrorCode::SyncSnapshotCorrupt,
    ErrorCode::SyncSnapshotIncomplete,
    ErrorCode::SyncUpgradeInProgress,
    ErrorCode::SyncUpgradeKeyFailed,
    ErrorCode::SyncUpgradeNotAbandonable,
    ErrorCode::SyncUpgradeStepInvalid,
    ErrorCode::TypesetDepthExceeded,
    ErrorCode::TypesetMissingGlyph,
    ErrorCode::TypesetNoFont,
    ErrorCode::TypeAffineMisuse,
    ErrorCode::TypeCrossDim,
    ErrorCode::TypeDimConflict,
    ErrorCode::TypeEmpiricalCoeff,
    ErrorCode::TypeFuncArgDimensioned,
    ErrorCode::TypeLogDimensioned,
    ErrorCode::TypeMathkindMismatch,
    ErrorCode::TypeQkMismatch,
    ErrorCode::TypeUnknownDim,
    ErrorCode::UnitAffineMisuse,
    ErrorCode::UnitCycle,
    ErrorCode::UnitDimSyntax,
    ErrorCode::UnitDuplicate,
    ErrorCode::UnitIncompatible,
    ErrorCode::UnitInvalidOffset,
    ErrorCode::UnitInUse,
    ErrorCode::UnitOverflow,
    ErrorCode::UnitUnknown,
];

/// 注册表登记的错误码：声明顺序与注册表 `code` 升序一致，`meta()` 按该顺序取元数据。
#[rustfmt::skip]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum ErrorCode {
    /// AST_JSON_INVALID（owner CORE-05）。
    AstJsonInvalid,
    /// AUTH_EMAIL_CODE_EXPIRED（owner CORE-45）。
    AuthEmailCodeExpired,
    /// AUTH_EMAIL_CODE_INVALID（owner CORE-45）。
    AuthEmailCodeInvalid,
    /// AUTH_EMAIL_SEND_FAILED（owner CORE-45）。
    AuthEmailSendFailed,
    /// AUTH_EMAIL_TAKEN（owner CORE-22）。
    AuthEmailTaken,
    /// AUTH_GUEST_EXISTS（owner CORE-23）。
    AuthGuestExists,
    /// AUTH_INVALID_CREDENTIALS（owner CORE-22）。
    AuthInvalidCredentials,
    /// AUTH_LOCKED（owner CORE-23）。
    AuthLocked,
    /// AUTH_NO_PROFILE（owner CORE-23）。
    AuthNoProfile,
    /// AUTH_PASSWORD_WEAK（owner CORE-22）。
    AuthPasswordWeak,
    /// AUTH_PROFILE_EXISTS（owner CORE-23）。
    AuthProfileExists,
    /// AUTH_RATE_LIMITED（owner CORE-22）。
    AuthRateLimited,
    /// AUTH_REAUTH_REQUIRED（owner CORE-22）。
    AuthReauthRequired,
    /// AUTH_RECENT_LOGIN_REQUIRED（owner CORE-22）。
    AuthRecentLoginRequired,
    /// AUTH_REFRESH_REVOKED（owner CORE-22）。
    AuthRefreshRevoked,
    /// AUTH_SETTING_INVALID（owner CORE-23）。
    AuthSettingInvalid,
    /// AUTH_TOKEN_EXPIRED（owner CORE-22）。
    AuthTokenExpired,
    /// AUTH_TOKEN_INVALID（owner CORE-22）。
    AuthTokenInvalid,
    /// AUTH_UPLOAD_RECONFIRM_REQUIRED（owner CORE-62）。
    AuthUploadReconfirmRequired,
    /// BACKUP_CANCELLED（owner CORE-27）。
    BackupCancelled,
    /// BACKUP_CORRUPT（owner CORE-27）。
    BackupCorrupt,
    /// BACKUP_DISK_FULL（owner CORE-27）。
    BackupDiskFull,
    /// BACKUP_PROTECTION_UNAVAILABLE（owner CORE-27）。
    BackupProtectionUnavailable,
    /// BACKUP_REPLACE_BLOCKED_BY_SYNC（owner CORE-27）。
    BackupReplaceBlockedBySync,
    /// BACKUP_SCHEMA_TOO_NEW（owner CORE-27）。
    BackupSchemaTooNew,
    /// BACKUP_SCOPE_INVALID（owner CORE-27）。
    BackupScopeInvalid,
    /// BACKUP_TOKEN_UNKNOWN（owner CORE-27）。
    BackupTokenUnknown,
    /// BACKUP_WRONG_SECRET（owner CORE-27）。
    BackupWrongSecret,
    /// CLOUD_BUDGET_BREAKER（owner CORE-33）。
    CloudBudgetBreaker,
    /// CLOUD_CONSENT_INVALID（owner CORE-33）。
    CloudConsentInvalid,
    /// CLOUD_HASH_MISMATCH（owner CORE-33）。
    CloudHashMismatch,
    /// CLOUD_IDEMPOTENCY_CONFLICT（owner CORE-33）。
    CloudIdempotencyConflict,
    /// CLOUD_IMAGE_TOO_LARGE（owner CORE-33）。
    CloudImageTooLarge,
    /// CLOUD_JOB_NOT_FOUND（owner CORE-33）。
    CloudJobNotFound,
    /// CLOUD_NOT_ELIGIBLE（owner CORE-33）。
    CloudNotEligible,
    /// CLOUD_OUTPUT_REJECTED（owner CORE-33）。
    CloudOutputRejected,
    /// CLOUD_PREVIEW_STALE（owner CORE-34）。
    CloudPreviewStale,
    /// CLOUD_PROVIDER_ERROR（owner CORE-33）。
    CloudProviderError,
    /// CLOUD_PROVIDER_TIMEOUT（owner CORE-33）。
    CloudProviderTimeout,
    /// CLOUD_QUOTA_EXCEEDED（owner CORE-33）。
    CloudQuotaExceeded,
    /// CLOUD_TOKEN_EXPIRED（owner CORE-34）。
    CloudTokenExpired,
    /// CLOUD_UNKNOWN_OUTCOME（owner CORE-33）。
    CloudUnknownOutcome,
    /// CONTENT_DUPLICATE（owner CORE-16）。
    ContentDuplicate,
    /// CONTENT_FIELD_INVALID（owner CORE-16）。
    ContentFieldInvalid,
    /// CONTENT_FIELD_MISSING（owner CORE-16）。
    ContentFieldMissing,
    /// CONTENT_LICENSE_FORBIDDEN（owner CORE-16）。
    ContentLicenseForbidden,
    /// CONTENT_LICENSE_MISSING（owner CORE-16）。
    ContentLicenseMissing,
    /// CONTENT_NOT_VERIFIED（owner CORE-16）。
    ContentNotVerified,
    /// CONTENT_REVIEW_INVALID（owner CORE-16）。
    ContentReviewInvalid,
    /// CRYPTO_DECRYPT_FAILED（owner CORE-21）。
    CryptoDecryptFailed,
    /// CRYPTO_KDF_MEMORY（owner CORE-21）。
    CryptoKdfMemory,
    /// CRYPTO_KEY_VERSION_UNKNOWN（owner CORE-21）。
    CryptoKeyVersionUnknown,
    /// CRYPTO_PARAM_INVALID（owner CORE-21）。
    CryptoParamInvalid,
    /// CRYPTO_PASSPHRASE_WEAK（owner CORE-21）。
    CryptoPassphraseWeak,
    /// CRYPTO_RECOVERY_CODE_FORMAT（owner CORE-21）。
    CryptoRecoveryCodeFormat,
    /// CRYPTO_RNG_FAILED（owner CORE-21）。
    CryptoRngFailed,
    /// DERIVE_CROSS_KIND_UNCONFIRMED（owner CORE-11）。
    DeriveCrossKindUnconfirmed,
    /// DERIVE_CYCLE（owner CORE-11）。
    DeriveCycle,
    /// DERIVE_DEPTH_EXCEEDED（owner CORE-11）。
    DeriveDepthExceeded,
    /// DERIVE_NODE_LIMIT（owner CORE-11）。
    DeriveNodeLimit,
    /// DERIVE_NOT_VERIFIED（owner CORE-11）。
    DeriveNotVerified,
    /// DERIVE_READ_ONLY（owner CORE-11）。
    DeriveReadOnly,
    /// DERIVE_TYPE_MISMATCH（owner CORE-11）。
    DeriveTypeMismatch,
    /// ENGINE_DATA_CONFLICT（owner CORE-56）。
    EngineDataConflict,
    /// ENGINE_DATA_INVALID（owner CORE-56）。
    EngineDataInvalid,
    /// ENGINE_UNAVAILABLE（owner CORE-56）。
    EngineUnavailable,
    /// EVAL_DIV_ZERO（owner CORE-10）。
    EvalDivZero,
    /// EVAL_DOMAIN（owner CORE-10）。
    EvalDomain,
    /// EVAL_LIMIT_EXCEEDED（owner CORE-10）。
    EvalLimitExceeded,
    /// EVAL_MULTI_BRANCH（owner CORE-93）。
    EvalMultiBranch,
    /// EVAL_NAN_OR_INF（owner CORE-10）。
    EvalNanOrInf,
    /// EVAL_NEEDS_INTERVAL（owner CORE-93）。
    EvalNeedsInterval,
    /// EVAL_NOT_COMPUTABLE（owner CORE-10）。
    EvalNotComputable,
    /// EVAL_NO_CONVERGE（owner CORE-93）。
    EvalNoConverge,
    /// EVAL_OVERFLOW（owner CORE-10）。
    EvalOverflow,
    /// EVAL_TIMEOUT（owner CORE-10）。
    EvalTimeout,
    /// EXPORT_NOT_RENDERABLE（owner CORE-52）。
    ExportNotRenderable,
    /// EXPORT_TOO_LARGE（owner CORE-52）。
    ExportTooLarge,
    /// FFI_BAD_ARG（owner CORE-03）。
    FfiBadArg,
    /// FFI_BUSY（owner CORE-03）。
    FfiBusy,
    /// FFI_PANIC（owner CORE-03）。
    FfiPanic,
    /// FFI_STALE_HANDLE（owner CORE-03）。
    FfiStaleHandle,
    /// FFI_UNKNOWN_OP（owner CORE-03）。
    FfiUnknownOp,
    /// FFI_VERSION_MISMATCH（owner CORE-03）。
    FfiVersionMismatch,
    /// GRADE_PARSE_FAILED（owner CORE-18）。
    GradeParseFailed,
    /// GRADE_TIMEOUT（owner CORE-18）。
    GradeTimeout,
    /// GRADE_UNSUPPORTED（owner CORE-18）。
    GradeUnsupported,
    /// IMG_CANCELLED（owner CORE-30）。
    ImgCancelled,
    /// IMG_CORRUPT（owner CORE-30）。
    ImgCorrupt,
    /// IMG_CROP_INVALID（owner CORE-30）。
    ImgCropInvalid,
    /// IMG_FORMAT_UNSUPPORTED（owner CORE-30）。
    ImgFormatUnsupported,
    /// IMG_PATH_INVALID（owner CORE-30）。
    ImgPathInvalid,
    /// IMG_TOO_LARGE（owner CORE-30）。
    ImgTooLarge,
    /// IMG_TOO_MANY_PIXELS（owner CORE-30）。
    ImgTooManyPixels,
    /// IMG_UPLOAD_TOO_LARGE（owner CORE-30）。
    ImgUploadTooLarge,
    /// LIB_BATCH_CANCELLED（owner CORE-54）。
    LibBatchCancelled,
    /// LIB_BATCH_TOO_LARGE（owner CORE-54）。
    LibBatchTooLarge,
    /// LIB_DRAFT_INVALID（owner CORE-61）。
    LibDraftInvalid,
    /// LIB_IMPORT_ROW_INVALID（owner CORE-14）。
    LibImportRowInvalid,
    /// LIB_IMPORT_TOO_LARGE（owner CORE-14）。
    LibImportTooLarge,
    /// LIB_META_INVALID（owner CORE-14）。
    LibMetaInvalid,
    /// LIB_NOT_FOUND（owner CORE-14）。
    LibNotFound,
    /// LIB_NOT_VERIFIED（owner CORE-14）。
    LibNotVerified,
    /// LIB_READ_ONLY（owner CORE-14）。
    LibReadOnly,
    /// LIB_TAGS_LIMIT（owner CORE-14）。
    LibTagsLimit,
    /// LIB_TRASHED（owner CORE-14）。
    LibTrashed,
    /// NET_HOST_NOT_ALLOWED（owner CORE-04）。
    NetHostNotAllowed,
    /// NET_OFFLINE（owner CORE-04）。
    NetOffline,
    /// NET_TIMEOUT（owner CORE-04）。
    NetTimeout,
    /// NET_TLS（owner CORE-04）。
    NetTls,
    /// NOTATION_AMBIGUOUS（owner CORE-07）。
    NotationAmbiguous,
    /// NOTATION_CONSTANT_CONFLICT（owner CORE-07）。
    NotationConstantConflict,
    /// NOTATION_LOG_BASE（owner CORE-07）。
    NotationLogBase,
    /// NOTATION_UNBOUND（owner CORE-07）。
    NotationUnbound,
    /// PACK_DEP_MISSING（owner CORE-15）。
    PackDepMissing,
    /// PACK_DOWNGRADE（owner CORE-15）。
    PackDowngrade,
    /// PACK_DOWNLOAD_INCOMPLETE（owner CORE-51）。
    PackDownloadIncomplete,
    /// PACK_EPOCH_ROLLBACK（owner CORE-15）。
    PackEpochRollback,
    /// PACK_FORBIDDEN_ENTRY（owner CORE-15）。
    PackForbiddenEntry,
    /// PACK_HASH_MISMATCH（owner CORE-15）。
    PackHashMismatch,
    /// PACK_INCOMPATIBLE（owner CORE-15）。
    PackIncompatible,
    /// PACK_KEY_UNKNOWN（owner CORE-15）。
    PackKeyUnknown,
    /// PACK_LIMIT_EXCEEDED（owner CORE-15）。
    PackLimitExceeded,
    /// PACK_METADATA_EXPIRED（owner CORE-15）。
    PackMetadataExpired,
    /// PACK_SIG_INVALID（owner CORE-15）。
    PackSigInvalid,
    /// PACK_STORAGE_LOW（owner CORE-51）。
    PackStorageLow,
    /// PACK_UNSAFE_PATH（owner CORE-15）。
    PackUnsafePath,
    /// PARSE_FORBIDDEN_COMMAND（owner CORE-06）。
    ParseForbiddenCommand,
    /// PARSE_HOLE_UNFILLED（owner CORE-06）。
    ParseHoleUnfilled,
    /// PARSE_LIMIT_EXCEEDED（owner CORE-05）。
    ParseLimitExceeded,
    /// PARSE_SYNTAX（owner CORE-06）。
    ParseSyntax,
    /// PARSE_TIMEOUT（owner CORE-06）。
    ParseTimeout,
    /// PARSE_UNICODE_NOT_EXPORTABLE（owner CORE-92）。
    ParseUnicodeNotExportable,
    /// PARSE_UNSUPPORTED_COMMAND（owner CORE-06）。
    ParseUnsupportedCommand,
    /// PLATFORM_CANCELLED（owner CORE-04）。
    PlatformCancelled,
    /// PLATFORM_FILE_TOO_LARGE（owner CORE-04）。
    PlatformFileTooLarge,
    /// PLATFORM_FILE_TYPE_MISMATCH（owner CORE-04）。
    PlatformFileTypeMismatch,
    /// PLATFORM_IO（owner CORE-04）。
    PlatformIo,
    /// PLATFORM_KEY_UNAVAILABLE（owner CORE-04）。
    PlatformKeyUnavailable,
    /// PLATFORM_PERMISSION_DENIED（owner CORE-04）。
    PlatformPermissionDenied,
    /// PLATFORM_UNSUPPORTED（owner CORE-04）。
    PlatformUnsupported,
    /// PLATFORM_UPDATE_DISK_FULL（owner CORE-04）。
    PlatformUpdateDiskFull,
    /// PLATFORM_UPDATE_HASH_MISMATCH（owner CORE-04）。
    PlatformUpdateHashMismatch,
    /// PLATFORM_UPDATE_ROLLED_BACK（owner CORE-04）。
    PlatformUpdateRolledBack,
    /// PLATFORM_UPDATE_SIG_INVALID（owner CORE-04）。
    PlatformUpdateSigInvalid,
    /// PRIVACY_CONSENT_MISSING（owner CORE-28）。
    PrivacyConsentMissing,
    /// PRIVACY_DIAGNOSTICS_DISABLED（owner CORE-28）。
    PrivacyDiagnosticsDisabled,
    /// PRIVACY_REPRO_FAILED（owner CORE-28）。
    PrivacyReproFailed,
    /// PRIVACY_REQUEST_BLOCKED（owner CORE-28）。
    PrivacyRequestBlocked,
    /// RECOG_ACTIVE_TASK_EXISTS（owner CORE-32）。
    RecogActiveTaskExists,
    /// RECOG_ALL_CANDIDATES_INVALID（owner CORE-31）。
    RecogAllCandidatesInvalid,
    /// RECOG_BACKEND_NOT_ALLOWED（owner CORE-29）。
    RecogBackendNotAllowed,
    /// RECOG_BACKEND_REMOTE（owner CORE-29）。
    RecogBackendRemote,
    /// RECOG_BACKEND_UNAVAILABLE（owner CORE-29）。
    RecogBackendUnavailable,
    /// RECOG_CANCELLED（owner CORE-29）。
    RecogCancelled,
    /// RECOG_HISTORY_KEY_UNAVAILABLE（owner CORE-32）。
    RecogHistoryKeyUnavailable,
    /// RECOG_IMAGE_LOST（owner CORE-32）。
    RecogImageLost,
    /// RECOG_INPUT_INVALID（owner CORE-29）。
    RecogInputInvalid,
    /// RECOG_KEEP_LAST_OUT_OF_RANGE（owner CORE-32）。
    RecogKeepLastOutOfRange,
    /// RECOG_MODEL_INCOMPATIBLE（owner CORE-35）。
    RecogModelIncompatible,
    /// RECOG_MODEL_NOT_INSTALLED（owner CORE-35）。
    RecogModelNotInstalled,
    /// RECOG_MODEL_OOM（owner CORE-35）。
    RecogModelOom,
    /// RECOG_MODEL_TIMEOUT（owner CORE-35）。
    RecogModelTimeout,
    /// RECOG_NO_CANDIDATE（owner CORE-29）。
    RecogNoCandidate,
    /// RECOG_OUTPUT_REJECTED（owner CORE-31）。
    RecogOutputRejected,
    /// RECOG_OUTPUT_TOO_LARGE（owner CORE-31）。
    RecogOutputTooLarge,
    /// RECOG_QUOTA_EXCEEDED（owner CORE-32）。
    RecogQuotaExceeded,
    /// RECOG_SESSION_NOT_FOUND（owner CORE-32）。
    RecogSessionNotFound,
    /// RECOG_SPAN_INVALID（owner CORE-31）。
    RecogSpanInvalid,
    /// RECOG_TRANSITION_INVALID（owner CORE-32）。
    RecogTransitionInvalid,
    /// SERVER_CLIENT_TOO_OLD（owner CORE-22）。
    ServerClientTooOld,
    /// SERVER_UNAVAILABLE（owner CORE-22）。
    ServerUnavailable,
    /// STORE_BUSY（owner CORE-13）。
    StoreBusy,
    /// STORE_CORRUPT（owner CORE-13）。
    StoreCorrupt,
    /// STORE_DISK_FULL（owner CORE-13）。
    StoreDiskFull,
    /// STORE_KEY_INVALID（owner CORE-13）。
    StoreKeyInvalid,
    /// STORE_MIGRATION_FAILED（owner CORE-13）。
    StoreMigrationFailed,
    /// STORE_SCHEMA_TOO_NEW（owner CORE-13）。
    StoreSchemaTooNew,
    /// STUDY_BOOK_READ_ONLY（owner CORE-19）。
    StudyBookReadOnly,
    /// STUDY_CARD_NOT_FOUND（owner CORE-17）。
    StudyCardNotFound,
    /// STUDY_CARD_PENDING_CHOICE（owner CORE-17）。
    StudyCardPendingChoice,
    /// STUDY_DAY_INVALID（owner CORE-17）。
    StudyDayInvalid,
    /// STUDY_INPUT_INVALID（owner CORE-19）。
    StudyInputInvalid,
    /// STUDY_K_OUT_OF_RANGE（owner CORE-19）。
    StudyKOutOfRange,
    /// STUDY_NO_CARDS（owner CORE-19）。
    StudyNoCards,
    /// STUDY_PARAMS_NO_PREVIOUS（owner CORE-17）。
    StudyParamsNoPrevious,
    /// STUDY_PARAMS_VERSION_STALE（owner CORE-17）。
    StudyParamsVersionStale,
    /// STUDY_PLAN_INVALID（owner CORE-19）。
    StudyPlanInvalid,
    /// STUDY_RETENTION_OUT_OF_RANGE（owner CORE-17）。
    StudyRetentionOutOfRange,
    /// STUDY_REVISION_NOT_VERIFIED（owner CORE-80）。
    StudyRevisionNotVerified,
    /// STUDY_SESSION_EXPIRED（owner CORE-19）。
    StudySessionExpired,
    /// STUDY_STATS_RANGE_INVALID（owner CORE-20）。
    StudyStatsRangeInvalid,
    /// SYNC_AAD_MISMATCH（owner CORE-26）。
    SyncAadMismatch,
    /// SYNC_BATCH_INVALID（owner CORE-78）。
    SyncBatchInvalid,
    /// SYNC_BATCH_UNKNOWN（owner CORE-78）。
    SyncBatchUnknown,
    /// SYNC_CHOICE_INVALID（owner CORE-26）。
    SyncChoiceInvalid,
    /// SYNC_CURSOR_INVALID（owner CORE-25）。
    SyncCursorInvalid,
    /// SYNC_DECRYPT_FAILED（owner CORE-26）。
    SyncDecryptFailed,
    /// SYNC_DISABLED（owner CORE-26）。
    SyncDisabled,
    /// SYNC_ENVELOPE_INVALID（owner CORE-25）。
    SyncEnvelopeInvalid,
    /// SYNC_EPOCH_STALE（owner CORE-25）。
    SyncEpochStale,
    /// SYNC_HASH_MISMATCH（owner CORE-25）。
    SyncHashMismatch,
    /// SYNC_KEY_MISSING（owner CORE-24）。
    SyncKeyMissing,
    /// SYNC_KEY_VERSION_REJECTED（owner CORE-25）。
    SyncKeyVersionRejected,
    /// SYNC_MERGE_CONFLICT（owner CORE-83）。
    SyncMergeConflict,
    /// SYNC_NOT_AVAILABLE（owner CORE-36）。
    SyncNotAvailable,
    /// SYNC_NOT_FOUND（owner CORE-25）。
    SyncNotFound,
    /// SYNC_PATH_INVALID（owner CORE-66）。
    SyncPathInvalid,
    /// SYNC_PAYLOAD_TOO_LARGE（owner CORE-25）。
    SyncPayloadTooLarge,
    /// SYNC_QUARANTINED（owner CORE-26）。
    SyncQuarantined,
    /// SYNC_QUOTA_EXCEEDED（owner CORE-25）。
    SyncQuotaExceeded,
    /// SYNC_SNAPSHOT_CORRUPT（owner CORE-66）。
    SyncSnapshotCorrupt,
    /// SYNC_SNAPSHOT_INCOMPLETE（owner CORE-25）。
    SyncSnapshotIncomplete,
    /// SYNC_UPGRADE_IN_PROGRESS（owner CORE-24）。
    SyncUpgradeInProgress,
    /// SYNC_UPGRADE_KEY_FAILED（owner CORE-24）。
    SyncUpgradeKeyFailed,
    /// SYNC_UPGRADE_NOT_ABANDONABLE（owner CORE-24）。
    SyncUpgradeNotAbandonable,
    /// SYNC_UPGRADE_STEP_INVALID（owner CORE-24）。
    SyncUpgradeStepInvalid,
    /// TYPESET_DEPTH_EXCEEDED（owner CORE-12）。
    TypesetDepthExceeded,
    /// TYPESET_MISSING_GLYPH（owner CORE-12）。
    TypesetMissingGlyph,
    /// TYPESET_NO_FONT（owner CORE-12）。
    TypesetNoFont,
    /// TYPE_AFFINE_MISUSE（owner CORE-09）。
    TypeAffineMisuse,
    /// TYPE_CROSS_DIM（owner CORE-09）。
    TypeCrossDim,
    /// TYPE_DIM_CONFLICT（owner CORE-09）。
    TypeDimConflict,
    /// TYPE_EMPIRICAL_COEFF（owner CORE-09）。
    TypeEmpiricalCoeff,
    /// TYPE_FUNC_ARG_DIMENSIONED（owner CORE-09）。
    TypeFuncArgDimensioned,
    /// TYPE_LOG_DIMENSIONED（owner CORE-09）。
    TypeLogDimensioned,
    /// TYPE_MATHKIND_MISMATCH（owner CORE-09）。
    TypeMathkindMismatch,
    /// TYPE_QK_MISMATCH（owner CORE-09）。
    TypeQkMismatch,
    /// TYPE_UNKNOWN_DIM（owner CORE-09）。
    TypeUnknownDim,
    /// UNIT_AFFINE_MISUSE（owner CORE-08）。
    UnitAffineMisuse,
    /// UNIT_CYCLE（owner CORE-08）。
    UnitCycle,
    /// UNIT_DIM_SYNTAX（owner CORE-08）。
    UnitDimSyntax,
    /// UNIT_DUPLICATE（owner CORE-08）。
    UnitDuplicate,
    /// UNIT_INCOMPATIBLE（owner CORE-08）。
    UnitIncompatible,
    /// UNIT_INVALID_OFFSET（owner CORE-08）。
    UnitInvalidOffset,
    /// UNIT_IN_USE（owner CORE-08）。
    UnitInUse,
    /// UNIT_OVERFLOW（owner CORE-08）。
    UnitOverflow,
    /// UNIT_UNKNOWN（owner CORE-08）。
    UnitUnknown,
}

#[rustfmt::skip]
impl ErrorCode {
    /// 注册表中该码的元数据；枚举声明顺序与 META 一致，故按判别值索引。
    fn meta(self) -> &'static Meta { &META[self as usize] }

    /// 全部已登记错误码，按注册表 `code` 升序。
    pub fn all() -> impl Iterator<Item = ErrorCode> { ALL.iter().copied() }

    /// 注册表 `code` 原文。
    pub fn as_str(self) -> &'static str { self.meta().code }

    /// 调度域：`code` 首段的小写形式。
    pub fn domain(self) -> &'static str { self.meta().domain }

    /// 注册表 `severity`。
    pub fn severity(self) -> Severity { self.meta().severity }

    /// 注册表 `retryable`。
    pub fn retryable(self) -> bool { self.meta().retryable }

    /// 简中消息键。
    pub fn message_key(self) -> &'static str { self.meta().message_key }

    /// 是否有修复建议消息 `message_key + ".fix"`。
    pub fn fix_hint(self) -> bool { self.meta().fix_hint }

    /// 注册表 `surface` 原文：`client`、`server` 或 `both`。
    pub fn surface(&self) -> &'static str { self.meta().surface }

    /// 该码是否可能由服务端输出（`server` 或 `both`）。
    pub fn is_server_output(self) -> bool { matches!(self.meta().surface, "server" | "both") }

    /// 服务端 HTTP 状态码：纯端侧码为 `None`，服务端码未声明时为 400。
    pub fn http_status(self) -> Option<u16> { self.meta().http_status }
}

#[rustfmt::skip]
impl fmt::Display for ErrorCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { f.write_str((*self).as_str()) }
}

#[rustfmt::skip]
impl FromStr for ErrorCode {
    type Err = UnknownErrorCode;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "AST_JSON_INVALID" => Ok(ErrorCode::AstJsonInvalid),
            "AUTH_EMAIL_CODE_EXPIRED" => Ok(ErrorCode::AuthEmailCodeExpired),
            "AUTH_EMAIL_CODE_INVALID" => Ok(ErrorCode::AuthEmailCodeInvalid),
            "AUTH_EMAIL_SEND_FAILED" => Ok(ErrorCode::AuthEmailSendFailed),
            "AUTH_EMAIL_TAKEN" => Ok(ErrorCode::AuthEmailTaken),
            "AUTH_GUEST_EXISTS" => Ok(ErrorCode::AuthGuestExists),
            "AUTH_INVALID_CREDENTIALS" => Ok(ErrorCode::AuthInvalidCredentials),
            "AUTH_LOCKED" => Ok(ErrorCode::AuthLocked),
            "AUTH_NO_PROFILE" => Ok(ErrorCode::AuthNoProfile),
            "AUTH_PASSWORD_WEAK" => Ok(ErrorCode::AuthPasswordWeak),
            "AUTH_PROFILE_EXISTS" => Ok(ErrorCode::AuthProfileExists),
            "AUTH_RATE_LIMITED" => Ok(ErrorCode::AuthRateLimited),
            "AUTH_REAUTH_REQUIRED" => Ok(ErrorCode::AuthReauthRequired),
            "AUTH_RECENT_LOGIN_REQUIRED" => Ok(ErrorCode::AuthRecentLoginRequired),
            "AUTH_REFRESH_REVOKED" => Ok(ErrorCode::AuthRefreshRevoked),
            "AUTH_SETTING_INVALID" => Ok(ErrorCode::AuthSettingInvalid),
            "AUTH_TOKEN_EXPIRED" => Ok(ErrorCode::AuthTokenExpired),
            "AUTH_TOKEN_INVALID" => Ok(ErrorCode::AuthTokenInvalid),
            "AUTH_UPLOAD_RECONFIRM_REQUIRED" => Ok(ErrorCode::AuthUploadReconfirmRequired),
            "BACKUP_CANCELLED" => Ok(ErrorCode::BackupCancelled),
            "BACKUP_CORRUPT" => Ok(ErrorCode::BackupCorrupt),
            "BACKUP_DISK_FULL" => Ok(ErrorCode::BackupDiskFull),
            "BACKUP_PROTECTION_UNAVAILABLE" => Ok(ErrorCode::BackupProtectionUnavailable),
            "BACKUP_REPLACE_BLOCKED_BY_SYNC" => Ok(ErrorCode::BackupReplaceBlockedBySync),
            "BACKUP_SCHEMA_TOO_NEW" => Ok(ErrorCode::BackupSchemaTooNew),
            "BACKUP_SCOPE_INVALID" => Ok(ErrorCode::BackupScopeInvalid),
            "BACKUP_TOKEN_UNKNOWN" => Ok(ErrorCode::BackupTokenUnknown),
            "BACKUP_WRONG_SECRET" => Ok(ErrorCode::BackupWrongSecret),
            "CLOUD_BUDGET_BREAKER" => Ok(ErrorCode::CloudBudgetBreaker),
            "CLOUD_CONSENT_INVALID" => Ok(ErrorCode::CloudConsentInvalid),
            "CLOUD_HASH_MISMATCH" => Ok(ErrorCode::CloudHashMismatch),
            "CLOUD_IDEMPOTENCY_CONFLICT" => Ok(ErrorCode::CloudIdempotencyConflict),
            "CLOUD_IMAGE_TOO_LARGE" => Ok(ErrorCode::CloudImageTooLarge),
            "CLOUD_JOB_NOT_FOUND" => Ok(ErrorCode::CloudJobNotFound),
            "CLOUD_NOT_ELIGIBLE" => Ok(ErrorCode::CloudNotEligible),
            "CLOUD_OUTPUT_REJECTED" => Ok(ErrorCode::CloudOutputRejected),
            "CLOUD_PREVIEW_STALE" => Ok(ErrorCode::CloudPreviewStale),
            "CLOUD_PROVIDER_ERROR" => Ok(ErrorCode::CloudProviderError),
            "CLOUD_PROVIDER_TIMEOUT" => Ok(ErrorCode::CloudProviderTimeout),
            "CLOUD_QUOTA_EXCEEDED" => Ok(ErrorCode::CloudQuotaExceeded),
            "CLOUD_TOKEN_EXPIRED" => Ok(ErrorCode::CloudTokenExpired),
            "CLOUD_UNKNOWN_OUTCOME" => Ok(ErrorCode::CloudUnknownOutcome),
            "CONTENT_DUPLICATE" => Ok(ErrorCode::ContentDuplicate),
            "CONTENT_FIELD_INVALID" => Ok(ErrorCode::ContentFieldInvalid),
            "CONTENT_FIELD_MISSING" => Ok(ErrorCode::ContentFieldMissing),
            "CONTENT_LICENSE_FORBIDDEN" => Ok(ErrorCode::ContentLicenseForbidden),
            "CONTENT_LICENSE_MISSING" => Ok(ErrorCode::ContentLicenseMissing),
            "CONTENT_NOT_VERIFIED" => Ok(ErrorCode::ContentNotVerified),
            "CONTENT_REVIEW_INVALID" => Ok(ErrorCode::ContentReviewInvalid),
            "CRYPTO_DECRYPT_FAILED" => Ok(ErrorCode::CryptoDecryptFailed),
            "CRYPTO_KDF_MEMORY" => Ok(ErrorCode::CryptoKdfMemory),
            "CRYPTO_KEY_VERSION_UNKNOWN" => Ok(ErrorCode::CryptoKeyVersionUnknown),
            "CRYPTO_PARAM_INVALID" => Ok(ErrorCode::CryptoParamInvalid),
            "CRYPTO_PASSPHRASE_WEAK" => Ok(ErrorCode::CryptoPassphraseWeak),
            "CRYPTO_RECOVERY_CODE_FORMAT" => Ok(ErrorCode::CryptoRecoveryCodeFormat),
            "CRYPTO_RNG_FAILED" => Ok(ErrorCode::CryptoRngFailed),
            "DERIVE_CROSS_KIND_UNCONFIRMED" => Ok(ErrorCode::DeriveCrossKindUnconfirmed),
            "DERIVE_CYCLE" => Ok(ErrorCode::DeriveCycle),
            "DERIVE_DEPTH_EXCEEDED" => Ok(ErrorCode::DeriveDepthExceeded),
            "DERIVE_NODE_LIMIT" => Ok(ErrorCode::DeriveNodeLimit),
            "DERIVE_NOT_VERIFIED" => Ok(ErrorCode::DeriveNotVerified),
            "DERIVE_READ_ONLY" => Ok(ErrorCode::DeriveReadOnly),
            "DERIVE_TYPE_MISMATCH" => Ok(ErrorCode::DeriveTypeMismatch),
            "ENGINE_DATA_CONFLICT" => Ok(ErrorCode::EngineDataConflict),
            "ENGINE_DATA_INVALID" => Ok(ErrorCode::EngineDataInvalid),
            "ENGINE_UNAVAILABLE" => Ok(ErrorCode::EngineUnavailable),
            "EVAL_DIV_ZERO" => Ok(ErrorCode::EvalDivZero),
            "EVAL_DOMAIN" => Ok(ErrorCode::EvalDomain),
            "EVAL_LIMIT_EXCEEDED" => Ok(ErrorCode::EvalLimitExceeded),
            "EVAL_MULTI_BRANCH" => Ok(ErrorCode::EvalMultiBranch),
            "EVAL_NAN_OR_INF" => Ok(ErrorCode::EvalNanOrInf),
            "EVAL_NEEDS_INTERVAL" => Ok(ErrorCode::EvalNeedsInterval),
            "EVAL_NOT_COMPUTABLE" => Ok(ErrorCode::EvalNotComputable),
            "EVAL_NO_CONVERGE" => Ok(ErrorCode::EvalNoConverge),
            "EVAL_OVERFLOW" => Ok(ErrorCode::EvalOverflow),
            "EVAL_TIMEOUT" => Ok(ErrorCode::EvalTimeout),
            "EXPORT_NOT_RENDERABLE" => Ok(ErrorCode::ExportNotRenderable),
            "EXPORT_TOO_LARGE" => Ok(ErrorCode::ExportTooLarge),
            "FFI_BAD_ARG" => Ok(ErrorCode::FfiBadArg),
            "FFI_BUSY" => Ok(ErrorCode::FfiBusy),
            "FFI_PANIC" => Ok(ErrorCode::FfiPanic),
            "FFI_STALE_HANDLE" => Ok(ErrorCode::FfiStaleHandle),
            "FFI_UNKNOWN_OP" => Ok(ErrorCode::FfiUnknownOp),
            "FFI_VERSION_MISMATCH" => Ok(ErrorCode::FfiVersionMismatch),
            "GRADE_PARSE_FAILED" => Ok(ErrorCode::GradeParseFailed),
            "GRADE_TIMEOUT" => Ok(ErrorCode::GradeTimeout),
            "GRADE_UNSUPPORTED" => Ok(ErrorCode::GradeUnsupported),
            "IMG_CANCELLED" => Ok(ErrorCode::ImgCancelled),
            "IMG_CORRUPT" => Ok(ErrorCode::ImgCorrupt),
            "IMG_CROP_INVALID" => Ok(ErrorCode::ImgCropInvalid),
            "IMG_FORMAT_UNSUPPORTED" => Ok(ErrorCode::ImgFormatUnsupported),
            "IMG_PATH_INVALID" => Ok(ErrorCode::ImgPathInvalid),
            "IMG_TOO_LARGE" => Ok(ErrorCode::ImgTooLarge),
            "IMG_TOO_MANY_PIXELS" => Ok(ErrorCode::ImgTooManyPixels),
            "IMG_UPLOAD_TOO_LARGE" => Ok(ErrorCode::ImgUploadTooLarge),
            "LIB_BATCH_CANCELLED" => Ok(ErrorCode::LibBatchCancelled),
            "LIB_BATCH_TOO_LARGE" => Ok(ErrorCode::LibBatchTooLarge),
            "LIB_DRAFT_INVALID" => Ok(ErrorCode::LibDraftInvalid),
            "LIB_IMPORT_ROW_INVALID" => Ok(ErrorCode::LibImportRowInvalid),
            "LIB_IMPORT_TOO_LARGE" => Ok(ErrorCode::LibImportTooLarge),
            "LIB_META_INVALID" => Ok(ErrorCode::LibMetaInvalid),
            "LIB_NOT_FOUND" => Ok(ErrorCode::LibNotFound),
            "LIB_NOT_VERIFIED" => Ok(ErrorCode::LibNotVerified),
            "LIB_READ_ONLY" => Ok(ErrorCode::LibReadOnly),
            "LIB_TAGS_LIMIT" => Ok(ErrorCode::LibTagsLimit),
            "LIB_TRASHED" => Ok(ErrorCode::LibTrashed),
            "NET_HOST_NOT_ALLOWED" => Ok(ErrorCode::NetHostNotAllowed),
            "NET_OFFLINE" => Ok(ErrorCode::NetOffline),
            "NET_TIMEOUT" => Ok(ErrorCode::NetTimeout),
            "NET_TLS" => Ok(ErrorCode::NetTls),
            "NOTATION_AMBIGUOUS" => Ok(ErrorCode::NotationAmbiguous),
            "NOTATION_CONSTANT_CONFLICT" => Ok(ErrorCode::NotationConstantConflict),
            "NOTATION_LOG_BASE" => Ok(ErrorCode::NotationLogBase),
            "NOTATION_UNBOUND" => Ok(ErrorCode::NotationUnbound),
            "PACK_DEP_MISSING" => Ok(ErrorCode::PackDepMissing),
            "PACK_DOWNGRADE" => Ok(ErrorCode::PackDowngrade),
            "PACK_DOWNLOAD_INCOMPLETE" => Ok(ErrorCode::PackDownloadIncomplete),
            "PACK_EPOCH_ROLLBACK" => Ok(ErrorCode::PackEpochRollback),
            "PACK_FORBIDDEN_ENTRY" => Ok(ErrorCode::PackForbiddenEntry),
            "PACK_HASH_MISMATCH" => Ok(ErrorCode::PackHashMismatch),
            "PACK_INCOMPATIBLE" => Ok(ErrorCode::PackIncompatible),
            "PACK_KEY_UNKNOWN" => Ok(ErrorCode::PackKeyUnknown),
            "PACK_LIMIT_EXCEEDED" => Ok(ErrorCode::PackLimitExceeded),
            "PACK_METADATA_EXPIRED" => Ok(ErrorCode::PackMetadataExpired),
            "PACK_SIG_INVALID" => Ok(ErrorCode::PackSigInvalid),
            "PACK_STORAGE_LOW" => Ok(ErrorCode::PackStorageLow),
            "PACK_UNSAFE_PATH" => Ok(ErrorCode::PackUnsafePath),
            "PARSE_FORBIDDEN_COMMAND" => Ok(ErrorCode::ParseForbiddenCommand),
            "PARSE_HOLE_UNFILLED" => Ok(ErrorCode::ParseHoleUnfilled),
            "PARSE_LIMIT_EXCEEDED" => Ok(ErrorCode::ParseLimitExceeded),
            "PARSE_SYNTAX" => Ok(ErrorCode::ParseSyntax),
            "PARSE_TIMEOUT" => Ok(ErrorCode::ParseTimeout),
            "PARSE_UNICODE_NOT_EXPORTABLE" => Ok(ErrorCode::ParseUnicodeNotExportable),
            "PARSE_UNSUPPORTED_COMMAND" => Ok(ErrorCode::ParseUnsupportedCommand),
            "PLATFORM_CANCELLED" => Ok(ErrorCode::PlatformCancelled),
            "PLATFORM_FILE_TOO_LARGE" => Ok(ErrorCode::PlatformFileTooLarge),
            "PLATFORM_FILE_TYPE_MISMATCH" => Ok(ErrorCode::PlatformFileTypeMismatch),
            "PLATFORM_IO" => Ok(ErrorCode::PlatformIo),
            "PLATFORM_KEY_UNAVAILABLE" => Ok(ErrorCode::PlatformKeyUnavailable),
            "PLATFORM_PERMISSION_DENIED" => Ok(ErrorCode::PlatformPermissionDenied),
            "PLATFORM_UNSUPPORTED" => Ok(ErrorCode::PlatformUnsupported),
            "PLATFORM_UPDATE_DISK_FULL" => Ok(ErrorCode::PlatformUpdateDiskFull),
            "PLATFORM_UPDATE_HASH_MISMATCH" => Ok(ErrorCode::PlatformUpdateHashMismatch),
            "PLATFORM_UPDATE_ROLLED_BACK" => Ok(ErrorCode::PlatformUpdateRolledBack),
            "PLATFORM_UPDATE_SIG_INVALID" => Ok(ErrorCode::PlatformUpdateSigInvalid),
            "PRIVACY_CONSENT_MISSING" => Ok(ErrorCode::PrivacyConsentMissing),
            "PRIVACY_DIAGNOSTICS_DISABLED" => Ok(ErrorCode::PrivacyDiagnosticsDisabled),
            "PRIVACY_REPRO_FAILED" => Ok(ErrorCode::PrivacyReproFailed),
            "PRIVACY_REQUEST_BLOCKED" => Ok(ErrorCode::PrivacyRequestBlocked),
            "RECOG_ACTIVE_TASK_EXISTS" => Ok(ErrorCode::RecogActiveTaskExists),
            "RECOG_ALL_CANDIDATES_INVALID" => Ok(ErrorCode::RecogAllCandidatesInvalid),
            "RECOG_BACKEND_NOT_ALLOWED" => Ok(ErrorCode::RecogBackendNotAllowed),
            "RECOG_BACKEND_REMOTE" => Ok(ErrorCode::RecogBackendRemote),
            "RECOG_BACKEND_UNAVAILABLE" => Ok(ErrorCode::RecogBackendUnavailable),
            "RECOG_CANCELLED" => Ok(ErrorCode::RecogCancelled),
            "RECOG_HISTORY_KEY_UNAVAILABLE" => Ok(ErrorCode::RecogHistoryKeyUnavailable),
            "RECOG_IMAGE_LOST" => Ok(ErrorCode::RecogImageLost),
            "RECOG_INPUT_INVALID" => Ok(ErrorCode::RecogInputInvalid),
            "RECOG_KEEP_LAST_OUT_OF_RANGE" => Ok(ErrorCode::RecogKeepLastOutOfRange),
            "RECOG_MODEL_INCOMPATIBLE" => Ok(ErrorCode::RecogModelIncompatible),
            "RECOG_MODEL_NOT_INSTALLED" => Ok(ErrorCode::RecogModelNotInstalled),
            "RECOG_MODEL_OOM" => Ok(ErrorCode::RecogModelOom),
            "RECOG_MODEL_TIMEOUT" => Ok(ErrorCode::RecogModelTimeout),
            "RECOG_NO_CANDIDATE" => Ok(ErrorCode::RecogNoCandidate),
            "RECOG_OUTPUT_REJECTED" => Ok(ErrorCode::RecogOutputRejected),
            "RECOG_OUTPUT_TOO_LARGE" => Ok(ErrorCode::RecogOutputTooLarge),
            "RECOG_QUOTA_EXCEEDED" => Ok(ErrorCode::RecogQuotaExceeded),
            "RECOG_SESSION_NOT_FOUND" => Ok(ErrorCode::RecogSessionNotFound),
            "RECOG_SPAN_INVALID" => Ok(ErrorCode::RecogSpanInvalid),
            "RECOG_TRANSITION_INVALID" => Ok(ErrorCode::RecogTransitionInvalid),
            "SERVER_CLIENT_TOO_OLD" => Ok(ErrorCode::ServerClientTooOld),
            "SERVER_UNAVAILABLE" => Ok(ErrorCode::ServerUnavailable),
            "STORE_BUSY" => Ok(ErrorCode::StoreBusy),
            "STORE_CORRUPT" => Ok(ErrorCode::StoreCorrupt),
            "STORE_DISK_FULL" => Ok(ErrorCode::StoreDiskFull),
            "STORE_KEY_INVALID" => Ok(ErrorCode::StoreKeyInvalid),
            "STORE_MIGRATION_FAILED" => Ok(ErrorCode::StoreMigrationFailed),
            "STORE_SCHEMA_TOO_NEW" => Ok(ErrorCode::StoreSchemaTooNew),
            "STUDY_BOOK_READ_ONLY" => Ok(ErrorCode::StudyBookReadOnly),
            "STUDY_CARD_NOT_FOUND" => Ok(ErrorCode::StudyCardNotFound),
            "STUDY_CARD_PENDING_CHOICE" => Ok(ErrorCode::StudyCardPendingChoice),
            "STUDY_DAY_INVALID" => Ok(ErrorCode::StudyDayInvalid),
            "STUDY_INPUT_INVALID" => Ok(ErrorCode::StudyInputInvalid),
            "STUDY_K_OUT_OF_RANGE" => Ok(ErrorCode::StudyKOutOfRange),
            "STUDY_NO_CARDS" => Ok(ErrorCode::StudyNoCards),
            "STUDY_PARAMS_NO_PREVIOUS" => Ok(ErrorCode::StudyParamsNoPrevious),
            "STUDY_PARAMS_VERSION_STALE" => Ok(ErrorCode::StudyParamsVersionStale),
            "STUDY_PLAN_INVALID" => Ok(ErrorCode::StudyPlanInvalid),
            "STUDY_RETENTION_OUT_OF_RANGE" => Ok(ErrorCode::StudyRetentionOutOfRange),
            "STUDY_REVISION_NOT_VERIFIED" => Ok(ErrorCode::StudyRevisionNotVerified),
            "STUDY_SESSION_EXPIRED" => Ok(ErrorCode::StudySessionExpired),
            "STUDY_STATS_RANGE_INVALID" => Ok(ErrorCode::StudyStatsRangeInvalid),
            "SYNC_AAD_MISMATCH" => Ok(ErrorCode::SyncAadMismatch),
            "SYNC_BATCH_INVALID" => Ok(ErrorCode::SyncBatchInvalid),
            "SYNC_BATCH_UNKNOWN" => Ok(ErrorCode::SyncBatchUnknown),
            "SYNC_CHOICE_INVALID" => Ok(ErrorCode::SyncChoiceInvalid),
            "SYNC_CURSOR_INVALID" => Ok(ErrorCode::SyncCursorInvalid),
            "SYNC_DECRYPT_FAILED" => Ok(ErrorCode::SyncDecryptFailed),
            "SYNC_DISABLED" => Ok(ErrorCode::SyncDisabled),
            "SYNC_ENVELOPE_INVALID" => Ok(ErrorCode::SyncEnvelopeInvalid),
            "SYNC_EPOCH_STALE" => Ok(ErrorCode::SyncEpochStale),
            "SYNC_HASH_MISMATCH" => Ok(ErrorCode::SyncHashMismatch),
            "SYNC_KEY_MISSING" => Ok(ErrorCode::SyncKeyMissing),
            "SYNC_KEY_VERSION_REJECTED" => Ok(ErrorCode::SyncKeyVersionRejected),
            "SYNC_MERGE_CONFLICT" => Ok(ErrorCode::SyncMergeConflict),
            "SYNC_NOT_AVAILABLE" => Ok(ErrorCode::SyncNotAvailable),
            "SYNC_NOT_FOUND" => Ok(ErrorCode::SyncNotFound),
            "SYNC_PATH_INVALID" => Ok(ErrorCode::SyncPathInvalid),
            "SYNC_PAYLOAD_TOO_LARGE" => Ok(ErrorCode::SyncPayloadTooLarge),
            "SYNC_QUARANTINED" => Ok(ErrorCode::SyncQuarantined),
            "SYNC_QUOTA_EXCEEDED" => Ok(ErrorCode::SyncQuotaExceeded),
            "SYNC_SNAPSHOT_CORRUPT" => Ok(ErrorCode::SyncSnapshotCorrupt),
            "SYNC_SNAPSHOT_INCOMPLETE" => Ok(ErrorCode::SyncSnapshotIncomplete),
            "SYNC_UPGRADE_IN_PROGRESS" => Ok(ErrorCode::SyncUpgradeInProgress),
            "SYNC_UPGRADE_KEY_FAILED" => Ok(ErrorCode::SyncUpgradeKeyFailed),
            "SYNC_UPGRADE_NOT_ABANDONABLE" => Ok(ErrorCode::SyncUpgradeNotAbandonable),
            "SYNC_UPGRADE_STEP_INVALID" => Ok(ErrorCode::SyncUpgradeStepInvalid),
            "TYPESET_DEPTH_EXCEEDED" => Ok(ErrorCode::TypesetDepthExceeded),
            "TYPESET_MISSING_GLYPH" => Ok(ErrorCode::TypesetMissingGlyph),
            "TYPESET_NO_FONT" => Ok(ErrorCode::TypesetNoFont),
            "TYPE_AFFINE_MISUSE" => Ok(ErrorCode::TypeAffineMisuse),
            "TYPE_CROSS_DIM" => Ok(ErrorCode::TypeCrossDim),
            "TYPE_DIM_CONFLICT" => Ok(ErrorCode::TypeDimConflict),
            "TYPE_EMPIRICAL_COEFF" => Ok(ErrorCode::TypeEmpiricalCoeff),
            "TYPE_FUNC_ARG_DIMENSIONED" => Ok(ErrorCode::TypeFuncArgDimensioned),
            "TYPE_LOG_DIMENSIONED" => Ok(ErrorCode::TypeLogDimensioned),
            "TYPE_MATHKIND_MISMATCH" => Ok(ErrorCode::TypeMathkindMismatch),
            "TYPE_QK_MISMATCH" => Ok(ErrorCode::TypeQkMismatch),
            "TYPE_UNKNOWN_DIM" => Ok(ErrorCode::TypeUnknownDim),
            "UNIT_AFFINE_MISUSE" => Ok(ErrorCode::UnitAffineMisuse),
            "UNIT_CYCLE" => Ok(ErrorCode::UnitCycle),
            "UNIT_DIM_SYNTAX" => Ok(ErrorCode::UnitDimSyntax),
            "UNIT_DUPLICATE" => Ok(ErrorCode::UnitDuplicate),
            "UNIT_INCOMPATIBLE" => Ok(ErrorCode::UnitIncompatible),
            "UNIT_INVALID_OFFSET" => Ok(ErrorCode::UnitInvalidOffset),
            "UNIT_IN_USE" => Ok(ErrorCode::UnitInUse),
            "UNIT_OVERFLOW" => Ok(ErrorCode::UnitOverflow),
            "UNIT_UNKNOWN" => Ok(ErrorCode::UnitUnknown),
            _ => Err(UnknownErrorCode),
        }
    }
}

#[rustfmt::skip]
impl TryFrom<&str> for ErrorCode {
    type Error = UnknownErrorCode;

    fn try_from(value: &str) -> Result<Self, Self::Error> { value.parse() }
}

#[rustfmt::skip]
impl Serialize for ErrorCode {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(self.as_str())
    }
}

#[rustfmt::skip]
impl<'de> Deserialize<'de> for ErrorCode {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        String::deserialize(deserializer)?.parse::<ErrorCode>().map_err(serde::de::Error::custom)
    }
}
