# BubeiGongshi

不背公式：以“不背单词”为原型、强化公式背诵的 Windows 与 Android 双平台应用（Flutter 共享界面 + Rust 核心 + 服务端），预留鸿蒙 C ABI 接口，支持手写与拍照识别公式。

规则以 `SADD/` 为准（`AGENTS.md` 是索引）；本文件只做仓库导航。

## 目录

| 路径 | 内容 | 所有者 |
| --- | --- | --- |
| `crates/` | Rust 领域 crate 工作区；当前只有 `fml-error` 的文档与 lint 骨架 | CORE-01 建骨架，各 crate 卡建实现 |
| `app/` | Flutter 共享界面：`pubspec.yaml`、`analysis_options.yaml`、`lib/main.dart` 空壳 | 前端类卡 |
| `contracts/` | 机器可读契约与架构策略：`policies/`、`dto/`、`vectors/`、`errors/` | 各契约所有者 |
| `server/` | 服务端（CORE-22 创建时加入工作区成员） | CORE-22 起 |
| `SADD/` | 需求基线、模块卡、测试方案、附录 A（ADR）与附录 D（就绪记录） | lead |
| `tools/` | 文档工具、`toolchain.versions`、Python 依赖与 CI 脚本 | 工具与工程卡 |

## 工具链来源（ADR-V5-15）

- Rust：`rust-toolchain.toml`（channel stable，组件 rustfmt、clippy；工程样品阶段不锁精确版本，开工实测 1.99.1 记于 ADR-V5-15）。
- Flutter / Dart：`app/.flutter-version` 是唯一来源，Dart 随该 SDK。
- Python、Node、cargo-fuzz、cargo-deny 与查询日期：`tools/toolchain.versions`；Python 包：`tools/requirements.txt`。
- 平台工具链：`app/android/toolchain.versions`（AND-01）、`app/windows/toolchain.versions`（WIN-01）。

## 检查命令

```bash
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
cargo deny check
cd app && flutter pub get && dart format --set-exit-if-changed . && flutter analyze && flutter test
```

聚合入口 `python tools/ci/run_all.py` 与 `maint_report` 由 CORE-41 交付，当前不存在。

## 约定

- 提交：Conventional Commits `<type>(<卡号小写>): <摘要>`；一卡一提交；main 始终可构建。
- Rust 领域 crate `#![forbid(unsafe_code)]`，公共项 `#![deny(missing_docs)]`；Dart 启用 `public_member_api_docs`。
- 每个 crate 与 Dart 特性目录提供 `README.md`，说明边界、线程模型与错误语义。
- 依赖方向、网络构造白名单、dep6 符号与平台检查模式见 `contracts/policies/`。
