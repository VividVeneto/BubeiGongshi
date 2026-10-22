### CORE-74 unsafe、ABI与错误注册表门禁

**目标**：检查unsafe边界、公开头文件兼容和生成错误码漂移。

**范围**
- 包含：从CORE-41拆出的UNSAFE-1/2、ABI-1、ERR-1～4及测试。
- 不包含：词法共用层（CORE-69）、CI编排。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-69

**接口契约**
只导入CORE-69的 `Finding`、`emit`、`run` 与0/1/2退出码，不复制common类型；rule取 `UNSAFE-1`、`UNSAFE-2`、`ABI-1`、`ERR-1`～`ERR-3`。`check_unsafe.py --root .`：UNSAFE-1是unsafe白名单——只允许fml-ffi/fml-imgproc/fml-recognize-local，其他crate出现 `unsafe` 块、`unsafe fn` 或 `unsafe` 修饰报1；UNSAFE-2是注释门禁——每块unsafe的起始行前3行内须有 `// SAFETY:`，缺失、注释内容为空或仅标点报1。`check_abi.py --header contracts/include/fmlcore.h [--base-ref <tag>] [--first-release]`：解析CORE-03固定C子集的函数名/参数类型文本/返回类型文本/struct字段名与类型文本顺序/`#define` 宏及 `FML_ABI_MAJOR`、`FML_ABI_MINOR`；只比较字段顺序与类型文本，不计算sizeof/offset/对齐（跨目标不可比）。基准取值顺序：显式 `--base-ref` 优先，否则自动取 `abi-v<MAJOR>.<MINOR>.<PATCH>` 标签中版本最高、且 `git merge-base --is-ancestor <tag> HEAD` 成立的一个；SADD文档标签（`sadd-v*`、`archive/*`）与其他标签不参与选择，`--base-ref` 指向非 `abi-v*` 标签即报2（不误用文档标签）。基准头文本用 `git show <tag>:contracts/include/fmlcore.h` 读取（subprocess数组参数、不经shell）；git不可用、标签不存在、该文件在基准中缺失或非零退出报2。删除函数或宏、改参数或返回类型文本、增删或重排struct字段而未同时提升 `FML_ABI_MAJOR` → ABI-1；新增函数或宏而未提升 `FML_ABI_MINOR` → ABI-1；两个版本号只能相对基准单调提升。`--first-release` 只在没有任何 `abi-v*` 基准时合法：输出 `ABI baseline: first-release`，只做自包含baseline fixture校验并返回0，不声称历史兼容；与 `--base-ref` 或已有 `abi-v*` 标签同时给出报2。`git rev-parse --is-shallow-repository` 为true且未给 `--base-ref` 时报2并提示 `fetch-depth: 0` 或 `--first-release`；无基准、未标首发、非浅clone同样报2，不伪造比较通过。`check_errors.py --registry contracts/errors/registry.yaml [--root .]`：只扫描CORE-02前缀表对应的大写字面量，`FML_` 程序标签不纳入；参与比较的生成物固定为CORE-02的五个投影（`crates/fml-error/src/codes.rs`、`app/lib/binding/error_codes.g.dart`、`contracts/errors/README.md`、`contracts/errors/ownership.yaml`、`contracts/policies/shared-writes.json` 的error投影），与registry一致返回0，任一投影漂移或生成物缺失报ERR-1（1），registry或生成物不可解析（YAML/生成块语法错误）报2；未注册字面量报ERR-2；重复定义（同code多条、同message_key多码、owner与ownership.yaml投影不一致）报ERR-3。ERR-4只在registry不存在阶段核对SADD唯一定义并输出“实现注册表未启用”，退出2（不记产品门禁通过、不假过）；SADD文档侧错误码一致性（多卡重复定义、owner与shared-writes投影不符）唯一归DTOcheck的XREF-01～05，本卡不重复实现，registry按CORE-02创建且生成器 `--check` 跑通后ERR-4关闭。消费卡错误表仅三列引用/所有者/本卡处理，定义表按CORE-02四列（服务端加HTTP）。

**实现约束**
- 不维护第二前缀表（前缀与登记唯一来自CORE-02），ABI解析只支持公共头所用语法；版本主变更仍需BREAKING CHANGE及ADR。
- 逐组件实现估算：unsafe70、ABI175、errors135、公共入口接入20，合计400；正反例测试与夹具不计，词法层复用CORE-69且不重复计。
- 与CORE-41的单写边界：`tools/ci/manifest.json` 的三个步骤行与 `.github/workflows/ci.yml` 的ABI作业行属CORE-41单写文件，本卡只提交片段（步骤id/owner/argv、`fetch-depth: 0`），由CORE-41所有者合入；规模只计本卡三个脚本文件内的代码，“公共入口接入20”指各脚本的 `main`、参数解析与退出码收敛。
- 外部前提：锁定Python/PyYAML，基准Git标签（`abi-v*` 由发布流程创建）；尚无标签时只有自包含基准fixture通过，不声称历史ABI兼容。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-74_TEST.md](../Test/S0/S0_CORE-74_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约400行；tools/ci/check_unsafe.py、check_abi.py、check_errors.py及本卡编写的公共入口接入行（各脚本的main与参数解析）；不计自测、夹具、registry/schema数据、生成头文件与报告；复用CORE-69公共词法而不重复计。
