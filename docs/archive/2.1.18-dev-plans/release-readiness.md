# 2.1.18 正式发布记录

## 当前状态：Workbench 已正式发布，两项外部事项按用户要求暂缓

2026-11-09：用户明确批准发布，Workbench [2.1.18 正式 Release](https://github.com/Wifabric/AISC/releases/tag/v2.1.18) 已上线并设为 Latest，源码 `52a5de6ed4fe47fb44b6caedfa14e80624122bc6`，随包 CLI 0.2.0。正式下载、SHA-256、发布说明和安装构建验证通过，真实公开更新数据经旧版与本版生产解析逻辑验证通过。产品与 Preview.13 用户验收已完成；本轮为单代理开发/自查，不称独立评审。

CLI 0.2.0 已完成 tag、TestPyPI 上传与实际安装验证；正式 PyPI 的仓库环境审批和八条反馈站回写，按用户“先不管这两项，先完成其他部分”的要求暂缓，由用户与 leader 协调有权限维护者。二者未标为完成。功能开发及已完成交付材料归档，外部待办继续在 [TODO](../../todo.md) 和本目录 [发布记录](release-readiness.md) 中保留；归档不代表整版外部闭环完成。整版成果及 leader 确认入口见 [DELIVERY](DELIVERY.md)。

## 已批准的发布内容

| 项目 | 准备内容 |
| --- | --- |
| Workbench | 2.1.18；Windows x86_64；正式 tag `v2.1.18`，只在已核对的 main 提交上创建 |
| CLI | 0.2.0，serve protocol 4；随 Workbench 提供；独立正式 tag `cli-v0.2.0`，通过 PyPI `aisc-cli` 分发 |
| 功能范围 | F1–F8/b1–b10、离线通用技能、在线科研/开发模块、个人能力迭代、S16 主题体验、开发流程/Skill；无新增工具升级或跨平台桌面发行承诺 |
| 发布说明 | [Workbench](../../releases/v2.1.18.md)、[CLI](../../releases/v0.2.0.md)；README 已按实际入口更新 |
| Workbench 资产 | `AISC-Workbench-2.1.18-setup.exe` 与 `.sha256`；正式 Release 非 draft/prerelease，核对 Latest、公开下载和更新发现 |
| CLI 渠道 | wheel/sdist 的守卫、TestPyPI 安装验证、实际 environment 审批、正式 PyPI 及安装验证；不附独立 CLI 安装器/归档/SBOM 到 Workbench Release |
| 反馈 | 本版 F1–F8 八条；[最终回复草稿](feedback-replies-draft.md) 仅在发布验证后追加，当前未发送 |

## 开发者准备清单

- [x] 对照 WIKI、交接、职责、Skill、D-8 后续裁定、本版 35 文件和当前发布渠道界定范围。
- [x] 更新用户教程、现行流程、devlog/TODO 与阶段当前状态，保留历史测试的真实结果。
- [x] 准备八条反馈的具体最终文案和仅本地可审查补丁；写入前仍须复读最新文件及权限。
- [x] 本轮文档检查 51 PASS / 0 warnings / 0 failures；52 份变更文档的相对链接/锚点通过（最终统计见本轮校验记录）；CLI 正式 tag 版本守卫和 git diff --check 通过。个人能力/会话现有测试 53 passed / 1 skipped；最初共享 venv 命中其他工作树，指定本工作树 PYTHONPATH 后重跑通过。打包与远端 CI 另列。
- [x] 交付补全 PR [#100](https://github.com/Wifabric/AISC/pull/100) 已合入 develop `c7c8790a791c89d751b7085e6d0d9043a57522ee`，合并树等于验证提交 `5362d08b`；后续通过 [#101](https://github.com/Wifabric/AISC/pull/101) 同步 main 至 `52a5de6e`，本页顶部记录其正式发布结果。
- [x] 已生成包含新 README 和随包主题技能文字的非发布 NSIS 候选；精确构建、安装冒烟和下载哈希见下方。
- [x] 版本、范围、资产标识、验证及遗留项已备齐；最终提交与 CI 核对后提交用户发布确认。用户现已批准，实际发布状态见本文顶部。

## 已完成的产品与安装验证

用户功能验收已完成，本轮不改变功能代码、依赖 pin 或 installer 模板；修正 README 和内置主题 Skill 的接入文字，明确普通会话不绑定主题。两者属于打包输入，因此重建候选。已有功能/交互安装证据按不变代码沿用，新候选构建/安装冒烟另外登记，不将旧文件哈希当作新包。

- Windows 交互安装 GUI：两个独立 Windows Sandbox 的新装、2.1.17 升级、首次启动、取消卸载、默认数据保留及 PATH，PASS，见 [安装验证](installer-verification.md)。guest 无 Docker，因此不声称在该 guest 测过真实 Docker 删除。
- Preview.13：Python 1843 passed / 74 skipped，Rust 422 passed / 2 ignored，前端 901 passed；真实进程上下文隔离和 GUI 子集见 PROGRESS/preview-gui；这些是对应候选的历史证据。
- main `07d6835c` 的 [Workbench](https://github.com/Wifabric/AISC/actions/runs/42502975879)、[NSIS](https://github.com/Wifabric/AISC/actions/runs/42502975841)、[sidecar](https://github.com/Wifabric/AISC/actions/runs/42502975813)、[Linux/macOS bundle](https://github.com/Wifabric/AISC/actions/runs/42502975882) 成功。NSIS release job 在分支构建按设计跳过。

### 已完成验证（2026-11-09）

- 本地发布/打包测试：227 passed / 9 skipped；版本同步守卫 PASS。
- 初轮 CI 暴露版本 fixture 与 pairing 测试仍写死 0.1.10，已同步 golden fixture，并将实际版本配对测试改为读取当前版本。定向 Python 49 passed / 19 subtests、前端 6 passed。
- 修正提交的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/42497630786) PASS；[Python 跨平台九组合](https://github.com/Wifabric/AISC/actions/runs/42497703252) PASS。
- 产品构建提交的 [Artifact 三平台](https://github.com/Wifabric/AISC/actions/runs/42496746449)、[Linux/macOS bundle](https://github.com/Wifabric/AISC/actions/runs/42496741867)、[CLI sidecar 三平台](https://github.com/Wifabric/AISC/actions/runs/42496736348) PASS。非 tag 构建的公开发布步骤按设计跳过。
- [NSIS 正式版本构建与安装冒烟](https://github.com/Wifabric/AISC/actions/runs/42496738996) PASS，包含静默安装、重装、PATH 与卸载数据保留；公开发布步骤按分支构建规则跳过。
- 本地冻结 CLI、完整 bundle、正式 NSIS 构建 PASS；实际运行冻结 CLI 报 CLI/bundle 均为 0.2.0。Workbench 为 2.1.18。
- wheel/sdist 构建及 `twine check` PASS。隔离审计环境升级自带旧 pip 后，`pip-audit` 未发现已知依赖漏洞；尚未发布的项目 0.2.0 自身不在 PyPI 数据库，因此跳过该项目项，不冒称审计覆盖产品源码。
- 文档检查 51 passed / 0 warnings / 0 failures。


## 本轮交付补全验证（源码 5362d08b，2026-11-09）

- [PR #100](https://github.com/Wifabric/AISC/pull/100)：head `5362d08b684711d45f00b02d4ed2e3ece838762a`，原 base `9a83cbc603ab760089181c53636d5662aa37b9f9`，merge `c7c8790a791c89d751b7085e6d0d9043a57522ee`；合并树与测试 head 完全相同。后续只补交付账本文档；自查，不称独立评审。
- 精确 head 的 [Workbench 三项](https://github.com/Wifabric/AISC/actions/runs/42582017470)、[Python 三平台九组合](https://github.com/Wifabric/AISC/actions/runs/42582037501)、[CLI sidecar 三平台](https://github.com/Wifabric/AISC/actions/runs/42582044253)、[Windows NSIS](https://github.com/Wifabric/AISC/actions/runs/42582041009) 全部成功。NSIS 包含安装、重装、PATH、卸载保留；公开发布 job 按分支构建规则跳过。
- 本轮本地 packaging：190 passed / 9 skipped；个人能力/会话 53 passed / 1 skipped。wheel/sdist 构建、twine、薄包检查、实际产物凭据扫描通过；隔离依赖审计未发现已知漏洞，未发布项目自身不在数据库，不能算源码安全审计。
- wheel/sdist 的安装、重装与卸载后重装及 pipx 验证通过。仓库外运行检查在清除继承 PYTHONPATH、使用仓库外 TEMP、启用 UTF-8、启动本机 Docker 后单独重跑通过；不宣称最初整套命令一次全绿。
- 已验证 wheel/sdist 内的接入说明、STATE 0.3.2 与源码一致；实际新主题复制新版随包技能，已有用户修改副本保持不变。
- 新候选安装器：384,135,154 bytes；SHA-256 `246d7d4c7769d92d67ae3154a1fb16cc531a7b3e7d9b10c2f9e26169fde9a539`；来源为上方 NSIS run 的 artifact `13657757926`，下载压缩包与 GitHub artifact digest 一致。该文件是内部候选，不是已经发布的公开资产。正式 tag 流水线会重建，发布后须对正式下载另验哈希，不能预先复用候选哈希。
- CLI 本地 wheel SHA-256 `afbadcd4b20ef29c75b9d07185cbbd6b3f992628cf6faf27327b7551a80fa309`；sdist `4ef7fdb72c4f6ba13d52ff3914fc29013357ffa638e981c6f768aa35a2fbd406`。正式 PyPI 产物以批准后 workflow 的实际构建/上传记录为准。

## 发布批准与后续执行，不能提前勾选

- [x] 用户于 2026-11-09 明确回复“ok，确认了，可以发布”，随后要求暂缓 PyPI 审批与反馈站回写，先完成其他交付。
- [x] Workbench 正式 tag/Release/Latest、公开下载/校验、随包版本和生产更新选择逻辑验证通过；实际正式安装器 SHA-256 `b9a578c34720577182b5fc2088e7bf579dbee93e430bca7b1776faffef479315`。
- [ ] CLI 正式 tag 与 TestPyPI 上传/实际索引安装验证已完成；正式 PyPI 等待环境审批，用户要求暂缓，不标全渠道完成。
- [ ] 获得反馈仓库写权限或由有权限维护者应用补丁；发布成功后更新八条，复核列表/详情缓存结果。
- [x] 已回填 Workbench 正式发布事实、整版 DELIVERY 与已完成阶段归档；两项外部待办明确转交协调并保留在 TODO，不用归档隐藏。
- [x] 发布源码长期分支已同步；已清理 26 个安全远端分支和 25 个本地分支；有 worktree 占用或未证明已合并的分支保留。当前无 prerelease Release，稳定 tag 不动。发布后文档通过单独 PR 同步，不覆盖正式 tag。
- [ ] 下一 CLI 开发号 0.2.1.dev0 依 WIKI 在正式 PyPI 发布结果确认后开启；它是本次暂缓渠道的后续动作，不在正式发布 tag 上改版本。整版交付链接已汇总至 DELIVERY。

## 已知边界与外部条件

- 反馈仓库 `Wifabric/aisc-issues-feedback` 当前仅 pull 权限，不能本机提权解决；补丁准备不等于已回写。原文、投票、附件及旧回复必须保留。八条仍为 submitted，只有正式发布验证后由获授权写入者更新。
- 已核对 GitHub `pypi` environment 的 required reviewers 为 `Evergarden-Alan` / `wangyuncepu`；发布获用户同意后仍须其中有权限维护者在 workflow 完成实际审批，不修改或绕过保护。`testpypi` 无 required reviewer，本轮已实际上传并通过索引安装验证。
- 真实多人协作未实测；本版交付流程规则/Skill和单代理实际执行，团队试用仍是后续事项，不标 PASS。
- 插件当前仅 Claude；远程镜像重建入口禁用；GitHub MCP 实际访问需要用户本人有效授权。现有用户验收不等于任意凭据均可访问任意仓库。
- 独立 pip CLI 是薄包，不包含镜像构建资源。本版不补发独立 CLI 归档；构建需对应源码/资源或 Workbench bundle，不能承诺 `bundle fetch` 自动取得不存在的资产。
- 自动化跳过/自然竞态未复现等沿用原报告边界。Workbench 正式下载与生产更新逻辑验证已通过；正式 PyPI 索引尚未验证，不预写 PASS。

## 正式发布证据及分支清理

- 发布后文档自查：文档一致性门禁 51 PASS / 0 warnings / 0 failures；44 份变更/归档文档的 262 个相对链接与锚点通过，`git diff --check` 通过。本轮仅 Markdown 变更，产品流水线按路径过滤未重新运行；不把未触发写成 PASS。正式 tag 保持原发布源码。
- 正式源码 `52a5de6ed4fe47fb44b6caedfa14e80624122bc6`；[发布流水线](https://github.com/Wifabric/AISC/actions/runs/42590818970)；[Release](https://github.com/Wifabric/AISC/releases/tag/v2.1.18)；正式安装器 384,119,029 bytes / SHA-256 `b9a578c34720577182b5fc2088e7bf579dbee93e430bca7b1776faffef479315`。
- 发布说明与源码完全一致，Latest、非 draft/prerelease、公开匿名下载、两项资产及校验通过。正式包与此前候选可因构建时间等因素哈希不同，以上只记录实际正式下载值。
- main 最终 CI 和具体交付范围见 DELIVERY；旧版/当前版更新生产逻辑均针对真实公开 feed 验证，未冒称此轮旧版 GUI 点击升级。

自动审批最初因授权未明确涵盖批量删除而拒绝；用户先选择保留，随后明确回复“那可以删除”。已据最新授权重新核对并完成下列清理。

已删除远端分支（其提交均为发布源码祖先，未占用工作树）：

- `codex/2.1.18-b2-work-record-menu`
- `codex/2.1.18-delivery-closeout`
- `codex/2.1.18-delivery-record`
- `codex/2.1.18-file-failure-gui`
- `codex/2.1.18-image-gui`
- `codex/2.1.18-preview2-validation`
- `codex/2.1.18-preview3-delivery`
- `codex/2.1.18-preview4-delivery`
- `codex/2.1.18-preview4-extensions`
- `codex/2.1.18-preview5-boundaries`
- `codex/2.1.18-preview5-verification`
- `codex/2.1.18-preview6-verification`
- `codex/2.1.18-preview7-verification`
- `codex/2.1.18-preview8-verification`
- `codex/2.1.18-preview-gui-record`
- `codex/2.1.18-preview-offline-verification`
- `codex/2.1.18-preview-plugin-recovery`
- `codex/2.1.18-preview-preparation`
- `codex/2.1.18-preview-rebuild-verification`
- `codex/2.1.18-preview-status-reconciliation`
- `codex/2.1.18-preview-target-isolation`
- `codex/2.1.18-preview-validation-gate`
- `codex/2.1.18-rebuild-gui`
- `codex/2.1.18-release-prep`
- `codex/2.1.18-remote-rename-protection`
- `codex/2.1.18-topic-experience`

保留项（不删除工作树/用户数据/独有提交）：

- `codex/2.1.18-b1-case-rename`：retain: not proven ancestor of approved release。
- `codex/2.1.18-b3-image-name`：retain: checked out worktree。
- `codex/2.1.18-b4-image-rebuild`：retain: checked out worktree。
- `codex/2.1.18-b5-extension-modules`：retain: checked out worktree。
- `codex/2.1.18-b6-module-operations`：retain: checked out worktree。
- `codex/2.1.18-b7-plugin-install`：retain: checked out worktree。
- `codex/2.1.18-b8-github-mcp-auth`：retain: checked out worktree。
- `codex/2.1.18-b9-skill-details`：retain: checked out worktree。
- `codex/2.1.18-b10-failure-dismiss`：retain: checked out worktree。
- `codex/2.1.18-team-workflow`：retain: checked out worktree。
