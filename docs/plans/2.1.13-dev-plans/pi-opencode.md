# agent 加上 Pi / opencode（免安装）

> 状态：计划待用户验收（2026-09-19 立项）——D-1 边界有一个语义确认（§5 Q1）
> 方法：ultracode workflow（研究员 web+代码双路 + 独立证据核验；verdict=corrected——npm 镜像源前提被修正，按需获取可行性上调）
> 对应 target：docs/todo.md「agent 加上 Pi/opencode（免安装，镜像不变）」；裁决 D-1

## 1. 外部事实（web 抓取 2026-09，本地不可核验处标置信度）

| 维度 | opencode | pi |
|---|---|---|
| CLI 命令 / npm 包 | `opencode` / `opencode-ai`（【高】） | `pi` / `@earendil-works/pi-coding-agent`，官方要求 `--ignore-scripts`（【高】） |
| 许可证 | MIT（sst/opencode，现 anomalyco/opencode）【高】 | MIT（badlogic/pi-mono，Mario Zechner）【高】 |
| 非交互 | `opencode run "prompt"`、`-m provider/model`、`--auto`、`-c/-s <id>` 续会话、`--format json`、`serve`【高】 | `pi -p "prompt"`（print）、`--mode json/rpc`、`-c` 续最近、`--session`、交互内 /resume【高】 |
| 认证 | `opencode auth login` → `~/.local/share/opencode/auth.json`；配置 `~/.config/opencode/opencode.json`；provider apiKey 支持 `{env:VAR}`【高】 | `/login` OAuth（Claude/ChatGPT/Copilot/xAI/OpenRouter…）→ `~/.pi/agent/auth.json`(0600)；env key 全套（ANTHROPIC_API_KEY 等）【高】 |
| 运行时 | 自足单二进制随 npm 分发；镜像有 node22、无 bun/uv【中】 | node 版本要求官方未标注【低】——npm 包在 node22 可运行性列为实施前实测项 |
| 权限模型 | 交互内建确认（run --auto 自动批准）【高】 | 无 yolo flag，靠 cwd+git 回滚哲学【高】 |

- **两者都不读 cc-switch 的 claude settings.json / codex config.toml**，不接 15701/15702 代理与模型 shim——provider 模板/路由对它们无意义；但都认 ANTHROPIC_API_KEY 类 env（cc-switch env_inject 机制理论上可桥接，列为后续可选路径，本期不做）。
- **npm 镜像源前提（核验修正，重要）**：Dockerfile:166 构建期 `npm config set registry npmmirror` 写入 `/root/.npmrc`，单阶段构建+root 用户+无清理 ⇒ **随镜像层持久化，运行时容器内 `npm i -g` 默认即走 npmmirror**——CN 网络下按需 npm 安装默认可达（可用 `docker run --rm <image> cat /root/.npmrc` 一行复核）。运行时真正无加速的只有 GitHub 直连（curl 单二进制路径）。研究员原文「npmmirror 仅构建期」不成立。
- **关键基础设施**：entrypoint.sh:224-233 `NPM_CONFIG_PREFIX=$TC/npm-global`（项目态持久 toolchain 卷）⇒ 「运行时装一次、项目态持久」天然成立；临时态随容器消亡。

## 2. 现状：新增 agent 的 touch-point 全集（file:line 在案）

- CLI 域：models.py:579-586 SessionAgent 枚举；main.py:179-188 糖命令循环、:881-885 artifact choices；commands/agents.py:20 AGENTS。
- application 四处 `("claude","codex")` 硬编码：provider.py:23-24、cc_switch_provider.py:22-24、conversation.py:60、session.py:132（resume 门禁）——**本期全部不动**（见 Out of Scope）。
- 容器：aisc-session-wrapper `AGENT_BINARIES`（:42-47，:258-259 白名单校验）、`_binary_available`=shutil.which 探测钩子（:172-176，天然支持「未安装检测」）、`_rebuild_env`（:134-151）；wrapper 装载模式=mv `-real`+COPY（Dockerfile:303-310）——**新增 wrapper=改镜像，本期不做**。
- Tauri：session.rs:53 AGENTS 白名单。前端：types/index.ts:4/:858 双 union、tabLayout.ts:64-72（AGENT_TITLE/AGENTS）、TabBar.vue 菜单（:441/:466/:472，cc-switch 过滤）、i18n tabbar.menu.*、workspaceRuntime.ts:170-175 providerStatuses（双 agent，不动）。

## 3. 方案裁决（研究推荐 C：混合，Claude 代定采纳）

**基线 = 注册 + 检测 + 引导（零网络代码）；增强 = 按需获取辅助（显式、可关）。镜像/容器会话链路的改动仅限 wrapper 白名单登记（见 Q1）。**

- 注册：pi/opencode 全链登记（枚举/糖命令/artifact choices/Tauri 白名单/前端 union/菜单/i18n）。
- 检测：会话开起时 wrapper which 探测，缺失 → 稳定错误码 + 中文指引（agent 名、临时/项目态两条安装命令、持久性说明）；Workbench 页签渲染「未安装」内联指引 + **一键复制安装命令**（`npm i -g opencode-ai`；`npm i -g --ignore-scripts @earendil-works/pi-coding-agent`；附 CN mirror 变体 `npm_config_registry=...` 作确定性手段）。
- 增强（可裁剪）：可选容器内 ensure 提示（需用户确认，`AISC_AGENT_ENSURE=off` 可关）；离线 fail-soft——稳定错误+手动指引，绝不阻塞 claude/codex/bash，绝不自动重试风暴。
- 否决：A 纯按需获取（首次使用网络等待+失败面大）；B 纯检测（便利性不足）——C=两者按用户控制权分层。

