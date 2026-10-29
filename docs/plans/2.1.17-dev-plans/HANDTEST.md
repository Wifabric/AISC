# v2.1.17 统一手测方案（全部批次预测试后执行）

> 运行前先完成本批代码与 targeted 验证。所有命令在 PowerShell 5.1+ 执行；
> `$Repo` 可按实际 checkout 修改，其余变量保持本文命名。

## 变量与前置准备

```powershell
$Repo = "C:\Users\wangyu\.codex\worktrees\217-b1-proxyless-extension-reliability\AISC"
$Artifacts = "$Repo\release-staging\2.1.17-r2"
$LegacyArtifacts = "$Repo\release-staging\2.1.17-b7" # 仅 b5 的 0.0.0 更新副本/旧 NSIS
$Aisc = "$Artifacts\review-dist-2\aisc.exe"
$Bundle = "$Artifacts\handtest-stage\aisc-bundle"
$Workspace = Join-Path $env:TEMP ("AISC-217-R2-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Workspace | Out-Null
$Query = "caveman"
```

1. 使用本阶段最终集成 checkout；`git -C $Repo status --short` 输出为空。不要使用尚未同步的 `E:\Projects\AISC` 旧 checkout 或指向它的 editable CLI。
2. `docker version --format "{{.Server.Version}}"` 输出一个非空版本号。
3. Workbench 已关闭；`Test-Path $Aisc` 和 `Test-Path "$Bundle\manifest.json"` 均为 True。使用 R2 ACCEPTANCE 本地构建（含插件市场删除警告修正）、review-dist-2 冻结 CLI 与当前源码重打的 bundle；启动器校验 GUI/CLI/adapter SHA256，记录见 `$Artifacts\artifacts.json`。这些是未发布的本机忽略产物；另建 checkout 必须重建。不要用旧 b7/R1 GUI 验收 R2。
4. 宿主无代理检查：
   - `netsh winhttp show proxy` 输出包含“直接访问”或等义“没有代理服务器”；
   - `Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" | Select-Object ProxyEnable,ProxyServer`
     显示 `ProxyEnable : 0`。
5. 在无代理环境变量下启动已准备的 Workbench（不需要重新编译）：

```powershell
$env:HTTP_PROXY=""; $env:HTTPS_PROXY=""; $env:ALL_PROXY=""; $env:GH_PROXY=""
& "$Artifacts\start-handtest.ps1"
```

6. 启动器使用隔离数据根 `C:\pt\aisc-217-r2-handtest-data` 并绑定上面的 CLI/bundle。首页选择/创建 `$Workspace`，在启动摘要展开高级设置，在“镜像”输入框填 `super-claude:2.1.17-r2-final` 后启动，等待 running。该镜像 ID 为 `sha256:2f54fad6d86c15468f0cf968535fc377c7ff11e9362f94dcb5f29e2ee6121556`，由 b7 `610cd7ebfa39…` 加最终 adapter 派生；`latest` 仍为 b7，不能用于 R2 来源维护验收。此处未进行从头全镜像构建。
7. 异常判定：上述任一步失败、Docker 未运行、sidecar 构建失败或运行时未启动，
   本轮手测停止并记录原始输出。

## H1 无代理正常安装（直连或镜像至少一条可用）

1. 左侧资源面板点击“扩展” → 顶部资产页签点击“技能”。
2. 点击“扩展市场”→“技能”，在搜索框输入 `$Query`，点击“搜索”。
3. 记录市场父组标题右侧“{count} 个技能”的实际 `count = N`。
4. 点击父组行右侧“安装全部”。
5. 理想结果：
   - 操作期间父组按钮显示 spinner，状态为 `0/N`；当前组级 IPC 不流式发送
     子项增量，成功返回后一次性达到 `N/N` 并清除，不承诺逐项递增；
   - 结束后 toast 文案为“安装完成：<父组名>”；
   - 关闭扩展市场后，主视图已安装技能列表中同名父组的子技能数为 `N`，没有缺项；
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
3. 理想结果：更新期间状态为 `0/N`，成功返回后一次性达到 `N/N` 并清除；
   被关闭项更新后 Codex 仍关闭、Claude
   保持原状态；其余未改动项双引擎保持开启。
