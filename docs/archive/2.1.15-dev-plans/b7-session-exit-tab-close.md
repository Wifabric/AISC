# v2.1.15 b7：会话退出自动关闭标签

> For agentic workers: 本文件是 b7 批次计划。执行须遵守分支先行、TDD、
> 本地门禁与远程 CI 全绿后并回 develop。

## 目标

用户裁定（2026-10-14，收尾前修复批次）：bash/codex/claude 会话退出后直接
关闭对应标签，不再保留显示 `[Session exited: process_exit, code 1]` 的
僵尸标签。

## 现状

- `workspaceRuntime.ts` 的 PTY Exit 事件处理（reason=process_exit）只把
  pane `sessionState` 置为 `exited`，标签保留并显示退出横幅
  （i18n `tabbar.exited` / `tabbar.exitedCode`）。
- A-G17-5「关闭最后一个 pane 保留 dormant leaf」规则适用于用户主动关闭，
  会话自行退出时不应套用。

## 方案

1. Exit 事件 reason=process_exit（含 user_close 的终态收尾）时，自动走
   pane 移除路径：单 pane 标签整体关闭；split 中仅移除退出 pane，其余
   pane 不动。
2. `transport_error` / `failed` 不自动关闭，保留现场供排查（横幅逻辑
   不动）。
3. 失败会话被自动关闭时若为 active，焦点迁移到相邻 pane/标签，沿用既有
   closePane 焦点策略。
4. 不改后端、不改 b6 删除链路（其 user_close → exited 终态与此自动关闭
   兼容，T6 行为不回退）。

## 验收形态

- 单测：process_exit 触发 pane/tab 移除；transport_error 保留标签；
  split 场景只移除退出 pane；active 焦点迁移正确。
- 手测：bash `exit`、codex `/quit`、claude 退出后标签直接消失；
  双 pane split 退出其一另一 pane 保留；b6 T6 删除运行成员链路不回归。
- 全量本地门禁 + 远程 CI 全绿。

## 分支

`2.1.15-b7-session-exit-tab-close`（从 develop 切出）。
