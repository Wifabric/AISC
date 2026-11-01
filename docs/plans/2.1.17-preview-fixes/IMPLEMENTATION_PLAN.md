# Preview 修复实施

## 逐批门

每批从最新 develop 独立分支：证据定位 → 回归测试 → 最小修复 → 定向/本地门禁 →
真实数据面 → 生产候选 → Computer Use → 用户单批验收 → 文档/集成。不能将六批堆积验收。
本次工作分支为 `codex/2.1.17-preview-b1-market-envelope`，基线 `7cc5a25`。

## b1

- [x] 用户反馈入 todo、规格和实施计划。
- [x] 复现常驻 serve `cli` 调用 `extensions updates-check` 的空输出，追踪命令出口。
- [x] 添加覆盖真实命令入口的回归（成功、可诊断失败、后续请求/重复调用）。
- [x] 最小协议/调度修复，不吞掉真实失败。
- [x] 定向测试与完整必要门禁。
- [x] 冻结/生产候选与真实容器验证，标识源码/sidecar/镜像。
- [x] Windows CU 覆盖扩展检查更新、独立市场、重复请求及失败后重试。
- [x] 提交推送与必要远端 CI、记录 PRETEST/HANDTEST，交付用户单批验收。
- [x] 2026-10-31 用户明确回复「b1 通过，进入 b2」；PR #53 合入 develop `cb60cd4`。

## b2–b6

实施前分别根据 PRD 补充准确文件、回归和实机操作。本轮只登记规格与排期，
不提前跨过上一批验收门。b4 的包大小公开资产/只读归因可以在等待中先收集，
不提前修改打包实现。

## b1 根因与修复边界

本机默认数据根 settings 的 pin 指向 `%LOCALAPPDATA%/AISC Workbench/aisc.exe`。
真实冻结 CLI 报版本 `0.1.9.dev0`，不含 `updates-check`；相同 serve 进程依次发
updates-check/list/updates-check，前后两次稳定返回用户原样空 envelope 错误，
stderr 是 `aisc extensions: ... invalid choice: 'updates-check'`；list 正常返回
runtime-not-found。当前源码与原 closeout 冻结 `0.1.10.dev0` 同请求返回完整协议错误。

1. 对当前 CLI 的 extensions 各级 argparse 传播 JSON 格式，错误参数也返回单个完整
   envelope。未知 op、缺参、不合法字段都不得回到 stderr-only。
2. Rust 在 `updates-check` 的旧 CLI 空输出边界，先用同一目标直连读取准确 argparse
   证据，仅确认缺少该 op 才恢复。Local 非 `--aisc-cli` 显式覆盖时，验证应用附带
   sidecar 并重试这个只读调用，成功后更新旧 pin；本次不实现任意失败自动重试。
3. Remote/显式覆盖/无兼容 sidecar 给可操作升级诊断，不能切换执行机器；权限、
   网络、数据库、未知空输出等保留真实失败。新 CLI 缺参属于参数错误，不能被修复
   成空成功。保留原用户数据根与 workspace，不复制认证或历史数据。

## b2 实施范围（2026-10-31，基线 cb60cd4）

工作分支 `codex/2.1.17-preview-b2-extension-details`。对应用户反馈 2、5、6，
同时修正 b1 CU 发现长错误提示挤压工具栏按钮的问题。

1. 核对 adapter 已安装/市场描述字段与上游技能正文，修正缺失描述的数据出口；
   `extensionSummaries.ts` 优先精确身份的可追溯中文简介，其次真实上游介绍，
   无描述明确显示缺失，删除来源/权限套话，不以同名跨仓库误配功能。
   市场技能详情增加只读 `skill-describe --id owner/repo:directory`，点击时按需读取
   上游 SKILL.md 的 frontmatter 描述（固定 GitHub HTTPS 源、限定路径/大小/超时）；
   不执行技能指令、不在搜索时扇出下载。描述请求有独立加载/失败状态与重试，
   工作区切换/快速换选不能串入其它条目。未知英文保留上游原文，不虚构翻译。
2. `ExtensionsView.vue` 技能组展开时在子技能前提供组能力摘要；单项详情放回
   对应子技能/MCP/插件卡片内，移除底部 sticky 浮层，避免遮挡其它条目。
3. `ExtensionDetailPanel.vue`、`ExtensionMarketDialog.vue` 使用现有主题变量，
   控制内边距/换行/滚动和收缩；蓝色外轮廓仅用于键盘焦点，点击展开使用中性边框。
   市场搜索结果详情跟随对应条目，不在旁边挤压长简介。保留开关、更新、安装、删除行为。
4. 回归覆盖真实描述/缺失描述/同名隔离、组简介和内联详情、切换/折叠及焦点；
   完成本地全门禁、必要 adapter 数据面、生产候选、Windows CU 与独立用户验收。
5. CU 检查正常及窄侧栏、市场长文本/推荐、鼠标与键盘焦点、组/子技能/MCP/插件
   详情与按钮可见性；不在本批实现 GitHub MCP 默认安装、更新器或文件管理。

- [x] b1 用户验收及集成。
- [x] b2 规格与准确实施范围落档。
- [x] b2 实现与回归。
- [x] b2 本地门禁、真实数据面和生产候选。
- [x] b2 CU 预测试、远端 CI、用户单批验收。

## b3 实施范围（2026-10-31，基线 66d9549）

