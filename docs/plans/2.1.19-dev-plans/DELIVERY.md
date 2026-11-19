# AISC 2.1.19-preview.1 整版交付记录

核对日期：2026-11-19。**本轮主要功能、已发现的编码/会话选择/滚动条缺口已修复；Python、前端、Rust 回归和 Windows 静默新装/升级链路通过。PR #104 已合入 develop，收尾 PR #105 正在完成最终提交验证。偶发卡死按用户决定暂缓。没有 leader 签收或正式 Release。**

## 1. 当前状态与责任

| 环节 | 状态 | 结论与接续 |
| --- | --- | --- |
| 15 条当前版本反馈 | 14 条有实现和相应证据，1 条暂缓 | 逐条见 §3；受控样本与反馈者原场景分开记录 |
| 自动化回归 | PASS | Python 1841 + 220 子测试；前端 902；Rust 455；环境跳过如实保留 |
| 实际桌面/容器 | PASS（已执行范围） | 文件/SSH/技能/节点/标签/记录，另补三引擎滚动条和 Docker 官方入口 |
| Windows 静默安装链路 | PASS | 正式旧版升级、启动/CLI/PATH、设置/记录/项目保留、静默卸载通过 |
| 人工安装体验 | NOT RUN | GUI 向导、Docker 依赖引导、取消卸载与额外清理选择不由静默 CI 代替 |
| 用户账号验收 | 用户报告 PASS | 不重复账号测试；技术编码与权限回归独立记录 |
| PR 与集成 | #104 已合入；#105 收尾 | 精确提交和 CI 见 §2、§4；按已有授权完成 develop 合入，自查不冒称独立评审 |
| leader 功能验收 | 未取得结论 | 按 HANDTEST 测试，同意上线需实际回复 |
| 正式发布/反馈/归档 | 待发布条件 | 不提前写 resolved、不创建 final tag、不归档活动计划 |

当前代码收尾与正式发布是不同阶段。最后一次难复现的卡死继续暂缓；原权限问题和日志问题缺少反馈者原始样本，已完成受控回归，但保留复现证据的限制。

## 2. 版本、来源与产物

