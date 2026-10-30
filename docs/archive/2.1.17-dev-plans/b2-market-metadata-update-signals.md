# v2.1.17 b2 — 市场元数据、更新标识与详情中文化

## 来源

- 反馈 N2：已安装 Skills / MCP / Plugins 需要新版本标识，有更新时加粗显示。
- 反馈 N4：市场详情中的单项简介需要中文化。
- 原 v2.1.17 开题范围中的市场元数据与更新信号；在 b1 修复无代理可靠性后实施。

## 问题

当前已安装快照与市场搜索结果缺少统一 identity/version 对齐，UI 无法可靠判断
“已有新版本”；详情文案直接沿用市场原文，界面中英文混杂且字段没有统一中文说明。

## 方案

1. 建立本地 metadata 快照：
   - 搜索、详情、安装共享 normalized identity 与 source/version/updated_at；
   - Skills 以 repo + directory + content hash/update time 对齐；
   - MCP 以 qualified name 与 server version/updated_at 对齐；
   - Plugins 以 marketplace version/lastUpdated 对齐。
2. 已安装列表加载后可触发更新检查：
   - 单项显示“可更新”徽标，组标题显示数量；
   - 有更新的名称加粗，操作仍支持单项更新；
   - 检查失败显示网络诊断，不把“无法检查”误报为“已是最新”。
3. 详情中文化：
   - 字段名、状态、来源、安装量、更新时间与操作说明全部中文；
   - 单项简介优先使用可靠中文摘要来源；
   - 无可靠中文来源时保留原文并标明“市场原文”，不用猜测翻译。
4. 搜索缓存只作为远端刷新失败后的显式兜底，不得掩盖 b1 修复的网络错误。

## 任务

- [x] 先写失败测试：三资产 installed/market identity 对齐与 update available。
- [x] 实现市场 metadata snapshot 与更新检查 API。
- [x] Workbench 单项 UI 显示“可更新”徽标、名称加粗和单项更新入口；组标题
      显示可更新数量；检查失败显示具体网络诊断。
- [x] Vitest 断言 zh-CN/en-US 均包含上述状态文案。
- [x] 详情区中文化与“市场原文”兜底。
- [x] 补搜索缓存兜底测试，确保远端失败时返回 cached 元数据。
- [x] targeted Python / Vitest / vue-tsc 与本地全门禁。
- [x] PR #41 远端 CLI/Rust/frontend CI 全绿，并回 develop（58aa2e0）。
- [x] 真实容器 Computer Use 预测试：更新检查、Skills/MCP 市场刷新与缓存标识、
      installed unsupported 徽标；统一用户手测仍按阶段规则等待 b2–b7 全部预测试。

## 2026-10-27 收口记录

- 语义裁定：Plugins marketplace 提供 `version` / `gitCommitSha`，可显示可靠
  更新信号；skills.sh 与 Smithery 当前无可比版本字段，Skills/MCP 显示
  “暂无可靠版本源”，不伪造 current/latest 对比。
- Adapter：市场搜索成功缓存 normalized query；远端失败时回退最近成功结果，
  envelope 暴露 cache metadata；`updates-check` 输出可靠/unsupported 两组。
- Host/Workbench：CLI 与 Rust runtime 白名单透传 `updates-check`；Extensions
  store 记录缓存与更新状态，UI 提供检查更新、可更新徽标、字段中文化与
  “已刷新 / 缓存结果”标识。
- 验证：adapter/bridge/dispatch Python `61 passed + 11 subtests`；
  extensions Vitest `25 passed`；Rust `368 passed`；vendor `1532` checksums
  通过；full gates Python `1492 passed, 57 skipped`、Rust `368 passed,
  1 ignored`、Vitest `648 passed`、vue-tsc 通过。

## 最终复核（2026-10-27）

- 最终 adapter SHA256：`657ddecc1881a6be5ce986199647f91766d8472fd7876760263505f058db8174`。
- 真实镜像：`sha256:3ad54ca40373bdb1f2a91d4e4c1f3d1131fdfeb7f5bf5f6c8ef5a797003eb3d2`；冻结 sidecar 实测 Skills/MCP 搜索与无已安装插件的 updates-check 通过。
- 审查修复：缓存写失败不影响远端成功、缓存上限 50 且不清理无关 JSON、上下文过期响应隔离、资产更新字典隔离、只清除被操作项的徽标、上下文切换重置 busy。
- 最新门禁 Python 1498 passed / 57 skipped / 140 subtests；Rust 368 passed / 1 ignored；Vitest 657 passed；vue-tsc 通过。审查补丁后全量前端验证及 debug Workbench 构建通过。
- vendor-verify：1532 verified，零 missing/mismatch/malformed。
- 当前会话工具清单没有 Computer Use / JavaScript 运行时，无法重复最终补丁后的 UI 预测试；已有 UI PASS 仅对应 PRETEST 所列先前产物，最终补丁 UI 为 NOT RUN。已恢复临时修改的全局 CLI pin。
