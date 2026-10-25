# v2.1.16 preview-fixes b2 — 扩展交互 / MCP 安装 / 服务合并 / 镜像兜底

> 2026-10-25 preview.2 第二轮反馈 9 项。

## 范围

1. Skill 子技能行为：操作按钮固定最右；说明在下方；再次点击子技能收起说明但父组保持展开。
2. 磁盘页删除第一层资源名重复列表，仅保留卡片与管理表。
3. 宿主工具（F2）从设置独立分组迁入左侧「服务」视图。
4. 出厂 caveman 改为 JuliusBrussee/caveman 仓库全部 7 个 skills + grill-me。
5. 操作进度条去除重复旋转图标，保留单个按钮 spinner + 进度条。
6. Smithery MCP 安装改用 HTTP `deploymentUrl`，不再假设本地 command。
7. Skills/MCP/Plugins 操作完成与失败增加 toast 提示。
8. 远程直连失败时镜像兜底：skills.sh → www；Smithery registry → api；GitHub git 操作 → ghfast/gh-proxy。
9. Skill 安装后默认 Claude + Codex 均启用；更新保留用户启停状态。

## 验证

- Vitest：子技能切换、进度不重复、toast、磁盘去重、服务合并。
- Python：Smithery HTTP、skill 双引擎启用、skill-update、镜像重试、skills.sh API fallback、caveman 全量出厂。
- 实机：MCP 搜索安装、GitHub skill 安装、无代理镜像重试、服务页宿主工具。

## 执行记录（2026-10-25）

- Smithery MCP 详情按 `connections[].deploymentUrl` 生成 HTTP MCP 配置；真实容器验证 `reportflow-mcp` 安装后 Claude/Codex 均启用。
- GitHub 直连失败时通过 `ghfast.top` / `gh-proxy.com` 的 git `insteadOf` 环境重试；skills.sh 搜索可回退 `www.skills.sh`；Smithery 可回退 `api.smithery.ai`。
- Skill 安装后显式 enable Claude/Codex；新增 `skill-update` op，更新保留用户启停状态。
- 操作完成/失败增加全局 toast；进度条改为文本 + 横向进度，不再与按钮 spinner 重复。
- 子技能说明独立 toggle；按钮保持最右，说明换行到下方。
- 磁盘页删除第一层 preview-name 行；宿主工具迁入 Services。
- 出厂技能为 caveman 仓库 7 个 skills + grill-me。
- 门禁：Python 1460 / Vitest 640 / vue-tsc / Rust 362 全绿。

## 实机预复测（2026-10-25）

- 新镜像空工作区首次启动：caveman 7 个 skills + grill-me 全部注册，Claude/Codex 均启用。
- `reportflow-mcp` 从 Smithery 安装成功，列表出现 HTTP transport，Claude/Codex 均启用。
- `obra/superpowers:using-superpowers` 安装后 Claude/Codex 均启用。
- Services 页显示「宿主工具（F2）」并保留 Web Services 区块；设置页不再有独立宿主工具分组。
- 扩展页无顶层“搜索文件”；`JuliusBrussee/caveman` 显示 7 个技能；子技能详情可展开/再次点击收起，父组保持展开。
