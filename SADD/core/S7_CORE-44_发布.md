### CORE-44 鸿蒙预留与 C 头文件消费者验证

**目标**：在 V1 不发布鸿蒙版本的前提下，保证核心引擎可编译到鸿蒙目标、C 头文件可被非 Dart 消费者调用，并记录端口在鸿蒙上的对应能力，为未来 ArkTS/ArkUI 前端或 Flutter 鸿蒙方案留出接口。

**范围**
- 包含：鸿蒙目标三元组 `aarch64-unknown-linux-ohos` 的交叉编译冒烟；一个最小 C 消费者程序；端口在鸿蒙上的对应关系表（本卡正文即该表，不另建文档）；CI 作业接入。
- 不包含：鸿蒙 UI、ArkTS/N-API 绑定、打包与上架（V1 范围外；甲方确认 V1 只保留 C ABI 与编译冒烟，见 README §6 Q6）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04

**接口契约**

```text
tools/ohos-smoke/
  build.sh          参数：--target ohos|host（默认 ohos）
                    ohos：OHOS_NDK_HOME 指向 OpenHarmony SDK native 目录；用其 clang 作为 linker，
                          cargo build -p fml-ffi --release --target aarch64-unknown-linux-ohos，产物 libfmlcore.so 存在且导出表含 fml_* 全部符号即成功
                    host：cargo build -p fml-ffi（debug），再用 clang -fsanitize=address 编译 consumer 并链接 libfmlcore 后运行
                    退出码：0 成功；1 构建或检查失败；2 环境缺失（如 OHOS_NDK_HOME 未设置）
  consumer.c        只 #include "fmlcore.h"（contracts/include/），步骤：
                    ① fml_abi_version() 的 MAJOR 等于 FML_ABI_MAJOR
                    ② fml_capabilities() 返回的 JSON 含 "engine.check"，随后 fml_free_buffer
                    ③ fml_call("engine.check", {"v":1,"trace_id":"00000000000000000000000000000044","body":{"source":"E = m c^2","notation_profile_id":"cn-default","user_decls":[],"empirical":false}})
                       返回0，响应JSON中ast非null，外层trace_id回显上述非零32hex；fml_free_buffer
                    ④ 用同一合法信封调用fml_call("no.such_op", ...)，返回-2且out错误信封含FFI_UNKNOWN_OP，外层trace_id与内层error.trace_id均为上述32hex；再以全零trace调用，须-1/FFI_BAD_ARG且错误信封两处trace均非零并一致；每次fml_free_buffer
                    ⑤ 每步失败打印步骤号并以 1 退出；全部通过打印 OK 并以 0 退出
                    JSON 不引入库：固定断言可作子串检查；trace 须在out.ptr/out.len有界缓冲内按外层与error对象位置分别提取32字节，校验全为小写hex且非全零，再memcmp比较两值/预期值；拒绝缺失、重复或越界字段，不得仅一次strstr错误码代替trace断言
.github/workflows/ci.yml 中的 ohos-smoke 作业（与 CORE-41 共用文件；ci.yml 单写维护者为 CORE-41，
                    本卡以契约变更单提交片段，不直接编辑该文件）：
                    片段只含 ohos-smoke 一个 job（key、needs、steps、缓存与环境）；needs 只引用
                    CORE-41 已定义的 lint/test 作业；steps 与 CORE-41 各作业一致，先跑 toolchain.py，
                    再执行 build.sh --target ohos；job key 与既有作业重复、needs 引用不存在作业或
                    缺 toolchain.py 前置时，由 CORE-41 拒绝合入并按变更单回退，不得静默改名或删除既有作业
```

端口在鸿蒙上的对应能力（未来实现时参考；V1 不编码）：

| CORE-04 端口 | 鸿蒙对应能力 | 备注 |
| --- | --- | --- |
| `SecureKeyValueStore` | HUKS（通用密钥库） | 包装密钥不出 HUKS |
| `LocalFileStore` | 应用沙箱目录（`filesDir`/`cacheDir`） | StoreArea 一一对应 |
| `ImagePicker` | PhotoViewPicker | 只取用户选中项 |
| `CameraController` | 相机服务 | 需相机权限 |
| `NotificationScheduler` | 后台代理提醒（reminderAgent） | 系统对提醒数量有上限 |
| `ClipboardAdapter` | 剪贴板服务（pasteboard） | |
| `RuntimeInfo` | 设备信息与系统能力查询 | abi 为 arm64 |
| `AppLifecycle` | UIAbility 生命周期 | 后台与低内存事件 |
| `HttpTransport` | 网络服务（http） | 仍须经 CORE-28 NetworkGuard |
| `FileExporter` | DocumentViewPicker 保存模式 | |
| `DocumentPicker` | DocumentViewPicker 选择模式 | |

- 本卡不登记 op，也不新增错误码；`consumer.c` 只使用 CORE-03 已登记的返回码与错误码。

**实现约束**
- 核心 crate 不得引入阻止鸿蒙目标编译的依赖；新增 Rust 依赖的 PR 若使 ohos-smoke 作业失败则不得合并（与 CORE-41 的必过检查一同配置）。
- `fml-ffi` 中与平台相关的代码只允许按 `target_os` 分支，鸿蒙目标走 Linux 分支，不新增鸿蒙专有代码路径。
- C 消费者在 x86_64 Linux 主机上以 AddressSanitizer 运行一次，验证头文件不依赖 Dart 专有约定；鸿蒙目标只编译不运行（CI 无鸿蒙设备）。
- 外部前提：Rust 工具链安装 `aarch64-unknown-linux-ohos` 目标（Rust 二级目标）；OpenHarmony SDK native 工具链版本在 M0 随 ADR-V5-15 锁定并缓存到 CI 镜像；SDK 下载需开发者账号时由开发团队在 M0 办理。

**验收标准**：测试方案全文见 [Test/core/S7_CORE-44_TEST.md](../Test/core/S7_CORE-44_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约200行；tools/ohos-smoke/及本卡编写的CI命令接入行（含作为交付物的consumer.c验证代码）；不计自测、夹具、说明文档、纯CI配置及生成库/报告。

