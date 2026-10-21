### CORE-51 资源包下载、导入与管理界面

**目标**：在两端以同一 Dart 实现完成资源包的更新检查、断点续传下载、安装、离线导入、卸载，以及按教育阶段与学科筛选的资源包管理页。

**范围**
- 包含：`PackService`（下载更新元数据 → `pack.check_updates` → 下载包文件 → `pack.install`；离线导入；卸载）；资源包管理页 `/packs`（已安装、可下载与可更新、筛选、进度、错误与续传）；启动后的后台更新检查（只检查不下载）；安装点 `installPacks`。
- 不包含：格式验签与安全读取（CORE-15）、设备安装激活与恢复（CORE-95）、TUF 防回滚（CORE-96）；包内容制作（CORE-16）；CDN 与元数据重签（CORE-43）；模型包卸载前的模型释放（CORE-35 经 CORE-95 卸载钩子完成）；存储紧张时的识别历史清理（CORE-50）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-15、CORE-36、CORE-55、CORE-28、CORE-58、CORE-95、CORE-96

**接口契约**

```dart
// app/lib/packs/pack_service.dart
final class PackOfferDto {
  final String packId, version, subject, educationLevel /* high_school | university | any */, urlPath, blake3Hex;
  final int sizeBytes;
  final bool upgrade;                 // 本机已装该包的较低版本
}
// InstalledPackDto由CORE-95完整InstalledPack schema经CORE-67生成，禁止本地截断定义。
sealed class PackTaskState { const PackTaskState(); }
final class PackDownloading extends PackTaskState { final int received, total; }
final class PackInstalling extends PackTaskState {}
final class PackDone extends PackTaskState { final InstalledPackDto pack; }
final class PackFailed extends PackTaskState { final String errorCode; final bool resumable; }

final class PackService {
  PackService({required CoreBinding core, required HttpTransport http, required LocalFileStore files,
               required DocumentPicker documents, required Uri packBase});
  ValueListenable<List<PackOfferDto>> get offers;                 // 最近一次检查结果（已过滤掉本机已装的同版本）
  Future<List<InstalledPackDto>> installed();                      // pack.list
  Future<List<PackOfferDto>> checkUpdates();                       // 见实现约束 ①
  Stream<PackTaskState> download(PackOfferDto offer, {CancelToken? cancel});   // 同时只执行一个任务，其余排队；同一 packId 重复调用返回同一流
  Future<InstalledPackDto?> importFile();                          // DocumentPicker.pick(extensions: ['fmlpack'], maxBytes: 256 MiB) → pack.install；取消返回 null
  Future<void> uninstall(String packId);                           // pack.uninstall；bootstrap-pack 不提供入口
}

// app/lib/packs/routes.dart（页面在 app/lib/ui/packs/，只收 VM 与 deps.ui）
List<GoRoute> packRoutes(AppDeps deps);                            // /packs
final class PacksVm extends ChangeNotifier {
  PacksVm(this._service);
  String? levelFilter; String? subjectFilter;                      // null = 全部；取值同 PackOfferDto
  List<InstalledPackDto> get installedPacks; List<PackOfferDto> get visibleOffers;
  PackTaskState? taskOf(String packId);
  Future<void> refresh(); Future<void> download(PackOfferDto o); Future<void> cancel(String packId);
  Future<void> importFile(); Future<void> uninstall(String packId);
}
// app/lib/packs/install.dart
void installPacks(CompositionContext ctx);   // 登记 PackService；order 10 恢复钩子与 order 15 更新检查钩子
```

- 错误码（本卡登记）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `PACK_STORAGE_LOW` | warning | 是 | 下载或导入前 `freeBytes()` < 包大小 × 3 + 100 MiB |
| `PACK_DOWNLOAD_INCOMPLETE` | warning | 是 | 下载结束时 `.part` 文件长度不等于 `sizeBytes` |

- 界面行为：`NET_*` 与 `PACK_DOWNLOAD_INCOMPLETE` 显示“下载中断”与“继续”按钮（`resumable = true`）；`PACK_*` 安装错误（CORE-15）显示对应文案并删除下载文件，旧版本保持可用；`PACK_METADATA_EXPIRED` 显示“更新信息已过期，请稍后重试或校准系统时间”，已安装内容照常使用。

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/packs/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/packs/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

pack.check_updates/install的完整响应分别是CORE-96 PackOffer[]/CORE-95 InstalledPack（pack_version等Rust字段名按schema生成，VM可派生version展示）；本卡不得手写删字段的InstalledPackDto冒充wire DTO。schema未实现前DTO门禁pending，见CORE-67/H6。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 下载与导入进度用 `LoadingState` 的确定进度形态，可取消；失败与可续传状态用 `showFmlToast` 与行内重试按钮，不弹阻塞对话框。
- ① 更新检查：经 `http`（组装后即 CORE-28 的 NetworkGuard）以 `purpose: updateCheck` 依次 GET `<packBase>/packs/metadata/{root,timestamp,snapshot,targets}.json`，四份原文 base64 后 `core.call('pack.check_updates', {root, timestamp, snapshot, targets})`；结果与 `pack.list` 比较，去掉已装同版本，标记 `upgrade`。游客同样可检查（CORE-28 允许 `updateCheck` 与 `packDownload`），请求不带账户令牌。
- ② 下载：目标文件 `root(StoreArea.staging)/<pack_id>-<version>.fmlpack.part`；已存在且长度 L < `sizeBytes` 时以 `rangeStart: L` 续传；`HttpRequestDto(method: get, url: packBase.resolve(urlPath), purpose: packDownload, saveTo: part, timeout: 60 s + sizeBytes / 128 KiB 秒)`；进度每 500 ms 读取 `.part` 长度；完成后长度不符 → `PACK_DOWNLOAD_INCOMPLETE` 并保留文件。
- ③ 安装：`core.submit('pack.install', {file, expected_size, expected_blake3})`；成功或安装错误后删除 `.part`；网络错误保留以便续传；`.part` 超过 7 天未完成时在下次检查时删除。
- ④' 启动钩子 order 10：按 CORE-95 执行 `pack.recover`、缺失时安装随应用分发的 bootstrap 包、`pack.list`；失败记录 `AppLog` 并继续（引擎保留内置层），不弹窗。
- ④ 启动钩子 order 15：`unawaited` 执行一次 `checkUpdates`，失败只记录 `AppLog`；有可更新项时管理页入口显示圆点；V1 不自动下载，也不区分 Wi-Fi 与蜂窝网络，下载前显示大小由用户确认。
- 管理页按 `educationLevel`（全部 / 高中 / 大学）与 `subject`（全部 / 数学 / 物理）筛选；已安装区显示版本与“卸载”（`bootstrap-pack` 与被依赖的包不显示卸载，后者以 `PACK_DEP_MISSING` 兜底）。
- 组装：`installPacks` 追加到 CORE-36 `installers.dart` 的 `featureInstallers` 末尾；`packRoutes` 追加到 `app/lib/composition/routes.dart`；页面只收 VM 与 `deps.ui`。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 外部前提：无新增第三方库（`ValueListenable` 来自 Flutter SDK）。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-51_TEST.md](../Test/core/S4_CORE-51_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约700行，分阶段（Ⅰ 元数据、下载队列与安装卸载编排约365行；Ⅱ 启动恢复/清理、任务VM、管理页及接入约335行；各阶段可独立构建与测试）；app/lib/packs/、app/lib/ui/packs/及本卡编写的composition/bootstrap接入行；不计自测、夹具、包资源数据与生成物。

