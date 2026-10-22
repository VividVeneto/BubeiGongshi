# CORE-40 测试方案

> 来源卡：[S5_CORE-40_界面.md](../../core/S5_CORE-40_界面.md)（识别流程编排、手写画布与图片预处理界面）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

- [R24][R26] RecognitionFlow以source而非裸core/固定account构造，start从捕获session读取账户策略，null不发profile op/上传；A整批多图在切换后不得next/retry到B，同profile新handle亦不复用。
- [R24][R31][R40] probe/prepare/ensure/推理/云submit/watch逐个Completer暂停，A关闭立即失效新入口、beforeClose取消await全部旧任务，迟到结果只清理不发布候选/不向B transition；native close晚于暂存清理。云未知不重提，取消失败传close，dispose不代替drain。
- [R19][R35] 模型startup40进程一次；档案50在A/B各一次且ensure先于同handle的recog.recover。paused30s/lowMemory卸载订阅不重复，离页重建不泄漏watch/任务/回调/暂存。
- [R06] 流程测试（Fake 核心与 Fake 端口）：`startInk` → `ChoosingBackend` → `run(local)` → `CandidatesReady`；会话转换序列为 Imported → Preview → Running → Succeeded。
- [R31] `startImages` 3 张：逐张进入 `Cropping`，生成 3 个会话；第 2 张解码失败时跳过并在结束时汇总。
- [R32] 修改增强选项后 `previewPath` 更新；在 `CloudPreviewing` 调用 `backToCrop` 后必须重新预览确认，旧 `ConsentToken` 未被使用。
- [R33] `keep_last = 5` 时导入 8 张 `needsKeepLastWarning` 为 true；`keep_last = 0` 时为 false。
- [R40] 注册用户云端路径（Fake `CloudRecognitionService`）：无同意 → `CloudConsentNeeded` → 同意 → `CloudPreviewing` → 确认 → `Running` → `CandidatesReady`；`cancel()` 后会话为 Cancelled；`CloudUnknown` 不触发重提。
- [R26] 游客：`ChoosingBackend.backends` 不含 networked 后端，且未调用任何 `CloudRecognitionService` 方法。
- [R04][R04.e] 手写作答：识别返回 `m v^2` 时编辑器显示原样转写；未点“确认作答”前不调用 `AnswerSink`；确认后提交 `answer_mode = handwriting`。
- [R31][R32] 请求与结果形状（Fake CoreBinding）：img.probe/prepare 与图片 recog.run、session.transition/get 请求都带 staging_root（等于 Fake LocalFileStore 暂存根）；开启增强时 img.prepare 带 gray_out_path 并展示对照图；postprocess 返回空 candidates 加 RECOG_ALL_CANDIDATES_INVALID 时进入手工输入且只提示一次；transition 请求带 now_ms 与 payload.networked。
- [R06][R40] 识别上下文：lookup 传 symbolHints ['F','m'] 与 subject 'physics' 时 recog.run 与 recog.postprocess 请求体 context 等于 {mode:'lookup',symbol_hints:['F','m'],subject:'physics',expected_kind:null,user_corrections:[]}，云端 submit 收到同一 subject/symbolHints；51 项或含空串时构造失败；answer 模式取期望修订字形去重前 50。
- [R32] 裁剪：连续三次 updateCrop 只发布最后一次结果，前两次的 IMG_CANCELLED 不产生 FlowFailed 或错误提示；img.prepare 请求 long_edge 为 2000，旧预览文件在新结果发布后被删除。
- [R06][R40] 错误行逐码（Fake）：RECOG_MODEL_NOT_INSTALLED/BACKEND_UNAVAILABLE 显示手工输入与其他本地模型且无云端项；MODEL_TIMEOUT/OOM → canRetry 为真，retry() 复用原 sessionId；NO_CANDIDATE 提示调整；ACTIVE_TASK_EXISTS 显示“查看/取消它”；CloudUnknown 显示“结果未知，可能已计费”且 submit 只调用一次；ALL_CANDIDATES_INVALID 进入 CandidatesReady；CLOUD_PREVIEW_STALE/TOKEN_EXPIRED/AUTH_UPLOAD_RECONFIRM_REQUIRED 回 CloudPreviewing；未列错误 canRetry 等于 FmlException.retryable。
- [R31] 队列：3 张图第 2 张 probe 失败时 next() 依次处理第 1、3 张并在末尾汇总一条跳过提示；全部 probe 失败时 session.start 零次、暂存清空、回导入入口且历史无新记录；空导入 session.start 零次；作答模式后端列表只含 faithful_transcription 为真者，游客只含 networked 为假者。
- [R06][R33] 安装点：installRecognition 位于 installStudy 之后；startup order 40 对 model- 包逐个 register、单个失败只记录；档案 order 50 先 ensure() 再 recover，ensure 返回 true 时提示恰一次；lifecycle paused 29 s 不卸载、30 s 卸载一次，lowMemory 立即卸载；页面销毁后暂存目录无本会话文件。
- [R04] 手写作答：确认后 AnswerSink 收到 answer_mode handwriting、raw_answer 等于编辑器最终 LaTeX、hint_used false、duration_ms 等于注入时钟差；未确认不调用。
- [R06] 进度：Fake 推理延迟 1.2 s 时 1 s 后出现进度与取消，延迟 0.8 s 时不出现。
