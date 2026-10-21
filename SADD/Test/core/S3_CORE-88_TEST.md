# CORE-88 测试方案

> 来源卡：[S3_CORE-88_界面.md](../../core/S3_CORE-88_界面.md)（公式编辑与草稿界面）。本文件是该卡“验收标准”字段的全文；修改功能时同步更新。工具自“**验收标准**”行起拼回卡片。

**验收标准**
- [R08] 编辑页：含空位或 Error 时保存禁用；Warning 时确认后修订带 `ConfirmRecord`；编辑中杀进程，重开编辑页提示恢复草稿且源码、声明、标题一致。
- [R42.e][R42.b] 页面接入验收：/library/:itemId/edit标题输入“动能”，源码E_k=\frac{1}{2}mv^2、光标在m前，360×800↔800×360往返3次；页面State同一对象，标题、源码、光标与焦点不变，期间不发library.*调用、不另存草稿；textScaler 2.0无异常，编辑页恰有1个primary“保存”。
- [R08] /library/new接受NewFormulaArgs(latex)，成功保存后pop返回Saved；存在new草稿时先询问恢复/放弃，保存成功清除对应草稿。
