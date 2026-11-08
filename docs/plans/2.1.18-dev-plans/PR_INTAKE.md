# 2.1.18 PR intake

## 当前整合：PR #95（2026-11-08）

- [PR #95](https://github.com/Wifabric/AISC/pull/95)，英文标题/说明；集中 S11 插件登记保护、S12 离线 16 项/保留用户编辑、S13 两个默认在线模块、S14 个人模板/迭代/会话注入，以及此前 Preview 记录。仅此一个收尾 PR。
- base `9cc7020cd2d6f73e844da5a781e07af23aee6607`；产品 head `7edb677dba431b4fccb809b2034d073bd95ae664`。[Workbench CI 42443819350](https://github.com/Wifabric/AISC/actions/runs/42443819350) frontend/rust/cli 均 success。
- 单代理自查：核对默认来源/许可、离线与在线边界、升级保留、原子保存/乐观版本冲突、历史恢复、目标切换、上下文快照和双引擎生产桥接。没有独立评审。大量删除来自未使用的旧 Superpowers vendored cache，不是删除用户安装或数据。
- 本地 Python 1834 passed / 57 skipped / 218 subtests，Rust 422 passed / 2 ignored，前端 893 passed，补充 Linux 22 passed / 47 subtests；类型/生产构建、NSIS 和完整镜像通过。真实 GUI 与原生进程验证见 DELIVERY / preview-gui。
- 最终候选产品源码不变；本条所在文档增量推送后，仍核对实际 head 的 checks 和 mergeability 再合入 develop。用户认证/验收、main/public release 保留。

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
