# b10 — MCP 市场/进度动画/终端复制/工厂清空（2026-10-23 第五轮）

| # | 反馈 | 修复 |
| --- | --- | --- |
| 1 | MCP 无市场 | Smithery API 搜索 + 一键安装（构造 mcpServers JSON → deeplink 导入） |
| 2 | 安装/卸载无进度 | opBusyId 跟踪 + spinner 动画（已装行 ✕/⟳ + 市场行 ＋） |
| 3 | 插件更新假象 | `claude plugin` 命令需要 CLAUDE_CONFIG_DIR env——适配器 `_run_cli` 统一注入 `/root/app/.claude` 兜底 |
| 4 | 卸载报 --kind 不识别 | host CLI plugin-uninstall/update/install 三子命令补 `--kind` 参数 |
| 5 | skill 来源追踪 | `_skill_items()` 交叉比对 installed_plugins.json：`sources`/`source`/`conflict` 字段 + UI ⚠ 标记 |
| 6 | 初始 skill/plugin 清空 | `BUNDLED_SKILLS = ()` + Dockerfile 跳过 _bundle plugins COPY + cc-switch-skills 离线提取移除 + factory 空目录+空 JSON |
| 7 | 选中文本自动复制 | xterm `onSelectionChange` → `writeText(sel)` 自动写系统剪贴板（bash/claude/codex 全适用） |

## 验证
- 镜像实测：skills list = []（清空 ✓）；adapter 语法修复（--query 冲突、列表结构）。
- pytest 1439 / Vitest 611 / vue-tsc 0 / cargo 0 / vendor 1520/0。
- BUNDLED_SKILLS 清空后 4 个旧工厂安装测试 skip（新语义：商城自装）。
