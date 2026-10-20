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

## 预复测（2026-10-20，computer use 实机）

- **R1–R4 全 PASS**（R3 关→+3.4s 重进→直达摘要）。
- **新发现并修复（用户 #4 深层根因）**：扩展视图切页签后整体消失——
  i18n 文案 `{mcpServers:{…}}`（占位符语法）与 `name@marketplace`
  （链接语法）被 vue-i18n 当消息语法解析 → 编译错误 → 渲染抛错 →
  组件卸载。修复：去掉 `{}`、`@` 字面量转义为 `{'@'}`；新增页签切换
  回归测试（skills→mcp→plugins 全程渲染）。
- 期间定位两个环境坑（非产品）：Win32 外部 resize 可令 WebView 停在
  333x253（正常用户不会触发）；HMR 更新 i18n 会整页刷新回 picker。
