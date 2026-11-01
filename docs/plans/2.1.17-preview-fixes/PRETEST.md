# Preview 修复预测试账本

## b1（2026-10-31）

结论：本地门禁、真实旧/新 CLI 恢复、Windows CU T1–T4 **PASS**。
用户单批验收 **PENDING**；不能把 agent 结果当用户验收。
产品 SHA `7c01bac16a4d5fc619cb34cc570f72d04f5e2d55` 的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/41113073318)
与 [CLI 三平台构建](https://github.com/Wifabric/AISC/actions/runs/41113143095) 均 SUCCESS，draft PR #53。

### 产物与环境

- 工作分支 `codex/2.1.17-preview-b1-market-envelope`，develop 基线 `7cc5a25`。
- 候选目录 `release-staging/2.1.17-preview-b1/`，Tauri build --no-bundle 正式静态构建。
  Workbench SHA256 `8846df53c59de18065fdc245948901ce68a99ea78233972c3dc9f9dba3fdecc1`。
- 新冻结 CLI `0.1.10.dev0`，SHA256 `765592ae3df28cec8f0516d79cea563f5f58ff37448764bb94d813b7c2ac4225`；
  旧安装 CLI `%LOCALAPPDATA%/AISC Workbench/aisc.exe` 为 `0.1.9.dev0`。
- 镜像 `super-claude:2.1.17-preview-b1`，ID
  `sha256:9831ce1d36dfc0b874e97a97420118393a105726943e41c0f0cbd88bce61444d`。
  用原 closeout 完整 bundle/receipt 重建，source-version 为 `0.1.10.dev0`，不改 latest。
- 独立数据根 `C:/pt/aisc217pfb1-data`，主工作区 `C:/pt/aisc217pfb1-workspace`。
  真实进程测试 runtime `741bd054-b971-4a1a-8df7-47aa9b819044`；GUI 正常回收无 lease
  测试 runtime 后新建 `f8b0d568-e2ff-45fa-b643-789623f36907`，容器 `aisc-wb-f8b0d568` / `77493241c310`。
- 第二工作区 `C:/pt/aisc217pfb1-workspace-other`，同镜像独立容器 `dee22d3f73b8`。
  未复制用户凭据或历史，未改正常数据根配置。完整本机路径与校验见 [b1-artifacts.json](b1-artifacts.json)。

### 自动化与真实数据面

| 验证 | 实际结果 | 结论 |
| --- | --- | --- |
| 新回归先 RED 后修复 | extensions 未知 op/缺参等4组中3组先复现空 envelope；修复后 AISC_ERR_USAGE / exit 2 | PASS |
| Python 定向 / 全门禁 | 19 passed / 15 subtests；全测 1699 passed、53 skipped、195 subtests | PASS |
| Rust lib / 前端 / 类型 | 407 passed、2 ignored；97 files / 822 tests passed；vue-tsc 通过 | PASS |
| 显式执行真实恢复测试 | 旧冻结 serve 复现→direct stderr 确认不支持→新冻结 CLI 同工作区成功→显式覆盖不切换；9.29秒，1 passed | PASS |
| 冻结 CLI / 生产 UI | PyInstaller 成功；Tauri custom-protocol 正式静态构建成功 | PASS |
| 含真实插件的更新数据 | 14 skills + frontend-design@claude-plugins-official 1.1.1，共15项；exit_code=0，errors=[]；unsupported/update_available=false 且保留原因 | PASS |
| 文档与 diff | check-docs 39 passed / 0 warnings / 0 failures；diff --check 通过 | PASS |

日志均在 `C:/pt/`：`aisc-217-pf-b1-python.log`、`aisc-217-pf-b1-rust-final.log`、
`aisc-217-pf-b1-vitest-2.log`、`aisc-217-pf-b1-real-recovery-2.log`、
`aisc-217-pf-b1-production.log`、`aisc-217-pf-b1-final-updates.json`。
Rust 的两条 ignored 中，本轮真实进程项已独立执行通过，另一条是既有环境测试。

### Computer Use（约 02:33–02:53，Asia/Shanghai）

使用 computer-use 技能的 node_repl + @oai/sky；直接操作真实 Workbench，未在 Bash/
Codex/Claude 终端 UI 输入命令。依赖故障通过工具命令在自有隔离容器中可逆设置。
主窗口 `26086558`、第二工作区窗口 `1117150`，均按返回对象选择、逐次刷新。

| 项 | 操作与实际窗口树/字段证据 | 结论 |
| --- | --- | --- |
| T1 旧 pin 恢复 | 初始设置确指向旧安装 CLI；启动本批镜像，扩展→检查更新，忙碌结束无原错误；caveman 13项、mattpocock/skills 1项保留，pin 实际变为本批目录 aisc.exe | PASS |
| T2 三市场查询 | 独立市场技能 research：出现 research（742211）等，点击有中文详情；MCP github：10条，GitHub（6059）详情/原文可读；插件 frontend：12条，frontend-design（1266133）详情可读；各页“已刷新/上次成功” | PASS |
| T3 重复/服务/隔离 | 重复检查结束；真实安装的 frontend-design 仍在，卡片“暂无可靠版本源 / claude-plugins-official · 1.1.1”；服务页宿主工具及“暂无已注册服务”正常。操作→从文件夹打开 workspace-other，启动同镜像，插件为空、检查后仍空；回主窗口插件1.1.1保留 | PASS |
| T4 失败后重试 | 暂时 mv 主容器适配器到同目录 .pfb1-backup，点击检查：警报含“extensions updates-check failed: aisc-scope: line 21: /usr/local/bin/aisc-extensions-adapter: No such file or directory”，列表保留；恢复后直接再检查，警报消失、忙碌结束，未重启 | PASS |

窗口树证据 `C:/pt/aisc-217-pf-b1-other-window.txt`、`C:/pt/aisc-217-pf-b1-main-window.txt`；
失败警报原文如 T4。截图在本次工具调用结果，未另导出截图文件。

### 限制与后续

- Remote/无 sidecar 只有策略单测，显式覆盖另有真实进程验证；未运行真实 SSH。
- 上游未给可靠版本字段时仍明确 unsupported；真实插件为 metadata unavailable，未伪称最新版或执行更新。
- 模板简介、详情蓝框、错误长文挤压按钮当时留给随后实施的 b2；现已在下方 b2 记录中复测通过。
- 初次普通 cargo release 候选访问 localhost:9000，已换为上列正确生产产物后完成 CU。
  初次真实测试未 drain pool 导致不退出，补清理后通过。初次 Vitest cwd 错误已正确重跑全绿。
- 本段记录的是 b1 当时的限制；b1 随后已由用户验收通过，b2 结果见下方，后续批次仍等待逐批验收。

- 2026-10-31 用户批次验收：用户明确回复「b1 通过，进入 b2」。b1 关闭；PR #53 已合入 develop `cb60cd4`，最新提交 Workbench CI SUCCESS。

## b2（2026-10-31）

结论：本地门禁、真实 adapter/镜像数据面、生产候选与 Windows CU **PASS**；2026-10-31 用户验收 B2-T1–T3 **PASS**。

### 产物与环境

- 分支 `codex/2.1.17-preview-b2-extension-details`，develop 基线 `cb60cd4b8f813fa65343b944edf079229aa91784`。
- 候选目录 `release-staging/2.1.17-preview-b2/`；最终 CU 启动器校验的 Workbench SHA256 为
  `6ab3a7ff0bc787773fc1ecc80d69be656e079540d2cd026472b7b63f0aaa7a67`，CLI SHA256 为
  `91d527d111387dcf332846e0c1e94b17bda7d6b19cabb4a7915feaa931e921c3`。
- 镜像 `super-claude:2.1.17-preview-b2`，ID `sha256:b7d746a3c3cb784bbe88018e4339cbc303e53f9b50c15f11acd22acf7e0e911b`；adapter SHA256
  `6f1370b4fc169728ae701c98ca5559fc9a9798962aa213b44edac2e55ec75d6b`。
- 数据根 `C:/pt/aisc217pfb2-data`，工作区 `C:/pt/aisc217pfb2-workspace`；本轮 fixture 中 MCP 与 frontend-design
  仅用于查看描述，未执行安装/卸载。

### 自动化与真实数据面

| 验证 | 实际结果 | 结论 |
| --- | --- | --- |
| Python 全门禁 | 1705 passed / 53 skipped / 201 subtests | PASS |
| Rust / 前端 / 类型 | 407 passed / 2 ignored；98 files / 831 tests passed；vue-tsc 通过 | PASS |
| sidecar、vendor、Docker、生产 Tauri | 冻结 CLI、vendor refresh、镜像重建与 `tauri build --no-bundle` 均完成 | PASS |
| 真实 `skill-describe` | `anthropics/skills:skill-creator` 返回真实上游描述；错误路径限制、超时/大小与 adapter dispatcher 有覆盖 | PASS |

### Computer Use

使用 computer-use 技能的 node_repl + `@oai/sky`，直接操作真实候选 Workbench；没有在 Bash/Codex/Claude
终端 UI 输入命令。窗口树证据保存于 `C:/pt/aisc-pfb2-market-description-window.txt`。

| 项 | 实际观察 | 结论 |
| --- | --- | --- |
| B2-T1 已安装项 | Caveman 组显示功能简介及 13 个子技能；evidence-review 显示费用/CaveScore/工作流/调用链/延迟/节省，compress 显示 CLAUDE.md/记忆/待办压缩；MCP 文件服务和 frontend-design 均在自身卡片显示实际描述 | PASS |
| B2-T2 推荐与市场 | 推荐分类显示 6 类、每类 10 项；推荐详情在单项卡片内；技能 `research` 显示中文功能介绍；`skill-creator` 先显示读取中，恢复 adapter 后显示真实上游介绍；MCP `github` 与插件 `frontend` 返回结果并可展开具体描述 | PASS |
| B2-T3 布局与焦点 | 侧栏拖至约 280px 后文本换行且按钮完整；搜索详情没有固定右栏；鼠标展开无蓝色外框，Tab/Enter 有键盘焦点框；Escape 收起并恢复对应条目焦点；长错误在详情内换行并提供“重新读取” | PASS |
| 更新回归 | 最终候选启动预检五项通过；扩展更新检查结束后 caveman 13 项与 mattpocock 1 项保留且无 b1 空 envelope 错误 | PASS |

故障恢复：通过工具将隔离容器 adapter 临时移走，`skill-describe` 详情保留搜索列表并显示
`AISC CLI 返回错误 ... No such file or directory` 与“重新读取”；恢复同一 adapter 后重试，详情显示
`Create new skills, modify and improve existing skills...` 的真实上游文本。未执行安装/删除等有副作用 UI 操作。

日志：`C:/pt/aisc-pfb2-python.log`、`aisc-pfb2-rust.log`、`aisc-pfb2-vitest-final.log`、
`aisc-pfb2-production-final.log`、`aisc-pfb2-image.log`、`aisc-pfb2-market-description-window.txt`。

## b3（2026-11-01）

结论：本地门禁、真实 adapter/镜像数据面、生产候选与用户实机验收 **PASS**。
Windows CU 完整自动预测试未完成：多实例/多显示器下部分 WebView 按钮无法获得
可点击坐标；保留为 NOT RUN，不冒充 CU PASS。用户随后明确验收 b3 通过。

### 产物与环境

- 分支 `codex/2.1.17-preview-b3-default-github-mcp`，develop 基线 `66d9549e7a841040b6d40ab014e10809fefa6900`，产品提交 `cc508da91ba0cda9658a5f92f2007c955cf7429c`。
- 候选目录 `release-staging/2.1.17-preview-b3/`。Workbench SHA256
  `f4660f84e614aa1461733a8673d7dda014469740a363e4f24c1357b96368fd60`，CLI SHA256
  `6839e327dfe53804495aba619ce5793aae40415bde2836c3e2970587088c8ec6`。
- 镜像 `super-claude:2.1.17-preview-b3 @ sha256:983ce21cc5259437926a49f0bf286c36d789b614598b8477d3ea543e7178df1a`。
  首次误用 b2 bundle 构建时发现新 helper 未入镜像；改用当前源码根重建最终镜像，
  该构建错误未覆盖，最终镜像包含 helper/adapter。
- 用户验收 runtime `aisc-wb-266263b2` 当时运行 `super-claude:latest`，本地 latest
  已临时指向上述 b3 image ID；验收后容器清理，latest 恢复为回退标签
  `sha256:f78a53822b9cbbc85162cf7f0130a5ccf615643d5b78169a5697a054cf69fbc5`。

### 自动化与真实数据面

| 验证 | 实际结果 | 结论 |
| --- | --- | --- |
| 官方远程端点 | 无 Authorization 请求 `https://api.githubcopilot.com/mcp/` 返回 401 与 Bearer 挑战 | PASS |
| 本地全门禁 | Python 1718 passed / 53 skipped / 201 subtests；Rust 407 passed / 2 ignored；Vitest 98 files / 833 passed；vue-tsc 通过；LOCAL GATES ALL GREEN | PASS |
| vendor / bundle | vendor refresh 后 1534 checksums 全部通过；候选 bundle stage/verify PASS | PASS |
| 默认首装 | cc-switch SSOT 有官方 URL、默认 Claude/Codex 开启；Claude `.mcp.json` 与 Codex `config.toml` 均正确写入 | PASS |
| 用户开关保留 | `cc-switch mcp disable github -a claude` 后重启，SSOT 为 Claude=false/Codex=true；Claude live 键移除、Codex 表保留 | PASS |
| 自定义同名 | 已有自定义 `github` SSOT/live 配置重启后 URL、启停与内容原样保留 | PASS |
| 认证状态 | 默认 required=true、整体/Claude/Codex=false、env=GITHUB_PAT_TOKEN；设置测试 env 后 Codex=true/Claude=false/整体=false；header+env 双侧才整体=true；输出不含测试 token | PASS |
| 生产候选 | 冻结 CLI、生产 Tauri `--no-bundle`、启动器解析与候选哈希校验通过 | PASS |

真实容器证据 roots：`C:/pt/aisc217pfb3-real-3`、`C:/pt/aisc217pfb3-final-real`；
用户验收摘录 `C:/pt/aisc-pfb3-user-acceptance.txt`。日志：`%TEMP%/aisc-pfb3-local-gates-final.log`、
`aisc-pfb3-vendor-verify-final.log`、`aisc-pfb3-image-final.log`、`aisc-pfb3-production-final.log`。
测试容器已停止/移除，未复制用户凭据，未内置 PAT。

PR #55 head `d43fae0aa1ea634cefc7b1a412255596a145674b` 的 Workbench CI run `41220190227` frontend/Rust/CLI 全部 SUCCESS；合并 develop `bf886f2579cabb2eb280879f4493f9acbbbfb3ec`。

## b4（2026-11-01）

结论：本地门禁、x64 bundle/NSIS、包体积归因与真实 Workbench 启动清理 **PASS**。
完整下载→交互安装→新版本启动链路的 Windows CU 待候选交付后执行；不把 Rust 注入测试
或启动清理冒充完整安装 CU。

### 产物与环境

- 分支 `codex/2.1.17-preview-b4-update-package-size`，基线 develop `b9f1dcf`，产品提交 `f39618ab0d97365c68547d603ed4c790a2eb3cd0`。
- x64 staged bundle 展开 397,386,330 字节，bundle verify PASS。
- 本地生产 NSIS `AISC Workbench_2.1.17_x64-setup.exe`：384,516,079 字节，SHA256
  `1f07d5e09c5fd6b8bc1ea1b98d26743d28d30d85ab8e15e3a361e07121332d8a`。
- 候选目录 `release-staging/2.1.17-preview-b4/`。Workbench SHA256
  `8d59ec8283bb62213a1f826073a97f7bd2cff1f5881f6be475a5bd8d385f97e9`，冻结 CLI SHA256
  `2bc2feb32bcee9b18376e107c7ed822e5a97d7102e741652dc379cc98c3ecbeb`。
  `start-handtest.ps1` 与 `start-cleanup-pretest.ps1` 均解析 PASS；后者已实跑返回
  `PASS real Workbench startup cleanup`。
- 7-Zip 列表确认仅包含 `codex-linux-x64`、`claude-code-linux-x64` 与
  `yazi-x86_64`，无 arm64 payload。

### 包体积实测

| 版本 | 压缩安装包 | 对比 |
| --- | ---: | ---: |
| 2.1.16 | 293,124,128 B | baseline |
| 2.1.17-preview.1 | 698,809,734 B | +405,685,606 B |
| 2.1.17 preview b4 x64 | 384,516,079 B | 比 preview.1 -314,293,655 B；比 2.1.16 +91,391,951 B |

preview.1 根因是每个安装包同时打入 x64/arm64离线 payload。b4剩余增长的约
90,804,023 B 展开载荷主要来自 Codex x64 +42,670,811 B、Claude x64 +35,570,393 B、
yazi +6,778,413 B、Mihomo +5,009,561 B 与 Workbench +1,233,920 B；geodata 合计略降。
完整数据见 [package-size-intake.json](package-size-intake.json)。

### 自动化与真实启动

| 验证 | 实际结果 | 结论 |
| --- | --- | --- |
| 全门禁 | Python 1722 passed / 53 skipped / 201 subtests；Rust 410 passed / 2 ignored；Vitest 98 files / 833 passed；vue-tsc 通过 | PASS |
| workflow/打包 | 三个 workflow 均目标架构 `--yazi` staging，不再 `--all-arches`；Git 不再跟踪 yazi zip | PASS |
| yazi 完整性 | x64/arm64官方 SHA256+size 入 pin；bundle 要求恰好一个目标架构 payload，过期/重复/损坏失败 | PASS |
| bundle/vendor | x64 stage/verify PASS；vendor 1533 checksums PASS | PASS |
| 更新 receipt | 下载校验成功写 receipt；当前版本 > 目标且 size/hash 复验一致才删除；同版本/字节变化/路径逃逸/无关文件保留 | PASS |
| 真实启动清理 | 隔离 TEMP 中启动生产 Workbench，旧已验证安装包与 receipt 删除，`user-download.exe` 保留 | PASS |

日志：`%TEMP%/aisc-pfb4-local-gates-2.log`、`aisc-pfb4-vendor-verify.log`、
`aisc-pfb4-freeze.log`、`aisc-pfb4-production.log`、`aisc-pfb4-nsis.log`。
2.1.16 对照安装包与两次 7-Zip 列表保存在 `C:/pt/aisc-pfb4-*`。清理测试根
`C:/pt/aisc-pfb4-cleanup` 保留无关文件证据，测试 Workbench 已关闭。

### 远端集成证据

最终 head `9f13847d53c1a4ea7862e57c46ef8c95b2945502` 四条流水线全部 SUCCESS：

| workflow | run | 关键结果 |
| --- | --- | --- |
| Workbench CI | 41226911753 | frontend / Rust / CLI |
| Bundle Linux/macOS | 41226973402 | deb / dmg |
| NSIS installer | 41226975807 | NSIS、安装/PATH/数据保留冒烟 |
| Artifact | 41226978184 | linux x64 / windows x64 / macOS arm64 目标架构 staging/verify |

修复过程中的 yazi GitHub API 限流失败保留为历史证据；最终实现改用 pinned release URL 后全绿。
