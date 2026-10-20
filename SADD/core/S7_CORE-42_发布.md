### CORE-42 发布流水线、版本矩阵与回滚

**目标**：统一两端的版本号、兼容矩阵、可复现构建、制品哈希与 SBOM、发布检查清单与回滚流程。

**范围**
- 包含：版本种类与兼容矩阵、`tools/release/` 脚本（版本号写入、构建、汇总哈希、生成 SBOM 与许可清单）、发布检查清单、保留最近两个正式版本的回退支持、事故复盘转为测试的流程。
- 不包含：平台签名与安装包制作（AND-11、WIN-02、WIN-12）；服务端部署（CORE-43）。

**依赖**：CORE-01、CORE-02、CORE-13、CORE-41

**接口契约**

| 版本 | 规则 |
| --- | --- |
| 应用版本 | SemVer，两端同号发布 |
| C ABI | `fml_abi_version()` 主版本不同即拒绝加载 |
| DTO schema、AST schema | 整数版本，只做向后兼容加法 |
| 数据库 schema | `SCHEMA_VERSION`，只前向迁移 |
| 服务端 API | `/v1`，低于最低客户端版本返回 426 |
| 资源包 | `format_version`、`pack_version`、`security_epoch` |
| 模型 | `model_version` + `vocab_version` |
| FSRS | 算法版本、参数版本、评分映射版本 |

```text
tools/release/                （命令行约定同 CORE-41 common.py：退出码 0 成功 / 1 门禁失败 / 2 脚本错误）
  bump_version.py <x.y.z> --revision <r>     同步写入 Cargo.toml、pubspec.yaml（version: x.y.z+build）、Android versionCode（= (x*10000+y*100+z)*10+r；x=0..20999，y/z=0..99，r=0..9，最终≤2100000000；pubspec +build 等于该整数；同版本重发r+1，r耗尽提升z，严格大于前次发布）、
                              Windows 应用版本资源（Runner.rc 取 pubspec 版本）与 Inno 脚本 AppVersion；任一文件版本不一致时退出 1。
                              不改 installer/windows/launcher/ 的版本资源与 launcher_protocol（WIN-16 固定为 1，只随 ADR 变更）；
                              另核对启动器源码中的 launcher_protocol 与 update.json 模板中的值相同，不同时退出 1
  collect_artifacts.py --dist dist/   汇总 AAB、APK、Windows 安装包与 update.json、资源包，写 dist/SHA256SUMS 与 dist/manifest.json（文件、字节、哈希、构建提交）
  size_gate.py --dist dist/   按下文体积上限检查，失败时输出按目录与文件类型分解的体积构成
  scan_secrets.py --dist dist/   解包 APK/AAB/MSIX 与安装包，扫描供应商 API Key 样式（初始规则及扩充流程见下文）、测试密钥指纹、本机绝对路径
  sbom.py --out dist/sbom.json   由 cargo metadata 与 pubspec.lock 生成 CycloneDX 1.5 SBOM 与 dist/THIRD_PARTY_LICENSES.txt
  repro_check.py --a dist1/ --b dist2/   比较两次构建的 Rust 核心库（libfmlcore.so、fmlcore.dll）与资源包哈希
  checklist.md                发布检查清单（逐项签字）
  rollback.md                 回滚流程
```

扫描初始规则（项目保守启发式，不保证任何供应商所有密钥都带前缀）：解包后所有文件含二进制分别作UTF-8与UTF-16LE字符串扫描；私钥头 `-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----`、疑似ID `\b(?:LTAI|AKID)[A-Za-z0-9]{8,64}\b`、通用供应商样式 `\bsk-[A-Za-z0-9_-]{16,128}\b`。对配置键 `(?i)(access[_-]?key[_-]?secret|secret[_-]?key|api[_-]?key)\s*[:=]\s*["']?([A-Za-z0-9_+/=-]{16,})` 检查非空值；本地路径按CORE-28路径模式。规则命中即退出1，仅输出文件/偏移/规则名，不输出命中值。额外读取CI受控测试密钥的SHA256指纹清单，扫描候选值后比指纹；不把真实密钥放夹具。正反例全部用合成串，普通LaTeX/空配置键/公开公钥头应通过。新供应商在ADR-V5-16定案时补官方凭据样例和合成正反例，未补前该供应商发布阻断。LTAI/AKID样例来源待锁版时核对官方凭据文档（外部前提，不把前缀当真实性证明）；长度边界为本项目扫描阈值。

产品约束追踪：见README §6 Q7、Q39；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 锁定工具链版本（ADR-V5-15）与依赖锁文件；Rust 核心库与资源包要求逐字节可复现（`--remap-path-prefix`、`SOURCE_DATE_EPOCH`，Windows 链接加 `/Brepro`）；完整安装包因平台签名与时间戳不要求逐字节一致，只记录哈希。发布标签 `vX.Y.Z` 并附变更日志。
- 回滚：Android 与 Windows 都不依赖“降级安装”；回滚版本 = 上一正式版代码 + 当前版本的全部迁移文件（迁移只增不删，CORE-13），版本号继续递增后发布（roll-forward）；服务端最低客户端版本不因回滚上调。
- 本卡不产生运行时错误码。
- 包体积门禁：Android 单 ABI 安装包 < 45 MB，Windows 安装包 ≤ 70 MB（不含可选资源包与模型包）；bootstrap 包 ≤ 8 MiB。
- 发布检查清单包含：两端真机冒烟、隐私网络审计、制品无供应商 API Key 与调试路径（字符串扫描）、符号与 mapping 归档、许可清单完整、隐私政策与 SDK/域名清单更新。
- 事故复盘的每个根因必须转为一条自动化测试或门禁。

**验收标准**
- [R03] 体积门禁：超过上限时发布流水线失败并输出体积构成。
- [R23] 发布演练：从同一标签在干净环境构建两次，`repro_check.py` 报告 Rust 核心库与资源包哈希一致；SBOM 与许可清单生成；`bump_version.py` 后 Cargo.toml、pubspec.yaml、versionCode、Windows 应用版本资源与 Inno AppVersion 一致，启动器版本资源与 `launcher_protocol` 未被改动。
- [R40] 制品扫描：APK、AAB、EXE、DLL、资源包中无供应商 API Key 样式字符串与测试密钥。
- [R23] 回滚演练（S7 两平台主机集成测试与人工checklist，记录构建/设备/数据库断言与恢复证据；本卡脚本单测只验证版本和迁移集合，不把它当本机自动验收）：安装含新迁移的版本 N+1 并写入数据，再覆盖安装回滚版本 N+2（N 的代码 + N+1 的迁移），数据库正常打开且数据完整。

- [R23] bump_version 1.2.3 r0→102030、1.2.3 r1→102031；y=100/r=10/非递增build/超过Android上限均拒绝且不改任何文件。

**规模**：约 420 行；`tools/release/`。

