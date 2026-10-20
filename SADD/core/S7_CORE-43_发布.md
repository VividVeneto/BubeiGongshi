### CORE-43 服务端部署、资源分发与监控

**目标**：部署认证、发信、同步与云识别网关服务，提供资源包、TUF 元数据与 Windows 更新清单的分发，并在不采集内容的前提下监控可用性与费用。

**范围**
- 包含：部署清单（容器镜像、编排、配置样例与必填键检查）；密钥与供应商 API Key（云识别、邮件发信）的注入与轮换流程；服务端数据密钥；发信供应商机密的通用注入；业务发信配置与告警归CORE-45；资源包、TUF 元数据（含定时重签 timestamp/snapshot）与 Windows 更新清单的静态分发；数据库每日加密备份与季度恢复演练；指标导出（`server/src/ops/`）与告警规则；日志保留策略；签名密钥保管记录。
- 不包含：业务接口（CORE-22、25、33、45；CORE-45 的发信计数由其自行经 `metrics` 门面上报，本卡不依赖 CORE-45）；内容包制作与包签名（CORE-16）；Windows 更新清单内容的生成（WIN-12）。

**依赖**：CORE-01、CORE-02、CORE-22、CORE-25、CORE-33、CORE-72

**接口契约**

```text
server/deploy/
  docker/Dockerfile          单一镜像（模块化单体，非 root 用户运行）；入口 fml-server --config /etc/fml/config.toml
  compose.yaml               本地（本卡验收）与预发（外部前提满足后）：server、postgres、minio（S3 兼容替身）、prometheus
  config.example.toml        本卡及依赖配置键的样例（键由各业务卡定义：CORE-22 auth.*；email.*唯一定义见CORE-45（下游配置插件，非本卡输入）；CORE-25 sync.*；CORE-33 recognition.*；
                             本卡 database.url、storage.{endpoint,bucket,region}、data_key.env、ops.metrics_addr）；机密值只写 *_env（环境变量名）
  required_keys.txt          本卡所列ops/database/storage/data_key键及依赖业务卡配置的必填清单；不含CORE-45 email.*，preflight.py 据此检查
  preflight.py --config <path>   缺键、机密键未以 _env 提供、对应环境变量为空、端点不在白名单 → 退出 1 并逐项列出
  backup.sh / restore.sh     pg_dump → age 加密 → 对象存储（保留 35 天）；restore 到新实例后运行 CORE-25 删除清单重放
  alerts.yaml                Prometheus 告警规则（见下）
  keys.md                    签名与机密保管记录：TUF root/targets 私钥离线（发布负责人保管，首个 key_id 登记于此）、
                             snapshot/timestamp 私钥在线（密钥管理服务）、包签名密钥（CORE-16）、服务端数据密钥、供应商 Key 的轮换周期
  tuf/refresh.sh             每日定时：用 tuftool 以在线密钥重签 snapshot 与 timestamp（timestamp 有效期 7 天），上传 /packs/metadata/
server/src/ops/
  metrics.rs                 安装 metrics-exporter-prometheus 导出器（业务卡用 metrics crate 门面计数，如 CORE-45 的发信计数）；
                             HTTP 中间件（按路由与状态码计数、时延直方图）；每 60 s 的数据库采样（识别任务按终态计数、
                             队列积压与最老排队时长、当日费用 ÷ 预算）；在 ops.metrics_addr（仅内网）暴露 /metrics
  health.rs                  GET /healthz（进程存活）、GET /readyz（数据库与对象存储可达）

静态分发：https://<cdn>/packs/<pack_id>/<version>.fmlpack、/packs/metadata/{root,targets,snapshot,timestamp}.json、/windows/update.json
```

| 指标（不含内容） | 告警阈值 |
| --- | --- |
| `fml_http_requests_total{route,status}` | 同步路由 5xx 比例 5 min 内 > 1% |
| `fml_recognition_jobs{state}` | `unknown` 终态 1 h 内占比 > 2% |
| `fml_recognition_budget_ratio` | ≥ 0.8 |
| `fml_recognition_queue_oldest_seconds` | 持续 10 min > 60 |
| `fml_tuf_timestamp_expires_seconds` | < 2 天（重签任务失效） |

- 识别数据库采样只消费 CORE-33 定义：recognition_job.state/created_at/updated_at，state按其状态机终态集合聚合，队列只计QUEUED（RUNNING不算积压）；费用读recognition_budget.day/spent_units，分母为recognition配置的每日预算。采样输出为gauge（快照，不能每60s累加历史计数），重命名fml_recognition_jobs_total为fml_recognition_jobs；按UTC日取当日，预算0时比例为0并单独标禁用。SQL契约测试在33迁移上插入终态/排队/跨日样本，断言分组、最老时长及预算比；状态/DDL变化使本测试失败，业务所有者先变更契约再迁移。
- 本卡不新增业务错误码；`preflight.py` 退出码同 CORE-41 约定。

产品约束追踪：见README §6 Q39、Q40；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 部署地域在境内（README §6 Q8）；云厂商与对象存储产品按 ADR-V5-18（待定）选择，配置只依赖 S3 兼容接口与 PostgreSQL，不使用厂商专有 SDK。
- 机密只经环境变量或密钥管理服务注入，镜像与仓库中不含机密；供应商 Key 轮换时新旧两把并存不超过 24 h。
- 恢复目标：RPO ≤ 24 h、RTO ≤ 8 h；每日加密备份，季度恢复演练并在 `keys.md` 同目录的 `drills.md` 记录。
- 网络与安全日志按法规保留不少于 6 个月，不含请求体与内容；`/metrics` 只在内网暴露，指标标签不含账户 ID、邮箱或 IP。
- 资源包 CDN 不需要账户，也不接收用户内容；访问日志只保留 IP 与路径的最短必要期限，并在隐私政策中披露；供应商与网络域名清单随隐私政策公开。
- 外部前提：Docker、PostgreSQL、S3 兼容对象存储、Prometheus、`metrics` 与 `metrics-exporter-prometheus` crate、`tuftool`（tough 项目 CLI）、`age`；版本按 ADR-V5-15 锁定；发信账号与域名、云识别供应商账号由甲方开通。

**验收标准**
- [R28] 本地用 `compose.yaml` + minio/Fake供应商部署，认证/同步/云识别集成测试通过（邮件集成归CORE-45）；删除 `required_keys.txt` 中任一键的值时 `preflight.py` 退出 1 并指出该键。
- [R40] 外部前提满足后的人工checklist（云厂商、账号和真实Key由甲方提供；未提供记阻断）：供应商 API Key 轮换演练：注入新 Key 并重启后新请求成功，撤销旧 Key 后无失败，客户端无需更新。
- [R30] 上传新版本资源包并运行 `tuf/refresh.sh` 后，客户端 `pack.check_updates` 能发现并安装；停用重签 8 天后客户端报告 `PACK_METADATA_EXPIRED`，`fml_tuf_timestamp_expires_seconds` 告警先于过期触发。
- [R19] 告警演练：用 Fake 供应商制造超时与 UNKNOWN，对应告警按阈值触发；`/metrics` 输出中不含邮箱与账户 ID。
- [R28] 恢复演练：`restore.sh` 恢复到新实例，同步数据完整，删除清单被重放。

**规模**：约 420 行；主包 `server/deploy/`（配置与脚本约 260 行），附属：`server/src/ops/`（指标与健康检查约 160 行，与 `server/` 同一 Cargo 构建单元）。

