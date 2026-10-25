# v2.1.16 preview-fixes b1 — 磁盘日志、扩展侧栏、独立进度、出厂技能

> 2026-10-25 preview.1 实测反馈 8 项。目标：进入 v2.1.16-preview.2 前修复 UI 稳定性与初始技能裁定。

## 范围

1. 磁盘清理结果压缩为一行；移除常驻估算 disclaimer；操作日志每次清空后只保留结果。
2. 扩展侧栏改为弹性列布局，内容随侧栏宽度收缩，不横向撑开。
3. Extensions store 按 skills/mcp/plugins 拆分列表、loading、busy、search busy、error 与操作状态；跨页签安装/搜索互不影响。
4. 三个市场搜索框清空时立即清空对应搜索结果。
5. Provider/Extensions 视图隐藏顶层“搜索文件”框（该框仅属于文件/产物面板）。
6. Skill 仓库组与子技能展开状态分离：点父级折叠/展开组，点子级只展示介绍，不再折叠父组。
7. 新增稳定操作进度条：显示动作、目标、`x/y`；批量操作逐项推进，完成前不重挂列表。
8. 出厂技能改为通过既有 cc-switch 同步管理工具安装 `grill-me` 与 `caveman`（覆盖 b10“全清”裁定）。

## 验证

- Vitest：settings 清理摘要、扩展状态隔离/进度/清空搜索、子技能展开、布局与顶层搜索静态契约。
- Python：出厂技能 exact 集合、Dockerfile 离线资源、entrypoint 文案与 cc-switch 状态查询。
- Docker：重建镜像后首次启动应看到 grill-me/caveman 已注册并同步到 Claude/Codex。
- 本地全门禁 + vendor checksum + 重建 sidecar/镜像。

## 执行记录（2026-10-25）

- 磁盘清理：常驻估算 disclaimer 移除；专用清理与完整清理均只输出一行结果。
- 扩展侧栏：内容改为弹性列，行/卡片随侧栏宽度收缩；Provider/Extensions 隐藏顶层文件搜索。
- 状态隔离：skills/mcp/plugins 独立 items/loading/busy/search/error/operation；技能安装刷新不再影响 MCP/插件。
- 搜索清空：三个市场查询为空时立即清空旧结果。
- 子技能展开：父仓库组与子技能详情状态分离，重复点击子技能不折叠父组。
- 进度：新增稳定操作条，显示动作、目标与 `x/y`；批量安装逐项推进且完成后静默刷新。
- 出厂技能：恢复仅 `grill-me` 与 `caveman` 两个技能，经 cc-switch 注册/同步链路安装。
- 门禁：Python 1454 / Vitest 633 / vue-tsc / Rust 362 全绿；针对性红→绿用例 33+。
- 清理量补充：Docker 29 的 captured builder prune 可能不输出 Total reclaimed；CLI 现按 df before/after 差值回填，避免 UI 把已清空的 Build Cache 误报为“无可回收”。

## 实机预复测（2026-10-25）

- 新镜像 + 空临时工作区首次启动：`grill-me`、`caveman` 均注册并同步到 Claude/Codex。
- 扩展页顶层不再出现“搜索文件”；Skill 页按仓库显示 `JuliusBrussee/caveman` 与 `mattpocock/skills`。
- 点击 caveman 子技能显示介绍；再次点击介绍保持，父组不折叠。
- 搜索 `superpowers` 后显示 `obra/superpowers · 12 个技能`；清空搜索后结果立即消失。
- 批量安装 `obra/superpowers`：稳定进度条从 `0/12` 推进到 `9/12` 后完成；切到 MCP 页时无技能进度/结果泄漏，回到技能页进度仍在。
- 磁盘页清理后仅显示一行“清理完成：…，Node 基础镜像标签已移除”；无估算 disclaimer、builder/dangling 噪音。
