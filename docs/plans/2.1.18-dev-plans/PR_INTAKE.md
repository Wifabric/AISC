# 2.1.18 PR intake

## 当前状态：用户验收通过，正式发布准备中

用户已明确确认 Preview.13 验收无问题，并要求完成剩余工作直到可确认 main 合并；此前整版手测同样报告通过。b1–b10、S12–S16 的用户验收据此记为 PASS，不改写历史开发者未执行项。正式版本为 Workbench 2.1.18 / CLI 0.2.0，发布分支源于已验收 develop，功能行为不变。

2026-11-09 重启后已完成两个独立 Windows Sandbox 的全新安装、2.1.17 → 2.1.18 升级、卸载取消、默认数据保留及 PATH 验证，全部 PASS；已安装 CLI/bundle 均为 0.2.0，Workbench 为 2.1.18。详见 [安装验证](installer-verification.md)。用户验收已完成，无需重复。main 合并、tag 和公开发布仍未执行；最终进度与合并确认边界见 [发布准备](release-readiness.md)。

以下保留 Preview.13 及更早验证证据；“待用户验收”等旧状态以本段为准。

## 当前增补交付：Preview.13 / S16

用户报告前一轮要求手测的项目全部通过；此处作为用户反馈记录，不改写历史开发者 NOT RUN。用户随后确认个人能力与主题体验方案。本批产品已完成并经 [PR #98](https://github.com/Wifabric/AISC/pull/98) 合入 develop `61db0b6fb5be291ea01945b10f306f7d5ca72495`；候选产品提交 `53bbe0e54a855664365cd579b2cb64b4d8e48022`，合并树与该提交完全相同。只有自查，不称独立评审。新版用户验收仍待进行。

普通新 Claude/Codex 不再继承最后主题；只有主题入口显式绑定新对话。回答偏好独立启停。顶栏只显示当前主题会话的简短状态，重复异常去重并暂停无效同步；可关闭、重试、停止采集。新手双入口、精简偏好表单、名称/目标/引擎创建主题、可编辑且不自动发送的开场草稿，以及目标/继续/成果入口已实现。旧主题、能力版本和记录保留，旧全局默认停用。

本地 Python 1843 passed / 74 skipped / 218 subtests；Rust 422 passed / 2 ignored；前端 901 passed；类型与生产构建 PASS。新增 18 项回归按既有约定留本地。[精确 head Workbench CI](https://github.com/Wifabric/AISC/actions/runs/42491875792) 三项、[跨平台 Python CI](https://github.com/Wifabric/AISC/actions/runs/42491877982) 九项、[Windows NSIS 与静默安装/重装/PATH/卸载保留](https://github.com/Wifabric/AISC/actions/runs/42491880924) 全部成功，公开发布 job 跳过。

冻结 CLI 与真实 Claude/Codex 原生进程参数验证 A/B/普通会话隔离及偏好独立注入。候选真实 GUI 验证双入口、无需进阶字段保存第 1 版、主题创建和开场草稿、普通对话无主题条、目标/成果页、窄窗口及正常关闭重开后的偏好与主题保留；关于页为 Preview.13。未操作登录或发送模型任务，不把进程参数称为模型回答效果通过。详见 [S16](s16-topic-experience.md) 和 [本轮验收步骤](preview13-acceptance.md)。

旧隔离 Windows 交互安装 GUI 环境缺口和反馈站只读权限仍单列保留，不能移交为用户代测。此批不包含 main/final 公开发布。

### S16 合并后最终核对

develop `61db0b6fb5be291ea01945b10f306f7d5ca72495` 的 [Workbench 三项](https://github.com/Wifabric/AISC/actions/runs/42493462413)、[三平台 CLI sidecar](https://github.com/Wifabric/AISC/actions/runs/42493462405)、[Linux deb / macOS dmg](https://github.com/Wifabric/AISC/actions/runs/42493462599)、[Windows NSIS 和静默安装/重装/PATH/卸载保留](https://github.com/Wifabric/AISC/actions/runs/42493462417) 全部成功，公开发布 job 跳过。合并树等于 Preview.13 的产品源码，后续仅交付账本文档，不改变二进制。仓库 open PR 为 0。本批只有产品 PR #98，纯文档收尾依 WIKI §1.2.2 直接落 develop。

文档一致性门禁 51 PASS / 0 warnings / 0 failures，10 份变更文档的 99 个相对链接无缺失，差异空白检查与启动脚本语法通过。测试客户端和测试容器已正常退出/清理；原 Preview.12 PID 1860 与原容器 `aisc-wb-8426e721` 保留。用户补验入口见 [Preview.13 验收](preview13-acceptance.md)，此前环境/权限依赖仍按上文保留。

合并前按全部 open PR 查询完成 1 页，只有 #98、非草稿，base develop `dbfff203`，head `53bbe0e5`。本批无父子 PR 依赖；实现、自查和修正责任均为当前开发助手。合并前核实适用 CI、实际 base/head 与 mergeable；merge 方式集成，合并树等于测试树。证据 `s16-open-prs.json`、`s16-merge.json`。流程状态为已集成、候选验证完成，用户新验收待进行。

## 历史整合：PR #97（2026-11-08）

### S15 已集成：当前候选 Preview.12

真实 SSH 续测发现远程同名改名会覆盖目标，已修复并重建统一候选。[PR #97](https://github.com/Wifabric/AISC/pull/97) 已合入 develop `20df2af8e5afa1322ddb4dd4129f6144c3ce8b05`；最终 head `9f988fd7806d5dde850bab827f609330cd72779b` 的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/42460238475) 三项、[跨平台矩阵](https://github.com/Wifabric/AISC/actions/runs/42460237430) 九项均成功。Windows/Linux/macOS × Python 3.11/3.12/3.13 全部执行，修正测试环境后没有跳过失败项。单代理自查，不称独立评审。

当前二进制对应 `813225cffc50dcddbf21220910ffbd88ab840b75`；后续提交只改既有测试、CI 和计划，产品树不变。[NSIS CI](https://github.com/Wifabric/AISC/actions/runs/42459492494) 在该产品提交完成真实静默安装、重装、PATH 与卸载数据保留验证。完整本地 Python 1833 passed / 58 skipped / 218 subtests，Rust 422 passed / 2 ignored，前端 893 passed；新增 Linux 11 项回归仅留本地，文档门禁 51 PASS。

Preview.12 真实 GUI / SSH 已通过：同名冲突提示且两文件不变；文件/目录大小写改名；关闭、重入、刷新后精确名称和子文件保持；镜像仅替换选中旧 tag；远程重建入口明确禁用。专用 SSH/Docker 目标、导入镜像 tar 和临时私钥已清理，known_hosts 恢复原始哈希，原用户平台与容器保持运行。证据见 `output/verification/s15-merge.json`、`remote-qa/s15-final-data.json` 和 [preview-gui](preview-gui.md)。

剩余条件分别记录：隔离 Windows 交互安装 GUI 仍缺可用桌面环境，属于开发者阻塞，不能移交为用户代测；真实 GitHub/提供者本人认证及模型效果、最终用户验收、收尾与公开发布未执行。反馈仓库权限再次核实为只读，草稿已更新但未发送、未关闭 F1–F8。自然慢网/导出竞态没有自然复现，已有受控故障覆盖，不能称自然场景 PASS。当前没有未合并的本版产品 PR，也没有把 TODO 标为整版完成。



### 合并后最终构建复核（2026-11-08）

develop 集成提交 `20df2af8e5afa1322ddb4dd4129f6144c3ce8b05` 的自动流水线全部成功：[Workbench 三项](https://github.com/Wifabric/AISC/actions/runs/42460797396)、[三平台 CLI sidecar](https://github.com/Wifabric/AISC/actions/runs/42460797323)、[Linux deb / macOS dmg](https://github.com/Wifabric/AISC/actions/runs/42460797456)、[Windows NSIS 与真实静默安装/重装/卸载保留](https://github.com/Wifabric/AISC/actions/runs/42460797464)。公开发布 job 跳过，仓库 open PR 为 0；后续只有交付账本文档，产品树不变。最终文档门禁 51 PASS / 0 warnings / 0 failures，13 份变更文档的 116 处相对链接检查通过。

Windows 环境复核：WindowsSandbox.exe 不存在；CIM 仅返回宿主机，管理层 Get-VM 被授权策略拒绝，不能据此断言机器上绝无其他虚拟机，也没有可用隔离桌面完成交互安装。反馈仓库仍 pull=true / push=false，private=true / allow_forking=false；回复草稿未发送。上述环境/权限依赖、本人认证、用户验收与发布条件没有被自动构建成功替代。证据 `s15-post-merge-ci.json`、`s15-isolated-windows.json`、`s15-doc-links.json`。

## 前轮整合：PR #95（2026-11-08）

- [PR #95](https://github.com/Wifabric/AISC/pull/95)，英文标题/说明；集中 S11 插件登记保护、S12 离线 16 项/保留用户编辑、S13 两个默认在线模块、S14 个人模板/迭代/会话注入，以及此前 Preview 记录。仅此一个收尾 PR。
- base `9cc7020cd2d6f73e844da5a781e07af23aee6607`；产品 head `7edb677dba431b4fccb809b2034d073bd95ae664`。[Workbench CI 42443819350](https://github.com/Wifabric/AISC/actions/runs/42443819350) frontend/rust/cli 均 success。
- 单代理自查：核对默认来源/许可、离线与在线边界、升级保留、原子保存/乐观版本冲突、历史恢复、目标切换、上下文快照和双引擎生产桥接。没有独立评审。大量删除来自未使用的旧 Superpowers vendored cache，不是删除用户安装或数据。
- 本地 Python 1834 passed / 57 skipped / 218 subtests，Rust 422 passed / 2 ignored，前端 893 passed，补充 Linux 22 passed / 47 subtests；类型/生产构建、NSIS 和完整镜像通过。真实 GUI 与原生进程验证见 DELIVERY / preview-gui。
- 已核对最终 head `55561c22f2cbc49d6c154f05d30d4effcb02fc7f` 的 [Workbench CI 42444336109](https://github.com/Wifabric/AISC/actions/runs/42444336109)：frontend/rust/cli 全部 success，合入前 mergeability 为 clean。PR #95 已合入 develop，merge `c9b21cf2c56a968eb05903f56caabd2900737735`，合并树与已验证 head 相同（`8890960e10b6c14070db7da06308e7ae0b0e9c45`）。证据：`output/verification/pr95-final-ci.json`、`pr95-merge.json`。用户认证/验收、main/public release 保留。

下文为逐批历史快照，不覆盖上述当前状态。

- 核查日期：2026-11-08；仓库 Wifabric/AISC；open PR 全仓查询 `state=open&per_page=100` 返回唯一 #64，未达分页上限。
- 当前阶段：开发阶段逐批验收；范围依据 F2、D-7/D-8/D-9/D-10。

## PR #64 — 工作记录右键菜单边界与误移修复

- 链接：https://github.com/Wifabric/AISC/pull/64；GitHub open、非草稿。
- 当前目标：develop `9db6f642d717fdefb3487d75936bd76868ca7245`；父 PR #63 已合入。
- 核查时远端 head：`36314112739a646edbc5b781302258d401641820`；本地集成提交 `b109f1e7` 包含上述 base/head。后续验证记录为文档增量；最终 head 与 CI 结果以 PR 检查页为准。
- 本轮准备推送的分支：`codex/2.1.18-b2-work-record-menu`，使用包含原 head 的快进更新，不改写历史。
- 主审/修正：本会话 Codex 单代理自查，不称为独立评审。
- 产品差异仅 `workbench/src/features/workspace-explorer/WorkRecordsView.vue`；没有引入父分支后来新增的无关功能。其余差异为本批计划、日志和证据。
- 自查：核对主/子菜单视口坐标、翻转与限宽、Teleport、内外滚动、焦点恢复和异步实例判断；与 F2/H2 对应。当前未发现阻断合入的代码问题。
- 本地证据：前端 98 文件/841 项、类型检查、生产构建通过；Rust 414 PASS/2 ignored，release 构建通过。Python 首轮环境失败均经路径适配及 UTF-8 环境复验，不记为一次全量全绿；packaging 190 PASS/9 skipped。详情见 PRETEST 2026-11-07。
- Windows CU：PRETEST 2026-11-08 已执行路径 PASS，真实改名/移动与数据比对通过；未测范围逐项保留。候选产品内容与本次仅文档更新后的产品内容相同，可沿用该范围的证据。
- 远端 CI：查询时无 check runs；本次推送后运行 Workbench CI，实际结果绑定新 head 在 PR 检查页展示，未完成前不得记为 PASS。
- 用户验收：待用户本人 H2 验收或明确放行。没有将自动化/CU 记为用户验收；不进入 b3。
- 当前流程状态：审查中（补齐远端 CI 与用户验收）；没有合并、发布或将 TODO 标为完成。
- 原始日志、合成 QA 数据、候选二进制、仅本地回归及凭据均不上传。

### 2026-11-08 最新状态

PR #64 已于北京时间 00:48 合入 develop，实际 merge commit 为 `b90d85ab38c56eb859ed42e762639d5d371d7a60`，合并父提交为 `9db6f642` 与 `4a2a8d12`。后者的 [Workbench CI #42392564054](https://github.com/Wifabric/AISC/actions/runs/42392564054) frontend/rust/cli 均 success；包括 Python tests、clean-room install smoke 与 baseline probe。上述“准备推送/无 CI”是早先快照，已由本条更新。

本轮已按签名提交 payload 重建并验证合并提交 SHA，tree `235de608a90ba6d68393fa28224c11ed0d85e811` 与此前验证 head 相同，无额外合并代码差异；本次反馈登记基于该实际 develop。用户功能验收与未测边界仍不因合并自动改为通过。增量扫描全仓 open PR 返回 0 条，F5–F8 无可直接承接的打开 PR。


## 2026-11-08 b3–b10 集成总账（当前状态）

D-12–D-16 为连续实现/测试/PR/集成、统一 Preview。以下均单代理自查，无独立评审；用户验收未完成。每批范围和本地证据见对应 b*.md/PRETEST。远端实时核对全部 merged，精确 head 的 frontend/rust/cli 三项 success。

| 批次 / PR | head | 实际合入 | CI |
| --- | --- | --- | --- |
| b3 / [#67](https://github.com/Wifabric/AISC/pull/67) | `89971647905822f23c8f7fd671982832d3c3a99c` | `c0f9ab11b345502832ac114bc422348da1384502` | [三项 PASS](https://github.com/Wifabric/AISC/actions/runs/42397722859) |
| b4 / [#68](https://github.com/Wifabric/AISC/pull/68) | `80e90919016a9e4874a81735d2600161c55f5a12` | `1efe0904b3770bf1bdc530b8c8b474f48fb00cd6` | [三项 PASS](https://github.com/Wifabric/AISC/actions/runs/42400554462) |
| b5 / [#69](https://github.com/Wifabric/AISC/pull/69) | `ea5170c11f5df864c41be12e840c3fccfa400e55` | `d3798c062a4da431d75e9acffdfbfa4cff8ebf7a` | [三项 PASS](https://github.com/Wifabric/AISC/actions/runs/42401663375) |
| b6 / [#70](https://github.com/Wifabric/AISC/pull/70) | `98187f9b681bc68ee227ecb0823c5f1e645be27e` | `ffc848855161ad4c08935f7f1b8f485388124e3a` | [三项 PASS](https://github.com/Wifabric/AISC/actions/runs/42404418532) |
| b7 / [#71](https://github.com/Wifabric/AISC/pull/71) | `6c33d6c8a1262159a1b7dde90915a4514734cc0a` | `61c70540e497c8568be1be55fc99869b1ef863c0` | [三项 PASS](https://github.com/Wifabric/AISC/actions/runs/42405637940) |
| b8 / [#72](https://github.com/Wifabric/AISC/pull/72) | `deb15d19171132b475501c940691ba2c1a2a8ebb` | `4ff4881fbe8831ce2f68118eca994dc2cb55a375` | [三项 PASS](https://github.com/Wifabric/AISC/actions/runs/42407318416) |
| b9 / [#73](https://github.com/Wifabric/AISC/pull/73) | `0ba8a1054526a6b1095387d31b86164eb1f7ba6b` | `c8a39b8a5c9fc36c1c1b3a2727fc28224ee8edde` | [三项 PASS](https://github.com/Wifabric/AISC/actions/runs/42408462987) |
| b10 / [#74](https://github.com/Wifabric/AISC/pull/74) | `4bad14edff4d25bbc71bf7a93f2fe8c668ee7586` | `b548728b8dc2ed58f1a4f7c5d54855929d8535c7` | [三项 PASS](https://github.com/Wifabric/AISC/actions/runs/42409016199) |


## 流程与整合修正

- [PR #95](https://github.com/Wifabric/AISC/pull/95)：head `55561c22f2cbc49d6c154f05d30d4effcb02fc7f`，base `9cc7020cd2d6f73e844da5a781e07af23aee6607`，合入 `c9b21cf2c56a968eb05903f56caabd2900737735`；[CI 42444336109](https://github.com/Wifabric/AISC/actions/runs/42444336109) frontend/rust/cli 三项成功，head 与合并树均为 `8890960e10b6c14070db7da06308e7ae0b0e9c45`。S11–S14 与统一候选整合；本地自动化、Preview.11 产物和 GUI 覆盖边界见 PROGRESS / DELIVERY / preview-gui。单代理自查，无独立评审，未代替用户验收。
- [PR #96](https://github.com/Wifabric/AISC/pull/96)：head `70f6c84e344cdf1955353c6caa3543503e4184bf`，base `83dfa3f9683e95f46cd0bcc3b36ae27036410d7d`，合入 `63f15f299480ba1603b3341c0d8611538b35b780`。修正文档门禁的离线技能清单并集中记录 H3/H4/H7/H9 开发者续测；本地门禁 51 PASS、相对链接 19 处通过。路径未自动触发产品 CI，显式 [run 42455070124](https://github.com/Wifabric/AISC/actions/runs/42455070124) 精确 head 的 frontend/rust/cli 全部成功；合并树同为 `f5ef5a3fc2e11131bc4d89850030a46987757343`。单代理自查，无独立评审。产品与候选哈希不变，环境阻塞、真实认证、用户验收和发布仍未完成。

- [PR #75](https://github.com/Wifabric/AISC/pull/75)：head 2816083e，合入 8502f7dd。纯文档/仓库 Skill；格式、105 个本地文件链接及差异检查 PASS，产品 CI 按路径未触发，不记远端 CI PASS。
- [PR #76](https://github.com/Wifabric/AISC/pull/76)：head be39b2a9，base 8502f7dd，合入 41d046d9。本地 Python 1791/适配器 87、真实资源链与 bundle 验证 PASS；路径未自动触发 CI，显式 dispatch [run 42411011239](https://github.com/Wifabric/AISC/actions/runs/42411011239)，frontend/rust/cli 三项成功后集成。
- 两项均单代理自查，无独立评审；用户验收、main/final 发布仍待完成。

- [PR #78](https://github.com/Wifabric/AISC/pull/78)：head 33227965，合入 fd8e7a0d543fd9500143b5e2a5ebe4bed7cfd9db；[CI 42412882668](https://github.com/Wifabric/AISC/actions/runs/42412882668) 三项 PASS。模块预检通道及成功结果提示修正，本地 Rust 35、前端模块 12 passed。
- [PR #79](https://github.com/Wifabric/AISC/pull/79)：head 15b47ab1，合入 a9834710796ef057f13d8fd7f257b71f1bcd23f1；[CI 42413674608](https://github.com/Wifabric/AISC/actions/runs/42413674608) 三项 PASS。模块 UTF-8 stdin 修正，Python 22 passed / 18 subtests，冻结 CLI 多语言及最终真实界面预检通过。
- [PR #83](https://github.com/Wifabric/AISC/pull/83)：head 51b5cff53d7a1ad61219d7754c212d203df9e2bf，合入 24d03cd379babc8a9d61499f9de2f5204856145c；[CI 42417635698](https://github.com/Wifabric/AISC/actions/runs/42417635698) 三项 PASS。H4/S6 重建复用普通构建的基础镜像回退、固定 digest 验证和本机 builder 绑定；定向 52、全套 Python 1796/54 skipped/207 subtests 及真实冻结 CLI 完整构建通过。单代理自查，无独立评审。当前本机候选更新为 Preview.4，产物及 GUI 证据见 DELIVERY/preview-gui。

- [PR #85](https://github.com/Wifabric/AISC/pull/85)：head d06b3269cc30bff8d5f2dfd7bf422fdd5c7bb704，合入 5467c9cf4a6cb58d0f1382da1982f8e45f6765f2；[CI 42420724178](https://github.com/Wifabric/AISC/actions/runs/42420724178) 三项 PASS。S7 四个科研推荐使用实际安装目录；28 项前端、构建、真实四项 installed→removed 通过。单代理自查，无独立评审；含修正的 Preview.5 已构建，GUI 及未测边界见 preview-gui。

- [PR #87](https://github.com/Wifabric/AISC/pull/87)：head `195ff2b6d42e628d36be97180c7e2ff0079ef9b7`，合入 `5677a6e67fd12283577d1efe73d5365092112dfd`；[CI 42425026074](https://github.com/Wifabric/AISC/actions/runs/42425026074) frontend/rust/cli 三项 PASS。S8 模块保存错误与重复空名称校验滚动定位，13 项相关回归及类型/构建通过。单代理自查，无独立评审；Preview.6 已构建，真实界面与边界见 preview-gui。

- [PR #91](https://github.com/Wifabric/AISC/pull/91)：head `5414a099192da1372380426fa2006b0f58c28016`，合入 `3b26609e7f0aef9f5eec449a91638c11eadb048e`；[CI 42429010839](https://github.com/Wifabric/AISC/actions/runs/42429010839) frontend/rust/cli 三项 PASS。S9 Windows 强杀后精确回收重建临时 tag，失败保留原终态并提示残留；103 项关联 Python / 19 subtests、2 项 Rust 协议测试、实际源码回收通过。Preview.7 冻结 CLI 幂等回收、真实缓存取消与受控残留 GUI 恢复通过，边界见 preview-gui。单代理自查，无独立评审。

- [PR #93](https://github.com/Wifabric/AISC/pull/93)：head `43f5934029a9b2594ea5bce6467e880a2848b40c`，合入 `e5c17c3eb7eb13bebf2a42db0556caea92b77633`；[CI 42432013590](https://github.com/Wifabric/AISC/actions/runs/42432013590) frontend/rust/cli 三项 PASS。S10 精确空登记迁移与新工厂 v2 格式，关联 94 / 16 subtests、完整 Python 1812 / 54 skipped / 212 subtests、Rust 422 / 2 ignored、前端 888、类型/构建通过。真实旧登记迁移、新工厂首次安装及最终标准候选重启回读分版本记账。单代理自查，无独立评审。
