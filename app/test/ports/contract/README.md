# CORE-04 可复用端口契约测试

各 *_contract.dart 暴露 run<Port>Contract(<Port> Function() create)，只依赖正式接口和测试 SDK，不依赖 Fake 类型。平台卡将同一个函数用于真实适配器；不要把 Fake 结果当作平台认证。测试工厂每次返回隔离的端口，调用方负责注册资源清理。

## 驱动夹具

- keys：隔离密钥别名空间，允许创建/删除 contract.key。
- files：真实应用私有根、允许创建文件和兄弟目录。符号链接仅在宿主支持时执行；不支持会明确打印 pending，不宣称已验证链接行为。
- picker/camera：系统测试驱动选择/拍摄一个可重复读取的小 PNG/JPEG/WebP；后续调用开始新批次。
- clipboard：初始文本/图片均空，支持文本读写。
- notifications：系统测试驱动允许通知；覆盖预约替换和取消。点击重放/事件由 Fake 驱动测试另行验证，平台需接真实通知驱动。
- runtime：返回合法真实平台信息；lifecycle：广播事件流。
- http：GET 到 PORT_CONTRACT_HTTP_URL 返回503、X-Contract: yes、字节1,2,3；默认URL为 https://example.invalid/core04，真机运行需通过 --dart-define 配置受控测试服务，不要发往公网业务站点。
- exporter：系统对话框驱动批准保存字节1,2,3；documents：每次选中 staging 内 contract.txt，字节1,2,3。

fakes_contract_test.dart 装配11个 Fake；dto_and_fakes_test.dart 验证取消/到期/权限/缺失夹具/流异常等反例；composition_test.dart 的 composeFixture 只是 Installer 消费协议示例，不是 CORE-36 composeApp。

## 验证入口

运行 flutter test test/ports/contract。entry_test.dart 的真实ABI用例需要 FML_TEST_LIBRARY 与 FML_BUMP_LIBRARY，缺少时会 skip，不能作为完整验收。DLL来自已经接受的 CORE-03 测试构建，不打包到产品。另运行 dart run test/ports/contract/local_time_no_assert_probe.dart，显式证明关闭assert仍校验时刻。

## 语言适配与边界

LocalTime 使用普通无名构造，不支持const调用；这是本轮lead对Dart语言矛盾的最小适配批准，后续平台不得使用const LocalTime。RuntimeSnapshot只检查标签的基本形状；注册语言标签完整语义由平台负责。HttpRequestDto不实施CORE-28的HTTPS、Cookie、白名单、同意策略。FakeHttpTransport仅回放预置结果，不实现真实下载/重试策略；实际网络契约由AND-09/WIN-10完成。

R41的Android/Windows平台目录与真机系统能力由后续平台卡交付。既有check_deps.py检查Rust DEP-1至4；Dart UI/网络分层实际由check_privacy.py检查。本卡复用既有检查器，不改规则；扫描通过不等于真机适配已通过。
