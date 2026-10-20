# WIN-10 测试方案

> 来源卡：[S2_WIN-10_平台.md](../../win/S2_WIN-10_平台.md)（网络传输）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R01] CORE-04 `HttpTransport` 契约套件对本实现通过（测试服务器 `integration_test/windows/http_server.dart`，测试 CA 只在测试构建中信任）。
- [R30] 续传：服务器发送一半后断开 → `NET_OFFLINE` 且保留已收字节；以 `rangeStart` 重发收到 206 后哈希一致；返回 200 时截断重写且哈希一致。
- [R26] 组合CORE-28包装后http/Cookie请求在守卫被拒，inner未收到请求；底层自签名证书返回NET_TLS；非测试构造器拒绝testContext。
- [R40] 服务器延迟 40 s、`timeout` 30 s 时抛 `NET_TIMEOUT`；进行中 `cancel()` 后 1 s 内抛 `FfiCancelled`。
- [R01] 在“设置 → 网络 → 代理”配置静态代理后，请求经该代理发出（代理日志可见）。