## 4. 规格

- **Scope**：§2 touch-point 登记（除 provider/conversation 数据面）+ wrapper 白名单登记（视 Q1）+ 缺失检测与引导 + 一键复制命令 + i18n + 测试。
- **Out of Scope**：镜像内置安装（D-1）；provider 体系覆盖（provider.py/cc_switch_provider.py 双元组不动——cc-switch 是 claude/codex 专用工具）；conversation 面板/`--resume-id` 适配（各自 JSONL 适配是独立后续切片）；认证持久化卷挂载（Q3 挂账）。
- **Constraints**：会话数据面必须走 aisc-session-wrapper（绕开=失去记录/受控终止，验收不建立在直启上）；秘密纪律（key 只走 agent 原生 login/env，不进 argv/日志）；agent 枚举跨五层同步，漏一层即 usage error；i18n 键奇偶强制。
- **Acceptance**：
  - [ ] Workbench 对运行中 runtime 新建 opencode 与 pi 页签，TUI 正常渲染/键入/退出
  - [ ] 未安装 → 中文指引（含两条安装命令与持久性说明）而非裸错误；一键复制可用
  - [ ] `npm i -g` 安装后（项目态）页签可用；容器重建后二进制仍可用（toolchain 卷持久）、auth 需重输（本期已知限制，文档明示）
  - [ ] × 终止走 wrapper terminate（session record 0600 落盘、无秘密）
  - [ ] claude/codex/bash/cc-switch 全回归；**镜像构建产物不含 pi/opencode 本体**（Dockerfile diff 审查 + image size 基线比对）
  - [ ] 离线容器 fail-soft 明确文案；i18n 键奇偶；cargo/vitest/pytest 全绿

## 5. 实施计划

1. 契约冻结：agent id 定名（`pi`、`opencode` 字面量）+ Q1/Q2/Q3 裁决 + Scope 定稿。验证：decisions.md 入档。
2. CLI 域登记：SessionAgent + 糖命令循环 + artifact choices + agents.py AGENTS——验证：单测；`aisc session open --agent opencode` 到达容器层（老镜像得稳定拒绝）。
3. 容器侧（视 Q1）：AGENT_BINARIES 加两项 + 缺失探测用户文案 + AISC_AGENT env 注入确认——验证：throwaway 容器实测（缺失→带指引错误；npm 安装→open 拉起 TUI；项目态重建后二进制仍在）。
4. Tauri：session.rs AGENTS 加两项 + 错误码映射——验证：cargo test + IPC 两分支手测。
5. 前端：types 双 union + tabLayout + TabBar 菜单 + i18n + 「未安装」内联指引/一键复制——验证：vitest（键奇偶/tab restore/类型收窄）。
6. 认证与首跑闭环：PTY 下 `opencode auth login` / pi `/login` 实测；ANTHROPIC_API_KEY env 继承验证；「容器重建后需重新 auth」写入用户文档。验证：手测清单。
7. 按需获取辅助（独立可裁剪）：一键复制命令（含 mirror 变体）+ 可选 ensure 提示——验证：离线 fail-soft / 在线装后可用 / image size 比对。
8. 验收清单执行 → devlog 入档 → todo 勾选。

## 6. 开放问题

| 决定 | 状态 | 默认 | 说明 |
|---|---|---|---|
| **Q1: D-1「镜像不变」的字面边界** | **open（用户裁）** | 仅指不预装 agent 本体；wrapper 白名单/登记脚本随常规镜像构建正常演进（否则 Workbench 只能 docker exec 直启降级，且新旧镜像白名单都拒绝新 agent） | 建议采纳默认：D-1 反对的是「装 agent 进镜像」，不是「镜像冻结」 |
| Q2: provider 体系覆盖 pi/opencode | assumed | 不覆盖，v2.1.13 挂账 | cc-switch 绑定 claude/codex 配置格式，放开工作量大 |
| Q3: 认证持久化（~/.pi、~/.local/share/opencode 随容器重建丢失） | open（挂账） | 本期接受，文档明示「重建后重新 auth login」；后续独立裁决宿主状态卷或 XDG 重定向 | 不违反 D-1（纯宿主侧变更） |
| 先后顺序 | assumed | 同批登记（touch-point 同构，边际成本≈0）；辅助安装先 opencode 后 pi | opencode 文档全、MIT、npm 单包 |
| artifact 登记纳入 | assumed | 纳入（choices 加两项，成本极低） | 产出物归因链可用 |
| ui.default_tab_agent 放开 | assumed | 允许（合法值即渲染），默认值保持 bash | 未装 agent 设默认会让 + 按钮总失败 |
| 会话面板适配其原生 JSONL | assumed | 不做，挂账后续 | =每家一套解析器+fixtures，独立 T 序列 |
