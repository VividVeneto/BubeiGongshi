### CORE-01 仓库骨架与工程约定

**目标**：建立单仓库目录、Cargo 与 Flutter 工作区和全局工程约定，使后续每张卡都能在固定位置落代码。

**范围**
- 包含：目录布局、Cargo workspace、Flutter 工程 `app/`、依赖方向规则、命名与注释约定、全局资源预算表、版本号种类。
- 不包含：具体业务代码；CI 工作流（CORE-41）；平台工程细节（AND-01、WIN-01）。（下游说明，非契约）

**依赖**：

**接口契约**

目录布局（全部卡片按此落位）：

```text
crates/                 Rust 核心，禁止 Flutter/Dart/JNI/HTTP 客户端依赖
  fml-error  fml-ast  fml-latex  fml-notation  fml-units  fml-type
  fml-eval   fml-derive  fml-typeset  fml-store  fml-pack  fml-srs
  fml-grade  fml-study  fml-crypto  fml-sync  fml-recognize
  fml-recognize-local  fml-imgproc  fml-export  fml-sync-proto  fml-ffi
contracts/              唯一事实源：错误码注册表、DTO schema、C 头文件、测试向量
  errors/registry.yaml  dto/*.schema.json  include/fmlcore.h  vectors/  policies/
app/                    Flutter 工程（Android 与 Windows 共用）
  lib/binding/          生成的 dart:ffi 绑定与类型化包装（CORE-03）（下游说明，非契约）
  lib/ports/            平台端口抽象（CORE-04）（下游说明，非契约）
  lib/platform/android/ lib/platform/windows/   端口的平台实现（AND/WIN 卡）
  lib/composition/      按平台组装端口与用例
  lib/<feature>/        用例编排：account sync recognition study study_stats library editor calc packs settings privacy export net design
  lib/ui/<feature>/     Widget：shell design editor library study study_stats books calc packs recognition settings
  lib/render/ lib/l10n/    共享绘制与本地化资源
  test/ integration_test/   单元/Widget与平台集成测试
  lib/main_*.dart          平台入口（平台卡创建）
  android/  windows/       平台原生工程
server/                 服务端模块化单体（CORE-22、25、33、43、45）（下游说明，非契约）
packs/                  资源包源数据（CORE-16）（下游说明，非契约）
tools/                  content/ ci/ release/ ohos-smoke/ perf/ android/host_tests/ windows/host_tests/
  sadd/ DTOcheck/         文档工具项（README §7.1，不进产品构建）
  toolchain.versions requirements.txt
installer/windows/launcher/  独立原生启动器（发布阶段创建）
```

Cargo workspace：根 `Cargo.toml` 为虚拟 workspace（`resolver = "2"`），初始 `members = ["crates/*"]`。本卡只创建 `crates/fml-error/Cargo.toml` 与含 crate 文档、`#![forbid(unsafe_code)]`、`#![deny(missing_docs)]` 的 `src/lib.rs` 最小可编译骨架，不声明占位 ErrorCode/FmlError API；该包的正式模型、生成器和后续维护唯一归 CORE-02（下游说明，非契约）。这样首卡 build/doc 确实编译一个目标，而非空 workspace 假通过。其他 crate 由各自卡首次交付时加入 `crates/`；根不预列尚不存在的 server 成员，CORE-22（下游说明，非契约）在首次创建 `server/Cargo.toml` 的同一提交把 "server" 追加到 members，并验收整个 workspace。共享第三方依赖的版本写在根 `[workspace.dependencies]`，由首张使用卡按 ADR-V5-15 添加（计入该卡附属改动）。

