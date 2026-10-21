# CORE-47 测试方案

> 来源卡：[S6_CORE-47_界面.md](../../core/S6_CORE-47_界面.md)（设置页与账户安全界面）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

- [R24][R27] 文件选择/prepare暂停切换A→null，立即清口令预览/禁用；A返回token只向A core discard，B零restore调用。commit/discard串行互斥，commit已进事务则native close/openB等待结果，不伪造取消/回滚，不将A报告发布B。disposeAsync/stopAndDrain等待任务与临时清理，失败阻止close。
- [R24][R34] HistorySettingsVm的ensure/setKeepLast/clearAll每个await后切换不写B，连续点击串行不并发rotate；null时FFI零次。相同profile新handle重建全部VM，旧devices/向导回调不更新B；旋转同一session保留表单，跨账户必须清除。Widget只收VM/UiDeps，所有明文字节副本finally清零、String释放。
- [R19] 向 `SettingsSections` 加入两个测试项（order 20、10）后设置首页依次显示 order 10、20 两项，未加入时不显示该区。
- [R28] 注册用户设置页可开启/关闭同步并显示最近同步时间、待推送数量与错误（Fake `SyncFacade` 驱动各 `SyncPhase`）。
- [R27] 备份界面（Fake `CoreBinding`）：只选“学习数据”时显示闭包提示，导出完成显示 `closure_added` 条数；恢复预览显示闭包条数与“不覆盖本机”说明；`commit_restore` 事务开始后取消按钮不可用；五项范围全取消时导出按钮禁用（`BACKUP_SCOPE_INVALID` 作为后备映射）。
- [R28] 升级向导：Fake `UpgradeFacade` 下“新建账户”经过显示恢复码 → 勾选已保存 → 完成；未勾选时无法继续；“并入已有账户”要求输入恢复码或同步密语。
- [R25] 游客设置页显示“游客：无内容上传”，不出现同步、设备与云识别项。
- [R27] 导出 → 选择文件恢复（Fake 端口）走完预览与确认；在预览页返回后 `discard_restore` 被调用，原库不变。
- [R27] 保护与模式（Fake CoreBinding）：游客不显示恢复码保护，已注册账户可选恢复码并发出 protection 为恢复码的 backup.export；恢复时 mode 随 prepare_restore 发出、commit_restore 只带 token/now_ms/day；预览后改选模式先 discard 再重新 prepare。
- [R34] 设置 `keep_last` 时输入 101 被拒绝并提示范围；设为 0 后调用 `recog.settings.set` 且 `keep_last` 为 0。
- [R42.f] Widget 测试：设置首页第一组显示“外观”项和当前预设/模式，点击后路由到 `/settings/appearance`（页面由 CORE-58 提供，本卡用占位页断言路由名）；游客模式同样可见。

- [R42.e][R42.b] 页面接入验收（Fake 门面与 CoreBinding）：备份导出页两个口令框已输入且焦点在第 2 个、`/settings` 首页滚到底部时，360×800 ↔ 800×360 往返 3 次，文本、焦点与滚动偏移不变；升级向导停在 `UpgradeStep.showRecoveryCode` 并勾选“我已保存”时旋转，仍在该步、勾选保留、恢复码文本不变，`UpgradeFacade` 不被再次调用；`textScaler` 2.0 下设置首页、外观子页、备份与升级向导 `tester.takeException()` 为 null；向导与表单每步恰有 1 个 `FmlButtonVariant.primary`；宽档为 `TwoPane`（左分组 240～360）。
