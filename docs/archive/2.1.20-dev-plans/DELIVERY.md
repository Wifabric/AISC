# Workbench 2.1.20 / CLI 0.3.1 交付记录

2026-11-27，用户确认本轮功能检查全部通过。验收使用 Windows 本地 Preview；用户审阅发布说明后授权提交正式版。安装器、公开下载和独立 CLI 渠道分别记账。

## 范围与证据

| 反馈及入口 | 用户可见结果 | 实现与验证 |
| --- | --- | --- |
| 1 升级保留 Provider | 同一数据目录和原工作区保留 Claude、Codex 配置 | #109。2.1.19 → preview.1 实机覆盖安装后 4 张第三方卡片保留，两侧仍为官方直连。另开市场工作区时原库记录仍在。 |
| 2 官方直连重复 | 每个引擎有明确的官方入口，用户配置独立显示 | #109；供应商迁移、列表测试和用户验收。 |
| 3 刷新及切换节点 | 显示策略组、已选节点及不可手选原因 | #110、Preview.2；真实 Mihomo 刷新、切换后读回和用户验收。 |
| 4 市场安装 | 单选 office-hours 只安装所选技能和运行依赖 | #111、Preview.2；新配置目录断网安装，两个引擎入口和上游辅助程序实测。 |
| 5 选中即复制 | Claude、Codex 滚动后可多次框选复制 | #112；真实 xterm 事件、用户验收。 |
| 6 设置和用量 | 订阅与节点操作可达，供应商和模型用量分表 | #113；前端布局检查、用户验收。 |
| 7 结构化预览 | 折叠、展开、文件与网址打开，exec 可读命令和结果 | #114、Preview.2；工具包装参数、中文输出与实际记录。 |
| 8 导出 Markdown | 两个入口均可选位置导出完整内容 | #114；长记录、中文末尾、取消及用户验收。 |
| 9 删除确认 | 显示影响范围并终止成员会话，保留无关标签 | #114、Preview.2；拖入记录标题、取消和真实进程对照。 |
| 10 标签栏工作目录 | 匹配目录可逐级选择，含空格路径可启动 Bash | #115；路径建议、会话启动及用户验收。 |
| 11 集合新建会话 | 直接或经主题启动的会话归入发起集合 | #115、Preview.2；菜单、工作目录及归属检查。 |
| 补充问题 | Codex 升级启动、密集滚动及快速切换标签、市场搜索超过 20 条 | 验收源码 `3872472b`。滚轮事件与快速切换压力回归；Preview.3 搜索 matt 一次返回 200 条唯一结果，其中 53 条来自 mattpocock/skills。数量随上游变化。 |

