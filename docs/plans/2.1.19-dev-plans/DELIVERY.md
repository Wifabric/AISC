# AISC 2.1.19-preview.1 整版交付记录

核对日期：2026-11-19。面向用户和 leader 的当前结论：**本地候选已完成开发、构建和主要功能实测，文档已同步；尚未创建 PR、完成 leader 验收或正式发布。安装、升级和卸载的数据保留尚未验证，不能称全项通过。**

## 1. 当前状态与下一步

| 环节 | 状态 | 结论与责任 |
| --- | --- | --- |
| 本轮功能及修复 | 本地实现完成，存在验证边界 | 15 条反馈逐项见下表；偶发卡死按用户要求跳过，原权限/日志问题保留 |
| 候选构建 | 已完成 | Workbench 2.1.19-preview.1 + CLI 0.3.0.dev0；Windows 安装包及便携测试目录均保留 |
| 自动化与真实操作 | 部分通过，1 条单测失败保留 | 前端、Rust、运行时定向检查通过；Python 全集不是全绿 |
| 用户账号验收 | 用户报告通过 | Provider 不再重复检查，不代替失败单测或原权限问题的复现 |
| leader 新功能验收 | 待执行 | 用户转交候选/后续 PR，leader 按 [HANDTEST](HANDTEST.md)填写实际结果 |
| Windows 安装链路 | NOT RUN / 已暂停 | 沙盒拦截安装程序；按 02:15 截止要求停止，不自动继续环境搭建 |
| 本轮文档 | 已更新 | 发布说明、用户/开发手册、测试交接、Skill、计划、TODO、devlog 均同步；检查结果见本文末 |
| PR、CI、合入 | 未完成 | 用户先前要求保留本地，尚无 PR；后续操作由用户决定，执行人届时补实际 head/CI |
| 正式发布及反馈闭环 | 未完成 | 尚无本版 Release/tag、公开下载或反馈回写；不提前归档 |

用户计划先让 leader 测试新功能，再安排上线。功能验收可使用同一候选的完整便携程序或源码构建；新版镜像也必须来自配套资源。功能通过不自动把安装风险标成已解决。恢复安装验证、接受遗留风险或变更发布范围时，据实际决定回写本记录。

## 2. 版本、来源与产物

| 项目 | 当前事实 |
| --- | --- |
| 基线 | 2026-11-18 核对的 main/develop：`1c39903dc146e00ac5b7d92c8bd48433a3d4a7f5`，位于正式 v2.1.18 后 |
| 本地目录 / 分支 | `D:\AISC\output\2.1.19-local` / `codex/2.1.19-local` |
| 候选源码提交 | 尚未创建；当前为上述基线上的未提交修改，不能拿基线 SHA 冒充候选 head |
| Workbench / CLI | `2.1.19-preview.1` / `0.3.0.dev0`，serve protocol 4 |
| Windows 安装包 | `D:\AISC\output\2.1.19-acceptance\AISC-Workbench-2.1.19-preview.1-setup.exe`，384,144,213 字节，未签名 |
| SHA-256 | `c40d352fcd0b98a9f2a5028a2286c1b13f3c2c3d124225859253a4d99909bf3b`；同目录有 `.sha256` |
| 本地功能测试 | 同目录“打开本地测试版.cmd”，读取 `client-retest` 中程序、CLI 与配套 bundle |
| 隔离数据 | 启动脚本使用同目录 `test-data` / `test-webview`；工作区文件及宿主 Docker 仍是真实资源 |
| 公开渠道 | 本轮没有 GitHub Release、PyPI/TestPyPI 上传、公开下载或发布 tag |

