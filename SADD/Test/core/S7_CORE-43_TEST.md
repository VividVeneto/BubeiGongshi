# CORE-43 测试方案

> 来源卡：[S7_CORE-43_发布.md](../../core/S7_CORE-43_发布.md)（服务端部署、资源分发与监控）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R28] 本地用 `compose.yaml` + minio/Fake供应商部署，认证/同步/云识别集成测试通过（邮件集成归CORE-45）；删除 `required_keys.txt` 中任一键的值时 `preflight.py` 退出 1 并指出该键。
- [R40] 外部前提满足后的人工checklist（云厂商、账号和真实Key由甲方提供；未提供记阻断）：供应商 API Key 轮换演练：注入新 Key 并重启后新请求成功，撤销旧 Key 后无失败，客户端无需更新。
- [R30] 上传新版本资源包并运行 `tuf/refresh.sh` 后，客户端 `pack.check_updates` 能发现并安装；停用重签 8 天后客户端报告 `PACK_METADATA_EXPIRED`，`fml_tuf_timestamp_expires_seconds` 告警先于过期触发。
- [R19] 告警演练：用 Fake 供应商制造超时与 UNKNOWN，对应告警按阈值触发；`/metrics` 输出中不含邮箱与账户 ID。
- [R28] 恢复演练：`restore.sh` 恢复到新实例，同步数据完整，删除清单被重放。