4. 异常判定：更新后覆盖用户显式关闭状态或缺少任一子项，记录为失败。

## 2026-10-26 执行记录（当前修订）

以下是历史 b1 证据；统一手测使用文首 b7 产物，不沿用历史镜像。

- 当前 adapter checksum：`eceb822ca20b5fbdd79c8a11fad77058179f9bfb1495ee97be2f45ed4354abeb`；
  当前验证镜像：`super-claude:latest @ sha256:21e4b9b6dd0991428958d4d4a4cc6d28f0f36f8dff5da8a649b1585ac2db2c4e`。
- **H1 UI：NOT RUN** — 未启动 Workbench 真窗口；不能声称进度文案 / toast / 子行状态已手测。
  Workbench store/Vitest 覆盖对应状态逻辑。
- **H2 数据面：PASS** — 宿主 WinHTTP direct、用户 `ProxyEnable=0`，ghfast 与 gh-proxy
  均可连接。启动真实 temporary runtime
  `2ca8d158-ad21-4523-8a4e-47c6d363cf8e` 后在容器 `/etc/hosts` 将 `github.com`
  指到 `127.0.0.1`，实测 direct `git ls-remote` rc=128、ghfast rc=0。执行 JSON
  specs 组安装 `caveman` + `caveman-commit`，operation `ec9a7f0a-adf8-4510-aae2-20c3805cad57`
  返回 `total=2, completed=2`，两项 `installed`；列表确认两项 Claude/Codex 均开启。
- **H2 UI 进度/文案：NOT RUN** — 数据面通过不代表父组按钮 `0/2→2/2` 与 toast 已在
  真窗口观察。当前组 IPC 无逐项流式进度，成功返回后一次性到达终态。
- **H3：NOT RUN** — 实测 ghfast 与 gh-proxy 均可连接，不满足“直连与镜像均不可用”
  前置；失败诊断由 adapter 单测覆盖 direct/mirror probe、clone fallback 与官方 CLI
  stderr tail，不伪充实网结果。
- **H4 数据面：PASS** — 先将 `caveman` Codex 显式关闭，再执行组更新，operation
  `9cc298c0-262f-4055-837c-f7f125848e6c` 返回 `total=2, completed=2`；列表确认
  `caveman` 为 Claude=true / Codex=false，`caveman-commit` 为 Claude=true /
  Codex=true，用户显式状态未被覆盖。
- 测试容器已 stop/remove；本地镜像保留为验证产物。

## b2 市场与更新信号

前置：按文首启动本版 Workbench/sidecar 和 ready 的隔离工作区，不启用系统代理。

1. 左侧“扩展”→“检查更新”，展开 caveman：无可靠版本字段的子技能显示“暂无可靠版本源”，不能显示“已是最新”。如有已安装插件和可比 marketplace 版本，更新项名称加粗并显示“可更新”；点开详情核对当前/最新版本。网络报错应显示具体错误。
2. 点击“扩展市场”，分别在技能/MCP/插件页签搜索 `caveman` / `pdf` / `superpowers`；成功结果标“已刷新”和时间，展开详情显示中文字段及“市场原文”。清空输入后结果和缓存提示一起清空。
3. 成功搜索后临时断开测试网络，再搜索同关键词：有缓存时显示“缓存结果”、上次成功时间与远端错误；首次搜索不存在的关键词不得显示前一关键词结果。恢复网络。
4. 切换工作区后上述结果/徽标必须清空，新运行时的查询不能被旧响应覆盖。出现永久禁用、错类徽标、静默吞掉网络错误均记为异常。

## b3 失败恢复（R2 紧凑失败区）

前置：本版 ready runtime，使用一次性测试扩展。R2 已删除旧插件 identity 输入框和操作日志；不要照历史截图寻找它们。仅当真实市场结果中的测试项可稳定触发安装失败时执行本组，否则记 NOT RUN，引用 `extensionsOperationRecovery` / `extensionFailureNotice` 自动化证据，不把搜索失败当成安装失败。

