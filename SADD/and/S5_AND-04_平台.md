### AND-04 相机

**目标**：用 CameraX 拍摄公式照片，取景时给出实时质量提示，用完立即释放相机，照片只进私有临时目录。

**范围**
- 包含：`CameraController` 端口实现；原生全屏取景 Activity（CameraX `PreviewView`，提示叠加层用原生视图绘制）；实时质量提示（清晰度、曝光、倾斜）；拍摄与写入临时目录；后台与中断时释放。
- 不包含：拍后预处理（CORE-30）；裁剪与识别界面（CORE-40）；权限对话框（AND-02 `PermissionService`）。

**依赖**：CORE-01、CORE-02、CORE-04、AND-02、AND-15

**接口契约**

实现的端口（CORE-04，逐字摘录）：

```dart
abstract interface class CameraController {
  Future<ImportedImage?> capture();                           // 用户取消返回 null；只写应用私有目录
}
```

本卡实现：

```dart
// app/lib/platform/android/camera/android_camera.dart
final class AndroidCameraController implements CameraController {
  AndroidCameraController(this.permissions);   // AND-02 PermissionService
  final PermissionService permissions;
  // capture()：① permissions.request(camera, rationaleKey: 'camera_rationale')，非 granted 抛 PLATFORM_PERMISSION_DENIED
  //            ② 通道 capture → null 返回 null；否则包装为 ImportedImage（mimeType 'image/jpeg'）
}
```

```text
MethodChannel "fml/android/camera"（CameraBridge.kt）
  capture → {name, mime: "image/jpeg", size, tmp_path} 或 null
            启动 CameraActivity（全屏，跟随系统旋转，方向处理见下）；拍照写入 cacheDir/camera/<UUID>.jpg（CameraX ImageCapture，JPEG 质量 95，
            写入时去除 GPS 等 EXIF，只保留方向）；用户返回或取消 → null；相机被占用或不存在 → 抛 PLATFORM_UNSUPPORTED
实时提示（CameraActivity 内，ImageAnalysis 640×480 YUV，后台线程，每秒 ≤ 10 次）：
  清晰度 = Y 平面拉普拉斯方差，< 阈值 → “请对焦或保持稳定”
  曝光   = Y 平面均值，< 50 → “光线太暗”；> 205 → “光线过亮”
  倾斜   = 加速度计与竖直方向夹角，> 15° → “请把手机放平”
阈值写在 CameraBridge.kt 常量中，AND-12 真机标定后可调
```

方向处理（README §6 Q17；不再锁定竖屏）：

| 项 | 规则 |
| --- | --- |
| 清单 | CameraActivity 不声明 `screenOrientation`；`configChanges="orientation\|screenSize\|smallestScreenSize\|screenLayout"`，旋转与分屏时不重建、不重新绑定相机（避免取景黑屏） |
| 预览 | CameraX `PreviewView`（`FILL_CENTER`）随显示旋转自动校正方向与缩放 |
| 成像方向 | `OrientationEventListener` 按设备物理方向（以 45° 为界取 0/90/180/270）设置 `ImageCapture.targetRotation`；系统锁定竖屏时横持拍摄，照片仍按横向正立记录 |
| 方向写入方式 | 只写 EXIF Orientation，不旋转像素；由 CORE-30 解码时按 EXIF 修正方向 |
| 界面 | 竖屏时快门与返回在底部，横屏时在右侧（`layout-land`）；快门直径不小于 64 dp，其他按钮不小于 48 dp；提示文字随显示方向 |

- 错误码：`PLATFORM_PERMISSION_DENIED`、`PLATFORM_UNSUPPORTED`（CORE-04 登记）；本卡不新增错误码。

质量提示复用CORE-30的8位灰度Laplacian初值100（低于提示模糊），不自行定义不同单位；硬件标定由AND-12按100图集完成。capture只允许一个在途请求：先写cacheDir/camera/pending-<uuid>.json（schema=1,relative_path（相对 cacheDir/camera/，即 <UUID>.jpg）,state=writing|ready,created_ms），照片先临时写、fsync后rename并将state原子置ready；进程重建后下一次capture优先取≤1h的ready结果并弹出恢复预览，用户取消就清理；writing/过期/损坏记录删除自有残留并提示重拍。旧进程MethodResult丢失不补发，重新attach的调用才取得结果。

临时目录仅camera自有；启动先读取pending日志并恢复尚有效ready文件，再按日志清理过期/中断项，不能被picker启动清理删除。初始化与capture串行，完成清理后才创建新文件；不同适配器批次互不失效。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

**实现约束**
- 预览帧不复制到 Dart；提示文案在原生 `strings.xml`（简体中文）。
- 照片不写相册、不写 MediaStore；临时副本的过期与清理规则同 AND-03（`ImportedImage` 1 h）。
- CameraActivity 进入 `onPause`（Home、来电、分屏失焦）时立即解绑全部用例并释放相机；返回后重新绑定。
- 相机不可用时由调用方（CORE-40）提示并提供相册导入入口。
- 旋转时不调用 `unbindAll`；只有 `onPause` 才释放相机。
- 外部前提：CameraX（`camera-core`、`camera-camera2`、`camera-lifecycle`、`camera-view`）版本随 ADR-V5-15 锁定。

**验收标准**：测试方案全文见 [Test/and/S5_AND-04_TEST.md](../Test/and/S5_AND-04_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 420 行；`app/lib/platform/android/camera/` 与 `app/android/.../CameraBridge.kt`、`app/android/.../CameraActivity.kt`（同属 `app/` 构建单元）。

