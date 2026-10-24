# b13 — MCP 403 / Codex 更新锁 / Skill 仓库分组 / Node 基础镜像清理

> 目标：修复本轮四项手测问题，并给出 R25–R28 复测步骤。

## 根因与方案

1. Smithery 403：Python urllib 默认 User-Agent 被 Cloudflare/WAF 拒绝；请求显式携带 `User-Agent: AISC/2.1.16`。
2. Codex 自更新 EACCES：project 模式 toolchain 是宿主 bind mount，正在运行的 npm 包目录无法在该文件系统上 rename。Codex wrapper 将持久 prefix 的整个 `@openai` scope 复制到 `/tmp/aisc-codex-shadow` 后用 node 启动 shadow 入口，更新仍写入持久 prefix。
3. Skill 分组：新增纯前端分组模型；已安装与搜索结果都按 `repo` 聚合。组行支持批量启用/禁用、批量更新（重装）、批量卸载/安装；展开后保留单技能操作。adapter 补 `directory` 字段用于更新重装。
4. 构建缓存清理：builder/dangling 清理后额外 untag 当前 Node 基础镜像（默认 `node:22-slim` 及其配置镜像源别名）。若容器直接占用则仅记录 warning，不强删。

## 验证

- Python：adapter UA、skill directory、cache node untag、wrapper 静态与真实容器 update。
- Vitest/vue-tsc：分组模型、store 批量操作、UI 组行。
- Docker：真实 bind mount 中 Codex 0.154 → 0.164 更新成功。
- Computer Use：MCP 搜索、Skill 分组 UI、缓存清理后 `node:22-slim` 消失。
# b13 追加实测记录

- Smithery 无 UA 请求复现 HTTP 403；`User-Agent: AISC/2.1.16` 返回 200。
- bind mount 中 Codex 0.154 直接 `codex update` 复现 EACCES rename；复制 @openai scope 到容器内 shadow 后更新成功 0.164（待用新 wrapper 复测）。
- 基础镜像清理先实现为仅 untag `node:22-slim` 与配置镜像源别名；若被容器直接占用则 warning，不强删。

## 实测记录（2026-10-24）

- Smithery：无 UA 复现 HTTP 403；`User-Agent: AISC/2.1.16` 后 `pdf` 搜索返回 10 条。
- Codex：bind mount + 0.154 直接 `codex update` 复现 EACCES rename；新 wrapper shadow 方案实测更新成功 `0.164.0`。
- Builder cache：`builder prune --force` 实测 1.303GB → 1.246GB，非全量；改为 `--force --all` 后实测 Build Cache `0B`。Node 基础镜像标签实测被移除，只保留 `super-claude:latest`。
- Skill 分组：单元/组件静态测试覆盖已装与商城同仓库聚合、组批量和子项操作。

## 预复测补充（2026-10-24）

- Workbench UI：MCP 搜索 `pdf` 返回 10 条，无 403；Skill 搜索 `superpowers` 后 `obra/superpowers` 聚合为“12 个技能”，展开可见 `brainstorming` 等子技能与单技能安装按钮。
- 真实清理：Build Cache 2.513GB → 0B；`node:22-slim` 标签移除；`super-claude:latest` 保留。
