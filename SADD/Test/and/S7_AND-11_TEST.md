# AND-11 测试方案

> 来源卡：[S7_AND-11_发布.md](../../and/S7_AND-11_发布.md)（打包、签名与发布）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R01] 在 CI 发布作业中 `build_release.sh` → `check_artifacts.py` → `archive_symbols.sh` 全部退出 0；用 bundletool 从 AAB 生成的设备 APK 与官网 APK 在同一真机上运行 AND-01 冒烟（显示 ABI 版本）结果一致。
- [R01] 用另一证书签名的 APK 放入 dist 时 `check_artifacts.py` 退出 1 并指出证书不符；去掉 16 KB 对齐的 .so 时退出 1。
- [R23] `dist/` 中存在 `fml-<版本>-android-symbols.zip`，其中含 mapping.txt 与 Dart 符号；`collect_artifacts.py` 的清单列出 AAB、APK 与符号包的哈希。
- [R26][R20] 对本卡产出运行 CORE-42 `scan_secrets.py` 退出 0；缺少签名环境变量时 `build_release.sh` 退出 2 且不产出未签名制品。
