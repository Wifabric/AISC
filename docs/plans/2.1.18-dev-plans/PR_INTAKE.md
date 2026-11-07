# 2.1.18 PR intake

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
