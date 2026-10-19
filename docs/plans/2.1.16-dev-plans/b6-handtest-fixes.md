# b6 — 用户手测四项修复（2026-10-19）

> 来源：用户统一手测第一轮反馈。分支 `2.1.16-b6-handtest-fixes`。

## 问题 → 根因 → 修复

| # | 反馈 | 根因 | 修复 |
| --- | --- | --- | --- |
| 1 | 顶部导航栏 Provider 供应商页残留，只保留 bash/codex/claude | 新建标签 ▾ 菜单仍有「Provider 管理」入口（cc-switch-ui menuitem）；AGENTS 还含 cc-switch；侧栏 auth 入口仍开 TUI 页签 | 删除菜单入口与分隔线；AGENTS 收敛为 claude/codex/bash；`openCcSwitch` 改走 rail 重定向 |
| 2 | 侧栏 Provider 页显示「暂无已注册服务…」 | WorkspaceExplorer 的 services 面板是裸 `v-else`，兜底吃掉一切未知 activeKind（providers/extensions 也落入） | 改为 `v-else-if="artifactFilter === 'services'"` |
| 3 | 关闭工作区（容器已删）后重进同一工作区被阻断，重启 Workbench 才恢复 | `teardownRuntimeAndRelease` 的 `leaseRelease` 是 fire-and-forget；立刻重进时 reconcile 撞上自己未过期租约（active_same_instance）且 launcher 无可聚焦实例 → 误入通用阻断页 | ① release 改 await（快速本地操作，不破坏视觉即时关闭）；② reconcile 对该形态自愈：release + 重跑一次，不再直接阻断 |
| 4 | MCP/Skill/Plugin 页也显示「暂无已注册服务…」，skill/plugin 加载不出合理 UI | 同 #2 的 services 泄漏（overlay 破坏布局） | 同 #2 |

## 测试

- 更新 TabBar 菜单测试：3 agents、无分隔线。
- 新增 WorkspaceExplorer 回归 ×2：providers/extensions 视图不渲染 services 空文案。
- #3 的 store 级自愈逻辑经 vue-tsc + 现有 runtime 套件回归；真实「关→立进」时序待用户复测。
- 门禁：Vitest 76 files / 610 tests；vue-tsc 0。