11 条反馈原文见[范围表](README.md#范围与验收)，操作步骤见[手测清单](HANDTEST.md)。批次 PR 为 [#109](https://github.com/Wifabric/AISC/pull/109) 至 [#115](https://github.com/Wifabric/AISC/pull/115)，候选整合见 [#116](https://github.com/Wifabric/AISC/pull/116)。Preview.2 本地回归有 912 项前端通过，Rust 423 项通过、2 项忽略，Python 相关测试 406 项通过、12 项跳过。以上计数属于各自候选。

## 正式候选验证

以 `387a8f02` 为功能与版本源码核验。Windows 本机通过前端生产构建与 914 项前端测试、Python 1,854 项测试和 220 项子测试（58 项跳过），Rust 通过 455 项（另有 2 项忽略）。文档检查通过 51 项，随包资源清单通过 1,371 项。CLI wheel、sdist 都通过元数据严格校验、干净环境安装、重装与卸载后重装；pipx 及无仓库环境安装通过。自动跳过项保留原状态。

[候选代码 CI](https://github.com/Wifabric/AISC/actions/runs/45862926958) · [Windows 安装与 2.1.19 覆盖升级流水线](https://github.com/Wifabric/AISC/actions/runs/45863292942)

## 发布前安排（历史）

| 项目 | 交付内容与完成条件 |
| --- | --- |
| 版本与来源 | Windows Workbench 2.1.20、CLI 0.3.1；CLI 定版覆盖会话、节点及市场适配器的实际变化。以审核并合入 main 的提交为发布来源。 |
| 文档 | [Workbench 说明](../../releases/v2.1.20.md)、[CLI 说明](../../releases/v0.3.1.md)、[使用手册](../../../README.md)、[开发手册](../../../DEVELOP_WIKI.md)、[开发日志](../../devlog.md)、[待办](../../todo.md)。 |
| Windows | 确认后使用 `v2.1.20`，GitHub Release 交付 `AISC-Workbench-2.1.20-setup.exe` 和同名 `.sha256`。发布后从公开下载独立核对，并验证旧版更新发现。 |
| 独立 CLI | 同源 `cli-v0.3.1`，先 TestPyPI 实装，再通过正式 PyPI 发布和实装验证。渠道结果分别回填。 |
| 反馈及收尾 | 发布可下载后逐条回复 11 项并回读；复核 Latest、发布证据与长期分支、归档阶段记录，向负责人交付最终下载及状态。 |
| 验证边界 | 本机用户验收不等于在每个 SSH 目标、订阅、模型账户或 Windows 签名策略下均已验证。集中发布证据以 Windows 安装升级报告及适用 CI 为准。 |

开发方法、备用库和 Skill 试用证据在项目外维护。产品内置的技能目录、市场、安装器与测试属于产品交付范围。公开材料只记录验收结论；用户数据库、订阅和凭据保留在本机。

## 正式发布结果（2026-11-27）

升级前请记下原工作区。运行 [Windows x64 安装包](https://github.com/Wifabric/AISC/releases/download/v2.1.20/AISC-Workbench-2.1.20-setup.exe) 覆盖升级后，打开同一工作区核对 Provider。需要新版镜像内工具时，请使用本版资源重建镜像。下载页同时提供 [SHA-256 文件](https://github.com/Wifabric/AISC/releases/download/v2.1.20/AISC-Workbench-2.1.20-setup.exe.sha256)。

| 核对项 | 结果 |
| --- | --- |
| 版本与来源 | Workbench 2.1.20、CLI 0.3.1；[发布 PR #119](https://github.com/Wifabric/AISC/pull/119) 合入 main，两个正式标签指向提交 `68d2d1a0d437fbe810a1d6778f2fe945dfd0d449`。 |
| Windows 下载 | [正式 Release](https://github.com/Wifabric/AISC/releases/tag/v2.1.20) 为 Latest，公开资产含安装包与校验文件。下载 439,491,566 字节，SHA-256 `4c08f55d617c3d9c3397f9f0d426410a9915bcc5c11bc4cbc0edef20aa98c1f3`。已与 GitHub 资产摘要、校验文件及正式标签升级报告逐项比对。 |
| 安装升级 | [正式标签运行](https://github.com/Wifabric/AISC/actions/runs/45875247387) 完成静默新装和从 2.1.19 覆盖升级，升级报告 8 步通过。安装后桌面版本 2.1.20，CLI 与 bundle 均为 0.3.1。 |
| 重跑说明 | [首次运行](https://github.com/Wifabric/AISC/actions/runs/45875247387/attempts/1) 在原生窗口检查通过后，清理脚本尝试结束已退出的进程，导致后续步骤中止。保留首次失败记录；上行结果取自同一标签重新执行后的完整通过报告。 |
| 旧版发现更新 | 用 2.1.19 与 2.1.20 的生产版本选择代码读取公开更新源。旧正式版及 Preview.3 均发现正式 2.1.20，已装正式版不会提示重复升级。 |
| 独立 CLI | CLI 0.3.1 已在 [PyPI](https://pypi.org/project/aisc-cli/0.3.1/) 上线，两个索引的实际安装均通过，公开 wheel 与源码包摘要一致。 [发布及安装核验](https://github.com/Wifabric/AISC/actions/runs/45875526268) |
| 用户验收 | Preview 的 11 项功能均获用户确认。正式安装包的证据来自上述标签构建、公开下载和安装升级检查。 |
| 反馈站 | 11 条反馈保留原文、投票与附件，追加本版处理说明。[反馈提交](https://github.com/Wifabric/aisc-issues-feedback/commit/72a4cc2499c1dfe09759bee72ff9dc742743af13) 已逐条验证；公开站点 11 个列表条目和 11 个详情均读回通过。 |
| 交接 | 本阶段已归档。Windows 安装器未做代码签名，实际远端 SSH、账号与订阅覆盖范围见上文。负责人对整版交付材料的签收另行记录。 |
| 开发线 | [PR #120](https://github.com/Wifabric/AISC/pull/120) 已在 develop 开启 CLI 0.3.2.dev0。main、正式安装包和两个正式标签继续对应 CLI 0.3.1。 |
