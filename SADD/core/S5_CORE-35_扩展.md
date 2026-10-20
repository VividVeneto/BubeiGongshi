### CORE-35 本地识别模型后端

**目标**：以可选模型包的形式提供离线手写与照片公式识别，主安装包不含模型权重。

**范围**
- 包含：模型包内容约定（在 CORE-15 包格式内用 `Model` 与 `Metadata` 条目承载）、推理运行时的内部抽象 `InferenceEngine` 与测试替身 `FakeEngine`、预处理与贪心/束搜索解码、`LocalModel` 后端（实现 CORE-29 `Recognizer`）、懒加载与内存释放、模型包安装后的注册与卸载时注销、FFI op。
- 不包含：真实推理运行时（ort 或 mnn）的绑定实现——ADR-V5-13 定案后作为本卡的 cargo feature 追加，不阻塞本卡编码完成；模型训练、导出与数据集（附录 B、附录 C）；YOLO 检测器（只在实验分支）；模型包的下载与安装入口（CORE-51，经 CORE-15 安装）。

**依赖**：CORE-01、CORE-02、CORE-15、CORE-29

**接口契约**

模型包约定（不改 CORE-15 `Manifest`，未知字段仍拒绝）：`pack_id` 以 `model-` 开头；条目 `model/model.json`（`type = metadata`，`logical_id = "model-config"`）+ 一个或多个 `type = model` 的权重条目（每个 ≤ 128 MiB，不申请 CORE-15 的限额例外）+ `model/vocab.txt`（`type = lexicon`，一行一个 LaTeX 记号）。`model.json`：

```json
{ "model_family": "hmer-encoder-decoder", "runtime": "onnxruntime" | "mnn" | "fake", "runtime_min_version": "1.17.0", "opset": 17,
  "files": { "encoder": "model/encoder.onnx", "decoder": "model/decoder.onnx" },
  "input": { "channels": 1, "long_edge": 512, "max_short_edge": 256, "normalize": { "mean": 0.5, "std": 0.5 }, "invert": true },
  "decode": { "max_tokens": 200, "beam_width": 3, "bos": 1, "eos": 2, "pad": 0 },
  "vocab_version": "v1", "model_version": "local-light-1.0.0",
  "model_license": "Apache-2.0", "weights_license": "Apache-2.0", "training_data_refs": ["CROHME-2019", "HME100K"],
  "memory_budget_mb": 300, "benchmark": { "device": "ref-android-mid", "p95_ms": 1500, "peak_mb": 260, "exp_rate": 0.52 } }
```

```rust
// crates/fml-recognize-local/src/engine.rs —— 运行时抽象（具体实现由 cargo feature 选择：ort 或 mnn，M0 只保留一个，见 ADR-V5-13（待定））
pub struct InputSpec { pub channels: u8 /* 固定1 */, pub long_edge: u32 /* 1..=4096 */,
    pub max_short_edge: u32 /* 1..=long_edge */, pub normalize: NormalizeSpec, pub invert: bool }
pub struct NormalizeSpec { pub mean: f32 /* 有限，0..=1 */, pub std: f32 /* 有限，>0 */ }
pub struct Tensor { pub shape: Vec<i64>, pub data: TensorData }
pub enum TensorData { F32(Vec<f32>), I64(Vec<i64>) }
pub trait InferenceEngine: Send {
    fn load(files: &[(String /* 角色 encoder|decoder */, PathBuf)], threads: u32) -> Result<Self, FmlError> where Self: Sized;
    fn run(&mut self, role: &str, inputs: &[(&str, Tensor)]) -> Result<Vec<Tensor>, FmlError>;
}
pub struct FakeEngine { /* 测试替身：按输入哈希返回预置 token 序列，可注入延迟与 OOM */ }

// crates/fml-recognize-local/src/lib.rs
pub struct ModelConfig { /* 与 model.json 一一对应；serde deny_unknown_fields */ }
pub struct LocalModel { /* caps、config、vocab、Option<Box<dyn InferenceEngine>>（懒加载）、last_used_ms */ }
impl LocalModel {
    pub fn from_pack(pack: &InstalledPack) -> Result<LocalModel, FmlError>;  // 只读 model.json 与 vocab.txt 并校验；不加载权重
    pub fn ensure_loaded(&mut self) -> Result<(), FmlError>;                // 首次识别时调用
    pub fn unload(&mut self);                                               // 释放引擎与张量缓冲
    pub fn is_loaded(&self) -> bool;
}
impl Recognizer for LocalModel { /* caps: id = "local:" + pack_id, input_kinds = [Image]（墨迹由 Registry 先 render_ink），
                                    networked = false, faithful_transcription = true, recommended_pixels, memory_budget_mb, model_version */ }
pub fn preprocess(img: &RecogImage, cfg: &InputSpec) -> Result<Tensor, FmlError>;   // 灰度、按长边缩放（不放大超过 2 倍）、反色、归一化、补边
pub fn decode_tokens(ids: &[i64], vocab: &[String]) -> Result<String, FmlError>;   // 记号以空格连接，再交 CORE-31 规范化
```

