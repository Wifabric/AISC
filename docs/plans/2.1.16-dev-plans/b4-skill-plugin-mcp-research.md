# b4 — 技能 / 插件 / MCP 统一管理调研与方案（待裁决）

> 需求来源：`20261017-希望增加技能-插件和MCP服务-Thomas`（需求 #2）。
> 本批为**调研批**：只产出方案与裁决点，不动码。实施批次待用户裁决后另立。

## 1. 玗事实基线（本仓库可核验）

### cc-switch v5.10.5 能力（vendored 二进制 strings 探针 + 既有调用面）

| 能力 | 状态 | 证据 |
| --- | --- | --- |
| Skills 管理 | **原生支持** | `skills list / sync / sync-method copy`；skill repo（owner/name）注册表；`skills` 表含 `enabled_claude / enabled_codex`（双引擎独立开关）；AISC 出厂已用它同步 caveman/document-skills/grill-me/superpowers（`container/cc_switch_skills.py`） |
| MCP 管理 | **原生支持** | `cc-switch mcp list`；add / edit / delete / import / per-app enable；统一配置 v2（`{"claude":…,"codex":…,"mcp":…}`）；Codex 落 `config.toml [mcp_servers]`、Claude 落 `.mcp.json`；Hermes 配置导入 |
| Plugin 管理 | **不支持** | 二进制中 plugin 仅出现在 Claude settings 通用配置文案；无 plugin 子命令 |

### 三类资产在两个引擎中的形态

| 资产 | Claude | Codex | AISC 现状 |
| --- | --- | --- | --- |
| Skills | `~/.claude/skills/`（扁平目录） | `~/.codex/skills/` | 出厂 `_bundle/skills`（gstack 等）+ 插件内技能经 cc-switch 双写；`cc_switch_skills.py` 幂等同步 |
| Plugins | marketplace 体系：`installed_plugins.json`（版本/gitCommitSha/installPath）+ `known_marketplaces.json` + cache 目录 | **无此概念** | 出厂 `_bundle/plugins` 预置 5 个（superpowers/claude-hud/caveman/document-skills/skill-creator）+ 构建期 `claude plugin install` |
| MCP | 项目级 `.mcp.json` + `enableAllProjectMcpServers` | `config.toml [mcp_servers]` | AISC 自管 `aisc-host`（host-tools，`register_host_mcp.py` 幂等注册/注销）；cc-switch 统一配置已含 mcp 域 |

### 现有数据面模式（复用依据）

- Provider 页签：Rust → `docker exec` → `aisc-cc-provider` adapter；**列表走只读 SQLite 快照，变更走官方非交互 CLI**（secret 只走 stdin）。Skills/MCP 可完整复刻该模式（cc-switch.db 同库）。
- 出厂初始化已存在：skills（离线 bundle + 哈希标记 + 文件锁）、plugins（预置 + 构建期安装）、MCP（aisc-host 注册）。

## 2. 方案（推荐形态）

### 2.1 统一模型：三 Tab「扩展管理」

Workbench 新增「扩展」入口（建议放设置页新分组，避免顶级导航膨胀——**裁决点 D-1**），
三个子页签共用「查看为主、破坏性操作二次确认」的交互骨架：

| Tab | 数据源（列表） | 生命周期操作 | 更新检查 |
| --- | --- | --- | --- |
| Skills | cc-switch.db skills 表（只读快照） | 启用/停用（claude/codex 各自）、安装（repo owner/name 或 zip）、卸载、同步 | repo 拉取对比（P2） |
| MCP | cc-switch 统一配置 mcp 域（只读快照） | 启用/停用（per-app）、新增（表单：stdio command / HTTP url）、编辑、删除、从 Claude/Codex 导入 | **不适用**（配置对象无版本） |
| Plugins | `installed_plugins.json` + marketplaces（容器内只读） | 查看（名称/版本/来源/scope/路径）+ 更新提示；安装/卸载桥接 `claude plugin install/remove`（P2） | version + gitCommitSha vs marketplace 刷新（反馈场景 2 的主战场） |

### 2.2 分期

- **P1（首期，建议纳入 v2.1.16 收尾前或转期——裁决点 D-2）**：
  三 Tab 统一查看 + Skills/MCP 的启用停用与删除（全部走 cc-switch 既有命令）+
  Plugins 只读与「有新版本」角标。**零新增依赖，纯桥接。**
- **P2**：Skills 安装（repo/zip）、MCP 新增/编辑表单、Plugins 安装/更新/卸载
  （`claude plugin` 容器内桥接 + 双向刷新）。
- **P3**： Skills 更新检查、marketplace 浏览器、按工作区隔离的扩展集。

### 2.3 数据面契约（P1）

- 复用 `aisc-cc-provider` 模式：新增 `aisc-extensions-adapter`（容器内 Python，
  只读 SQLite/JSON 快照 + 变更走 `cc-switch` 非交互命令；输出 secret-free）。
- Rust 新命令：`extensions_list(kind)` / `extensions_toggle(kind, id, app, on)` /
  `extensions_delete(kind, id)`。
- 出厂初始化零改动（三资产现状即首屏内容——满足反馈场景 1）。

## 3. 裁决点

| # | 问题 | 选项 | 推荐 |
| --- | --- | --- | --- |
| D-1 | 入口位置 | a) 设置页新分组「扩展」；b) 顶级导航页签 | **a**（导航不膨胀，与 Provider 页签平级迁移容易） |
| D-2 | P1 排期 | a) 本阶段（2.1.16）收尾前实施；b) 转下一阶段 | **b**（本阶段 b1–b3+CI 修复已重，P1 建议独立开 2.1.17 或 2.1.16 加批，避免收尾拖延） |
| D-3 | Plugins 操作深度 | a) P1 只读+更新提示，P2 桥接 claude CLI；b) P1 直接桥接安装/卸载 | **a**（claude plugin 交互行为需实测，先稳后动） |
| D-4 | MCP 新增表单归属 | a) P1 只管已有 server 开关；b) P1 即含新增 | **a**（新增涉及 stdio/url 双形态校验，放 P2） |

## 4. 风险

- cc-switch 非交互输出格式无公开契约：P1 列表走 SQLite 直读规避；变更命令以
  exit code + stderr 归因（与 provider adapter 同法）。
- Codex 无 plugin 概念：Plugins Tab 明示「仅 Claude」，避免用户误解。
- 容器内 marketplace 网络受限：更新检查失败要显式降级为「无法检查」，不阻塞查看。
