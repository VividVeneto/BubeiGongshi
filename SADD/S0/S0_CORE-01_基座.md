### CORE-01 仓库骨架与工程约定

**目标**：建立单仓库目录、Cargo 与 Flutter 工作区和全局工程约定，使后续每张卡都能在固定位置落代码。

**范围**
- 包含：目录布局、Cargo workspace、Flutter 工程 `app/`、依赖方向规则、命名与注释约定、全局资源预算表、版本号种类。
- 不包含：具体业务代码；CI 工作流（CORE-41）；平台工程细节（AND-01、WIN-01）。

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
  lib/binding/          生成的 dart:ffi 绑定与类型化包装（CORE-03）
  lib/ports/            平台端口抽象（CORE-04）
  lib/platform/android/ lib/platform/windows/   端口的平台实现（AND/WIN 卡）
  lib/composition/      按平台组装端口与用例
  lib/<feature>/        用例编排：account sync recognition study study_stats library editor calc packs settings privacy export net design
  lib/ui/<feature>/     Widget：shell design editor library study study_stats books calc packs recognition settings
  android/  windows/    平台原生工程
server/                 服务端模块化单体（CORE-22、25、33、43、45）
packs/                  资源包源数据（CORE-16）
tools/                  content/ ci/ release/ ohos-smoke/ perf/  toolchain.versions  requirements.txt
```

Cargo workspace：根 `Cargo.toml` 为虚拟 workspace（`resolver = "2"`），`members = ["crates/*", "server"]`；新增 crate 只在 `crates/` 下建目录，无需修改 `members`；共享第三方依赖的版本写在根 `[workspace.dependencies]`，由首张使用该依赖的卡按 ADR-V5-15 添加一行（计入该卡附属改动，不另立卡）。

依赖方向规则：
1. `fml-ast` 不依赖解析器、存储与 UI；`fml-type` 只依赖 `fml-ast`、`fml-units`、`fml-notation`（另见本条末的通用例外）；`fml-eval` 只依赖 `fml-ast`、`fml-type`、`fml-units`；`fml-typeset` 不直接读字体文件，字体字节由 CORE-56 上下文注入（S1内置，S4包扩展）。通用例外：所有 crate 均可依赖 `fml-error`（`FmlError` 与诊断）；需要取消检查的 crate（如 `fml-imgproc`）可依赖 `fml-ast` 仅为使用 `CancelFlag`；CORE-69 的 DEP-1 允许表据此包含这两项。
2. 领域 crate（ast、latex、notation、units、type、eval、derive、typeset、export、srs、grade、study、crypto，以及 sync 的合并逻辑）无 I/O：不访问网络、文件、时钟与平台 API；时间、随机数和文件内容由调用方以参数传入（sans-I/O：输入事件与状态，输出新状态与待执行的 I/O 命令）。
3. `fml-store` 可依赖领域 crate，领域 crate 不得依赖 `fml-store`。
4. `fml-ffi` 是唯一允许出现 `extern "C"` 的 crate。
5. Dart 分层：`app/lib/ui/<feature>/` 只放 Widget、绘制与路由视图，不 import `binding/` 的运行时（只允许纯数据 `binding/dto/*.g.dart`）、`platform/` 或发起 HTTP；`app/lib/<feature>/` 放 ViewModel、用例、Controller、Worker 与 DTO，可持有 CoreBinding；`composition/` 构造与注入服务，平台实现只经端口调用；共享界面不得判断平台。
6. 平台层不得实现公式解析、量纲与单位换算、排版布局、FSRS 调度、同步合并、资源包验签。

全局资源预算（各卡验收引用此表）。测量口径：release 构建，P95，真机，冷启动 ≥30 次、核心操作 ≥1000 次、图片 ≥100 张；基准设备在 M0 登记型号、系统版本与环境温度，不用模拟器替代。Windows集成驱动按WIN-13用Profile并单列趋势，正式预算判定用Release外部采样；Profile结果不能单独作为Release达标证据。

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

界面性能行（点击到可见反馈至主题切换）由 ADR-V5-25 引入，按上述口径计为核心操作；Android 另在平板上测旋转（AND-12）。预算调整只能经附录 A 的 ADR，由需求负责人接受，且不得改变测量口径。能耗：不设常驻服务，不做周期性网络轮询；空闲时除每日一次本地提醒外没有定时唤醒。

版本号种类：App（SemVer）、ABI（`FML_ABI_MAJOR/MINOR`）、DTO schema、AST schema、DB schema（`PRAGMA user_version`）、服务端 API 主版本（`/v1`）、资源包格式与安全序号、模型与词表版本、FSRS 参数与评分映射版本、AAD 版本。兼容矩阵由 CORE-42 维护。

命名约定：Rust crate 名 `fml-<域>`，模块与函数 snake_case，类型 UpperCamelCase；Dart 文件 snake_case，类型 UpperCamelCase，成员 lowerCamelCase；op 名 `<域>.<动作>`（CORE-03）；错误码见 CORE-02；SQLite 表名与列名 snake_case；资源包 ID 小写短横线（如 `content-hs-math`）。

提交约定：Conventional Commits，格式 `<type>(<模块编号小写>): <摘要>`，如 `feat(core-05): 定义公式 AST 节点`；type 取 feat、fix、refactor、perf、test、docs、build、ci、chore；契约破坏性变更在正文写 `BREAKING CHANGE:` 并引用 ADR。一个提交只涉及一张卡。

注释约定：每个 crate 与 Dart 特性目录有 `README.md`，说明边界、线程模型与错误语义；Rust 公共项启用 `#![deny(missing_docs)]`，Dart 启用 `public_member_api_docs`；公共 API 文档注释含示例与错误条件；复杂算法注明输入假设、单位、精度与失败条件；不要求逐行注释，禁止无信息量的注释。

网络构造白名单唯一文件：contracts/policies/network-construction.yaml（本卡创建，version:1，allow:["app/lib/platform/android/net/**/*.dart","app/lib/platform/windows/net/**/*.dart"]）。只豁免这些文件构造 HttpClient/Socket 与网络包导入；privacy/、composition/ 不豁免。源码扫描不禁止正常文件I/O的dart:io导入，而检查网络类构造与http/dio包。CORE-28 与 CORE-41 引用同一文件，不各写一份路径列表。平台构造器只返回composition，须由NetworkGuard包装后注入；`app/lib/composition/` 以外读取 PlatformPorts 的 http 字段即报 DEP-5（composition 只用它初始化 CompositionContext.http，再由 CORE-28 包装）。

