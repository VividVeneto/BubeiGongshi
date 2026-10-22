# CORE-47 测试方案

> 来源卡：[S6_CORE-47_界面.md](../../core/S6_CORE-47_界面.md)（设置页与账户安全界面）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

- [R24][R27] 文件选择/prepare暂停切换A→null，立即清口令预览/禁用；A返回token只向A core discard，B零restore调用。commit/discard串行互斥，commit已进事务则native close/openB等待结果，不伪造取消/回滚，不将A报告发布B。disposeAsync/stopAndDrain等待任务与临时清理，失败阻止close。
- [R24][R34] HistorySettingsVm的ensure/setKeepLast/clearAll每个await后切换不写B，连续点击串行不并发rotate；null时FFI零次。相同profile新handle重建全部VM，旧devices/向导回调不更新B；旋转同一session保留表单，跨账户必须清除。Widget只收VM/UiDeps，所有明文字节副本finally清零、String释放。
- [R19] 向 `SettingsSections` 加入两个测试项（order 20、10）后设置首页依次显示 order 10、20 两项，未加入时不显示该区。
- [R28] 注册用户设置页可开启/关闭同步并显示最近同步时间、待推送数量与错误（Fake `SyncFacade` 驱动各 `SyncPhase`）。
- [R27] 备份界面（Fake `CoreBinding`）：只选“学习数据”时显示闭包提示，导出完成显示 `closure_added` 条数；恢复预览显示闭包条数与“不覆盖本机”说明；`commit_restore` 进行中“取消”按钮始终可点：Fake 让 commit 在取消后仍成功时显示成功报告并附“恢复已完成，未能取消”，返回 `BACKUP_CANCELLED` 时显示“已取消，原数据未改变”；五项范围全取消时导出按钮禁用（`BACKUP_SCOPE_INVALID` 作为后备映射）。
- [R28] 升级向导：Fake `UpgradeFacade` 下“新建账户”经过显示恢复码 → 勾选已保存 → 完成；未勾选时无法继续；“并入已有账户”要求输入恢复码或同步密语。
- [R25] 游客设置页显示“游客：无内容上传”，不出现同步、设备与云识别项。
- [R27] 导出 → 选择文件恢复（Fake 端口）走完预览与确认；在预览页返回后 `discard_restore` 被调用，原库不变。
- [R27] 保护与模式（Fake CoreBinding）：游客不显示恢复码保护，已注册账户可选恢复码并发出 protection 为恢复码的 backup.export；恢复时 mode 随 prepare_restore 发出、commit_restore 只带 token/now_ms/day；预览后改选模式先 discard 再重新 prepare。
- [R34] 设置 `keep_last` 时输入 101 被拒绝并提示范围；设为 0 后调用 `recog.settings.set` 且 `keep_last` 为 0。
- [R42.f] Widget 测试：设置首页第一组显示“外观”项和当前预设/模式，点击后路由到 `/settings/appearance`（页面由 CORE-58 提供，本卡用占位页断言路由名）；游客模式同样可见。
- [R28] 设备页（Fake `ApiClient` 与 `SyncFacade`）：返回两台设备（一台 `current`）时 load 得到两个 `DeviceDto` 且字段逐一对应；响应缺字段时显示通用加载失败并允许重试；吊销调用 `SyncFacade.revokeDeviceAndRotate` 恰一次，随后显示新恢复码，未勾选“已保存”不能离开，并显示“重新设置同步密语”提示与直达按钮；游客模式设置首页不出现设备项。
- [R28] needsKey 与同步密语（Fake `SyncFacade`）：phase 为 needsKey 时出现输入卡，选恢复码/同步密语分别以恢复码/密语输入调用 `provideKey`；设置同步密语两次输入不一致时提交按钮禁用，Fake 抛 `CRYPTO_PASSPHRASE_WEAK` 时错误显示在输入框。
- [R28] 修订选择（Fake `SyncFacade`）：`status.openChoices` 为 2 时同步页出现入口，子页列出 `choices()` 两条；选定后以（choiceId, chosenRevisionId）调用 `resolveChoice` 恰一次；Fake 抛 `SYNC_CHOICE_INVALID` 时重新加载列表。
- [R27] 账户页（Fake `SecureKeyValueStore` 与 `AccountController`）：`securityLevel` 返回 software 时显示“本机密钥保护能力较弱”及原因，返回 tee 时不显示；“恢复出厂或清除应用数据会丢失本机密钥…”始终显示；以 `fml.<profileId>.db` 调用 `securityLevel`，current 为 null 时不调用；“删除本机数据”须二次确认后才调用 `logout(deleteLocalData: true)`。
- [R27] 导出口令与错误（Fake `CoreBinding` 与文件端口）：两次口令不一致时导出按钮禁用；Fake 返回 `CRYPTO_PASSPHRASE_WEAK` 显示在口令框；恢复时 `BACKUP_WRONG_SECRET` 回显并允许重输，`BACKUP_TOKEN_UNKNOWN` 提示重新选择文件；同步开启时 Replace 选项禁用并显示说明；文件选择或导出返回取消（null）时不调用任何 backup op。
- [R27] 恢复预览四项（Fake `CoreBinding`）：`RestorePreviewDto` 的 replaced、kept_local、possible_duplicates 非空、missing_packs 非空时四项都显示，后两项各带“不会自动合并”“重新安装资源包后自动关联”提示。
- [R34] 识别历史一键清空（Fake `HistoryKeyUnlocker`）：`clearAll` 经二次确认后调用一次；连续点击只执行一次。
- [R19] 提醒、隐私与关于（Fake 路由表）：`/settings/reminders` 重定向到 `/study/reminder`、`/settings/privacy` 重定向到 `/privacy`（占位路由断言路由名）；`/study/reminder` 未登记时设置项置灰；资源包项在 `/packs` 未登记时置灰；关于页显示 `AboutInfo.appVersion`（测试环境为 0.0.0-dev），点击“开源许可”打开许可页。

- [R42.e][R42.b] 页面接入验收（Fake 门面与 CoreBinding）：备份导出页两个口令框已输入且焦点在第 2 个、`/settings` 首页滚到底部时，360×800 ↔ 800×360 往返 3 次，文本、焦点与滚动偏移不变；升级向导停在 `UpgradeStep.showRecoveryCode` 并勾选“我已保存”时旋转，仍在该步、勾选保留、恢复码文本不变，`UpgradeFacade` 不被再次调用；`textScaler` 2.0 下设置首页、外观子页、备份与升级向导 `tester.takeException()` 为 null；向导与表单每步恰有 1 个 `FmlButtonVariant.primary`；宽档为 `TwoPane`（左分组 240～360）。
