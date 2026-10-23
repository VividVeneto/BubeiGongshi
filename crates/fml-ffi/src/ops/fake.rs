// Debug/test fixtures only, never business implementations and no handle-producing op.
use super::*;
use fml_error::ErrorCode;
use serde_json::{Value, json};
struct Fake;
impl OpHandler for Fake {
    fn call(&self, ctx: &OpCtx<'_>, body: &[u8]) -> OpReply {
        let body: Value = serde_json::from_slice(body).expect("runtime JSON");
        #[cfg(test)]
        crate::jobs::tests::gate(ctx, &body);
        match ctx.op {
            "fake.panic" | "fake.async_panic" => panic!("injected static panic"),
            "fake.error" | "fake.async_error" => {
                return OpReply::Err(FmlError::new(ErrorCode::EvalTimeout));
            }
            "fake.traced" | "fake.async_traced" => {
                return OpReply::Err(
                    FmlError::new(ErrorCode::EvalTimeout).with_trace(TraceId([7; 16])),
                );
            }
            "fake.invalid" | "fake.async_invalid" => return OpReply::Ok(b"invalid JSON".to_vec()),
            _ => (),
        }
        if ctx.op == "fake.wait" {
            let deadline = std::time::Instant::now()
                + std::time::Duration::from_millis(
                    body["wait_ms"].as_u64().unwrap_or(1000).min(5000),
                );
            while !ctx.cancel.is_cancelled() && std::time::Instant::now() < deadline {
                std::thread::park_timeout(std::time::Duration::from_millis(1));
            }
        }
        if BUDGET_OPS.contains(&ctx.op) && ctx.budget_ms.is_some_and(|budget| budget < 2) {
            // This test-only handler really exceeds its budget; production domains own clocks.
            let start = std::time::Instant::now();
            std::thread::sleep(std::time::Duration::from_millis(2));
            assert!(start.elapsed().as_millis() > u128::from(ctx.budget_ms.unwrap()));
            return OpReply::Err(FmlError::new(ErrorCode::EvalTimeout));
        }
        OpReply::Ok(
            serde_json::to_vec(&json!({"echo":body,"dto":ctx.dto,"budget_ms":ctx.budget_ms}))
                .unwrap(),
        )
    }
}
static HANDLER: Fake = Fake;
macro_rules! entries { ($($name:literal => $mode:ident / $scope:ident),* $(,)?) => { &[$(OpEntry { op:$name, mode:OpMode::$mode, scope:Scope::$scope, handler:&HANDLER }),*] }; }
pub(super) const ENTRIES: &[OpEntry] = entries![
    "fake.echo" => Sync / None, "fake.error" => Sync / None, "fake.traced" => Sync / None,
    "fake.panic" => Sync / None, "fake.invalid" => Sync / None, "fake.profile" => Sync / Profile,
    "fake.async" => Submit / Device, "fake.wait" => Submit / Device,
    "fake.async_error" => Submit / None, "fake.async_traced" => Submit / None,
    "fake.async_panic" => Submit / None, "fake.async_invalid" => Submit / None,
    "fake.async_profile" => Submit / Profile,
    "engine.parse" => Sync / None, "calc.evaluate" => Sync / None, "grade.answer" => Sync / None,
];