1. “扩展”→“扩展市场”→对应资产页签搜索测试项→单击真实结果→详情“安装”。记录完整 identity；失败后关闭市场。理想：主视图显示一块“最近失败”，包含类型、安装动作、名称和诊断；无历史日志列表。
2. 仅当最近失败区有“重试”按钮时点击。理想：仅重试同一 identity/参数，仍失败则更新最近失败；已成功项不重复安装。若状态为“结果未知”，只能先刷新核对实际状态，不能显示可盲目重试按钮。没有可重试真实失败时本项记 NOT RUN，不制造虚假 PASS。
3. 仅在隔离测试组真实出现部分失败时，核对成功项仍在、失败项可恢复；组内成功项不重复执行以真实数据面及自动化另证。缺少前置则记 NOT RUN。
4. 最近失败区点击“复制诊断”，粘贴到本地文本编辑器：包含 identity、动作、尝试次数、起止时间和错误，敏感值遮蔽，超长诊断有截断标记。主视图无需显示全部日志字段。
5. 等待测试操作时切换工作区。理想：新工作区无旧失败/错误，旧组剩余操作不能发送到新工作区；连续重试只执行一次。成功项重复执行、跨工作区操作或凭据残留均判异常。

## b4 分类推荐与发现（R2 市场入口）

前置：先在未启动 runtime 的工作区打开扩展市场，再启动隔离 ready runtime。主视图不再显示推荐。

1. 左侧“扩展”→“扩展市场”→“推荐”：科学研究/教育学习/知识文档/数据可视化/写作表达/开发工程六类，每类 10 条；每条含类型、中文理由、来源与有据可查的热度/官方目录标签。未启动 runtime 时详情“搜索市场”禁用；不能显示假热度。
2. ready 后，依次选择知识文档的 Context7（MCP）、开发工程的 superpowers（插件）及科学研究的一项技能推荐，单击详情“搜索市场”。理想：进入对应资产页签，关键词与推荐 query 一致；真实结果详情可安装，推荐详情只能先搜索。不得再要求旧 caveman/context7/superpowers 三卡并列布局。
3. 在市场中连续更换搜索词，再清空输入：最终只显示当前关键词结果；清空后迟到结果不能重现。切工作区后不能残留上个工作区的已安装行。
4. “来源管理”加载错误与关键词搜索错误各在相应位置显示，错误不能伪装为空结果。切英文后理由/按钮/离线说明均为英文。分类少于 10 条、关键词错类、离线伪刷新或跨工作区数据残留均判异常。

## b5 显式更新与健康报告

前置：Windows、可替换的测试安装目录。先关闭常规 2.1.17 Workbench，执行以下命令启动专用更新测试副本；它由同一份源码构建，仅以临时配置把版本设为 0.0.0，使现有正式 release 可触发下载，数据根独立为 `C:\pt\aisc-217-update-flow-data`。关于页必须显示 0.0.0；否则停止并记录。普通 2.1.17 构建高于当前正式 release，不能用它验证下载按钮。先保存工作区文件，真实安装器出现后可取消，避免安装旧正式版。非 Windows 只复核手动安装提示。

```powershell
& "$Artifacts\start-handtest.ps1" -UpdateFlow
```

