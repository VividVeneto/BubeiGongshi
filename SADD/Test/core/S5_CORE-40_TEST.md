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
