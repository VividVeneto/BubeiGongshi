// Debug/test fixtures only, never business implementations and no handle-producing op.
use super::*;
use fml_error::ErrorCode;
use serde_json::{Value, json};
struct Fake;
impl OpHandler for Fake {
    fn call(&self, ctx: &OpCtx<'_>, body: &[u8]) -> OpReply {
        let body: Value = serde_json::from_slice(body).expect("runtime JSON");
        match ctx.op {
            "fake.panic" => panic!("injected static panic"),
            "fake.error" => return OpReply::Err(FmlError::new(ErrorCode::EvalTimeout)),
            "fake.traced" => {
                return OpReply::Err(
                    FmlError::new(ErrorCode::EvalTimeout).with_trace(TraceId([7; 16])),
                );
            }
            "fake.invalid" => return OpReply::Ok(b"invalid JSON".to_vec()),
            _ => (),
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
macro_rules! entries { ($($name:literal => $scope:ident),* $(,)?) => { &[$(OpEntry { op:$name, mode:OpMode::Sync, scope:Scope::$scope, handler:&HANDLER }),*] }; }
pub(super) const ENTRIES: &[OpEntry] = entries![
    "fake.echo" => None, "fake.error" => None, "fake.traced" => None,
    "fake.panic" => None, "fake.invalid" => None, "fake.profile" => Profile,
    "engine.parse" => None, "calc.evaluate" => None, "grade.answer" => None,
];
