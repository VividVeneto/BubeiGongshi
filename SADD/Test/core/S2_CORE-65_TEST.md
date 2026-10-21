# CORE-65 测试方案

> 来源卡：[S2_CORE-65_账户.md](../../core/S2_CORE-65_账户.md)（账户客户端控制器与安全令牌存取）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

- [R24][R27] Fake Completer屏障：close(A)同步前缀已current=null且新业务零次；drain未完成时native close/openB零次，A/null/B顺序。beforeClose冻结列表，第一项抛错仍启动其余stop，等待全部settle后按登记顺序报错；失败保持closing/null，显式重试只跑失败阶段。两个并发close共享Future，成功后幂等；重复id拒绝，注销不撤销已冻结drain。同profile新handle拒收旧回调。
- [R24][R27] 早登记ProfileHooks的drain等待晚登记特性任务，晚登记stop同步发取消信号：全部回调先启动才await，无死锁；首回调失败仍调用所有stop且native close/openB零次。旧unwrap/refresh/save晚到不落B的profile_blob，明文Uint8List及副本在所有异常路径全零；String只释放引用。
- [R24][R25] Fake 端口注册/登录/游客路径改变客户端状态；登出后进入 registeredLocked，重新登录恢复；切换档案先关闭旧库。
- [R27] 刷新令牌仅包装密文落 profile_blob，访问令牌仅内存，登出清理。
- [R27] 删除本地数据：未二次确认时 account.delete_profile 与 keys.delete 零次；确认后调用顺序严格为 set_logged_out(true) → close_profile(lock:true) → delete_profile → keys.delete('fml.<id>.db') → uninitialized；Fake delete_profile 返回 STORE_BUSY 时 keys.delete 零次、状态保持 registeredLocked，重试成功后才删别名。open_profile 成功后 touch_last_used 恰一次且 now_ms 取注入时钟；其失败不关闭档案。

- [R24][R27] Fake连续切换A→B：在A请求未排空前B的open不执行，changes依次A/null/B；close失败时仍为null；创建后的wrap/put_blob/open每处注入失败，明文临时缓冲均填零且没有Unlocked通知。