来源入口：[v2.1.18](https://github.com/Wifabric/AISC/releases/tag/v2.1.18)、[基线提交](https://github.com/Wifabric/AISC/commit/1c39903dc146e00ac5b7d92c8bd48433a3d4a7f5)、[反馈站](https://feedback.alanevergarden.xyz)。这些是历史核对来源，不表示本轮文档更新重新查询了远端最新状态。

交给另一台电脑时，需准备不含测试状态和凭据的完整运行文件；不能只发送启动脚本或单个 Workbench exe。正式版版本号、提交、tag、资产和校验值在发布准备时重新核对；当前文档更新没有重打二进制或变更产品版本。

## 3. 全部 15 条反馈的处理

第 1 条来自 11 月 18 日的 Isaac，其余来自 11 月 13 日的 Thomas。“实现”与“原问题已复现并解决”分别记录。

| # | 反馈 | 本轮处理与用户可见变化 | 实际验证 / 保留边界 |
| --- | --- | --- | --- |
| 1 | 设置里查看网络和用量 | 设置打开当前工作区网络页，保留订阅刷新，新增节点列表、切换和测速；导入后更新启动摘要 | 测试订阅的列表、切换、刷新读回及 DIRECT 测速通过；不替代个人订阅验证 |
| 2 | Codex Provider 默认配置 | 新建默认 Responses；仅 Codex 新建列表隐藏 Ark；按格式填入 DeepSeek/智谱/Kimi 地址，已有和手填地址保留 | 用户报告账号手测通过；公开模型接口的鉴权响应不当作真实账号成功 |
| 3 | 侧边栏移动文件和文件夹 | 右键移动及单项拖动到目录，本地/SSH 接入文件操作；同名不覆盖，拖入终端不执行 | 本地与真实 SSH 文件/目录、冲突及内容对照通过 |
| 4 | 默认安装 gh CLI | 新镜像增加 GitHub CLI | 真实镜像执行 `gh --version` 返回 2.23.0；仅是本轮实测版本 |
| 5 | Codex、Bash、Claude 终端滚动条 | 加宽终端滚动条，便于回看历史输出 | Bash 从第 274 行回到第 85 行，再回到第 300 行；其他两个 agent 独立场景未逐项实测 |
| 6 | 工作记录与实际会话不一致 | 按引擎与原生 ID 归并，重复日志取最近写入记录；依据原生父子信息归档，缺信息留未归档 | 自动化及受控样本通过；反馈者原始日志的预览/恢复一致性尚需核对 |
| 7 | 父工作记录移动/删除时的子记录 | 移动覆盖后代，删除确认计算受影响数量，列表按层级显示 | 父/子/孙整体移入、移出、删除通过，无关记录保留；取消删除通过 |
| 8 | 标签导航栏调整 | 拖动排序、加号及分屏选择启动目录；修复桌面原生拖动失效 | 双向排序、当前会话不变、A/B 分屏独立目录通过；重开工作区仍从单个 Bash 开始 |
| 9 | Codex、Claude 官方直连报错 | 刷新当前官方卡时重新应用配置 | 新容器两个 agent 连续切换及用户账号手测通过；重建卷权限错误未复现 |
| 10 | 标签与会话对应关系不清楚 | 标签和记录对应编号，引擎颜色区分，双击关联标签定位 | 桌面双击定位通过；独立终端单独编号 |
| 11 | Docker 重置按钮 | 设置提供 Docker Desktop 恢复出厂指引 | 只验证入口和说明；没有执行宿主 Docker 恢复出厂 |
| 12 | 镜像构建 UI 重复提示 | 按提示内容去重，避免相同警告反复出现 | 真实专用镜像构建 140.3 秒完成，未观察到原重复提示；另有前端回归 |
| 13 | 技能更新全部报错 | 嵌套目录定位、唯一匹配及异常链接检查 | 真实 `mattpocock/skills` 20 项更新通过，界面恢复可操作，适配器退出码 0 |
| 14 | 技能安装全部报错 | 同一定位修复用于整组安装，保留原启停状态 | GUI 安装列表从 2 项增至 20 项，刷新后数量正确，适配器退出码 0 |
| 15 | 单个标签偶发卡住 | 已加入焦点/页面恢复及 WebGL 恢复时重绘 | 有限输出检查未复现原问题；按用户要求跳过，不标为已解决 |

实测追加修复：Docker 47000 端口冲突后残留容器导致重试名称冲突，现按本次完整容器 ID 清理失败对象，再改用 47001 成功；不强制删除运行对象。远程最近工作区的机器名被长路径挤压，已调整布局并复测。Windows WebView 文件树单项拖动由指针处理补正，真实远程拖动通过。

## 4. 验证证据与实际限制

下列日志位于开发机 `D:\AISC\output`。未上传到 PR 的本地证据不能当作远端 CI 已通过。

| 类别 | 结果 | 证据 |
| --- | --- | --- |
| 最终前端 | PASS：107 个文件、900 项测试 | `2.1.19-ui-pointer-final.log` |
| Rust | PASS：455 项通过、2 项忽略；之后未再改 Rust | `2.1.19-rust-verified.log` |
| 运行时定向 | PASS：75 项、6 项子测试 | `2.1.19-port-retry-tests.log` |
| 最新 Python 全集 | FAIL：1827 通过、74 跳过、218 子测试通过、10 失败 | `2.1.19-python-port-final.log` |
| Bash 环境失败复测 | PASS：上述 10 失败中的 9 项改用 Git Bash 后通过；该次另有 2 项跳过 | `2.1.19-python-port-env-recheck.log` |
| Provider 剩余单测 | FAIL：`test_live_fetch_fills_an_empty_catalog`；按用户决定停止此项复查 | 同 Python 全集日志；不因用户账号手测通过而删除失败记录 |
| 本地 GUI | PASS（已执行子集）：移动/冲突、目录、排序、记录操作 | `2.1.19-device-checks/cu-file-conflict.png`、`cu-split-directories.png`、`cu-tabs-pointer-reordered.png`、`cu-records-deleted-unrelated-retained.png` |
| SSH GUI 与内容 | PASS（已执行子集）：文件/目录移动、冲突、拖入 Bash、最近列表 | 同目录 `cu-remote-directory-moved.png`、`cu-remote-move-conflict.png`、`cu-remote-move-content-proof.json`、`cu-remote-terminal-drop.png`、`cu-remote-recent-layout-fixed.png` |
| 技能真实数据面/GUI | PASS：20 项安装、20 项更新 | `2.1.19-gui-market20.log`、`2.1.19-gui-frontend-verified.log` |
| 代理节点与启动摘要 | PASS：QA-Select 切换/读回、DIRECT 1131 ms、导入后警告消失 | `2.1.19-proxy-session.log`、`2.1.19-packaged-nodes.json`、device-checks 中 before-import/after-import 截图 |
| 便携程序 | PASS：本地测试入口启动最终候选 | `2.1.19-portable-smoke.json` 及后续 device-checks；不代表安装流程通过 |
| 用户账号测试 | 用户报告 PASS | 2026-11-18 用户回复“全部测试过了，没问题”；范围为其账号教程 |
| PR CI / leader 验收 | NOT RUN | 尚无候选 PR/head 或 leader 结论 |
| Windows 安装链路 | NOT RUN / 暂停 | 下节说明 |

历史 `2.1.19-python-final.log` 的 1834 通过属于前一轮结果，不用来覆盖最终全集的失败。测试数量按各次运行分别列出，不将重测次数加总成“全套通过”。

## 5. Windows 安装问题与清理记录

未验收项目：全新安装；正式 2.1.18 → 候选升级；安装后启动及 CLI/PATH；升级保留设置/记录/项目文件；取消卸载、默认数据保留及额外清理范围。

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
| [活动计划](README.md) / [手测教程](HANDTEST.md) | 范围、顺序、暂停决定、leader 测试步骤及结果模板已同步 |
| [devlog](../../devlog.md) / [TODO](../../todo.md) / [计划索引](../README.md) | 功能、文档更新与待办分别记账；旧版 PyPI 外部待办独立保留 |
| [开发 Skill](../../../skills/aisc-development/SKILL.md) | 补充发布说明需与实现及 tag 文件命名一致的检查，保留原授权边界 |
| 正式 2.1.19 / CLI final 说明与资产 | 尚未定稿或发布；当前说明属于预览候选，不伪造 final 验收结论 |
| 反馈站、归档、分支清理 | 未执行；发布及验收未闭环，计划保留活动状态 |

下一步按现有授权推进：用户确定 PR 提交时机；开发者准备实际提交及适用 CI；leader 执行功能验收；安装风险、Provider 剩余单测与未复现问题的后续处置由实际决定记录。正式发布后才填写 Release/tag/下载/反馈回写/归档证据，不能预先勾选完成。

本轮文档检查：仓库 `tools/check-docs.sh` **51 项通过、0 警告、0 失败**；版本与发布说明的现有契约测试 **10 项通过**；两条版本及对应 Release Notes 文件名/标题匹配；本轮新增和修改内容中的 **54 个相对链接有效**；开发 Skill 校验通过。日志位于 `D:\AISC\output\2.1.19-docs-check.log`、`2.1.19-docs-contract-tests.log`、`2.1.19-docs-version-check.log` 和 `2.1.19-docs-links.json`。

共同步 13 份仓库文档；本地 `2.1.19-acceptance/一步一步测试.md` 已同步新版教程并转换为本机可用的链接，沙盒续测说明已在开头标注停止状态，防止后续误执行历史连接步骤。当前更新不重跑暂停的安装测试、不重建二进制，也不代表新增 PR 或发布。
