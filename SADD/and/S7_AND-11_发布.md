### AND-11 打包、签名与发布

**目标**：从同一提交产出签名的 AAB（应用商店）与 APK（官网），执行 Android 专属发布检查并归档符号与 mapping。

**范围**
- 包含：`tools/release/android/` 三个脚本；`app/android/app/build.gradle.kts` 的 release 段（签名配置读取环境变量、R8 与 ProGuard 规则、ABI 过滤）；国内应用市场上架材料清单（`tools/release/android/store_materials.md`）。
- 不包含：版本号写入、哈希汇总、体积门禁、密钥扫描、SBOM（CORE-42 `tools/release/`，本卡只调用）；清单权限检查脚本（AND-02）；真机性能（AND-12）。

**依赖**：CORE-01、CORE-02、CORE-42、AND-01、AND-02、AND-15

**接口契约**

调用（CORE-42，命令行约定：退出码 0 成功 / 1 门禁失败 / 2 脚本错误）：`bump_version.py <x.y.z>`、`collect_artifacts.py --dist dist/`、`size_gate.py --dist dist/`、`scan_secrets.py --dist dist/`、`sbom.py --out dist/sbom.json`；AND-02 `tools/ci/check_android_manifest.py`。

```text
tools/release/android/（本卡实现，退出码约定同上）
  build_release.sh --dist dist/
      需要环境变量 FML_ANDROID_KEYSTORE（base64 的 .jks）、FML_ANDROID_KEYSTORE_PASSWORD、FML_ANDROID_KEY_ALIAS、FML_ANDROID_KEY_PASSWORD，
      FML_API_HOST、FML_PACK_HOST；缺任一 → 退出 2
      flutter build appbundle --release --split-debug-info=build/symbols/android --obfuscate --dart-define=...
      flutter build apk --release --target-platform android-arm64 （同一参数）
      产出 dist/fml-<版本>.aab、dist/fml-<版本>-arm64.apk
  check_artifacts.py --dist dist/
      ① apksigner verify --print-certs：证书 SHA-256 等于 tools/release/android/cert_sha256.txt
      ② zipalign -c -P 16 -v 4 通过，且每个 .so 的 LOAD 段对齐 ≥ 16 KB（readelf -lW）
      ③ AndroidManifest：android:debuggable 不存在或为 false；调用 check_android_manifest.py 通过
      ④ bundletool build-apks --mode=universal 后与 APK 的 classes.dex 数量与 .so 列表一致
      任一失败 → 退出 1，并逐项输出失败原因
  archive_symbols.sh --dist dist/
      打包 build/symbols/android（Dart 符号）、build/app/outputs/mapping/release/mapping.txt、
      未裁剪的 libfmlcore.so 调试符号 → dist/fml-<版本>-android-symbols.zip
store_materials.md：隐私政策链接、权限用途说明（对应 AND-02 白名单逐项）、SDK 与第三方库清单（由 sbom.json 生成）、
                    域名清单（FML_API_HOST、FML_PACK_HOST）、应用备案号与软件著作权登记号（发布前由甲方提供）
```

- 错误码：本卡不产生运行时错误码。

未裁剪Rust符号唯一来源为target/<Rust-target>/release/libfmlcore.so（cargoNdkBuild完成、strip前），复制到dist/symbols/<AppVersion>/<abi>/libfmlcore.so并附BLAKE3/build-id。Android合并库检查路径为app/build/app/intermediates/merged_native_libs/release/mergeReleaseNativeLibs/out/lib/<abi>/libfmlcore.so（Flutter构建目录重定向以实际Gradle任务输出为准），该处只核对打包来源，不能假设合并库仍保留全部符号；符号归档不得从stripped_native_libs回拷。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

产品约束追踪：见README §6 Q1、Q39；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 签名密钥只来自 CI 受保护环境变量，脚本把 .jks 解码到临时目录并在退出时删除；仓库中不得出现 keystore 文件与口令（`.gitignore` 含 `*.jks`、`key.properties`）。Google Play 使用 Play App Signing 时，本密钥为上传密钥。
- AAB 与 APK 必须由同一次 `build_release.sh`、同一提交、同一 `--dart-define` 产出。
- R8 规则保留 Flutter 引擎与各 MethodChannel 处理类；JNI 不需要保留规则（核心库经 `dart:ffi` 加载，不经 JNI）。
- 外部前提：Android SDK build-tools（`apksigner`、`zipalign`，版本 ≥ 35 以支持 `-P 16`）、`bundletool`、NDK 的 `llvm-readelf`；版本写入 `app/android/toolchain.versions`（ADR-V5-15）。

**验收标准**
- [R01] 在 CI 发布作业中 `build_release.sh` → `check_artifacts.py` → `archive_symbols.sh` 全部退出 0；用 bundletool 从 AAB 生成的设备 APK 与官网 APK 在同一真机上运行 AND-01 冒烟（显示 ABI 版本）结果一致。
- [R01] 用另一证书签名的 APK 放入 dist 时 `check_artifacts.py` 退出 1 并指出证书不符；去掉 16 KB 对齐的 .so 时退出 1。
- [R23] `dist/` 中存在 `fml-<版本>-android-symbols.zip`，其中含 mapping.txt 与 Dart 符号；`collect_artifacts.py` 的清单列出 AAB、APK 与符号包的哈希。
- [R26][R20] 对本卡产出运行 CORE-42 `scan_secrets.py` 退出 0；缺少签名环境变量时 `build_release.sh` 退出 2 且不产出未签名制品。

**规模**：约 260 行；主包 `tools/release/android/`（约 220 行），附属：`app/android/app/build.gradle.kts` release 段与 `proguard-rules.pro`（约 40 行）。

