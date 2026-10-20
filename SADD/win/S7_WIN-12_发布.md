### WIN-12 代码签名与发布检查

**目标**：对 EXE、DLL 与安装器做 Authenticode 签名，生成更新清单，并执行 Windows 制品门禁与符号归档。

**范围**
- 包含：`tools/release/windows/` 下的构建编排、签名、签名验证、制品检查、更新清单生成与 PDB 归档脚本；Windows 发布检查清单项。
- 不包含：版本号写入、哈希汇总与 SBOM（CORE-42）；安装脚本（WIN-02）；启动器源码（WIN-16）；更新清单的托管（CORE-43）；MSIX（ADR-V5-12 不采用）。

**依赖**：CORE-01、CORE-02、CORE-42、WIN-02、WIN-03、WIN-17

**接口契约**

```text
tools/release/windows/（PowerShell 7 与 Python 3；退出码约定同 CORE-42：0 成功 / 1 门禁失败 / 2 脚本错误）
  build_release.ps1 -Version <x.y.z> -ApiHost <host> -PackHost <host> [-Unsigned]
      1 flutter build windows --release --dart-define=FML_API_HOST=… --dart-define=FML_PACK_HOST=…
      2 cmake 构建 installer/windows/launcher（Release，/Brepro）
      3 未给 -Unsigned 时 sign.ps1 仅签名本项目生成的 runner、fmlcore.dll、启动器；Flutter/插件/微软运行库作为供应方制品，保持原字节与签名，按 dependency-pes.json 记录来源/哈希/签名策略
      4 ISCC（WIN-02 参数；未给 -Unsigned 时传 /DSignToolName=fmlsign 与 /Sfmlsign="pwsh sign.ps1 $f"）→ dist\BubeiGongshi-<v>-setup.exe
      5 verify_signatures.ps1、check_artifacts.py、archive_symbols.ps1、gen_update_manifest.py 依次执行，任一非 0 即停止
  sign.ps1 <path…>
      硬件令牌：signtool sign /fd SHA256 /tr $env:FML_SIGN_TIMESTAMP_URL /td SHA256 /sha1 $env:FML_SIGN_CERT_THUMBPRINT <path>
      云签名：设置 $env:FML_SIGN_COMMAND 时改为执行该命令（{path} 占位）；两个变量都缺失 → 退出 2
  verify_signatures.ps1 -Dir <dir>   对自有 PE 文件 signtool verify /pa /all，并核对实际签名叶证书 DER SHA-256 在 signer-pins.json；依赖 PE 按 dependency-pes.json 的锁定哈希与供应方签名策略校验，未知 PE 拒绝
  check_artifacts.py --setup <exe> --build <dir>
      安装器字节 ≤ CORE-01 预算表“安装包”行的 Windows 值（70 MB）；
      构建输出与安装器解包内容（innounp 或 ISCC 输出清单）不含 .pdb、.map、测试证书；
      对全部文件做密钥字符串扫描（CORE-41 secret_scan 规则）；fmlcore.dll 的 dumpbin /dependents 不含 vcruntime140.dll
  archive_symbols.ps1 -Version <v>   先断言三个 PDB 存在且非空（缺失退出1），再复制 bubeigongshi_app.pdb、fmlcore.pdb、BubeiGongshi.pdb 到 dist\symbols\<v>\ 并写 SHA256SUMS
  gen_update_manifest.py --setup <exe> --version <v> --pack-host <host> --notes <md>   输出 dist\windows\update.json（格式见 WIN-03）
  signer-pins.json                   {"schema":1,"cert_sha256":["<64位小写hex>"]}；生成 WIN-03 编译期白名单
  dependency-pes.json                {"schema":1,"files":[{"path":"<相对路径>","sha256":"<64hex>","signature":"microsoft|vendor|hash-only","source":"<锁定发布来源>"}]}；禁止路径穿越，微软 DLL 必须有效微软签名
```

- 错误码：脚本不经核心，不使用错误码。

证书轮换：先发布含旧/新双指纹、仍由旧证书签名的桥接版本，再以新证书发布；未安装桥接版的客户端引导手动安装。不从网络清单扩展信任；CN 不作为身份依据。供应方二进制绝不重签（ADR-V5-37）。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

产品约束追踪：见README §6 Q39；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 签名私钥只在硬件令牌或云签名服务中，不进入仓库、普通 CI 变量与构建日志；时间戳服务必须使用 RFC 3161。
- 代码签名不保证立即获得 SmartScreen 信誉；发布说明不承诺 EV 证书一定消除拦截。
- 不产出 MSIX：启动器与版本子目录布局（WIN-02、WIN-16）与 MSIX 的只读安装目录和自身更新机制冲突（ADR-V5-12）。
- 外部前提：代码签名证书（OV 或 EV）与时间戳服务由甲方在 S7 开始前提供；Inno Setup、Windows SDK（signtool）版本见 `app/windows/toolchain.versions`（WIN-01，ADR-V5-15）。

**验收标准**：测试方案全文见 [Test/win/S7_WIN-12_TEST.md](../Test/win/S7_WIN-12_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 250 行；`tools/release/windows/`。

