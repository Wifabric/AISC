# 2.1.18 夜间交付与次日验收

2026-11-08 最新范围：D-17 已授权补齐截图三层能力；U-4 默认成员不再待批准。S11 与 S12–S14 已集中经英文整合 PR #95 合入 develop `c9b21cf2`。新增离线通用技能、科研/开发模块及个人能力流程已实现，Preview.10 完成下列实测；最终 Preview.11 已构建并完成重启回读，PR 最终 head 的三项 CI 已成功。开发者剩余验证、本人认证、用户验收和正式发布分别记账，不能概括为“只剩用户手测”。

### 截图要求对应结果

- 离线通用基础：13 个 caveman 技能、grill-me、grilling、Karpathy，共 16 项。新增两项固定上游提交、原始许可材料与 SHA-256。全新 GUI 工作区实际显示 13 + 2 + 1 项；真实 cc-switch 双引擎登记、升级保留个人修改通过。
- 在线模块初版：科研基础（arXiv/OpenAlex）、开发基础（系统化调试/TDD）已启用。旧 Superpowers 未使用的离线缓存移出安装资源。Preview.10 GUI 从空目标预检科研两项为缺失，经确认在线安装，两项均显示已安装；四项来源及安装/卸载的既有真实数据面验证见默认模块提案。
- 个人迭代与注入：三项初始模板、个人副本、规则/技能编辑、修改原因及验证记录、启停、版本历史和恢复已实现。真实 GUI 保存第一版、按反馈保存第二版、恢复第一版形成第三版通过，落盘保留所有历史。新工作区无提供者认证，GUI 新建 Claude 正确进入登录引导；另用实际冻结 CLI 创建隔离 Claude/Codex 会话，两个真实原生进程的上下文均与 GUI 第三版快照匹配，正常结束。没有登录、发送模型任务或将参数匹配称为模型效果验收。
- 自动化：完整 Python 1834 passed / 57 skipped / 218 subtests；Rust 422 passed / 2 ignored；最终前端全套 893 passed（107 files）；Linux 补充 22 passed / 47 subtests。

旧 Preview.9 的产物和验证记录保留在下方，不能用于声称新增三层能力已经交付。新候选源码、构建和剩余 Preview 项见 PROGRESS。

## 当前候选：Preview.11

