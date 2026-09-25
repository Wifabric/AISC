# 历史会话重构：「工作记录」+ 网页版聊天界面

> 状态：计划待用户验收（2026-09-19 立项）——大特性，四批次交付，批 0 探针前置
> 方法：ultracode workflow（研究员 + 独立证据核验；verdict=corrected，两处行号/表述修正已并入）
> 对应 target：docs/todo.md「历史会话重构：网页版聊天的界面 +『工作记录』概念」

## 0. 术语与概念对齐

- 「网页版聊天界面」= Workbench 内类 ChatGPT/Claude 网页版的消息流**只读回放**视图（读 transcript 渲染）；与 web-services/aisc-web-gateway（容器服务端口暴露）无关，规格撇清撞名。
- 用户模型：aisc 会话 = bash 包住 codex 会话的 runtime（记忆空间）；**工作记录**负责记录/保存打开过的 bash(内含 codex) 会话状态；与 codex resume 记录非一一对应（惯用单会话=1:1；一任务一干净会话=1:N）。
- 本项是 v2.1.8 设计 §7 明文的下周期欠账（「对话内容预览/浏览」）的立项。

## 1. 现状（file:line 在案）

- **真实空白**：「这个 bash 会话里跑过哪些 provider 会话」当前**任何地方都没有记录**——wrapper 记录字段全集无 resume_id/conversation_id/title（container/aisc-session-wrapper:154-169，--resume-id 转 argv 后即弃 :177-205）；Workbench history.json 铁律不存 session ID（history.rs:8-10）；tab 恢复=placeholder+新 session ID（03-lifecycle-contract §六）。
- **wrapper 记录是易失态**：/run/aisc/sessions 在容器可写层；stop 保留容器（runtime.py:1678-1690）、remove 全丢（:1745 起）⇒ 工作记录不能落容器，也不能为它新增卷挂载（破坏 config fingerprint）。
- **transcript 本体已持久在 host**：项目态挂载 `<ws_dir>/claude`→/root/.claude、`codex`→/root/.codex（runtime.py:1227-1234）；实机取样确认 claude `projects/-/<uuid>.jsonl`（2.1.270）与 codex `sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl`（0.154.0，session_meta 带 session_id/cwd/cli_version）。
- **薄读层（方案 A）已冻结**：ID 从文件名提取、10MB 上限头扫 200 行、注入上下文排除、双 provider 提取器 `_EXTRACTORS`（conversation.py:38-58、:80-160）；标题覆盖表 `<ws_dir>/runtime/conversation_titles.json`（:316-338）=「AISC 自有小状态放 runtime 目录」的直接先例。2.1.10 韧性：权限坏文件跳过（:191-196，核验修正：原引 94-109）、非字符串标题降级（:98-100）。
- **格式全集已实测**（fixtures 9 个 + 实机）：codex 行类型 session_meta/event_msg(task_*/item_completed/token_count)/response_item(message|reasoning|function_call|function_call_output)/world_state/turn_context；claude 行类型 queue-operation/user/assistant/attachment/last-prompt/atis-latch。
- **历史面板现状**：v2.1.8 T4 扁平列表 + resume 两调用（preflight→open --resume-id，findLiveResumeTab 防重复；workspaceExplorer.ts:625-681）；resume 门禁仅 claude/codex（session.py:132-137）；契约冻结：两调用编排 + wrapper 纯透传不得动（2.1.8 v8/v9）。
- **未决事实（批 0 探针对象）**：codex `resume <id>` 后 rollout 续写原文件还是 fork 新文件？claude `--resume` 是否恒同文件追加？仓库内外均无证据；且 `_find_conversation_file` 对同 ID 多文件返回**未排序 rglob 首个命中**（conversation.py:376-398，核验修正：非代码保证的字典序）——若 fork 同 ID 会命中不确定文件。

## 2. 方案裁决（研究推荐，Claude 代定采纳）

1. **数据层**：`<ws_dir>/runtime/worklogs.json` 单文件（schema `aisc.worklog/v1`，沿标题覆盖表同款原子写+锁）。记录：worklog_id(uuid)/title(sanitize 后)/created_at/last_opened_at/state(active|archived)/sessions[]（terminal_session_id、agent、conversation_id|None、resume_of_conversation_id|None、opened_at、closed_at|None、exit_code|None）。禁入 workspace 树（DATA-01）/history.json//run。
2. **写入时机**：CLI 侧会话开/关钩子——`build_session_exec`（session.py:72，open_session 与 serve PTY op 共用咽喉）open 时 append；`terminate_session`（:245）与 Workbench 关 tab 路径收尾更新。**fail-open**：账本写失败不阻塞开会话。resume_id 非空记 `resume_of`；裸 docker exec 直启场景记不到（与 bash 历史同盲区，可接受）。
3. **聊天界面**：**只读 transcript 渲染**——新 CLI `aisc conversation read`（--agent/--conversation-id，尾部懒加载分页）+ Workbench 只读「对话」pane：user/assistant 文本全渲染；tool_use/function_call 与结果折叠单行摘要（可展开）；reasoning 默认折叠；session_meta/event_msg/world_state 等不渲染；图片→附件 chip 不内联。**不允许从聊天视图输入**（输入通道只有容器 PTY；「继续对话」按钮跳 resume 两调用）。
4. **一对多聚合**：worklog 为聚合节点 + `resume_of` 边；sessions[] 按 opened_at 排序即时间线；codex fork 出新文件→新条目挂同一 worklog；时间窗推断回填标 `inferred=true`（UI 可见可改）。
5. **与旧面板关系**：**并存过渡**——「历史」tab 内分段切换「工作记录 / 全部会话」（flat 列表原样保留）；工作记录视图手测通过后由用户裁决下线（推翻「直接替换」：正确性未验证就砍可用功能违反小批交付惯例）。
6. **存储中性**：conversation 解析器保持 per-agent 可注册（`_EXTRACTORS` 模式）——Pi/opencode 未来接入第三种 transcript 不改数据模型。

