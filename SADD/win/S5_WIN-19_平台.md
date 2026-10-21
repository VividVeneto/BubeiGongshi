### WIN-19 图片拖放与文件夹导入

**目标**：实现识别页的拖放接缝、单层文件夹扫描与确认，复用WIN-04受限图片复制和WIC转码，不重复实现文件对话框。

**范围**
- 包含：WindowsImageDrop、WM_DROPFILES、scanFolder、批次计数/筛选/确认、订阅与drop临时目录生命周期、installWindowsDrop接入。
- 不包含：ImagePicker/DocumentPicker/FileExporter与copyImage（WIN-04）；业务确认框/识别页（CORE-50）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-50、WIN-01、WIN-04、WIN-17

**接口契约**

定义唯一见CORE-50；以下为平台实现接缝，端口不迁到平台卡。

```dart
abstract interface class ImageDropSource {          // 平台卡经 platformInstallers 登记（WIN-19）；未登记时识别页不响应拖放
  Stream<DroppedImages> drops({Future<bool> Function(int count, int bytes, int other)? confirmFolder}); }
final class WindowsImageDrop implements ImageDropSource { WindowsImageDrop(this.files); final LocalFileStore files; }
void installWindowsDrop(CompositionContext ctx);   // 登记 ImageDropSource；追加到 ports_windows.dart 的 platformInstallers（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
```

```text
MethodChannel fml/windows/drop（app/windows/runner/image_drop.cpp；本卡唯一handler，Dart WindowsImageDrop唯一接收端；不在WIN-04的fml/windows/files上注册第二个handler）
  scanFolder {path}           → {images: [path], other: int, bytes: int}   只扫描一层，不跟随符号链接与连接点
  Dart 收到的调用：dropped {paths: [string]}                    WM_DROPFILES（DragAcceptFiles(hwnd, TRUE)）→ DragQueryFileW 全部路径
  ImageDropSource.drops：dropped 路径按扩展名分为图片与其他；某路径为文件夹 → scanFolder，调用drops的confirmFolder(count,bytes,other)，共享界面负责确认框；回调缺失按取消，平台不创建业务确认UI；
                       取消则整批丢弃；图片取前 10 张 copyImage，其余计入 skippedOverLimit，非图片计入 skippedNotImage；
                       0 张图片时仍发送批次以便提示（images 为空的批次不进入识别流程，由 CORE-50 只显示提示）
```

安装点追加到ports_windows.dart的platformInstallers，登记片段由聚合维护者单写合入，接入行计入本卡。copyImage沿用WIN-04的fml/windows/files方法：每图片max_bytes=20MiB，HEIC失败/过大/文件类型规则不另定义。

- WIN-19提供RegisterImageDropChannel(messenger, topHwnd, viewHwnd)与可注销WM_DROPFILES delegate；WIN-01聚合维护者在OnCreate登记一行并加入image_drop.cpp构建，接入行计WIN-19。scanFolder请求/结果与dropped反向InvokeMethod仅走fml/windows/drop；copyImage只调用fml/windows/files已有handler。工作结果经WIN-01队列回平台线程；detach注销delegate、DragAcceptFiles(FALSE)并停止事件，不覆盖files handler。

**实现约束**
- 拖放只在识别页订阅期间生效（CORE-50）；其他页面拖入时 `drops` 无订阅者，事件被丢弃且不复制文件。
- drop独占staging/tmp-import/drop/<batch_id>/，batch_id每次新UUID；调用copyImage复制到本批目录，末尾返回DroppedImages给CORE-50。一层scanFolder不跟随符号链接/连接点，不读用户子目录。
- 工厂发布前await drop唯一init Future，只清理上次进程已确认遗留drop目录；活动集合永不删除；到期（1h）/结束先关句柄再删自己的上批，失败下次启动补删，不触碰picker/clipboard。无订阅时不复制文件。
- 原文件路径不持久化，不删除/修改/加锁源文件；复制失败删已写部分；工作线程只计算，回复/消息在平台线程执行（WIN-01）。
- 错误码仅复用CORE-04的PLATFORM_IO/PLATFORM_UNSUPPORTED/PLATFORM_FILE_TOO_LARGE/PLATFORM_FILE_TYPE_MISMATCH；无需新增。
- 主机验收复用WIN-17协议，缺设备/桌面保持pending，S7由WIN-18汇总，不以fixture冒充真机性能。

**验收标准**：测试方案全文见 [Test/win/S5_WIN-19_TEST.md](../Test/win/S5_WIN-19_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约390行；`app/lib/platform/windows/drop/` 与 `app/windows/runner/image_drop.cpp`（拖放/扫描/确认/筛选260，drop生命周期/订阅/接入130）。不计WIN-04复制/转码实现、自测与数据。