依赖方向规则：
1. `fml-ast` 不依赖解析器、存储与 UI；`fml-type` 只依赖 `fml-ast`、`fml-units`、`fml-notation`（另见本条末的通用例外）；`fml-eval` 只依赖 `fml-ast`、`fml-type`、`fml-units`；`fml-typeset` 不直接读字体文件，字体字节由 CORE-56 上下文注入（S1内置，S4包扩展）。通用例外：所有 crate 均可依赖 `fml-error`（`FmlError` 与诊断）；需要取消检查的 crate（如 `fml-imgproc`）可依赖 `fml-ast` 仅为使用 `CancelFlag`；CORE-69 的 DEP-1 允许表据此包含这两项。（下游说明，非契约）
2. 领域 crate（ast、latex、notation、units、type、eval、derive、typeset、export、srs、grade、study、crypto，以及 sync 的合并逻辑）无 I/O：不访问网络、文件、时钟与平台 API；时间、随机数和文件内容由调用方以参数传入（sans-I/O：输入事件与状态，输出新状态与待执行的 I/O 命令）。
3. `fml-store` 可依赖领域 crate，领域 crate 不得依赖 `fml-store`。
4. `fml-ffi` 是唯一允许出现 `extern "C"` 的 crate。
5. Dart 分层：`app/lib/ui/<feature>/` 只放 Widget、绘制与路由视图，不 import `binding/` 的运行时（只允许纯数据 `binding/dto/*.g.dart`）、`platform/` 或发起 HTTP；`app/lib/<feature>/` 放 ViewModel、用例、Controller、Worker 与 DTO，可持有 CoreBinding；`composition/` 构造与注入服务，平台实现只经端口调用；共享界面不得判断平台。
6. 平台层不得实现公式解析、量纲与单位换算、排版布局、FSRS 调度、同步合并、资源包验签。

全局资源预算（各卡验收引用此表）。测量口径：release 构建，P95，真机，冷启动 ≥30 次、核心操作 ≥1000 次、图片 ≥100 张；基准设备在 M0 登记型号、系统版本与环境温度，不用模拟器替代。Windows集成驱动按WIN-13用Profile并单列趋势，正式预算判定用Release外部采样；Profile结果不能单独作为Release达标证据。（下游说明，非契约）

| 指标 | Android 中端（4 GB arm64） | Windows（4 核 / 8 GB / SSD） |
| --- | --- | --- |
| 冷启动到首页 | < 2 s | < 1.5 s |
| 公式解析（≤256 节点） | < 20 ms | < 10 ms |
| 量纲校验 | < 10 ms | < 5 ms |
| 单式排版 | < 30 ms | < 20 ms |
| 单题判分 | ≤ 50 ms | ≤ 25 ms |
| 排程取下一题（10000 条公式 / 50000 张卡） | ≤ 20 ms | ≤ 10 ms |
| 公式库搜索首屏（10000 条） | < 100 ms | < 60 ms |
| 公式复制（≤256节点，点击到写入器收到负载P95） | ≤ 300 ms | ≤ 150 ms |
| 补全rankCandidates（锁定完整数据，P95） | ≤ 4 ms | ≤ 4 ms |
| 库批量写入（10000条加一标签，P95） | ≤ 3 s | ≤ 3 s |
| 列表滚动 | 60 FPS，掉帧 < 1% | 60 FPS（100%–200% DPI） |
| 手写墨迹上屏 | ≤ 50 ms | ≤ 40 ms |
| 点击到可见反馈（按压态出现） | ≤ 100 ms | ≤ 50 ms |
| 作答到判定反馈（提交到判定条出现，含判分） | ≤ 150 ms | ≤ 100 ms |
| 转场与动效 | 60 FPS，掉帧 < 1%；单段 ≤ 400 ms | 60 FPS，掉帧 < 1%；单段 ≤ 400 ms |
| 旋转与窗口尺寸变化（到新布局首帧） | ≤ 300 ms，页面状态不丢失 | ≤ 100 ms；拖动缩放期间 60 FPS |
| 主题切换（预设或外观模式，到新主题首帧） | ≤ 100 ms，不重建路由 | ≤ 100 ms，不重建路由 |
| 图片预处理 | < 500 ms | < 300 ms |
| 本地模型识别（单式，模型已加载） | ≤ 2 s | ≤ 1 s |
| 本地模型首次加载 | ≤ 3 s | ≤ 2 s |
| 常驻内存 | < 150 MB | < 250 MB |
| 连续 20 张 12 MP 图片 | 无 OOM，60 s 内回落到空闲值 +20 MiB | 无 OOM，+30 MiB |
| 安装包（不含可选模型与内容包） | < 45 MB | 安装器 ≤ 70 MB |
| bootstrap 资源包（计入安装包） | 压缩后 ≤ 8 MiB | 压缩后 ≤ 8 MiB |

