### WIN-02 安装器与卸载

**目标**：用 Inno Setup 提供按用户安装、无需管理员权限的官方安装器；卸载默认保留用户数据，删除数据须用户明确选择并二次确认。

**范围**
- 包含：`installer/windows/bubeigongshi.iss` 安装脚本（ADR-V5-12 选定 Inno Setup 6）；程序文件放置与经 WIN-16 `--register-install` 的版本登记；开始菜单快捷方式与 AppUserModelId；更新模式参数 `/UPDATE=1`；安装前空间检查与降级拦截；卸载选项与清理；简体中文界面文本。
- 不包含：启动器（WIN-16）与更新下载（WIN-03）；代码签名与构建脚本（WIN-12 调用 ISCC 并签名）；数据库迁移（CORE-13）。

**依赖**：CORE-01、CORE-02、CORE-42、WIN-01、WIN-16、WIN-17

**接口契约**

```text
安装布局（per-user；完整文件清单与控制文件格式以 WIN-16 为准，本卡只放置程序文件）：
  %LOCALAPPDATA%\Programs\BubeiGongshi\
    BubeiGongshi.exe        启动器（WIN-16 构建；快捷方式、开机自启都指向它）
    app-<version>\          WIN-01 构建输出（bubeigongshi_app.exe、fmlcore.dll、flutter_windows.dll、data\）
    current.txt、pending.txt、journal.json 等控制文件   只由 WIN-16 写入；安装器经 --register-install 登记版本
  用户数据根：%LOCALAPPDATA%\BubeiGongshi\（布局见 WIN-07）；注册表：HKCU\Software\BubeiGongshi（WIN-06）

ISCC 调用（由 WIN-12 build_release.ps1 执行）：
  ISCC /DAppVersion=<x.y.z> /DBuildDir=<app 构建输出> /DLauncher=<BubeiGongshi.exe> [/DSignToolName=fmlsign /Sfmlsign=<命令>] bubeigongshi.iss
  输出 dist\BubeiGongshi-<x.y.z>-setup.exe

关键指令：AppId={{<M0 生成后固定的 GUID>}；PrivilegesRequired=lowest；DefaultDirName={localappdata}\Programs\BubeiGongshi；DisableDirPage=yes；
          ArchitecturesAllowed=x64compatible；ArchitecturesInstallIn64BitMode=x64compatible；MinVersion=10.0.17763；
          AppMutex=Local\BubeiGongshi.SingleInstance（与 WIN-06 同名，Setup/Uninstall启动时均检查）；CloseApplications=no；
          Compression=lzma2/max；SolidCompression=yes；定义 SignToolName 时 SignTool={#SignToolName} 且 SignedUninstaller=yes
快捷方式：{userprograms}\BubeiGongshi.lnk → {app}\BubeiGongshi.exe，AppUserModelID: "BubeiGongshi.App"

[Code] 规则：
  InitializeSetup    可用空间 < 3 × 安装后体积 → 提示并中止；已安装 current.txt 版本高于 AppVersion → 提示“已安装更新的版本”并中止
  IsUpdateMode       ExpandConstant('{param:UPDATE|0}') = '1'（命令行含 /UPDATE=1）
  [Files] 启动器     不用 onlyifdoesntexist，按 Inno 默认版本比较（仅 FileVersion 更高时替换，版本由 WIN-16 单独维护），
                     并加 Check: ShouldInstallLauncher（Result := not IsUpdateMode and not CheckForMutexes('Local\BubeiGongshi.Launcher')）：
                     更新模式与启动器运行中都不替换；首版固定 launcher_protocol=1，协议不兼容须停止更新并走专项安装迁移 ADR，不能静默替换。
  ssPostInstall      普通模式：Exec(ExpandConstant('{app}\BubeiGongshi.exe'), '--register-install {#AppVersion}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)；首次安装由其写 current，
                     已有 current 时登记 pending，不能绕过验证；退出码非 0（启动器正在验证/恢复或 10 s 内拿不到互斥）→ 提示
                     “应用正在更新或恢复，请稍后重新运行安装程序”，app-<AppVersion> 已放置但未登记，不改变当前版本
                     更新模式：不写任何控制文件、不重建快捷方式；登记由发起安装的 WIN-16 --install-after-exit 进程在 Inno 退出码 0 后完成
  InitializeUninstall 自定义窗体：单选 [保留本机数据（默认）] / [同时删除本机数据]，按钮 [继续卸载] / [取消卸载并打开应用导出备份]
                     后者启动 {app}\BubeiGongshi.exe 并中止卸载；选择删除数据时二次确认“未同步或未导出的数据将无法恢复”
  usPostUninstall    删除 {app} 整个目录、HKCU\Software\Microsoft\Windows\CurrentVersion\Run 下的值 BubeiGongshi、HKCU\Software\BubeiGongshi；
                     选择删除数据时 DelTree('{localappdata}\BubeiGongshi')
```

- 错误码：安装器不经核心，不使用错误码；失败以 Inno 退出码表示（0 完成；2 安装前取消；5 安装中取消或错误对话框 Abort；全部非零都不能切换版本，其他含未知码记 PLATFORM_IO；不是所有 5 都代表主动取消）。

- 自动更新由 WIN-16 `--install-after-exit` 模式发起；该进程先取得旧应用的进程句柄、校验创建时间，等句柄结束且 SingleInstance 不存在后才启动 Inno，最长 30 s。安装器仍保留 AppMutex，用户手工启动时正常提示关闭；不依赖 InitializeSetup 比 AppMutex 更早执行。退出中不能强杀旧应用。安装状态持有 Launcher mutex，后来的快捷方式不能启动新写者。
- 安装器不直接写 current/pending/journal 等控制文件（Inno Pascal 无法满足 WIN-16 的原子写与 journal 检查）；全部经 WIN-16 命令完成，失败保留旧 current。安装成功后不自动启动应用；更新失败的提示与 update-failed.txt 由 WIN-16 负责。
- 官方行为依据：Inno 的 AppMutex 与 Setup Exit Codes（见附录 A ADR-V5-31）。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

产品约束追踪：见README §6 Q1、Q5；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 不写 `C:\Program Files` 与 HKLM，不请求管理员权限；安装器与卸载器都不访问网络。
- 安装包不含供应商 API Key、测试密钥与调试符号；体积门禁由 WIN-12 `check_artifacts.py` 按 CORE-01 预算表“安装包”行执行。
- 界面语言简体中文：使用 Inno Setup 非官方翻译 `ChineseSimplified.isl`（随许可证一并入库于 `installer/windows/`），自定义文本写在 `[CustomMessages]`。
- 外部前提：Inno Setup 6.x 具体版本见 `app/windows/toolchain.versions` 的 `inno=`（WIN-01，ADR-V5-15）；AppId GUID 在 M0 生成后写入脚本且永不更改。

**验收标准**：测试方案全文见 [Test/win/S7_WIN-02_TEST.md](../Test/win/S7_WIN-02_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 270 行；`installer/windows/`。组件估算：Inno可执行安装/登记/互斥/空间/版本逻辑约 160 行，卸载选择/确认/清理约 110 行。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。