[唯一整合 PR #95](https://github.com/Wifabric/AISC/pull/95) 已合入 develop `c9b21cf2`，产品源码 `7edb677dba431b4fccb809b2034d073bd95ae664`，base develop `9cc7020c`。最终 head `55561c22` 的 [CI](https://github.com/Wifabric/AISC/actions/runs/42444336109) frontend/rust/cli 全部 success，合并树与已验证 head 相同；纯验收文档后续提交不改变下面二进制。

- 启动：`D:\AISC\p18\start-candidate11.ps1`；完整目录 `D:\AISC\p18\candidate11`。
- 安装包：`D:\AISC\p18\AISC Workbench_2.1.18-preview.11_x64-setup.exe`。
- 清单：`D:\AISC\p18\candidate11-manifest.json`；独立配置 `D:\AISC\p18\qa-data`。
- 镜像：`aisc-personal:preview11`，ID `sha256:22891f8aa447f6d3c09f3b9a53bb40a7edc00a20192d36f9acfe8548dd44db14`。
- Workbench SHA256：`66910757da6ffd1b8067e5d1f5c0b9117374d20908d896976b710d249be8e600`。
- CLI SHA256：`47b7536a330c005914e2ee7b2670e3ccd1fe6423f847f0b59aa5cc21dc8c7965`。
- 安装包 SHA256：`8d1784ab8f59719f02007b7a5a20f9ff627707b4cd15c597055c85469245fd42`。

本机版本覆盖为 Workbench `2.1.18-preview.11`；CLI/bundle `0.1.10`，未创建公开 tag/Release。真实 GUI 用该完整镜像重新打开 `ui-personal10`：新入口“个人能力与主题”、三模板、个人第 3 版和 16 项预装技能及 2 项科研在线技能均正常显示。个人登记文件 SHA256 在重启前后相同。用户原平台和工作区未替换。Windows 安装器构建通过不等于安装/升级 GUI 已验收；认证后的模型任务、SSH/其余 HANDTEST 边界和最终用户验收继续保留。

## 变更说明

- F1/F2：仅大小写改名保留目标名称；工作记录菜单/子菜单按边界避让并避免误移。
- F3：完整镜像名称编辑与随机默认名；本机镜像重建预检和进度，运行容器阻止重建，不自动停删，远程重建入口明确禁用。
- F4：用户模块定义、编辑、持久化、缺项安装、逐项恢复，以及共享/预装/用户修改保护；D-17 已启用科研/开发默认模块。
- F5：插件安装独立等待预算、容器进程锁和超时后实际状态核对；未知结果不盲目重试。
- F6：GitHub MCP 按引擎配置认证、取消/失败保护与显式连接检查；凭据不进入诊断或重试历史。
- F7：多层技能目录、固定来源、简介缓存/空简介/重试，合法连字符名称与下划线目录匹配，歧义继续拒绝。
- F8：关闭失败卡片与同次重复错误文案，保留日志/诊断，新失败仍提示，焦点恢复和目标隔离。
- 协作：贡献者必要测试后提 PR，主开发者处理小修正、集成和统一 Preview；WIKI、职责、贡献者、PR intake 与 [开发 Skill](../../../skills/aisc-development/SKILL.md) 一致。单代理兼任只记自查。

## 历史本机候选（Preview.9）

**当前为整合分支候选：** Preview.9 已包含 S11 升级时保留插件登记的修复，真实完整镜像升级/重启及标准候选 GUI 启动回读通过；跨目标等剩余检查、收尾 PR 和精确 head CI 尚未完成，不代表整版可发布。具体证据见 [preview-gui](preview-gui.md)。

本机输出，不作为仓库文件上传，也尚未创建公开 Release/tag：

| 产物 | 位置 |
| --- | --- |
| 隔离候选启动脚本 | `D:\AISC\p18\start-candidate.ps1` |
| 完整可运行目录 | `D:\AISC\p18\candidate` |
| Windows 安装包 | `D:\AISC\p18\AISC Workbench_2.1.18-preview.9_x64-setup.exe` |
| 源码、哈希与状态清单 | `D:\AISC\p18\candidate-manifest.json` |
| 详细测试日志 | `D:\AISC\output\preview-2.1.18-20261108\output\verification` |

PowerShell 执行 `& 'D:\AISC\p18\start-candidate.ps1'` 启动独立配置候选。数据根为 `D:\AISC\p18\qa-data`，WebView 数据也独立；原平台安装和原工作区未替换。每轮检查后正常退出独立候选，原平台进程保留。QA 工作区与证据保留；QA-A 科研模块、QA-C 混合定义及历史保留供继续复测，QA-B 已验证删除定义不删资产。选择隔离工作区完成 HANDTEST，避免把原工作区当测试数据。

本地 Workbench 版本覆盖为 `2.1.18-preview.9`，源码仍保留现有正式版本标识；CLI/Bundle 为 `0.1.10`，CLI 沿用已验证冻结产物，资源包包含 S11。此处是可审查的本地候选，不是已发布 Preview。阶段收尾决定后，再统一更新正式候选的双轨版本及 Release Notes、重建并执行发布流程。

候选产品源码为整合分支提交 `11b5b18ff19732c803cf89387f2c5ea73e9bf7ff`，base develop 为 `9cc7020c`；S11 尚未合入、精确 head CI 待统一收尾 PR，不能沿用 #93 CI 宣称新源码已通过。后续纯文档不改变二进制。SHA256：

| 文件 | SHA256 |
| --- | --- |
| workbench.exe | `1c01963d8d95f51e96cb25a342a8a83b46fd25db93599cb7d7cc20456005a220` |
| aisc.exe | `e000a775ae16a446330b45cf22373f24b63c00088e228021701435920a84daf1` |
| setup.exe | `c593069d8f1d3c1128011395e3388ed76cd6cb8b7b4fd7a676ce2ac8b95a5825` |

## 验证结果

- 最近完整本地门禁（S10）：Python 1812 passed、54 skipped、212 subtests；Rust 422 passed、2 ignored；前端 888 passed，类型/生产构建通过；适配器/工厂定向 94 passed、16 subtests。
- 整合 PR #76 精确 head 的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/42411011239) frontend/rust/cli 全部 success。b3–b10 的 PR/CI/merge 逐项见 [PR_INTAKE](PR_INTAKE.md)。纯文档 PR #75 未触发产品 CI，Skill 格式和 105 个本地链接校验通过。
- 完整 bundle 初次校验发现过期/遗漏 checksum，修正后 1534 项覆盖及完整校验通过。NSIS 初次因长路径失败，使用本地短路径引用同一资源后，含最终修正的 Windows 安装包构建通过。
- 候选冻结 CLI + 实际打包资源：模块应用/卸载、合成双引擎认证配置及真实客户端读取、grill-me 详情通过。补充科研详情实际读取和四项提案成员 installed→removed 通过。该轮自建 QA 容器均已清理；后续 H4 的专用停止容器和镜像保留供继续复测。
- Windows 真实候选启动与“帮助 → 关于”基础检查通过：工作区选择页正常，显示 Workbench `2.1.18-preview.3`、CLI/Bundle `0.1.10`。真实 GUI 的本机 H1/H3、H5/H6/H9/H10 子集与发现的三项整合修正见 [统一候选复测](preview-gui.md)；**完整 H1–H10、安装/升级手测、SSH、真实 GitHub 凭据与工具权限仍未完成**。合成令牌和 DOM 测试不替代这些项目。

- GUI 发现并修复：模块预检独立通道避免拖慢后台同步，成功终态去掉旧预检原因，冻结 CLI 明确按 UTF-8 读取中文模块请求。Rust 定向 35、前端模块定向 12、Python 模块/分发 22 + 18 subtests 通过；冻结 CLI 多语言真实预检 48.38 秒通过。#78 [CI](https://github.com/Wifabric/AISC/actions/runs/42412882668) 和 #79 [CI](https://github.com/Wifabric/AISC/actions/runs/42413674608) 三项全部 success。Preview.3 完整 NSIS 构建通过；旧 Preview.1/.2/.3 仅保留作历史产物，不再用作当前验收入口。

Preview.4 补充：#83 [CI](https://github.com/Wifabric/AISC/actions/runs/42417635698) frontend/rust/cli 全部 success。真实完整镜像重建验证了基础镜像回退、固定 digest、本机 builder 和无缓存参数，选中标签更新、其他标签及停止容器引用保持；新镜像适配器哈希与 Node/Claude/Codex 版本探针通过，Codex 另有旧临时目录跨设备清理警告，未据此宣称所有工具运行场景通过。Preview.4 的真实 GUI 两入口缓存重建成功、无缓存取消与镜像保护、About 版本核验通过；缓存取消尝试时构建已先完成，未记取消通过。修正后的冻结 CLI、Workbench 和 384431133 字节 NSIS 安装包已重新生成并替换当前候选；旧 Preview.3 仅留作历史。具体 GUI 覆盖及未测项目继续见 [统一候选复测](preview-gui.md)。

Preview.5 补充：#85 [CI](https://github.com/Wifabric/AISC/actions/runs/42420724178) 三项 success 后合入。修正四个科研推荐的真实安装目录，前端 28 项/类型/构建及冻结 CLI 四项 installed→removed 通过；384419837 字节 NSIS 与独立 Workbench 已生成。CLI 与 bundle 相对 Preview.4 未变化，旧 Preview.4 保留作历史。H7 正常插件安装已在 Preview.4 实机通过。Preview.5 GUI 已实际安装 arXiv/OpenAlex，验证预装 research 保留、当前项完成后停止、重新预检仅补缺项，以及关闭市场/切换视图后执行终态保留；共享卸载等后续结果见 preview-gui。H2 追加键盘 Home/上下键、底部菜单、窄短窗口左展与内部滚动，以及实际改名/移动后磁盘逐项比对通过，未扩写为完整手测通过。

Preview.6 补充：#87 [CI](https://github.com/Wifabric/AISC/actions/runs/42425026074) 三项 success 后合入。修正短窗口编辑器底部保存时看不到上方错误的问题，模块相关 13 项、类型/生产构建通过；384429548 字节 NSIS 与独立 Workbench 已生成。CLI/bundle 未变，Preview.5 留作历史。双窗口冲突保护、明确重新读取后保存和目标容器离线保存已在 Preview.5 通过；Preview.6 实机重复空名称提示、冲突自动可见、草稿保留与显式恢复保存通过，磁盘核对外部修改没有被覆盖。H2 追加侧栏滚动和实际缩窄后菜单关闭、数据不变通过；About 显示 Preview.6 / CLI/Bundle 0.1.10。完整覆盖与未测边界见 [统一候选复测](preview-gui.md)。

H9 后续实机补测：隔离目标断网时返回带说明的搜索缓存，技能详情明确失败并提供来源/重试。恢复网络后首次重试仍失败，确认实际连通后再次重试成功；固定提交来源、普通查询切换和摘要缓存通过，1,545 个技能文件哈希保持不变。网络恢复完毕。跨工作区和真实迟到响应 GUI 仍未完成；精确结果见 [统一候选复测](preview-gui.md)。本轮只有验证文档变化，Preview.6 二进制与哈希不变。

Preview.7 补充：#91 [CI](https://github.com/Wifabric/AISC/actions/runs/42429010839) 三项 success 后合入，修复 Windows 取消重建遗留临时 tag。关联 Python 103 / 19 subtests、Rust 协议 2 通过；CLI 与 Workbench 重新构建，384428294 字节 NSIS 完成，bundle 不变。真实 GUI 缓存取消 9.5 秒、无缓存构建受控残留取消 27.5 秒通过：临时 tag 回收，selected/其他 tag/停止容器保持不变。冻结 CLI 精确回收/幂等、About 版本与四项哈希核验通过；原候选已备份。Preview.6 的完整无缓存 GUI 123.8 秒成功仍按其版本记录，原取消泄漏不改写为 PASS；自然导出竞态未在修后重复撞中，完整边界见 [统一候选复测](preview-gui.md)。

Preview.8 补充：#93 [CI](https://github.com/Wifabric/AISC/actions/runs/42432013590) 三项 success 后合入，修复旧空插件登记并将新工厂格式设为 v2。新完整资源包/镜像通过校验，真实新工作区首次安装与其他工作区隔离通过；最终标准候选重启回读与 About 通过。最终 NSIS 384409353 字节，完整 bundle 对比只有预期三文件变化，旧版备份保留。首次 GUI 构建与最终重打包二进制的精确哈希分别记录，不混写；详见 [统一候选复测](preview-gui.md)。

## 后续职责与实际阻塞

开发者仍负责补足可独立完成的边界验证、测试环境恢复、结果记录及必要修复；不以等待真实认证作为停止全部工作的理由。本轮追加 Preview.11 默认模块复制/隐藏/恢复、窄窗口右边缘菜单、MCP/插件卸载保护和旧适配器保守保留的真实 GUI 证据，详见 preview-gui。

安装器 GUI 升级仍为 NOT RUN：安装入口会检查所有 workbench.exe，升级流程还会处理 AISC 容器和默认镜像，在本机直接运行会影响用户仍在使用的旧平台。Windows Sandbox 不可用，Hyper-V 查询返回操作系统权限不足，尚无可用隔离 Windows 环境。此项是开发者验证的环境阻塞，不能算用户手测已接手或安装验证通过。SSH/远程场景同样缺少配置好的隔离目标；其余边界逐项见 PROGRESS，不与最终用户验收合并。

以下 Preview.9 内容为历史补充，PR 状态以本文开头及 PR_INTAKE 为准。

Preview.9 当前补充：S11 的完整镜像升级/重启、标准 GUI 原插件保留，以及同窗跨工作区模块预检隔离均通过。追加 H7 受控原生超时、锁释放/明确重试、重试安装中关闭并切工作区、重启后原生安装恢复；H10 旧失败卡片不带入新目标通过。三次 QA runtime 正常结束，其他工作区登记与候选四项哈希不变。安装向导、模块执行中切目标及其余未测项没有被覆盖；受控延迟不冒充自然慢网复现。收尾分支仍未新建 PR，后续统一用英文标题和正文提交。

H9 追加：受控延迟真实详情响应后，新查询先显示、旧响应后交付，界面未串结果；详情读取中正常关闭旧目标再同窗切换，新目标状态独立并可正常读取固定来源简介。1,942 项技能文件/插件登记、候选哈希不变。精确时序和受控夹具边界见 [统一候选复测](preview-gui.md)，不将其扩写为用户验收通过。

1. **U-4 默认成员已由 D-17 解除等待**：四项已落默认清单；后续集中验收使用效果，不重复请求排期批准。
2. **统一 Preview 验收**：按 [HANDTEST](HANDTEST.md) 执行；用户本人完成真实 GitHub 认证。记录实际 PASS/FAIL/NOT RUN，再决定修复或收尾，不预记验收通过。
3. **反馈站写权限**：当前凭据对反馈数据仓库只有读取权限。回复草稿见 [反馈进度文案](feedback-replies-draft.md)，尚未发布；有权限后先刷新原文/新回复，再按实际阶段更新，验收发布前不置 resolved。
4. **发布与归档**：当前未合入 main、未发布公开 Preview/final、未归档本版或关闭反馈。待用户宣布收尾并满足验收/版本条件后执行；已有授权沿用，正式发布批准不由本地构建代替。