界面性能行（点击到可见反馈至主题切换）由 ADR-V5-25 引入，按上述口径计为核心操作；Android 另在平板上测旋转（AND-12）。预算调整只能经附录 A 的 ADR，由需求负责人接受，且不得改变测量口径。能耗：不设常驻服务，不做周期性网络轮询；空闲时除每日一次本地提醒外没有定时唤醒。（下游说明，非契约）

版本号种类：App（SemVer）、ABI（`FML_ABI_MAJOR/MINOR`）、DTO schema、AST schema、DB schema（`PRAGMA user_version`）、服务端 API 主版本（`/v1`）、资源包格式与安全序号、模型与词表版本、FSRS 参数与评分映射版本、AAD 版本。兼容矩阵由 CORE-42 维护。（下游说明，非契约）

命名约定：Rust crate 名 `fml-<域>`，模块与函数 snake_case，类型 UpperCamelCase；Dart 文件 snake_case，类型 UpperCamelCase，成员 lowerCamelCase；op 名 `<域>.<动作>`（CORE-03）；错误码见 CORE-02；SQLite 表名与列名 snake_case；资源包 ID 小写短横线（如 `content-hs-math`）。（下游说明，非契约）

提交约定：Conventional Commits，格式 `<type>(<模块编号小写>): <摘要>`，如 `feat(core-05): 定义公式 AST 节点`；type 取 feat、fix、refactor、perf、test、docs、build、ci、chore；契约破坏性变更在正文写 `BREAKING CHANGE:` 并引用 ADR。一个提交只涉及一张卡。

注释约定：每个 crate 与 Dart 特性目录有 `README.md`，说明边界、线程模型与错误语义；Rust 公共项启用 `#![deny(missing_docs)]`，Dart 启用 `public_member_api_docs`；公共 API 文档注释含示例与错误条件；复杂算法注明输入假设、单位、精度与失败条件；不要求逐行注释，禁止无信息量的注释。

网络构造白名单唯一文件：contracts/policies/network-construction.yaml（本卡创建，version:1，allow:["app/lib/platform/android/net/**/*.dart","app/lib/platform/windows/net/**/*.dart"]）。只豁免这些文件构造 HttpClient/Socket 与网络包导入；privacy/、composition/ 不豁免。源码扫描不禁止正常文件I/O的dart:io导入，而检查网络类构造与http/dio包。CORE-28 与 CORE-41 引用同一文件，不各写一份路径列表。平台构造器只返回composition，须由NetworkGuard包装后注入；`app/lib/composition/` 以外读取 PlatformPorts 的 http 字段即报 DEP-5（composition 只用它初始化 CompositionContext.http，再由 CORE-28 包装）。（下游说明，非契约）

工程配置交付清单：本卡创建根 `Cargo.toml`（workspace.package 的 version/edition、workspace.dependencies、workspace.lints）、`rust-toolchain.toml`（精确 channel，components 含 rustfmt/clippy）、`rustfmt.toml`（仅锁定稳定版支持的设置）、`deny.toml`、`.gitignore`、`.gitattributes`、`.editorconfig`、根 `README.md`，以及 `app/pubspec.yaml`、`app/analysis_options.yaml`、`app/lib/main.dart` 的无绑定/无平台判定空壳与上述 fml-error 骨架。analysis_options 启用 public_member_api_docs，Rust 骨架显式继承 workspace.lints；missing_docs 用 crate 属性，禁止只配置未继承的 lint。deny.toml 对依赖清单明确允许已核对的 SPDX 许可，未知许可/禁用依赖拒绝；GUST 字体及 SQLCipher 等非 Cargo 数据另由其首次使用/发布卡核验，不伪造 Cargo 许可证例外。未来目录以有说明的占位文档保留，不预建业务 Cargo manifest；Flutter 平台原生工程由平台卡生成（下游说明，非契约：AND-01、WIN-01），不得把其生成器实现行数算到本卡。

