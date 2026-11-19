# AISC 2.1.19 整版交付记录

核对日期：2026-11-19。**Workbench 2.1.19 正式版已发布为 Latest，随包 CLI 0.3.0；PR #106 已合入 main。正式包重新构建，静默新装、2.1.18 升级、启动/CLI/PATH、保留及下载 SHA-256 均通过。用户已确认功能和剩余安装交互全部手测无问题。14 条本版反馈已回复并置 resolved，阶段已归档；偶发卡死按用户决定暂缓。**

独立 CLI **0.3.0** 已发布至 [PyPI](https://pypi.org/project/aisc-cli/0.3.0/)，TestPyPI 与正式 index 安装验证通过。正式发布证据见第 8 节；前期 Preview 包与历史测试保留原版本及摘要。

## 1. 当前状态与责任

| 环节 | 状态 | 结论与接续 |
| --- | --- | --- |
| 15 条当前版本反馈 | 14 条有实现和相应证据，1 条暂缓 | 逐条见 §3；权限与工作记录问题按本轮回归和用户验收收口 |
| 自动化回归 | PASS | Python 1841 + 220 子测试；前端 902；Rust 455；环境跳过如实保留 |
| 实际桌面/容器 | PASS（已执行范围） | 文件/SSH/技能/节点/标签/记录，另补三引擎滚动条和 Docker 官方入口 |
| Windows 静默安装链路 | PASS | 正式旧版升级、启动/CLI/PATH、设置/记录/项目保留、静默卸载通过 |
| 人工安装体验 | PASS（用户报告，2026-11-19） | 安装完成页、启动/快捷方式、Docker 缺失/启动/重新检测、卸载取消及五轮保留/清理全部手测通过；与 CI/CU 分开记账，见第 5 节 |
| 用户账号验收 | 用户报告 PASS | 不重复账号测试；技术编码与权限回归独立记录 |
| PR 与集成 | #104、#105 已合入 develop；#106 已合入 main | [#105](https://github.com/Wifabric/AISC/pull/105) 合入提交 `6877334d`；代码验收提交和 CI 见 §2、§4；本轮为自查 |
| 整版用户验收 | PASS（用户报告） | 用户确认“我都手测完了，没有问题”，要求准备最终版；不要求重新做已通过的手测，也不冒称另有 leader 署名 |
| Preview 下载发布（历史） | PASS，2026-11-19 15:17（北京时间）；保留历史资产并标注由正式版接替 | [v2.1.19-preview.1](https://github.com/Wifabric/AISC/releases/tag/v2.1.19-preview.1)：安装包和 SHA-256 已公开，远端摘要与验收包一致，下载链接已验证；当时 latest 为 v2.1.18，现已由 v2.1.19 接替 |
| 正式发布/反馈/归档 | Workbench 已发布、14 条反馈已回写、计划已归档 | 正式包与渠道结果见第 8 节；独立 CLI 状态单独记账 |

当前代码收尾与正式发布是不同阶段。最后一次难复现的卡死继续暂缓；权限与工作记录问题按本轮回归和用户验收结论收口。代码签名沿用旧版分发方式，按用户决定本轮暂不处理，不列为发布前新增任务。

## 2. 验收候选版本、来源与产物（历史）

本节保留已验收 Preview 的真实版本和包摘要；正式版来源及下载见第 8 节。

| 项目 | 当前事实 |
| --- | --- |
| 初始基线 | v2.1.18 后的 `1c39903dc146e00ac5b7d92c8bd48433a3d4a7f5` |
| 主更新 | [PR #104](https://github.com/Wifabric/AISC/pull/104)，develop 合入 `df448d3af9aa287e8337789583f05612fe3c4850` |
| 收尾 | [PR #105](https://github.com/Wifabric/AISC/pull/105)，`codex/2.1.19-closeout`；首个已通过 CI 的提交 `58b25ecdfd0dfed3c0d920a05d7d612eccb75d40` |
| 最终代码验收 | `2a8758af212493b1321e3a434992fa1451ff03f4`，Workbench CI 44462727381 和 NSIS 44462773106 全部 PASS；其后的修订仅更新不随程序打包的验收文档，构建输入不变 |
| Workbench / CLI | `2.1.19-preview.1` / `0.3.0.dev0`，serve protocol 4 |
| 本地便携入口 | `D:\AISC\output\2.1.19-acceptance\打开本地测试版.cmd`；配套 `client-retest` 程序、CLI 和 bundle 已更新 |
| 便携可执行文件 SHA-256 | Workbench `7b94806eb4c42dde03d6cb0626880f2182ffcc7ebe68ff3b9234bb318ddf983d`；CLI `91d2841c0b15a7b46241cee7c8fc409ff95f505423eb3e25eb09b4c1e89643a5`；后续仅更新外部容器脚本和校验表 |
| 初次 CI 安装包 | [run 44458626580](https://github.com/Wifabric/AISC/actions/runs/44458626580)，artifact `aisc-workbench-windows-nsis`，对应 58b25ecd；SHA-256 `1a9ba08b5089a53f7b39d058675222f0f59ed236fc46ba6fa5c87985bc63546f` |
| 最终 CI 安装包 | [run 44462773106](https://github.com/Wifabric/AISC/actions/runs/44462773106)，artifact `aisc-workbench-windows-nsis`；SHA-256 `cc330f34980b4b82ffff7288ce8a38200812d303e54fe7a59060ae3a60aa2b7f`；早期 `c40d352f…` 包不含本轮收尾修复 |
| 隔离数据 | acceptance 下 `test-data` / `test-webview`；测试工作区和宿主 Docker 仍是真实资源 |
| 公开渠道 | [v2.1.19-preview.1](https://github.com/Wifabric/AISC/releases/tag/v2.1.19-preview.1) 已发布安装包及 SHA-256；本版 CLI 尚未发布 PyPI/TestPyPI，Workbench final 尚未发布 |

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
| 6 | 工作记录与实际会话不一致 | 按引擎与原生 ID 归并，Codex 优先选择原生 SQLite 索引指定的记录；无可用索引时取最近写入记录；依据原生父子信息归档，缺信息留未归档 | 重复旧日志/原生索引回归通过；Codex 8 条消息预览与原生恢复四轮一致，Claude 4 条消息含相同 220 行输出；本轮验收收口 |
| 7 | 父工作记录移动/删除时的子记录 | 移动覆盖后代，删除确认计算受影响数量，列表按层级显示 | 父/子/孙整体移入、移出、删除通过，无关记录保留；取消删除通过 |
| 8 | 标签导航栏调整 | 拖动排序、加号及分屏选择启动目录；修复桌面原生拖动失效 | 双向排序、当前会话不变、A/B 分屏独立目录通过；重开工作区仍从单个 Bash 开始 |
| 9 | Codex、Claude 官方直连报错 | 刷新当前官方卡时重新应用配置 | 用户账号手测通过；隔离无网络容器内两个 agent 各验证正常刷新、真实 EACCES 拒绝、恢复权限后三阶段，共 6 项 PASS；本轮验收收口 |
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
| 权限拒绝与恢复 | PASS：Claude/Codex 共 6 阶段 | `2.1.19-closeout-permissions.json`；隔离、无网络、无用户账号 |
| 本地/SSH GUI | PASS：移动、冲突、目录、标签、多代记录；远程内容对照 | `2.1.19-device-checks/cu-file-conflict.png`、`cu-remote-move-content-proof.json`、`cu-tabs-pointer-reordered.png`、`cu-records-deleted-unrelated-retained.png` |
| 技能真实数据面/GUI | PASS：20 项安装及更新 | `2.1.19-gui-market20.log`、`2.1.19-gui-frontend-verified.log` |
| 网络节点与摘要 | PASS：切换/读回、DIRECT 测速及导入摘要 | `2.1.19-proxy-session.log`、`2.1.19-packaged-nodes.json` |
| 用户账号测试 | 用户报告 PASS | 2026-11-18 用户回复“全部测试过了，没问题” |
| 安装完成页/实际清理/Docker 完整引导 | PASS（用户报告） | 2026-11-19 用户确认前述手测清单全部无问题；原 CI/CU 范围不变 |
| final 发布 | Workbench PASS；CLI 状态见第 8 节 | main、不可变标签、正式包重建、安装升级和公开下载已核对 |

旧 `2.1.19-python-port-final.log` 的 10 失败为历史记录：9 项与 Bash 环境有关，剩余模型目录日志编码已修复；以本轮明确源码路径的全集及编码回归为准。

最终代码验收提交 `2a8758af212493b1321e3a434992fa1451ff03f4`：

- [Workbench CI 44462727381](https://github.com/Wifabric/AISC/actions/runs/44462727381)：frontend / rust / cli 全部 success。
- [Windows NSIS 44462773106](https://github.com/Wifabric/AISC/actions/runs/44462773106)：构建、静默新装/PATH/重装保留、官方 2.1.18 升级全部 success；`windows-upgrade-acceptance` 的六个步骤均 PASS。
- 从最终镜像重新创建运行时、新建 Codex 正常进入；实际进程包含 `--no-alt-screen`，容器脚本摘要与最终源码一致。证据：`2.1.19-closeout-runtime-final.json`、`2.1.19-closeout-codex-new-final.png`。
- 原模拟 Provider 已移除并恢复原官方选择；两轮桌面测试运行时及权限测试容器已删除，保留测试样本与证据。没有重置宿主 Docker。

## 5. Windows 安装覆盖与历史环境问题

**最新结论：安装交互已收口。** 2026-11-19 用户在收到完整操作清单后回复：“我都手测完了，没有问题，现在准备上传最终版”。因此以下剩余项目记为 **PASS（用户报告）**：完成页启动/桌面快捷方式勾选与取消、Docker 退出后启动、未安装 Docker 时下载指引及安装后重新检测、三项均不选的卸载保留、仅工具链清理、仅 Docker 清理、仅应用数据清理、Docker 不可达时资源保留与提示。此前卸载界面/三个选项/取消也已由用户确认通过。本地记录为 `windows-install-cu-20261119/evidence/user-final-acceptance.json`；不虚构用户未提供的逐项截图、设备信息或开发者重测记录。

**已通过：**静默全新安装、用户 PATH、同版本重装/保留；校验官方 2.1.18 安装包后升级到候选；升级前后真实设置、最近工作区、项目文件和原生 Codex 会话字节对照；已安装 CLI 读取会话；Workbench 创建原生窗口；启动后设置和历史语义保留；静默卸载保留样本并移除程序 bundle。测试只运行在一次性 Windows runner，不碰用户现有安装。

**Computer Use 已通过（2026-11-19）：**使用最终验收包验证中英文语言选择/欢迎页、旧版维护页、“请勿卸载”选择、D 盘安装路径输入及空间显示、返回上一步、安装前取消。另验证目录浏览取消后保留原路径、空路径禁用继续、中文和空格路径可输入。目录页“下一步”会直接开始安装；检测到已有 Workbench 运行后选择取消，安装明确中止，原进程继续运行，注册版本仍为 2.1.17。仅创建了空测试目录，核对后已清理；未在宿主完成安装或执行卸载。证据为本地 `windows-install-cu-20261119/evidence/installer-navigation.json`。

**卸载确认与取消已通过（用户手测）：**从公开候选原包在一次性 Windows runner 安装后提取真实卸载程序，摘要为 `20423686b6dd28178804ff5a505899c2362409840676f44c67a93ae8b86da675`。用户确认其 D 盘测试目录、三个清理选项与取消操作正常；随后核对本机注册版本/安装位置/卸载命令、测试哨兵和卸载程序摘要、原 Workbench 进程均保留。此项由用户完成；Computer Use 工具策略拒绝启动卸载程序。提取任务 [run 44483581493](https://github.com/Wifabric/AISC/actions/runs/44483581493) 通过。

**Docker 提示及重新检测已通过（Computer Use 受控场景）：**[run 44484606364](https://github.com/Wifabric/AISC/actions/runs/44484606364) 从同一公开候选提取实际 Workbench/CLI，摘要分别为 `6d5fe42fe63c266856f708dfa066412995a159e568cacb13d969b92e4f4869cf` / `5c0551a1301083d8677435b25231edb94825ff7913b45aed0e350e86041cea0c`。在 D 盘独立数据目录的测试进程中限制 Docker Desktop 路径可见性，界面显示“未安装”并给出自行安装说明；恢复路径可见性后点击“重新检查”，变为“已安装”且说明消失，“继续设置”进入工作区选择。宿主 Docker 引擎全程运行并可达；这不覆盖真正从零安装 Docker 或启动停止的引擎。截图/结果位于 `windows-install-cu-20261119/evidence/docker-desktop-*.png` 和 `docker-onboarding-result.json`。

本轮空测试 VM、临时 Hyper-V 读取权限、未完成系统镜像下载和 Docker 测试路径联接均已清理并验证；测试实例已退出，专用 WebView 缓存和重复下载压缩包已删除，候选运行文件与验收证据留在 D 盘，宿主 AISC 和 Docker 保留。清理回执见 `windows-install-cu-20261119/evidence/test-storage-cleanup.json`。临时 GitHub QA 分支已删除，运行记录保留；该轮测试没有新 PR、产品代码变更或 Final 发布；后续正式发布见第 8 节。

**测试来源边界：**上述完整交互的最终通过结论来自用户手测；CI 的 `/S` 跳过交互，开发者 Computer Use 只覆盖已留证范围，不把这两者扩写为完整交互测试。原未测清单已由用户补验收口。签名按用户决定暂不处理，不作为本轮新增发布任务。

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

## 6. 文档与发布前交接记录（历史）

下表保留发布前文档准备记录；正式发布后的最终状态以第 8 节为准。

| 文档 / 环节 | 本轮状态 |
| --- | --- |
| [Workbench Release Notes](../../releases/v2.1.19-preview.1.md) | 参照 2.1.17 按功能分组重写；说明行为、使用入口、依赖及限制；文件名修正为 tag 对应的 v 前缀 |
| [CLI Release Notes](../../releases/v0.3.0.dev0.md) | 补充命令参数、文件服务、会话与运行时变化、配对及渠道边界 |
| [用户手册](../../../README.md) | 更新候选版本、文件移动、标签/目录、节点、Provider 模板、技能与升级限制 |
| [开发手册](../../../DEVELOP_WIKI.md) / [Workbench](../../../workbench/README.md) / [安装器维护](../../../workbench/src-tauri/nsis/README.md) | 补齐本版交接、构建资源配对、接口与签名说明、功能与安装验收边界 |
| [活动计划](README.md) / [手测教程](HANDTEST.md) | 范围、实际 CI/桌面结果、leader 步骤及安装边界已同步 |
| [devlog](../../devlog.md) / [TODO](../../todo.md) / [计划索引](../../plans/README.md) | 功能、文档更新与待办分别记账；旧版 PyPI 外部待办独立保留 |
| [开发 Skill](../../../skills/aisc-development/SKILL.md) | 补充发布说明需与实现及 tag 文件命名一致的检查，保留原授权边界 |
| 正式 2.1.19 / CLI 0.3.0 说明与资产 | [Workbench 正式说明](../../releases/v2.1.19.md)和 [CLI 正式说明](../../releases/v0.3.0.md)已准备；正式版本号、产物和渠道尚未切换，不将 Preview 摘要标作 Final |
| 反馈站、归档、分支清理 | 用户验收已通过；正式发布后的回写和归档尚未执行，计划保留活动状态 |


PR #105 按已有授权提交、验证和合入 develop，用户验收已通过。接下来按正式发布流程处理版本、main/final tag、公开资产及反馈 resolved 回写；不另加一次重复用户或 leader 功能验收门，亦不伪造 leader 署名。当前计划保持活动状态直到正式渠道和后续交付完成。反馈站当前版本 15 条中偶发卡死继续单列，发布后仅回写本版已解决的 14 条。历史实时富文本增强另属既有 intake，不追加进本版范围。

此前代码收尾的文档检查 51 项通过、0 警告、0 失败；会话/版本/工作流契约 81 项通过、11 项按环境跳过；1368 个容器资源摘要全部一致。日志为 `2.1.19-closeout-docs-check.log`、`2.1.19-closeout-final-contracts.log`、`2.1.19-closeout-vendor-final.json`。便携包关键文件摘要见 `2.1.19-closeout-portable-final-sha256.json`。本次发布前复核结果另列于第 7、8 节，不把两轮计数累加。

最终代码验收 CI 与产物摘要见上文；PR 页面记录文档修订 head 与实际合入结果。文档修订不得改变已验收的构建输入；若修改程序、容器或安装逻辑，须重新验证。本地手测教程与沙盒交接开头同步当前状态，避免后续误按历史 VM 步骤重建环境。

<a id="7-正式发布前核对与下一步"></a>

## 7. 发布前检查记录（版本切换前）

本节是版本切换前的历史快照，其中未执行事项已由第 8 节的实际发布结果接续。

2026-11-19 远端核对：develop 为 `6877334d`，main 仍为 `1c39903d`；#105 已合入，适用前端/Rust/CLI、三平台 sidecar、Linux/macOS bundle、Windows NSIS 均成功。Preview 标签触发的重复 NSIS 任务 44478447971 已主动取消以保留已验收包，不是构建测试失败。GitHub 无开放 Issue/PR，反馈数据提交仍为 `497b37bd`，与本版审计快照一致。记录在本地 `2.1.19-final-remote-audit.json`。

本次复核通过：文档检查 **51 项，0 警告、0 失败**；版本/发布说明/工作流/会话命令契约 **67 项**；16 份当前文档及开发 Skill 的 **107 个相对链接**有效；**1368 个容器资源摘要**一致。安装包本地 SHA-256 与公开资产一致，README 推荐服务保留区未改，程序运行代码与已验收集成提交一致。除文档外仅将 pyproject 的项目链接修正为当前 Wifabric/AISC；没有修改版本或运行逻辑。记录为 `2.1.19-final-docs-check.log`、`2.1.19-final-contract-check.log`、`2.1.19-final-docs-check.json` 与 `2.1.19-pr-vendor-fast.json`。

公开 Preview Release 的验收状态已同步并读回验证，标签、预发布标识、安装包和校验文件均保持；本地回执为 `2.1.19-preview-acceptance-update-receipt.json`。本轮仓库文档与包元数据修改仍在本地工作区，待纳入正式发布提交，不能把本地文件更新说成远端源码已更新。

| 后续事项 | 当前状态与执行要求 |
| --- | --- |
| 正式版本与说明 | 目标 Workbench **2.1.19** / CLI **0.3.0**，两份正式说明已准备；当前源码事实源仍是 Preview/dev 版本，发布执行时先同步版本及 CLI fixture |
| 发布源码 | 将本轮文档与正式版本变更纳入发布提交，经 PR 合入 main，核对实际提交与适用 CI；已有功能验收沿用，不把新正式包的构建检查省略 |
| 正式安装器 | 用正式版本的 CLI、Workbench 和 bundle 重新构建；校验内嵌版本、SHA-256、静默安装/升级结果；不得仅给 Preview exe 改名 |
| Workbench 渠道 | 审核发布提交上创建 v2.1.19，发布安装器与校验文件，核对公开下载、Latest 和旧版更新发现 |
| CLI 渠道 | 同源 cli-v0.3.0，沿用 pypi-publish 流水线分别验证 TestPyPI/PyPI；旧 0.2.0 外部待办单列，不因新说明存在而自动销账 |
| 发布后交付 | 按既有范围回写 14 条反馈；保留暂缓卡死及历史实时富文本 intake；回填发布证据、归档并清理已合入的临时对象 |

本次是发布前检查和材料准备，尚未推送正式 tag、发布 Final/PyPI、关闭反馈或删除 Preview。用户手测已收口，不再把安装补测或原反馈样本列为剩余工作。

## 8. 正式发布完成（2026-11-19）

用户明确要求“上传正式版”。发布提交只同步正式版本、CLI fixture、升级验收期望、项目链接与文档；产品运行逻辑及容器资源与已验收 Preview 保持一致。正式安装包重新构建，没有将 Preview exe 改名使用。

| 项目 | 最终结果 |
| --- | --- |
| 发布 PR / 源码 | [PR #106](https://github.com/Wifabric/AISC/pull/106)，main `8d748eefa37b39baaf7563a556e1a7d0c74f43cc`；merge tree 与已验证候选 bb232584 一致 |
| 标签 | annotated `v2.1.19`、`cli-v0.3.0` 均指向同一发布提交；已发布标签不移动 |
| Workbench 渠道 | [v2.1.19](https://github.com/Wifabric/AISC/releases/tag/v2.1.19)；非 draft、非 prerelease，Latest 为 v2.1.19 |
| Windows 安装包 | `AISC-Workbench-2.1.19-setup.exe`，385064220 bytes；随包 CLI 0.3.0 |
| SHA-256 | `c790ed32e2360964813500382f578952617cd76b7dd4a9344f39427fc82be60d`；公开下载、同名 .sha256、GitHub asset digest 及该包的升级报告一致 |
| 正式标签构建 | [NSIS run 44499717575](https://github.com/Wifabric/AISC/actions/runs/44499717575) SUCCESS；静默新装/PATH/重装保留/卸载通过；2.1.18 升级 6 个步骤全部 PASS，实际 installedVersion=2.1.19 |
| 候选门禁 | [Workbench CI 44496426046](https://github.com/Wifabric/AISC/actions/runs/44496426046)、[NSIS 44496431772](https://github.com/Wifabric/AISC/actions/runs/44496431772) 在 bb232584 上成功 |
| 合入后的发布源码检查 | 8d748eef 的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/44499652819)、[三平台 CLI](https://github.com/Wifabric/AISC/actions/runs/44499652845)、[Linux/macOS Bundle](https://github.com/Wifabric/AISC/actions/runs/44499653011) 与 [Windows NSIS](https://github.com/Wifabric/AISC/actions/runs/44499652910) 全部成功 |
| 本地定版复核 | Python 1841 passed、58 skipped、220 subtests passed（不含 integration 目录）；51 项文档检查、107 个当前链接、1368 个资源摘要和正式 bundle stage/verify 通过 |
| 用户验收 | 已验收 Preview 的功能与完整安装交互用户报告 PASS；正式定版没有功能改动。新包自动化与下载结果单独绑定，不冒称用户重复安装 Final |
| 更新发现 | 实际公开 Releases API 选出 v2.1.19；原样提取并编译运行 2.1.18 与 2.1.19 的生产 Atom 选择/比较函数，旧正式版及同版 Preview 检出 2.1.19/0.3.0，正式版本身不误报更新。使用真实公开 feed 和 tag VERSION；未重复执行宿主 GUI 安装 |
| CLI 独立渠道 | [CLI 0.3.0](https://pypi.org/project/aisc-cli/0.3.0/) 已正式发布；[PyPI run 44499736389](https://github.com/Wifabric/AISC/actions/runs/44499736389) 的构建守卫、TestPyPI 与正式 PyPI 上传及真实安装验证全部成功。两个 index 的 wheel/sdist 摘要与同源构建产物一致，正式下载另行校验通过。 |
| 反馈回写 | 14 条已解决项追加正式回复并置 resolved；[反馈提交](https://github.com/Wifabric/aisc-issues-feedback/commit/c133e06d08037e90bf884e3248edc9f982542b82)，站点 14 条列表及详情已读回通过。原文/附件/投票保留，偶发卡死及范围外 intake 不变 |
| 文档 / 归档 | README、WIKI、Workbench、双轨 Release Notes、HANDTEST、DELIVERY、devlog、TODO 和计划索引同步；开发 Skill 已复核；阶段材料归档到 docs/archive/2.1.19-dev-plans |
| 历史 Preview | 预发布记录、安装包及 tag 保留，已标注由正式版接替。自动审批认为本次发布授权未明确包含永久删除，故未删除历史资产；不影响 final 的 Latest 或更新发现 |
| 下一开发号 | [PR #107](https://github.com/Wifabric/AISC/pull/107) 在 47 项版本/fixture/工作流契约及 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/44502340793) 通过后合入 develop，CLI 开启 0.3.1.dev0；没有发布此开发号或改变已发布标签。正式安装仍使用 2.1.19 / 0.3.0 |

发布回执与原始下载报告位于 D:\AISC\output：`2.1.19-final-publication-receipt.json`、`2.1.19-final-pypi-result.json`、`2.1.19-final-feedback-receipt.json`、`2.1.19-final-release-python.log`、`2.1.19-final-release-docs.log`。本地证据不是交付给用户的安装依赖。

剩余产品项仅为用户明确暂缓的偶发卡死；签名按用户决定暂不开展。CLI 0.3.0 的 TestPyPI 和正式 PyPI 均已完成发布与安装验证；2.1.18 的历史 0.2.0 发布记录不冒称已补发。