- InputSpec 与 model.json.input 逐字段同名；不另引 height/max_width 第二套字段。预处理先等比例缩放使长边≤long_edge、短边≤max_short_edge且放大≤2倍，尺寸向下取整且最少1；灰度值除255，invert时用1-v，然后(v-mean)/std。补白至长边long_edge、短边max_short_edge的画布（横图H=max_short_edge/W=long_edge，竖图相反），左上对齐，白色同样归一化，Tensor形状[1,1,H,W]，F32行优先。非法配置在from_pack报RECOG_MODEL_INCOMPATIBLE；夹具包含横/竖/单像素与std=0拒绝。
- 识别流程：`preprocess` → encoder 一次 → decoder 逐步束搜索（`beam_width` 条，`max_tokens` 上限，每步检查 `CancelFlag`）→ 每条束得到 `RawCandidate { latex, confidence: Some(exp(平均对数概率)), align: [] }`，按置信度降序。
- FFI op：`recog.local.register`（同步）`{ pack_id }` → `BackendCaps`（`from_pack` 后调 CORE-29 `Registry::register`；同 id 重复注册替换）；`recog.local.unregister` `{ pack_id }` → `{}`（`pack.uninstall` 前由调用方先调）；`recog.local.unload_all`（同步）`{}` → `{ freed: u32 }`。识别本身走 CORE-29 `recog.run`。启动时由组装层对 `pack.list` 中 `model-` 开头的包逐个调 `register`。
- 卸载联动：首次执行 `recog.local.register` 时向 CORE-15 `add_uninstall_hook` 登记一次钩子：卸载 `model-` 开头的包前先 `unload` 并从 CORE-29 注册表移除对应后端（Windows 上释放文件句柄，保证目录可删）；资源包管理页（CORE-51）因此无需依赖本卡。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `RECOG_MODEL_NOT_INSTALLED` | error | 否 | `pack_id` 未安装，或包内缺 `model.json`、权重或词表条目 |
| `RECOG_MODEL_INCOMPATIBLE` | error | 否 | `runtime` 与本构建的运行时不同（`fake` 只被启用 `fake-engine` feature 的测试构建接受，发布构建一律拒绝）、`runtime_min_version` 高于内置版本、`opset` 不支持、词表行数与解码器输出维度不符或 `model.json` 有未知字段 |
| `RECOG_MODEL_OOM` | error | 是 | 加载或推理时分配失败，或驻留内存超过 `memory_budget_mb` 的 1.2 倍（加载后检查）；随即卸载 |
| `RECOG_MODEL_TIMEOUT` | warning | 是 | 单次识别超过 10 s（解码循环内检查，已产生的束丢弃） |

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `RECOG_CANCELLED` | CORE-29 | 识别中 `CancelFlag` 置位（复用 CORE-29） |

产品约束追踪：见README §6 Q37；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 模型包只含权重、配置与词表，禁止自定义算子库与可执行文件（CORE-15 规则）；推理运行时随应用发布，静态链接或随包分发的动态库版本写在 `THIRD_PARTY_NOTICES`（CORE-42）。
- 首次识别时懒加载；组装层订阅 CORE-04 `AppLifecycle.events()`，收到 `paused` 超过 30 s 或 `lowMemory` 时调用 `recog.local.unload_all`。
- 推理线程数 = min(4, 逻辑核数 / 2)，在 CORE-03 长任务线程上执行，不阻塞 FFI 同步调用。
- 模型与训练数据许可逐项登记（附录 C），`model_license`、`weights_license` 或 `training_data_refs` 为空的包拒绝注册（`RECOG_MODEL_INCOMPATIBLE`）。
- 本地后端不联网、不初始化遥测；运行时的遥测或在线功能须在构建配置中关闭。
- 性能按 CORE-01 预算表“本地模型识别”“本地模型首次加载”两行验收；`benchmark` 字段只作说明，以本卡验收的实测为准。
- 外部前提：运行时二选一（ONNX Runtime 的 Rust 绑定 `ort`，或 MNN 的 C API 自写绑定）及其版本，M0 定案（ADR-V5-13（待定））；可用的公开模型与许可见附录 B、附录 C；在模型就绪前，本卡全部单测与集成测试用 `FakeEngine` 与 `tests/fixtures/model-fake/` 假模型包完成。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-35_TEST.md](../Test/core/S5_CORE-35_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 420 行；`crates/fml-recognize-local/`（不含测试夹具）。

---