机器可读架构策略（本卡定义并在骨架交付时创建，检查实现归 CORE-69；下游说明，非契约）：
- `contracts/policies/dep-allow.yaml`：顶层 `{version:1, crates:{<Cargo package name>:[<允许的本仓库直接依赖包名>,...]}}`。值为去重字符串数组，不支持通配符；本仓库路径依赖按 package 真名解析，不能靠 dependency alias 绕过。unknown key/版本、未知已实现包名、重复元素和自依赖为配置错误；尚未实现的白名单包不要求存在。普通/build/dev/target 条件下的本仓库直接依赖均检查；第三方版本仍由锁文件管，不受本表当作任意项目边的豁免。图中环无条件拒绝。初始值如下表，花括号内短名全部带 fml- 前缀；server 使用首次建包时固定的 package name `fml-server`。新增真实边先按§8.4修订本卡与机器表，不能由检查器推测允许。

| crate | 初始允许的本仓库直接依赖（全部列举，不含自身） |
| --- | --- |
| fml-error | 空 |
| fml-ast | error |
| fml-latex | ast、error |
| fml-units | ast、error |
| fml-notation | ast、latex、units、error |
| fml-type | ast、units、notation、error |
| fml-eval | ast、type、units、error |
| fml-derive | ast、type、units、eval、notation、error |
| fml-typeset | ast、latex、error |
| fml-export | ast、latex、typeset、error |
| fml-srs | ast、error |
| fml-grade | ast、latex、notation、units、type、eval、srs、error |
| fml-study | ast、latex、notation、units、type、eval、srs、grade、error |
| fml-crypto | ast、error |
| fml-sync-proto | error |
| fml-imgproc | ast、error |
| fml-recognize-local | ast、imgproc、error |
| fml-recognize | ast、latex、notation、units、type、imgproc、recognize-local、error |
| fml-pack | ast、crypto、store、error |
| fml-store | ast、latex、notation、units、type、eval、derive、typeset、export、srs、grade、study、crypto、sync-proto、sync、recognize、error |
| fml-sync | ast、crypto、sync-proto、error |
| fml-ffi | ast、latex、notation、units、type、eval、derive、typeset、export、srs、grade、study、crypto、sync-proto、imgproc、recognize-local、recognize、pack、store、sync、error |
| fml-server | error、sync-proto |

- 本表是允许上界而非要求全部依赖；不授予跨卡实现权限。fml-sync-proto 的协议数据无I/O；fml-recognize 的状态转换/候选纯逻辑无I/O，持久化在fml-store；fml-sync 的全部合并逻辑无I/O，不依赖store；CORE-26/66仓储编排在fml-store::sync，故只允许store→sync。fml-pack→store仅用于实现CORE-14的PackCatalog只读trait（下游说明，非契约：CORE-14、CORE-15），不允许反向store→pack；fml-pack、imgproc、recognize-local 与 store 的I/O仅限对应卡范围。fml-error 的公共模型无I/O，后续独立日志模块不赋予领域函数读钟/读文件权利。普通领域模块禁止 std::fs/net/time::SystemTime；被允许依赖 ast 但只用取消的模块仍只导入 CancelFlag，须词法检查加人工复核，表中允许边不覆盖此限制。
- `contracts/policies/dep6_symbols.txt`：UTF-8，一行 `op:<精确op名>` 或 `type:<精确类型token>`，空行和首字符#的注释忽略，唯一非注释头 `version:1`；去重、词法精确匹配，不支持正则。初始op行 engine.parse、engine.check、calc.evaluate、calc.solvable_targets、typeset.layout、typeset.glyph_outlines、derive.rank、derive.substitute、derive.run_plan；初始type行 FormulaNode、DimensionFull、DisplayList。用于阻止平台目录实现/搬运领域算法；普通说明字符串不命中，op只在调用表达式参数的字符串token检查，type只在类型/标识符token检查。新增领域入口由其卡提交数据片段，CORE-01所有者合入，不宣称初始清单可证明一切变相实现。
- `contracts/policies/platform-check-patterns.json`：`{version:1, patterns:[{library, receiver, member}]}`；三个值为精确字符串，receiver可为null表示顶层符号，成员不支持正则。初始规则：dart:io / Platform / isAndroid,isWindows,isLinux,isMacOS,isIOS,isFuchsia,operatingSystem；package:flutter/foundation.dart / null / defaultTargetPlatform,kIsWeb；package:flutter/foundation.dart / TargetPlatform / android,windows,linux,macOS,iOS,fuchsia（每个member独立一项）。检测ui内普通/前缀导入别名及静态成员访问；间接封装无法证明时显式warning并登记人工项，不能把未解析代码当通过。
- 上述三份文件及既有 network-construction.yaml 均只由本卡维护、未知字段拒绝；CORE-69（下游说明，非契约）消费同一四文件，不维护第二份白名单。预算表第一列是机器键，消费方必须逐字引用；测量次数/设备与Release口径不因键名校验改变。

