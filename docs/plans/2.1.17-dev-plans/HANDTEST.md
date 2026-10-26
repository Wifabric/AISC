# v2.1.17 b1 手测方案 — 无代理 skill 组安装/更新

> 运行前先完成本批代码与 targeted 验证。所有命令在 PowerShell 5.1+ 执行；
> `$Repo` 可按实际 checkout 修改，其余变量保持本文命名。

## 变量与前置准备

```powershell
$Repo = "E:\Projects\AISC"
$Aisc = "$Repo\.venv\Scripts\aisc.exe"
$Workspace = Join-Path $env:TEMP ("AISC-217-B1-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -LiteralPath $Workspace | Out-Null
$Query = "caveman"
```

1. `git -C $Repo status --short` 输出为空；当前分支为本批工作分支。
2. `docker version --format "{{.Server.Version}}"` 输出一个非空版本号。
3. Workbench 已关闭；随后执行 `powershell -File $Repo\scripts\build-cli.ps1`
   成功结束，未出现文件锁错误。
4. 宿主无代理检查：
   - `netsh winhttp show proxy` 输出包含“直接访问”或等义“没有代理服务器”；
   - `Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" | Select-Object ProxyEnable,ProxyServer`
     显示 `ProxyEnable : 0`。
5. 激活工具链并在无代理环境变量下启动 Workbench：

```powershell
. "$Repo\scripts\dev-env.ps1"
$env:HTTP_PROXY=""; $env:HTTPS_PROXY=""; $env:ALL_PROXY=""; $env:GH_PROXY=""
Set-Location "$Repo\workbench"
npm run tauri dev -- -- --aisc-cli $Aisc
```

6. 在 Workbench 首页选择/创建 `$Workspace`，等待运行时状态为 running。
7. 异常判定：上述任一步失败、Docker 未运行、sidecar 构建失败或运行时未启动，
   本轮手测停止并记录原始输出。

## H1 无代理正常安装（直连或镜像至少一条可用）

1. 左侧资源面板点击“扩展” → 顶部资产页签点击“技能”。
2. 在“搜索技能商城（skills.sh）”输入 `$Query`，点击“搜索”。
3. 记录市场父组标题右侧“{count} 个技能”的实际 `count = N`。
4. 点击父组行右侧“安装全部”。
5. 理想结果：
   - 操作期间父组按钮显示 spinner，进度文案从 `0/N` 递增到 `N/N`；
   - 结束后 toast 文案为“安装完成：<父组名>”；
   - 已安装技能列表中同名父组的子技能数为 `N`，没有缺项；
   - 每个新安装子技能的 Claude/Codex 启用状态均为开启；
   - 错误区为空。
6. 异常判定：中途停止在 `x/N`、toast 只报“AISC CLI错误”、已安装少于 `N` 项、
   任一子技能双引擎为关闭，均记录为失败。

## H2 直连失败但镜像可用

1. 前置探测：

```powershell
(Test-NetConnection github.com -Port 443).TcpTestSucceeded   # 期望 False
(Test-NetConnection ghfast.top -Port 443).TcpTestSucceeded   # 期望 True
```

2. 若两条不满足，H2 标记 NOT RUN 并保留输出；不得通过修改系统网络伪装通过。
3. 满足后重复 H1 的搜索与“安装全部”。
4. 理想结果：安装可经镜像完成，最终状态与 H1 第 5 条一致；UI 错误区为空。
5. 异常判定：只安装一个子技能、失败信息不包含目标 repo/spec，或无法从镜像
   完成，均记录为失败。

## H3 失败诊断（仅当直连与镜像均不可用的真实环境）

1. 前置探测：

```powershell
(Test-NetConnection github.com -Port 443).TcpTestSucceeded      # 期望 False
(Test-NetConnection ghfast.top -Port 443).TcpTestSucceeded      # 期望 False
(Test-NetConnection gh-proxy.com -Port 443).TcpTestSucceeded    # 期望 False
```

2. 若任一源可用，H3 标记 NOT RUN；失败诊断以 adapter 单元测试中的模拟 stderr
   为自动化证据，不冒充实网手测。
3. 全部不可用时，对一个未安装的多子技能市场组点击“安装全部”。
4. 理想结果：Workbench 不退出；错误文案包含“操作失败”，technical detail 包含
   repo、目标 spec、direct 与 mirror 探测结果、官方 CLI stderr 尾部；错误文本可
   复制；刷新后不会把半安装项标成完整安装。
5. 异常判定：只显示泛化的“AISC CLI错误”、无法复制详情、半安装组显示为完整成功，
   均记录为失败。

## H4 组更新保留状态

1. 在 H1 完成后，把其中一个子技能 Codex 开关显式关闭并等待列表刷新。
2. 点击该已安装父组右侧“更新全部”。
3. 理想结果：更新进度从 `0/N` 到 `N/N`；被关闭项更新后 Codex 仍关闭、Claude
   保持原状态；其余未改动项双引擎保持开启。
4. 异常判定：更新后覆盖用户显式关闭状态或缺少任一子项，记录为失败。


## 2026-10-26 执行记录

- **H1 UI：NOT RUN** — 未启动 Workbench 真窗口，不能声称进度文案 / toast / 子行
  状态已手测。Workbench store/Vitest 已覆盖对应状态逻辑。
- **H2 数据面补充：PASS** — 宿主 WinHTTP direct、用户 `ProxyEnable=0`；
  `github.com:443=False`，`ghfast.top:443=True`，`gh-proxy.com:443=True`。
  重建镜像 `sha256:10de26fee8dc...` 后启动真实 temporary runtime
  `50a5b7df-55e5-426a-8756-3f3ab31fd2b0`，执行
  `extensions skill-install-group` 安装 `caveman` + `caveman-commit`，返回
  `total=2, completed=2`，两项 `status=installed`；列表确认两项
  `enabled_claude=true, enabled_codex=true`。
- **H2 UI 进度/文案：NOT RUN** — 数据面通过不代表父组按钮 `0/2→2/2` 与 toast
  已在真窗口观察。
- **H3：NOT RUN** — 实测 ghfast 与 gh-proxy 均可连接，不满足“直连与镜像均不可用”
  前置；不得伪造失败诊断实网结果。
- **H4 数据面：PASS** — 先将 `caveman` Codex 显式关闭，再执行组更新，返回
  `total=2, completed=2`；列表确认 `caveman` 为 Claude=true / Codex=false，
  `caveman-commit` 为 Claude=true / Codex=true，用户显式状态未被覆盖。
- 测试容器已 stop/remove；镜像保留为 `super-claude:latest` 本地验证产物。
