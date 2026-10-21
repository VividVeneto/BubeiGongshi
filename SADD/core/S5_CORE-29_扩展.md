### CORE-29 识别契约与后端注册

**目标**：定义与具体模型无关的识别输入、输出与后端能力契约，使本地模型、云端 LLM 与实验后端可插拔替换。

**范围**
- 包含：`Recognizer` trait、输入/上下文/输出类型、后端能力声明、后端注册表与选择规则（本地后端与远程后端描述符）、两种识别模式、墨迹规范表示与规范渲染、`recog.backends` 与 `recog.run` op。
- 不包含：具体后端实现（CORE-34 云端、CORE-35 本地、附录 B 的 YOLO 实验分支）；图片预处理（CORE-30）；后处理（CORE-31）；会话持久化（CORE-32）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05

**接口契约**

```rust
// crates/fml-recognize/src/lib.rs
pub enum InputKind { Ink, Image }
pub enum AccountKind { Guest, Registered }
pub struct RecogImage { pub png: Vec<u8>, pub width: u32, pub height: u32, pub sha256: [u8; 32] }   // 来自 CORE-30 img.prepare 写入暂存区的 PNG
pub enum RecognizerInput { Ink(InkStrokes), Image(RecogImage) }
pub struct InkStrokes { pub strokes: Vec<Vec<InkPoint>>, pub width: f32, pub height: f32 }   // 画布逻辑像素；≤ 500 笔、≤ 20000 点
pub struct InkPoint { pub x: f32, pub y: f32, pub t_ms: u32, pub pressure: Option<f32> /* 0..=1 */ }
#[derive(Serialize, Deserialize)] #[serde(rename_all="snake_case")]
pub enum RecognitionMode { Lookup /* 查找：可按上下文重排、给出提示 */, Answer /* 作答：忠实转写 */ } // 唯一契约定义；线上值 lookup/answer 见 CORE-02 recognition-mode.json
pub struct CorrectionHint { pub wrong: String, pub right: String }   // 用户近期校正过的 LaTeX 片段，最多 20 条
pub struct RecognitionContext { pub mode: RecognitionMode, pub symbol_hints: Vec<String> /* ≤ 50 */, pub subject: Option<String>,
                                pub expected_kind: Option<MathKind> /* CORE-05 */, pub user_corrections: Vec<CorrectionHint> }
pub struct AlignSpan { pub latex_range: (u32, u32), pub region: Option<[f32; 4]> /* 归一化 x, y, w, h */ }
pub struct RawCandidate { pub latex: String, pub confidence: Option<f32> /* 无可靠置信度时为 None */, pub align: Vec<AlignSpan> }
pub struct RawOutput { pub candidates: Vec<RawCandidate>, pub backend_id: String, pub model_version: String, pub diagnostics: Vec<Diagnostic> }
pub struct BackendCaps { pub id: String, pub input_kinds: Vec<InputKind>, pub networked: bool, pub faithful_transcription: bool,
                         pub recommended_pixels: u32, pub memory_budget_mb: u32, pub model_version: String }
pub trait Recognizer: Send + Sync {
    fn caps(&self) -> &BackendCaps;
    fn recognize(&self, input: &RecognizerInput, ctx: &RecognitionContext, cancel: &CancelFlag) -> Result<RawOutput, FmlError>;
}
pub struct Registry { /* 本地后端 + 远程描述符 */ }
impl Registry {
    pub fn register(&mut self, r: Box<dyn Recognizer>);           // 本地后端（CORE-35）；同 id 重复注册替换旧的
    pub fn register_remote(&mut self, caps: BackendCaps);          // 远程后端只登记描述符（networked = true），实际调用在 app 层 CORE-34
    pub fn available(&self, account: AccountKind) -> Vec<BackendCaps>;   // 游客永远不含 networked 后端；按 id 字典序
    pub fn run(&self, id: &str, account: AccountKind, input: &RecognizerInput, ctx: &RecognitionContext, cancel: &CancelFlag) -> Result<RawOutput, FmlError>;
}
pub fn render_ink(ink: &InkStrokes, long_edge_px: u32 /* 256..=2048 */) -> Result<RecogImage, FmlError>;
```

- 墨迹规范渲染：按包围盒缩放到长边 `long_edge_px`，四周留 5% 白边；笔宽 `max(2, long_edge_px / 200)` 像素，圆头圆角，忽略压力；白底黑字 8 位灰度；用 tiny-skia 软件光栅化、png crate 编码（压缩级别固定），使两端像素逐字节一致。
- `run` 的检查顺序：id 不存在 → `RECOG_BACKEND_UNAVAILABLE`；networked 且游客 → `RECOG_BACKEND_NOT_ALLOWED`；networked（注册用户）→ `RECOG_BACKEND_REMOTE`（调用方改走 CORE-34）；输入类型不在 `input_kinds` 且为墨迹 → 先 `render_ink` 再识别；其余调用后端。后端返回空候选 → `RECOG_NO_CANDIDATE`。
- FFI op：`recog.backends`（同步）`{ account }` → `{ backends: BackendCaps[] }`；`recog.register_remote`（同步）`{ caps }` → `{}`（CORE-34 在注册用户解锁后调用）；`recog.run`（长任务）`{ backend_id, account, input: { ink } | { image_path }, context }` → `RawOutput`（`image_path` 须位于 `StoreArea.staging`，由 CORE-30 产出）。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `RECOG_BACKEND_UNAVAILABLE` | error | 否 | 后端 id 未注册，或本地模型未加载成功 |
| `RECOG_BACKEND_NOT_ALLOWED` | error | 否 | 游客请求 networked 后端 |
| `RECOG_BACKEND_REMOTE` | info | 否 | 注册用户经 `recog.run` 请求远程后端（应改走 CORE-34） |
| `RECOG_INPUT_INVALID` | error | 否 | 墨迹为空、超过笔数或点数上限、坐标非有限值；图片路径不在暂存区或不是 PNG |
| `RECOG_CANCELLED` | info | 否 | `CancelFlag` 置位 |
| `RECOG_NO_CANDIDATE` | warning | 是 | 后端返回零个候选 |

**实现约束**
- 作答模式下后端只做逐字转写：不重排、不自动纠错、不补全、不选“最可能的标准式”；查找模式下才允许上下文重排与建议，且建议须用户确认。
- 本地识别低置信度、失败或内存不足时，不得自动切换到云端；本地模式不初始化任何远程 SDK 或遥测。
- 没有安装本地模型时，游客的识别入口显示“不可用”，只提供编辑器与手工输入，不给假结果。
- `yolo-experiment` 只存在于实验分支，主线代码中不得出现其注册调用（附录 B）。
- 外部前提：tiny-skia、png（版本按 ADR-V5-15 锁入 `Cargo.lock`；渲染一致性测试在两端 CI 运行）。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-29_TEST.md](../Test/core/S5_CORE-29_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约435行；主包crates/fml-recognize/src/{lib,registry,ink,validate}.rs 360行，附属crates/fml-ffi/src/ops/recognize.rs三op及staging读取75行；无分阶段；schema/向量、自测和具体后端不计。 单阶段可独立构建测试；只计本卡实现及本卡编写的附属接入，不计数据/生成物/自测。