**实现约束**
- 所有纯函数所需时间显式传 now_ms（UTC毫秒），学习日相关再传 StudyDay/已算好的边界；不读系统时钟。Dart用例在调用边界取一次UTC毫秒并按各op显式now_ms字段传入，Rust处理层只转交；未声明时间输入的op不得在领域层自行读钟。CORE-04没有Clock端口，不作跨语言反向调用。随机种子、ID、文件内容同样由调用方提供；每个纯函数契约列所需输入与固定向量。（下游说明，非契约）
- 版本锁定文件（ADR-V5-15）：本卡开工当天查询官方最新稳定版并写入 `rust-toolchain.toml`（Rust stable）、`app/.flutter-version`（Flutter 唯一来源，Dart SDK 随之）、`tools/toolchain.versions`（`python=`、`node=`、`fuzz_nightly=`（cargo-fuzz 用 nightly 日期）、`cargo_fuzz=`，每行 key=value）与 `tools/requirements.txt`（PyYAML 等 Python 包，精确版本）；`app/android/toolchain.versions` 由 AND-01、`app/windows/toolchain.versions` 由 WIN-01 在 S0 写入。第三方 crate 与 Dart 包由首张使用卡开工时锁入 `Cargo.lock`/`pubspec.lock`，各卡“外部前提”只列包名；平台卡 toolchain.versions 不重复 Rust 与 Flutter 版本。（下游说明，非契约）
- 锁版日期统一写 `tools/toolchain.versions` 的 `queried_date=YYYY-MM-DD`，并与 ADR-V5-15 的查询记录逐项对应；app/.flutter-version只含单行Flutter版本，requirements.txt只含精确依赖，不往机器版本值中塞日期。平台锁版/后续依赖分别在其所有者首次使用时登记，不把未创建的锁文件伪报齐全。
- 领域 crate 加 `#![forbid(unsafe_code)]`；`fml-ffi`、`fml-imgproc`、`fml-recognize-local` 的每个 unsafe 块须带 `// SAFETY:` 注释。
- 不可逆决策（技术栈替换、契约主版本变化、预算调整）写入附录 A 的 ADR。
- 提交按本卡“提交约定”；main 始终可构建；特性分支生命周期不超过 3 天。
- 外部前提：Rust stable 工具链、Flutter stable 渠道与 Dart SDK、Python 3（`tools/` 脚本）的具体版本由本卡按 ADR-V5-15 写入上述锁定文件，并在 ADR-V5-15 回填查询日期、版本与兼容依据；Android SDK/NDK 见 AND-01，Visual Studio 生成工具见 WIN-01。（下游说明，非契约）

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-01_TEST.md](../Test/S0/S0_CORE-01_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约95行；主包 app/lib/main.dart 空壳与接入骨架约80行，附属 crates/fml-error/src/lib.rs 文档/lint骨架约15行（CORE-02后续正式模型不计本卡）。根Cargo/pubspec/analysis_options、锁版、deny/rustfmt/policies、忽略/属性配置均为数据，README为文档，不计实现行数；本卡骨架各自可构建测试。CI骨架与平台原生工程归各所有者，不重复计入；不生成业务代码占位。（下游说明，非契约）