| 项目 | 当前事实 |
| --- | --- |
| 初始基线 | v2.1.18 后的 `1c39903dc146e00ac5b7d92c8bd48433a3d4a7f5` |
| 主更新 | [PR #104](https://github.com/Wifabric/AISC/pull/104)，develop 合入 `df448d3af9aa287e8337789583f05612fe3c4850` |
| 收尾 | [PR #105](https://github.com/Wifabric/AISC/pull/105)，`codex/2.1.19-closeout`；首个已通过 CI 的提交 `58b25ecdfd0dfed3c0d920a05d7d612eccb75d40` |
| 当前补修 | Codex 内联滚动及交付文档；最终 head 和后续 CI 以 PR 检查和本记录后续补记为准，不把首轮结果当作补修提交结果 |
| Workbench / CLI | `2.1.19-preview.1` / `0.3.0.dev0`，serve protocol 4 |
| 本地便携入口 | `D:\AISC\output\2.1.19-acceptance\打开本地测试版.cmd`；配套 `client-retest` 程序、CLI 和 bundle 已更新 |
| 便携可执行文件 SHA-256 | Workbench `7b94806eb4c42dde03d6cb0626880f2182ffcc7ebe68ff3b9234bb318ddf983d`；CLI `91d2841c0b15a7b46241cee7c8fc409ff95f505423eb3e25eb09b4c1e89643a5`；后续仅更新外部容器脚本和校验表 |
| 初次 CI 安装包 | [run 44458626580](https://github.com/Wifabric/AISC/actions/runs/44458626580)，artifact `aisc-workbench-windows-nsis`，对应 58b25ecd；SHA-256 `1a9ba08b5089a53f7b39d058675222f0f59ed236fc46ba6fa5c87985bc63546f` |
| 旧本地安装包 | acceptance 目录中旧摘要 `c40d352f…` 的安装包不含 #105 补修；不能仅按相同版本号当作最新候选 |
| 隔离数据 | acceptance 下 `test-data` / `test-webview`；测试工作区和宿主 Docker 仍是真实资源 |
| 公开渠道 | 没有本版 Release/tag、PyPI/TestPyPI 或公开 final 下载；Actions artifact 不是正式 Release |

转交其他机器时只提供完整运行文件或 CI 安装包，不打包测试凭据、test-data、test-webview 或个人配置。包、提交和摘要应成套交接。

## 3. 全部 15 条反馈的处理

第 1 条来自 11 月 18 日的 Isaac，其余来自 11 月 13 日的 Thomas。“实现”与“原问题已复现并解决”分别记录。

| # | 反馈 | 本轮处理与用户可见变化 | 实际验证 / 保留边界 |
| --- | --- | --- | --- |
| 1 | 设置里查看网络和用量 | 设置打开当前工作区网络页，保留订阅刷新，新增节点列表、切换和测速；导入后更新启动摘要 | 测试订阅的列表、切换、刷新读回及 DIRECT 测速通过；不替代个人订阅验证 |
| 2 | Codex Provider 默认配置 | 新建默认 Responses；仅 Codex 新建列表隐藏 Ark；按格式填入 DeepSeek/智谱/Kimi 地址，已有和手填地址保留 | 用户报告账号手测通过；公开模型接口的鉴权响应不当作真实账号成功 |
| 3 | 侧边栏移动文件和文件夹 | 右键移动及单项拖动到目录，本地/SSH 接入文件操作；同名不覆盖，拖入终端不执行 | 本地与真实 SSH 文件/目录、冲突及内容对照通过 |
| 4 | 默认安装 gh CLI | 新镜像增加 GitHub CLI | 真实镜像执行 `gh --version` 返回 2.23.0；仅是本轮实测版本 |
| 5 | Codex、Bash、Claude 终端滚动条 | 加宽滚动条；Codex 新建/恢复使用 --no-alt-screen，保留外层终端历史，不改全局配置 | Bash 300 行回滚通过；Claude 原生客户端经本地模拟接口产生 220 行，拖到第 37 行再回第 220 行；Codex 内联模式拖看四轮原生历史并返回输入行通过 |
| 6 | 工作记录与实际会话不一致 | 按引擎与原生 ID 归并，Codex 优先选择原生 SQLite 索引指定的记录；无可用索引时取最近写入记录；依据原生父子信息归档，缺信息留未归档 | 重复旧日志/原生索引回归通过；Codex 8 条消息预览与原生恢复四轮一致，Claude 4 条消息含相同 220 行输出；无反馈者原样本，不称原自然场景已复现 |
| 7 | 父工作记录移动/删除时的子记录 | 移动覆盖后代，删除确认计算受影响数量，列表按层级显示 | 父/子/孙整体移入、移出、删除通过，无关记录保留；取消删除通过 |
| 8 | 标签导航栏调整 | 拖动排序、加号及分屏选择启动目录；修复桌面原生拖动失效 | 双向排序、当前会话不变、A/B 分屏独立目录通过；重开工作区仍从单个 Bash 开始 |
| 9 | Codex、Claude 官方直连报错 | 刷新当前官方卡时重新应用配置 | 用户账号手测通过；隔离无网络容器内两个 agent 各验证正常刷新、真实 EACCES 拒绝、恢复权限后三阶段，共 6 项 PASS；原重建卷自然触发条件未知 |
| 10 | 标签与会话对应关系不清楚 | 标签和记录对应编号，引擎颜色区分，双击关联标签定位 | 桌面双击定位通过；独立终端单独编号 |
| 11 | Docker 重置按钮 | 设置打开 Docker 官方 Dashboard，提示进入 Troubleshoot，由官方最终确认 | Computer Use 验证 Dashboard 关闭后可从 AISC 重新打开、官方 Troubleshoot 有重置入口、退出页面；未执行宿主恢复出厂 |
| 12 | 镜像构建 UI 重复提示 | 按提示内容去重，避免相同警告反复出现 | 真实专用镜像构建 140.3 秒完成，未观察到原重复提示；另有前端回归 |
| 13 | 技能更新全部报错 | 嵌套目录定位、唯一匹配及异常链接检查 | 真实 `mattpocock/skills` 20 项更新通过，界面恢复可操作，适配器退出码 0 |
| 14 | 技能安装全部报错 | 同一定位修复用于整组安装，保留原启停状态 | GUI 安装列表从 2 项增至 20 项，刷新后数量正确，适配器退出码 0 |
| 15 | 单个标签偶发卡住 | 已加入焦点/页面恢复及 WebGL 恢复时重绘 | 有限输出检查未复现原问题；按用户要求跳过，不标为已解决 |

实测追加修复：Docker 47000 端口冲突后残留容器导致重试名称冲突，现按本次完整容器 ID 清理失败对象，再改用 47001 成功；不强制删除运行对象。远程最近工作区的机器名被长路径挤压，已调整布局并复测。Windows WebView 文件树单项拖动由指针处理补正，真实远程拖动通过。

## 4. 验证证据与实际限制

本地证据位于 `D:\AISC\output`。下列本地计数不冒充远端 CI，独立重测也不相加成全集数量。

| 类别 | 实际结果 | 证据 |
| --- | --- | --- |
| Python 全集 | PASS：1841 通过、74 跳过、220 子测试通过 | `2.1.19-closeout-python-all.log`，显式 candidate PYTHONPATH 与 Git Bash |
| 前端 | PASS：107 文件、902 项 | `2.1.19-closeout-frontend-all.log` |
| Rust | PASS：455 项、2 忽略 | `2.1.19-closeout-rust.log`；环境门控的 SSH/运行时用例不等于实际数据面执行 |
| Windows 编码 | PASS：原空目录失败及 UTF-8/写入错误回归 | `2.1.19-closeout-catalog-cp1252.log`，PYTHONUTF8=0 |
| 工作记录 | PASS：79 项 | `2.1.19-closeout-conversations.log` |
| Codex 内联补修 | PASS：55 项、11 环境跳过 | `2.1.19-closeout-inline-tests.log`，新建/恢复参数及会话命令 |
| 本地编译 | PASS：冻结 CLI、前端 production、Tauri release | `2.1.19-closeout-cli-build.log`、`2.1.19-closeout-desktop-build.log` |
| 首轮 Workbench CI | PASS，58b25ecd | [run 44458639592](https://github.com/Wifabric/AISC/actions/runs/44458639592) |
| 首轮 NSIS / 安装升级 | PASS，58b25ecd | [run 44458626580](https://github.com/Wifabric/AISC/actions/runs/44458626580)，`windows-upgrade-acceptance/upgrade-result.json` |
| 安装报告本地副本 | PASS：6 个升级步骤及摘要 | `2.1.19-44458626580-windows-upgrade-acceptance/upgrade-result.json` |
| Codex 原生预览/恢复/滚动 | PASS：8 条消息、四轮历史一致；滚动条回顶/中间/末尾 | `2.1.19-closeout-codex-preview.png`、`-codex-inline-top.png`、`-codex-inline-history.png`、`-codex-inline-bottom.png` |
| Claude 原生滚动与预览 | PASS：220 行回滚，预览含同一输出 | `2.1.19-closeout-claude-scroll-history.png`、`-claude-scroll-returned.png`、`-claude-preview.png`；使用容器内本地模拟接口，不是新账号测试 |
| Docker 官方入口 | PASS：从 AISC 重开 Dashboard、进入官方 Troubleshoot 后退出 | `2.1.19-closeout-docker-official-flow.png`、`-docker-reopened.png`；没有重置宿主数据 |
| 权限拒绝与恢复 | PASS：Claude/Codex 共 6 阶段 | `2.1.19-closeout-permissions.json`；隔离、无网络、无用户账号，不能替代反馈者自然复现 |
| 本地/SSH GUI | PASS：移动、冲突、目录、标签、多代记录；远程内容对照 | `2.1.19-device-checks/cu-file-conflict.png`、`cu-remote-move-content-proof.json`、`cu-tabs-pointer-reordered.png`、`cu-records-deleted-unrelated-retained.png` |
| 技能真实数据面/GUI | PASS：20 项安装及更新 | `2.1.19-gui-market20.log`、`2.1.19-gui-frontend-verified.log` |
| 网络节点与摘要 | PASS：切换/读回、DIRECT 测速及导入摘要 | `2.1.19-proxy-session.log`、`2.1.19-packaged-nodes.json` |
| 用户账号测试 | 用户报告 PASS | 2026-11-18 用户回复“全部测试过了，没问题” |
| leader、人工安装交互、final 发布 | 未执行/未取得结论 | 不用自动化或本地开发者自测代签 |

旧 `2.1.19-python-port-final.log` 的 10 失败为历史记录：9 项与 Bash 环境有关，剩余模型目录日志编码已修复；以本轮明确源码路径的全集及编码回归为准。

## 5. Windows 安装覆盖与历史环境问题

**已通过：**静默全新安装、用户 PATH、同版本重装/保留；校验官方 2.1.18 安装包后升级到候选；升级前后真实设置、最近工作区、项目文件和原生 Codex 会话字节对照；已安装 CLI 读取会话；Workbench 创建原生窗口；启动后设置和历史语义保留；静默卸载保留样本并移除程序 bundle。测试只运行在一次性 Windows runner，不碰用户现有安装。

**NOT RUN：**图形安装向导的逐页点击、缺失 Docker 时的依赖安装、交互卸载取消以及可选额外清理。CI 的 `/S` 刻意跳过这些交互；原生窗口启动仅为启动检查。未签名包在强制应用控制环境中的拦截仍可能存在，需发布方签名或可接受候选的正常测试环境；没有改任何 Windows 安全策略。

以下保留本机历史环境调查和清理事实，不把它们作为当前自动化安装失败：

- 本轮沙盒内 Smart App Control 状态为 1（强制执行），CodeIntegrity 3077/3033 指向候选安装程序；正式旧版也受阻。安装向导未运行，不能据此判定 AISC 安装逻辑本身成功或失败。
- 宿主只读核对 SAC 为 0，不能把原因归结为宿主 SAC 已开启。旧成功沙盒未保存策略状态，差异原因仍未证实。
- guest 缺少 SecHealthUI，Windows Security 链接无法打开；用户手动运行微软修复包后界面仍未恢复。没有修改宿主或 guest 安全策略。
- 发布构建脚本已支持发布方签名配置并检查本次产物的 Authenticode 签名；当前未提供有效签名证书或服务，最终候选仍未签名。这是构建能力，不是已经解决策略拦截。
- Hyper-V 路线未完成 Windows 安装，后续替代路线仅完成 ISO 校验和 QEMU 镜像准备。按用户“02:15 前未开始 AISC 实测就停止”的要求，02:14 停止准备，没有把环境搭建记成测试。
- 新建沙盒、空 Hyper-V VM、ISO/分片、临时账户材料、修复包及本轮 QEMU Docker 镜像/精确缓存均已清理。最后一轮删除下载约 15.92 GiB，核对无本轮运行容器、测试卷或沙盒；保留源码、候选安装包和证据。

证据索引（同在 `D:\AISC\output`）：

| 事项 | 文件 |
| --- | --- |
| 最终候选策略拦截 | `sandbox-tests/20261119-final/fresh/observe-probe.json`、`smart-app-control.png` |
| 修复包未恢复安全界面 | `sandbox-tests/20261119-final/fresh-repair/security-repair-after-user.json` |
| 宿主策略只读核对 | `sandbox-tests/20261119-final/host-policy-readonly.json` |
| 按旧成功流程重试仍被拦截 | `sandbox-tests/20261119-original-flow/fresh/fresh-launch-result.json` |
| 空 Hyper-V VM 与第一轮下载清理 | `windows-vm-tests/20261119/evidence/cleanup.json` |
| 截止时停止与最后一轮清理 | `windows-vm-tests/20261119-browser/evidence/cleanup.json` |
| 前一阶段 SSH 测试环境清理 | `2.1.19-device-checks/cu-remote-cleanup.json` |

用户之前批准的安装、单台 VM 控制台连接等操作不代表测试仍在继续；这些临时目标已移除，旧的手动连接请求作废。

## 6. 文档、发布与后续交接

| 文档 / 环节 | 本轮状态 |
| --- | --- |
| [Workbench Release Notes](../../releases/v2.1.19-preview.1.md) | 参照 2.1.17 按功能分组重写；说明行为、使用入口、依赖及限制；文件名修正为 tag 对应的 v 前缀 |
| [CLI Release Notes](../../releases/v0.3.0.dev0.md) | 补充命令参数、文件服务、会话与运行时变化、配对及渠道边界 |
| [用户手册](../../../README.md) | 更新候选版本、文件移动、标签/目录、节点、Provider 模板、技能与升级限制 |
| [开发手册](../../../DEVELOP_WIKI.md) / [Workbench](../../../workbench/README.md) / [安装器维护](../../../workbench/src-tauri/nsis/README.md) | 补齐本版交接、构建资源配对、接口与签名说明、功能与安装验收边界 |
| [活动计划](README.md) / [手测教程](HANDTEST.md) | 范围、实际 CI/桌面结果、leader 步骤及安装边界已同步 |
| [devlog](../../devlog.md) / [TODO](../../todo.md) / [计划索引](../README.md) | 功能、文档更新与待办分别记账；旧版 PyPI 外部待办独立保留 |
| [开发 Skill](../../../skills/aisc-development/SKILL.md) | 补充发布说明需与实现及 tag 文件命名一致的检查，保留原授权边界 |
| 正式 2.1.19 / CLI final 说明与资产 | 尚未定稿或发布；当前说明属于预览候选，不伪造 final 验收结论 |
| 反馈站、归档、分支清理 | 未执行；发布及验收未闭环，计划保留活动状态 |


PR #105 按已有授权提交、验证和合入 develop。正式版本、main/final tag、公开资产及反馈 resolved 回写等到 leader 结果与对应发布条件满足后执行；当前计划保持活动状态。反馈站当前版本 15 条中偶发卡死继续单列，未发布之前不伪装“用户已拿到修复”。历史实时富文本增强另属既有 intake，不追加进本版范围。

本轮文档检查 51 项通过、0 警告、0 失败；会话/版本/工作流契约 81 项通过、11 项按环境跳过；1368 个容器资源摘要全部一致。日志为 `2.1.19-closeout-docs-check.log`、`2.1.19-closeout-final-contracts.log`、`2.1.19-closeout-vendor-final.json`。便携包关键文件摘要见 `2.1.19-closeout-portable-final-sha256.json`。

最终 head 的 CI、产物摘要及合入结果在本记录后续补记；早期文档检查和旧产物不能代替最终提交验证。本地手测教程与沙盒交接开头同步当前状态，避免后续误按历史 VM 步骤重建环境。