工作分支 `codex/2.1.17-preview-b3-default-github-mcp`。官方来源已核实：
GitHub hosted MCP URL 为 `https://api.githubcopilot.com/mcp/`，未带授权实测返回
401 与 Bearer 挑战；Claude 官方指南用 HTTP MCP，Codex 官方指南要求
`bearer_token_env_var`。不引入嵌套 Docker，不内置/代管 PAT。

1. 新增容器内幂等默认 MCP 同步：SSOT 写 cc-switch `mcp_servers.github`
   官方 URL/描述/tags，默认 Claude/Codex 开启；所有权用独立 secret-free marker 记录（tags 仅兼容），首次安装与重启均保留已有行
   的 server_config 与启停选择。若同名 `github` 已存在且没有 AISC marker/tag，
   视为用户自定义配置，完全不覆盖其 SSOT 与 live 配置。
2. AISC default 专属 live 同步不能调用 cc-switch 5.11.3 的通用 HTTP sync
   （实测会生成 Codex `type="stdio"`/空 command）。改为精确合并：Claude
   `/root/app/.mcp.json` 仅维护 `github` 键并保留其它 server；Codex
   `config.toml` 仅重写 `[mcp_servers.github]`，写官方 URL 与
   `bearer_token_env_var = "GITHUB_PAT_TOKEN"`，保留其它 TOML 内容。禁用时移除
   AISC default 的 live 键/表；自定义同名配置不接管。
3. adapter 的 MCP 快照增加脱敏认证状态：官方 GitHub URL 标记需要认证；
   认证状态按 Claude/Codex 分别推导：Claude 需要 Authorization header，Codex 需要
   `GITHUB_PAT_TOKEN` 实际存在；双侧可用才显示整体已配置，单侧可用显示部分配置，
   永不返回 header/env 值。Workbench MCP 卡片中英文一致展示。
4. 回归覆盖空库首装、重复启动、用户关闭、已有自定义同名、live 配置保留/
   移除、官方 401 挑战记录、认证状态脱敏与 UI 展示。真实容器验证 cc-switch
   SSOT、Claude/Codex live 文件、自定义行不覆盖；生产候选与 Windows CU 按
   B3-T1–T3 预测试后交付用户验收。
5. 不在本批实现 PAT 输入/存储/OAuth 浏览器流，不把未认证服务显示为可调用
   成功；用户凭据仍由既有安全边界管理。

- [x] b2 用户验收及集成。
- [x] b3 规格与准确实施范围落档。
- [x] b3 RED 回归与实现。
- [x] b3 本地门禁、真实数据面和生产候选。
- [x] b3 用户单批验收（2026-11-01 用户明确回复「b3测试通过，进入下一个批次开发」）。
- [ ] b3 Windows CU 完整自动预测试（多窗口/坐标点击受阻，未冒充 PASS；用户实机验收放行）。
- [x] b3 远端 CI（PR #55 三项 Workbench CI SUCCESS，develop 集成 `bf886f2`）。

## b4 实施范围（2026-11-01，基线 b9f1dcf）

工作分支 `codex/2.1.17-preview-b4-update-package-size`。对应用户反馈 4、9。

1. 显式更新清理：下载成功并校验 SHA256 后原子写入 secret-free receipt
   （目标版本、安装包文件名、hash、大小）。启动时后台读取应用自更新临时目录；
   仅当当前版本大于 receipt 目标、文件仍在本目录、文件名受控且 size/hash 复验一致时，
   删除该安装包与 receipt。取消安装、安装失败、仍在旧版本或字节变化时保留。
   不读取/写入凭据，不清理用户 Downloads 或手动选择的 exe。
2. 包体积根因与优化：preview.1 相比 2.1.16 增加 405,685,606 字节，主要来自
   x64+arm64 双架构离线 payload 同时进入 NSIS。三个打包 workflow 改为按目标 runner
   原生架构执行 `stage-npm --yazi`（Windows/Linux x64、macOS arm64），移除双架构合并。
3. yazi 从 Git/vendor checksum 改为发布时按架构获取，不再用旧 x64 zip 作为仓库保底；
   `versions.env` 固定 x64/arm64 官方 SHA256，bundle verify 要求恰好一个目标架构 zip
   且 hash/大小匹配。npm 主包/伴生包配对校验保持不变，不降低 checksum 或离线完整性。
4. 重新构建本批 x64 NSIS，报告 2.1.16、preview.1、b4 的压缩安装包与展开 bundle 体积、
   删除的最大离线 payload 与剩余增长归因；离线安装、bundle verify、升级/卸载语义不得回退。
5. 回归覆盖 workflow 架构选择、yazi 单架构强校验、Git/vendor 不再跟踪分发 zip、
   receipt 写入/启动清理、取消保留、hash/size 拒删、路径逃逸拒绝和仅清理自有目录。
   完成本地门禁、生产候选、真实 Windows CU 与用户单批验收。

- [x] b3 用户验收及集成。
- [x] b4 规格与准确实施范围落档。
- [x] b4 RED 回归与实现。
- [x] b4 本地门禁、真实数据面和生产候选。
- [x] b4 远端 CI（PR #56 最终 head `8960587` 的 Workbench/Bundle/NSIS/Artifact 全部 SUCCESS；合入 `7c154cd`）。
- [ ] b4 Windows CU 完整下载安装链路、用户单批验收（真实启动清理预测试已 PASS）。
