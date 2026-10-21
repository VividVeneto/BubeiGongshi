# CORE-95 测试方案

> 来源卡：[S4_CORE-95_功能.md](../../core/S4_CORE-95_功能.md)（资源包安装激活恢复与引擎层接入）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**
- [R29] bootstrap 包在断网首次启动时可用，应用可完成公式输入、校验与排版。
- [R30] 安全用例（`crates/fml-pack/tests/`，夹具由测试内生成的测试密钥签名）：签名错误、公钥被替换、条目哈希错误、版本降级、安全序号回滚、依赖缺失、超限、每条危险路径、包内可执行文件均被拒绝，且返回CORE-15唯一定义的错误码；每例结束后旧包仍可 `open_entry`。
- [R30] 中断用例：下载或解压中途终止后旧包可用、无半截目录；崩溃恢复只保留完整已验证目录。
- [R01] 同一包在 Android 与 Windows 安装后条目数、逻辑 ID 与内容哈希一致。
- [R30] 回滚：安装 v2（epoch 2）后用 v1 时期的 pack_meta.db 覆盖当前库并重启，`pack.recover` 后生效 `max_epoch` 仍为 2、安装 epoch 1 的包返回 `PACK_EPOCH_ROLLBACK`；删除 pack_meta.db 后从完成标记重建索引，高水位不降；active.json 指向要求更高 min_app_version 的目录时回退到 previous_version。
- [R29] 引擎层：安装含单位条目的包后 CORE-56 generation + 1 且新单位可用于 `calc.evaluate`；与现有包同 ID 冲突的包被拒、旧包与 generation 不变；卸载后单位消失。
- [R30] uninstall按登记顺序调用钩子，任一失败中止；有读者不删旧目录，Windows重命名失败保留旧指针并下次启动激活；bootstrap/被依赖包拒绝卸载。SecurityState镜像先临时刷盘原子换，再库/active事务，三源max不降低。
- [R29] 设备安装不遍历账户库；catalog generation变化时按CORE-14刷新只读投影。四op不调用CORE-96，离线路径可独立构建/测试。