1. 顶部菜单“关于与更新”→“检查更新”，再打开设置→更新。检查失败时应显示错误，不能提示“已是最新”；有新版时显示 GUI/CLI 当前与目标版本。
2. 点击“下载更新”，等待按钮变为“退出更新”。理想：Workbench 仍运行，安装器尚未启动；下载文件位于 `%TEMP%\aisc-workbench-update\workbench-setup-<目标版本>.exe`。
3. 点“退出更新”→取消。理想：仍显示“退出更新”，可重新确认，无安装进度或自动退出。
4. 再点“退出更新”→确认。理想：Explorer 打开安装包目录并选中该 exe，随后出现正常 NSIS 安装界面，Workbench 退出；安装器没有 `/S` 静默参数。
5. 另下载一次，在确认前临时重命名测试下载包后确认。理想：显示文件缺失错误，Workbench 保持运行；恢复原文件名。若出现 UAC 拒绝或启动失败，同样必须保留应用并报错。
6. 打开“诊断”→展开“本机更新网络观测”→复制健康报告并粘贴到本地文本编辑器。理想：没有请求时显示“尚未探测”，有请求时显示 direct/mirror、传输、状态、耗时和时间；容器扩展网络明确未探测；CLI/bundle 检查列出实际路径、版本、manifest 规则与原因，不能把 Workbench 2.x 与 CLI 0.x 直接判为版本不匹配。
7. 在诊断进行时切工作区或关闭后重开。理想：当前诊断结果不被旧请求覆盖。静默安装、下载即退出、失败后退出、未知版本被报健康、复制出凭据或旧结果覆盖均为异常。

完成后关闭更新测试副本，运行 `& "$Artifacts\start-handtest.ps1"` 返回 2.1.17，继续其余批次。需要另测本批 NSIS 安装器时使用 `$Artifacts\AISC-Workbench-2.1.17-R2-setup.exe`；它来自最终 PR NSIS CI `40923914879`，SHA256 为 `7d1c3981d16f9aa25704e4030f51fd756426a61449b2f8df35a37c4516187831`，已核对下载压缩包与 GitHub artifact digest。它是未发布的 R2 安装器，不是更新服务当前发布目标。

## b6 注册服务分组与 caveman 默认态

前置：本版 R2 Workbench、Docker 已启动，按文首选用 R2 final 镜像，全新隔离项目工作区进入 ready。使用工作区的 bash 标签执行以下容器命令，勿在宿主 PowerShell 执行：

```bash
python3 -m http.server 3000 --bind 0.0.0.0 >/tmp/aisc-b6-3000.log 2>&1 &
python3 -m http.server 5173 --bind 0.0.0.0 >/tmp/aisc-b6-5173.log 2>&1 &
aisc-web-expose 5173
aisc-web-expose 3000 --name "docs preview"
```

1. 左侧 Services 视图：先出现“宿主工具（F2）”，随后同类标题“注册服务”；注册服务行按 3000→5173 排列，名称分别为 docs preview、端口 5173。协议/注册状态有对应中文，切英文后分组/状态为英文。
2. 点击 3000 的“复制”并粘贴核对 URL，点击“打开”显示测试 HTTP 目录页。缺少 runtime-services capability 的旧 CLI 只显示不支持提示、仍保留宿主工具；不出现假服务行。
3. “扩展”→已安装→展开 caveman，核对 13 个子技能 C/X 均 on。关闭 caveman 的 X、caveman-commit 的 C、caveman-compress 的 C/X，再重启工作区或升级镜像：对应状态应保持 1/0、0/1、0/0，其他项仍双开。
4. 仅卸载测试子技能 caveman-stats 后重新安装；理想 C/X 均 on。若容器启动同步补回缺失的内置技能，同样必须双开，不能覆盖其他已有 off。
5. 服务刷新等待时切换 A→B→A，再刷新；只显示当前 runtime 的服务，不残留旧错误或提前解除忙碌。分组缺失、顺序颠倒、空白名称、升级强制开启、重装仍关闭或跨工作区旧响应均判异常。

## b7 稳定工具与三轮统一冒烟

前置：已完成本文件前置准备，使用 b7 新镜像，隔离工作区 ready。仅对测试扩展执行安装/卸载。版本记录见 dependency-evidence.md 和 PRETEST b7；不将宿主 Node 22 与容器 Node 24 混淆。