**实现约束**
- 所有纯函数所需时间显式传 now_ms（UTC毫秒），学习日相关再传 StudyDay/已算好的边界；不读系统时钟。Dart用例在调用边界取一次UTC毫秒并按各op显式now_ms字段传入，Rust处理层只转交；未声明时间输入的op不得在领域层自行读钟。CORE-04没有Clock端口，不作跨语言反向调用。随机种子、ID、文件内容同样由调用方提供；每个纯函数契约列所需输入与固定向量。
- 版本锁定文件（ADR-V5-15）：本卡开工当天查询官方最新稳定版并写入 `rust-toolchain.toml`（Rust stable）、`app/.flutter-version`（Flutter 唯一来源，Dart SDK 随之）、`tools/toolchain.versions`（`python=`、`node=`、`fuzz_nightly=`（cargo-fuzz 用 nightly 日期）、`cargo_fuzz=`，每行 key=value）与 `tools/requirements.txt`（PyYAML 等 Python 包，精确版本）；`app/android/toolchain.versions` 由 AND-01、`app/windows/toolchain.versions` 由 WIN-01 在 S0 写入。第三方 crate 与 Dart 包由首张使用卡开工时锁入 `Cargo.lock`/`pubspec.lock`，各卡“外部前提”只列包名；平台卡 toolchain.versions 不重复 Rust 与 Flutter 版本。
- 领域 crate 加 `#![forbid(unsafe_code)]`；`fml-ffi`、`fml-imgproc`、`fml-recognize-local` 的每个 unsafe 块须带 `// SAFETY:` 注释。
- 不可逆决策（技术栈替换、契约主版本变化、预算调整）写入附录 A 的 ADR。
- 提交按本卡“提交约定”；main 始终可构建；特性分支生命周期不超过 3 天。
- 外部前提：Rust stable 工具链、Flutter stable 渠道与 Dart SDK、Python 3（`tools/` 脚本）的具体版本由本卡按 ADR-V5-15 写入上述锁定文件，并在 ADR-V5-15 回填查询日期、版本与兼容依据；Android SDK/NDK 见 AND-01，Visual Studio 生成工具见 WIN-01。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-01_TEST.md](../Test/S0/S0_CORE-01_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 95 行（根 Cargo.toml、app/pubspec.yaml、analysis_options.yaml、main.dart 骨架与仓库忽略/属性配置）；仓库根。锁版文件、deny.toml/lints 等策略配置与 README 为数据/文档，不计行数；CI 骨架归 CORE-41；平台工程由 AND-01/WIN-01 生成，不计本卡。

