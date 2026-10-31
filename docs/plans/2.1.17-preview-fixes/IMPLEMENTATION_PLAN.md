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
- [ ] b2 CU 预测试、远端 CI、用户单批验收。
