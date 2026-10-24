# b12 — Docker 冷启动、插件商城、Codex 选区修复

> 目标：清空 Docker 后 `aisc build` 不长时间卡在首个基础镜像源；插件页具备默认官方市场与搜索安装；Codex 普通拖选/右键复制与 bash、claude 一致。

## 范围

- `src/aisc/cli/commands/build.py`：基础镜像预拉默认超时降为 120s，输出可预期超时与自动切换提示；失败指引使用实际 bare tag。
- `container/Dockerfile`：出厂已安装插件仍为空，但内置 `claude-plugins-official` 市场目录与注册表，供商城搜索。
- Extensions 链路：新增 `plugin-search`（adapter → host application → CLI parser/dispatch → Rust allowlist → Pinia store → Vue UI）并补齐 b10 MCP op 漏接。
- `workbench/src/features/terminal/codexMouseSelection.ts`：仅 Codex 且 xterm 处于 mouse tracking 时，把普通左键拖选转为 xterm 强制选区；未拖动的单击回放给 Codex，保留点击行为。右键菜单使用最近一次选区兜底。

## 验证

- Python：adapter、build、extensions wiring 相关 unittest。
- Workbench：Vitest + vue-tsc。
- Rust：cargo fmt/clippy/test。
- Docker：重建镜像后验证 `installed=[]`、official marketplace available 非空。
- Computer Use：启动 Workbench/Codex，普通拖选后宿主 Ctrl+V 粘贴出所选文本，右键菜单“复制”可点。
> 2026-10-24 预复测补充：R21 已在清空 Docker 后实测通过；R22 UI 已实测官方市场+搜索+展开，安装链路用临时容器实测通过；R23/R24 已用 Computer Use/宿主剪贴板实测通过。