## 3. 规格

- **Scope**：批 0 探针；worklog 数据层 + 会话开/关钩子 + reconcile；`conversation read` + 只读 pane；历史 tab 分段切换 + worklog CRUD + 存量收编。
- **Out of Scope**：聊天视图输入/续写；富渲染（代码高亮/图片内联/思考流动画）；--resume-id 支持 bash/cc-switch；改 resume 链路契约；conversation 解析层与「长对话恢复」bug 的重叠改动（两边立项互相引用，**禁止两处同时动 conversation 解析/读取层**——见 long-conversation-repro.md，等复现样本结论或先做只读渲染避开写路径）。
- **Constraints**：provider 会话文件严格只读（conversation.py 模块头铁律）；秘密纪律（不写 env/argv/key/token/PTY 字节；标题过 sanitize_title）；temporary scope 无 data-root 挂载→工作记录降级缺席（UI 不承诺持久）；Windows 原子写 tmp+os.replace、跨进程锁、UTF-8。
- **Acceptance**：
  - [ ] 纯 CLI：开两会话（其一 resume）→ terminate → `aisc worklog list` 聚合正确（resume_of 边在）
  - [ ] 只读 pane：claude/codex 各一会话渲染正确；工具调用折叠/展开；10MB 超限与坏行降级
  - [ ] resume 链路回归零破坏（preflight→open→findLiveResumeTab）
  - [ ] 容器 remove 后工作记录与 transcript 仍在；temporary scope 无持久承诺
  - [ ] 新旧视图切换零数据丢失；pytest/vitest/cargo 全绿

## 4. 实施计划（四批，批间独立可交付）

- **批 0（T0 探针，规格冻结前置）**：scratch runtime 实测 codex resume 后 sessions 目录 diff（续写/fork 同 ID/fork 新 ID）；同法 claude --resume。结论入 fixtures + 本文件修订。验证：探针报告入库。
- **批 1（数据层）**：domain/worklog.py 纯模块（schema/校验/时间窗推断）→ application/worklog.py 存取 ops（list/get/create/rename/archive/delete/link/unlink/close）→ build_session_exec/terminate 钩子（fail-open）→ `aisc worklog reconcile`（新 jsonl 头扫 ≤200 行回填，inferred 标记）+ CLI 面——验证：pytest 矩阵 + CLI 手测。
- **批 2（渲染层，仅依赖批 0）**：`conversation read` 归一化消息流 → Workbench 只读 pane（双 provider 渲染器/折叠/懒加载/降级文案）→ 历史面板行「查看对话」入口（与「恢复」并存）——验证：fixture 单测 + 实机手测 + resume 回归。
- **批 3（聚合+收敛）**：历史 tab 分段切换「工作记录/全部会话」→ worklog CRUD UI + 拖挂/解挂 + reconcile 触发与「未归组」提示 → 存量收编（首启动合成「未归档会话」worklog）→（用户裁决门）flat 下线与否——验证：手测矩阵 + 收口流程。

## 5. 开放问题

| 决定 | 状态 | 默认 | 说明 |
|---|---|---|---|
| codex/claude resume 文件行为 | open（批 0 探针） | 按「fork 新文件同 session_id」设计；preflight 改取 mtime 最新 | 决定条目粒度与「一对多」边记法 |
| worklog 创建粒度 | assumed | 每次 PTY 会话开立自动建（占位名可改），fail-open | vs 用户显式新建 |
| 聊天视图允许输入 | **open（用户裁）** | 只读回放 | 允许输入=复杂度数量级上升且撞冻结契约 |
| 存量会话收编 | assumed | 合成「未归档会话」worklog 收容，可后续拆分 | 首启动体验 |
| bash/cc-switch 会话入账 | assumed | 记状态级条目（UI 占位卡），渲染仅 claude/codex | 用户模型里 bash 是一等公民 |
| flat 视图下线时机 | open（用户裁，批 3 门） | 保留为「全部会话」标签，手测通过后裁决 | 涉回归风险与用户习惯 |
| reconcile 触发时机 | assumed | 启动一次 + 列表页「n 个未归组」提示按时间窗建议归组 | 大 workspace IO 成本 |