1. 工作区 bash 中运行 `node --version; codex --version; claude --version; cc-switch --version; mihomo -v; yazi --version`。理想依次含 24.22.1、0.164.0、2.1.311、5.11.3、1.19.33、26.9.1。设置→关于应显示 Workbench 2.1.17，诊断的 CLI/bundle 均 0.1.10.dev0 且配对 pass。
2. 连续执行三轮：扩展→打开扩展市场，分别在技能/MCP/插件页签搜索 caveman/context7/superpowers→从真实市场结果选择测试项安装→检查更新→卸载测试项。至少一轮安装两个 caveman 子技能。理想安装后列表与 C/X 对齐，卸载后测试项消失；Skills/MCP 更新源为 unsupported，不显示虚构“可更新”；Plugins 显示实际市场元数据判断。
3. 按 b3 的受控失败步骤仅重试失败项，成功项保持一次；切工作区 A→B→A。理想新工作区无旧错误/日志、按钮不永久忙碌，主视图无历史日志，仅最近失败；内部记录上限 100 条、单项诊断上限 8 KiB 由自动化核对，复制后敏感值遮蔽。
4. 复核 b6 的 Services 和 caveman；显式更新按 b5 切到专用 0.0.0 副本完成 ready→取消→确认。真实安装器应显示正常界面，Explorer 选中包，Workbench 随后退出。
5. 发现版本不同、混装旧包、跨工作区污染、成功项重复执行、升级覆盖 off 或静默安装均记 FAIL，并记录批次、实际操作与原始错误。CU NOT RUN 项需用户最终复核，不把单测/数据面通过等同 UI 通过。


## R2 扩展 UI 重设计追加手测

前置：使用 R2 构建与当前源码 CLI（构建账本见 `R2-EXTENSION-UI-REDESIGN.md`），隔离工作区 ready。测试来源只使用一次性仓库/市场，不删除 built-in 或官方来源。

1. 打开“扩展”主视图。理想：只显示 技能/MCP/插件、已安装列表、检查更新、扩展市场；不出现精选推荐、操作日志、市场搜索表单或来源表单。
2. 点击“扩展市场”。理想：弹窗显示 推荐/技能/MCP/插件/来源管理；推荐含 科学研究、教育学习、知识文档、数据可视化、写作表达、开发工程 六类，每类正好 10 条，热度来源只出现一次。
3. 切到教育学习，单击 Microsoft Learn。理想：右侧详情先显示中文简介，再看类型/来源/安装量；点击“搜索市场”后进入 MCP 搜索并保留缓存时间。
4. 搜索后单击一条非目录 MCP。理想：详情标题切换，显示中文 fallback 简介和市场原文，不把 MCP 称为技能。
5. 来源管理→技能仓库：添加 `wshobson/agents`（若已存在则换全新隔离工作区），列表出现该 ID、main、已启用后点击该行删除。确认文案必须说明不会卸载已安装技能；确认后列表消失，已安装技能仍在主视图。
6. 在宿主 PowerShell 执行 `& "$Artifacts\prepare-source-fixture.ps1" -Workspace $Workspace`。来源管理→插件市场输入 `/root/app/.aisc-r2-handtest-market`→添加，列表出现 `aisc-r2-handtest`；市场“插件”页搜索 `aisc-r2-demo`，单击结果→安装。关闭市场后核对主视图有 `aisc-r2-demo@aisc-r2-handtest`，再进入来源管理删除该测试市场。确认文案必须明确“同时卸载来自该市场的已安装插件”；先取消，市场/插件均保留；再确认，市场及其测试插件均消失。其他市场的插件不受影响。禁止删除 built-in/官方市场。2026-10-30 真容器已证实官方删除会卸载来源插件，旧“保留”预期作废。
7. 将窗口宽度压到 720px 以下。理想：弹窗详情移到单列、无横向文字重叠；主视图分组和子技能行仍可读，动作可键盘到达。
8. 操作失败时只显示最近失败提示，可复制诊断；已知可重试项才显示重试，不出现历史日志列表。实际 add→delete、窄屏与失败路径为本批用户手测重点。

## 2026-10-30 清单同步说明

上述步骤已按 R2 最终界面替换旧市场入口/操作日志步骤。旧版截图与 PRETEST 历史证据保留，不能视为 R2 最终二进制全部重测通过。当前会话没有 `node_repl`，无法调用 Computer Use 的 `@oai/sky`；来源 add→delete、窄屏、键盘/焦点、旧 runtime 提示仍为 NOT RUN。用户统一手测仍未开始。
