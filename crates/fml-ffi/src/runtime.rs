use crate::{ABI_MAJOR, ABI_MINOR, DTO_MAJOR, actor, ops::*, trace};
use fml_error::{ErrorCode, FmlError, TraceId};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
pub(crate) type Failure = (i32, FmlError);
pub(crate) fn failure(status: i32) -> Failure {
    let code = match status {
        -1 => ErrorCode::FfiBadArg,
        -2 => ErrorCode::FfiUnknownOp,
        -3 => ErrorCode::FfiVersionMismatch,
        -4 => ErrorCode::FfiStaleHandle,
        -6 => ErrorCode::FfiBusy,
        _ => ErrorCode::FfiPanic,
    };
    (status, FmlError::new(code))
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Envelope {
    v: u32,
    trace_id: TraceId,
    body: serde_json::Map<String, Value>,
    #[serde(default)]
    budget_ms: Option<u32>,
    #[serde(default)]
    profile_handle: Option<String>,
    #[serde(default)]
    expected_generation: Option<String>,
}
fn decimal(text: &str) -> Option<u64> {
    if text.is_empty() || !text.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    text.parse().ok()
}
pub(crate) fn parse(bytes: &[u8], trace: &mut Option<TraceId>) -> Result<Envelope, Failure> {
    // Recover a valid supplied trace even when another envelope field is malformed.
    let value: Value = serde_json::from_slice(bytes).map_err(|_| failure(-1))?;
    *trace = value
        .get("trace_id")
        .and_then(|v| serde_json::from_value::<TraceId>(v.clone()).ok())
        .filter(|id| !id.is_zero());
    let env: Envelope = serde_json::from_value(value).map_err(|_| failure(-1))?;
    if env.trace_id.is_zero()
        || env
            .profile_handle
            .as_deref()
            .is_some_and(|s| decimal(s).is_none())
        || env
            .expected_generation
            .as_deref()
            .is_some_and(|s| decimal(s).is_none())
    {
        return Err(failure(-1));
    }
    Ok(env)
}
pub(crate) fn dispatch(op: &str, env: Envelope) -> Result<Value, Failure> {
    if cfg!(debug_assertions) {
        assert_unique();
    }
    let entry = OPS
        .iter()
        .find(|e| e.op == op && e.mode == OpMode::Sync)
        .ok_or_else(|| failure(-2))?;
    let handle = env.profile_handle.as_deref().and_then(decimal);
    let actor = match (entry.scope, handle) {
        (Scope::Profile, Some(h)) => actor::lookup(h).ok_or_else(|| failure(-4))?,
        (Scope::Profile, None) => return Err((1, FmlError::new(ErrorCode::AuthNoProfile))),
        (_, Some(_)) => return Err(failure(-1)),
        (_, None) => std::sync::Arc::new(HandleActor::new(0, None)),
    };
    let _lease = actor.lease().ok_or_else(|| failure(-4))?;
    if let Some(id) = env.body.get("profile_id")
        && entry.scope == Scope::Profile
        && id.as_str() != actor.profile.as_deref()
    {
        return Err(failure(-1));
    }
    if let (Some(h), Some(body_handle)) = (handle, env.body.get("handle"))
        && body_handle.as_str().and_then(decimal) != Some(h)
    {
        return Err(failure(-1));
    }
    if env.v != DTO_MAJOR {
        return Err(failure(-3));
    }
    let ctx = OpCtx {
        op: entry.op,
        dto: DTO_MAJOR,
        mode: entry.mode,
        scope: entry.scope,
        handle,
        actor: &actor,
        cancel: &CancelHandle::default(),
        trace_id: env.trace_id,
        budget_ms: if BUDGET_OPS.contains(&entry.op) {
            env.budget_ms
        } else {
            None
        },
    };
    match entry.handler.call(
        &ctx,
        &serde_json::to_vec(&env.body).map_err(|_| failure(-5))?,
    ) {
        OpReply::Ok(bytes) => serde_json::from_slice(&bytes).map_err(|_| failure(-5)),
        OpReply::Err(error) => Err((1, error)),
    }
}
#[derive(Serialize)]
struct ErrorEnvelope {
    v: u32,
    trace_id: TraceId,
    error: FmlError,
}
pub(crate) fn response(result: Result<Value, Failure>, trace_id: TraceId) -> (i32, Vec<u8>) {
    match result {
        Ok(ok) => (
            0,
            serde_json::to_vec(
                &json!({"v":DTO_MAJOR,"trace_id":trace_id,"ok":ok,"diagnostics":[]}),
            )
            .expect("JSON value"),
        ),
        Err((status, error)) => {
            let error = error.with_trace(trace_id);
            let envelope = ErrorEnvelope {
                v: DTO_MAJOR,
                trace_id: error.trace_id,
                error,
            };
            (
                status,
                serde_json::to_vec(&envelope).expect("valid error metadata"),
            )
        }
    }
}
pub(crate) fn fallback_trace(trace_id: Option<TraceId>) -> TraceId {
    trace_id.unwrap_or_else(trace::fresh)
}
pub(crate) fn capabilities() -> Vec<u8> {
    if cfg!(debug_assertions) {
        assert_unique();
    }
    let ops: Vec<_> = OPS.iter().map(|e| json!({"op":e.op,"dto":DTO_MAJOR,"mode":if e.mode == OpMode::Sync {"call"} else {"submit"},"budget":BUDGET_OPS.contains(&e.op)})).collect();
    serde_json::to_vec(&json!({"abi":format!("{ABI_MAJOR}.{ABI_MINOR}"),"ops":ops,"build":{"app":env!("CARGO_PKG_VERSION"),"git":env!("FML_GIT"),"target":env!("FML_TARGET"),"test_build":cfg!(any(test, feature="test_ops", feature="abi_major_bump"))}})).expect("capabilities JSON")
}
