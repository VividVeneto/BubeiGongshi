# CORE-101 测试方案

> 来源卡：[S5_CORE-101_功能.md](../../core/S5_CORE-101_功能.md)（识别存储压力与档案守护）。本文件保存由CORE-50拆出的全部存储守护验收及新增会话生命周期断言；自“**验收标准**”行起由材料工具拼回来源卡。修改来源卡时同步修改。本卡未独立整卡复核，以下是待实现的测试方案，不是运行通过记录。

**验收标准**
- [R33] 原CORE-50迁移断言：FakeLocalFileStore.freeBytes 返回400 MiB时，每档案首次ProfileHooks order55后恰好提交一次recog.gc，任务成功完成后StorageStatus=true；10分钟内再次resumed不重复提交。提示文案与/settings/history跳转UI只读消费测试保留于CORE-50，守护不依赖UI。
- [R33] 容量边界499/500/599/600 MiB：仅<500触发GC；500至不足600维持先前状态；≥600置false。false状态遇500不得凭空变true，true状态遇599不提前清除；GC失败不得虚报已清理。重复resumed/lowMemory并发只共享一次Future，10分钟恰到边界可重新检查。
- [R25][R33] 安装只构造一个StorageStatus、一份生命周期订阅；预先登记HistoryKeyUnlocker后才成功，缺失前置实例安装失败。ProfileHooks order55每个新handle恰好一次，不复制普通StartupHook、不重跑进程或首帧动作，登记回执owner为CORE-101。本卡无CORE-50/识别流程import。
- [R25][R33] FakeProfileSessionSource驱动null→A→closing/null→B，B同profileId不同handle仍新检查；null时无ensure/freeBytes/FFI/GC，A水位不得跳过B首次检查。A close在第一个异步取消前即观察到current=null、StorageStatus=false。
- [R25][R33] 对ensure、freeBytes、提交GC、等待GC完成及状态发布前后逐项设置屏障切换档案：每个调用固定捕获session.core，不向B提交A的GC，A迟到结果不能修改B状态。ensure因平台密钥失效/库与密钥不匹配已完成clear=true轮换并清空历史而返回true时仍继续，false也继续；断言true不解释成软件密钥后端警告，抛错则无GC；now_ms为本次调用边界一次UTC毫秒，绝不发送空body。
- [R25][R33] beforeClose先同步停止所有新检查/重试并取消，再等待已发ensure/文件查询/GC/清理；与较早ProfileHooks及HistoryKeyUnlocker停止前缀同一轮全启动，不形成相互等待。已提交GC事务完成后才允许native close，不能伪称取消回滚；注入取消/GC/清理失败则closing/null、A未close/B未open，显式重试只补未完成项。
- [R25][R33] A关闭后resumed/lowMemory不复活旧任务，订阅总数仍1；只清理本守护持有的staging副本，不删除Pin图片/持久历史/其他VM文件。检查与关闭日志无密钥/图片/私有路径，取消错误复用CORE-03通道，不新增业务码。
