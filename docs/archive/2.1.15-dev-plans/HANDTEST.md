# v2.1.15 手测清单

> 每项必须先完成前置准备，再按步骤执行；只有理想结果全部满足才记通过。
> 出现任何异常时记录时间、分支/构建号、窗口 target、工作区路径形态和完整报错。

## b1：远程 lease target 修复

### T1：远程窗口 lease heartbeat 保持远程 target

**前置准备**

- 使用一台可 SSH 的 Linux/macOS 远端；
- 本地与远端均安装可配对的 AISC CLI；
- 远端 Docker 可用；
- Workbench 设置中存在该远程机器；
- 准备一个远端工作区；若复用旧工作区，先执行 reconcile 并确认无 active lease；
- 在远端工作区数据目录准备好查看 `runtime-lease.json` 的方式；
- 记录 Workbench 版本、分支/构建号、远端主机标识（手测记录可用别名）。

**精确操作步骤**

1. 启动 Workbench，进入主窗口；
2. target 切到该远程机器；
3. 选择远端工作区并执行 reconcile；
4. 启动任一 runtime；
5. claim 后不关闭窗口，保持至少 70 秒；
6. 每 15–20 秒查看远端 `runtime-lease.json` 的 `lease_last_seen_at`；
7. 等待时间结束后进入 bash 会话并执行 `echo AISC_REMOTE_LEASE_OK`；
8. 不关闭窗口，再开一个本 Workbench 实例，尝试 reconcile 同一工作区一次。

**字段级理想结果**

- `targetGet.machine.name` 与选中远程机器一致；
- claim 返回 `outcome` 为 `claimed` / `claimed_stale` / `reclaimed` 之一；
- claim 返回非空 `lease_id` 和 `workspace_key`；
- 远端 `runtime-lease.json.schema` 为 `aisc.workspace-lease/v1`；
- `workbench_instance_id` 保持不变；
- 至少 4 次 heartbeat 后 `lease_last_seen_at` 持续更新；
- bash 出现提示符，`echo` 输出精确为 `AISC_REMOTE_LEASE_OK`；
- 第二实例 reconcile 被 active lease 明确阻塞，且不清理第一个 runtime。

**异常判定**

- 远端 `lease_last_seen_at` 超过 45 秒未更新 → fail；
- bash 停留在无提示符光标超过 30 秒 → fail；
- 出现 `AISC_ERR_ACTIVE_WORKSPACE_LEASE` 指向第一个仍存活实例 → fail；
- heartbeat 请求出现在本机 AISC 数据根而不是远端 → fail；
- 任一异常保留日志/截图，先停止测试，不改代码。

### T2：切换 global target 后原 remote lease 不漂移

**前置准备**

- 至少两台远程机器：`remote-a`、`remote-b`；若只有一台远端，可再用一个 local 主窗口；
- 两边 CLI/Docker 均可用；
- 准备 `remote-a` 工作区 A；
- 确认无历史 active lease。

**精确操作步骤**

1. 窗口 1 target 设为 `remote-a`；
2. 启动工作区 A runtime 并通过 T1 前半段确认 heartbeat 正常；
3. 窗口 1 保持打开；
4. 另开窗口 2，将窗口 2 target 设为 `remote-b`（或 local）；
5. 等待 70 秒；
6. 回到窗口 1，打开 bash 并执行 `echo SAME_WINDOW_TARGET_OK`；
7. 关闭窗口 1 的 runtime；
8. 检查 `remote-a` 的 lease 已释放，且 `remote-b`/本机没有工作区 A 的 lease。

**字段级理想结果**

- 窗口 1 claim 后 heartbeat 仍打到 `remote-a`；
- 窗口 2 切 target 不影响窗口 1 的 bash；
- bash 输出精确为 `SAME_WINDOW_TARGET_OK`；
- 关闭 runtime 后远端 `runtime-lease.json` 不再是 fresh，或被明确 release；
- `remote-b`/本机不出现工作区 A 的 fresh lease。

**异常判定**

- 窗口 2 切换导致窗口 1 lease conflict → fail；
- heartbeat 打到非 `remote-a` → fail；
- release 后仍残留 fresh lease 并阻塞下次启动 → fail。

### T3：local direct heartbeat 不回归

**前置准备**

- 使用本机 Docker；
- target 为 local；
- 本机工作区无 active lease；
- 环境变量未设置 `AISC_LEASE_HEARTBEAT=cli`。

**精确操作步骤**

1. 启动 Workbench，选择本机工作区；
2. reconcile 并启动 runtime；
3. 保持窗口可见 40 秒；
4. 查看本机工作区数据根 `runtime-lease.json`；
5. 进入 bash 执行 `echo LOCAL_DIRECT_OK`；
6. 停止 runtime 并确认下次 reconcile 可继续。

**字段级理想结果**

- `runtime-lease.json` 每 15 秒左右刷新；
- bash 输出精确为 `LOCAL_DIRECT_OK`；
- 本地日志中不出现每 15 秒一次的 lease CLI spawn；
- 停止后无 fresh lease 阻塞下次启动。

**异常判定**

- 本地 direct-write 改成高频 CLI spawn → 记为性能回归，不合并；
- fresh lease 残留 → fail；
- bash/PTY 行为本批不得回归。
## b4：顶部状态栏拖拽边界 + F3 方案裁决

### b4-T1：顶部状态栏不再参与上下拖拽

**前置准备**

- 分支 `2.1.15-b4-ui-history-model` 已构建并启动 debug Workbench；
- 至少打开一个 workspace；
- TabBar 中存在 bash / codex / claude 至少两类标签；
- 记录窗口尺寸、UI 字号、构建号。

**精确操作步骤**

1. 将鼠标移到顶部 bash/codex/claude 状态栏及其底部边缘；
2. 按住左键从状态栏区域内垂直拖动 20–40 px；
3. 从状态栏底部边缘垂直拖动 20–40 px；
4. 释放后切换到另一个 tab；
5. 关闭 Workbench，重新打开同一 workspace。

**字段级理想结果**

- 步骤 2/3 中光标不出现 `row-resize`；
- TabBar 高度无变化；
- 终端区域顶边不被推开；
- 重启后 TabBar 仍为自然高度，旧 `panel-layout` 中的 `tabbarHeight` 不生效；
- 切 tab 后仍无高度漂移。

**异常判定**

- 任一路径出现状态栏高度变化或 `row-resize` → fail；
- 状态栏与终端之间无边框 → fail。

### b4-T2：侧边栏与分屏边界回归

**前置准备**

- 与 b4-T1 同一 Workbench 实例；
- Explorer 未折叠；
- 当前 workspace 至少一个终端 tab。

**精确操作步骤**

1. 拖动 Explorer 右侧 handle 左右移动；
2. 双击该 handle；
3. 重新展开 Explorer；
4. 在终端内 split 出两个 pane；
5. 拖动 pane 间 divider；
6. 切换 tab 后回到 split tab；重启 Workbench 后重新打开同一 workspace，确认按 O9 r2 进入全新单 Bash tab。

**字段级理想结果**

- Explorer handle 拖动有效，panel 宽度被限制在 240–600 px 的既有区间（可见 dock 含 40 px rail，为 280–640 px）；
- 双击折叠、rail 展开恢复正常；
- pane divider 拖动改变分屏比例；
- tab 切换时 split pane 数量、比例与焦点无本批新增回归；重启后按 O9 r2 恒为全新单 Bash tab，不要求自动恢复布局。

**异常判定**

- Explorer 拖拽失效 → fail；
- pane divider 拖拽失效 → fail；
- 同一 Workbench 进程内的 tab 切换导致会话重开或输出丢失 → fail；按 O9 r2 重开 workspace 后的全新单 Bash 不判 fail。

### b4-T3：F3 方案裁决项

**前置准备**

- 阅读 `docs/plans/2.1.15-dev-plans/b4-ui-history-model.md` 的 F3 推荐方案与 8 个开放裁决点。

**精确操作步骤**

1. 逐项确认 Work Record 粒度、自动分组、bash/cc-switch、flat 视图、删除语义、runtime provenance、归档可见性、实施顺序。

**理想结果**

- 每项均有用户明确裁决；
- 裁决记录写入 `decisions.md` 后才允许实施对应代码。

**异常判定**

- 缺任一裁决即实施 F3 代码 → 违反 D-2，不合并。

## b6：Work Record / Collection

### 2026-10-13 缺陷修复复测执行记录

**环境**

- 分支：`2.1.15-b6-work-record-collection`，修复基线 `5124839`，修复提交 `afe1f83`，新 tab 身份关联提交 `a71b16f`。
- 本地 debug Workbench，Vite 源刷新后连接 `http://localhost:9222`。
- 工作区：`E:\pt\b6-manual`，隔离 provider transcript fixture。

**本轮实测**

| 项 | 结果 | 证据 |
| --- | --- | --- |
| Work Records 刷新双通道 | PASS | UI 打开后新增 `b6 refresh fixture` transcript，点击 Work Records「刷新」后未切换视图，unfiled 立即显示该 fixture。 |
| T3 移出成员后 unfiled 立即恢复 | PASS | `b6-manual` 中 `init` 成功移出；未手动刷新时该会话立即出现在未归档会话，成员列表清空。 |
| 新开 provider tab 身份关联 | PASS（单测） | `a71b16f` 记录 provider conversation 快照；唯一新增且唯一 pending live tab 时才建立当前 Workbench 会话内关联，歧义时不关联、不关闭。已覆盖唯一关联与歧义拒绝。 |
| T6 删除运行中成员 | PASS | Codex 配置可用后，目标成员 `5f3c9a72-1b64-4f8e-9a20-6d7c8e91b234` 恢复为真实 running session；用户确认后点击删除并通过原生确认框确认。目标 session 先变为 `user_close`/exited（不再 live），Collection 消失；刷新后目标 Codex transcript 与 Claude fixture `847f9a08-781e-45a7-8c75-a2874ec0c50c` 均不再出现在 All Sessions；无 delete failures。未匹配身份的无关 Codex live tab 保持运行。 |

**缺陷修复范围**

- Collection 删除前按成员 `conversation_id` 匹配 `resumeConversationId`，await 匹配 live pane 的 `close_session()` 后再调用物理级联删除。
- 新开 Claude/Codex tab 在 open session 前记录 provider conversation 快照；Work Records mount、refresh、delete 时尝试保守关联。该关联只保存在当前 Workbench 会话内存中，不持久化、不修改 transcript，也不使用 `runtime_id` 判定身份。
- Work Records 刷新同时刷新 ledger 和 provider conversations。
- 成员移出成功后立即 reload ledger，恢复 unfiled。

**当前边界**

- `a71b16f` 补充了无 `resumeConversationId` 时的保守身份关联：仅在同一 agent 恰好一个 pending live tab 且 conversation 快照恰好新增一个时关联；任何歧义都不关联、不关闭。不得用 agent 或 `runtime_id` 批量关闭。
- T6 已在 Codex 配置可用后用真实 running session 完成实机删除验证；未匹配身份的 live tab 未被批量关闭。

## b7：会话退出自动关闭标签（2026-10-14 追加）

### T1：process_exit 自退直接关闭标签

**前置准备**

- 本地 debug Workbench（develop ≥ `ecddb2d`，或本分支构建）；
- 工作区可用，runtime 正常启动。

**精确操作步骤**

1. 打开一个 bash 标签，在其中执行 `exit`；
2. 观察标签行为；
3. 新开一个 codex 标签（已配置 provider），执行 `/quit` 退出；
4. 观察标签行为；
5. 开一个 bash 标签并 split 出第二个 pane，在其中一个 pane 里 `exit`；
6. 观察标签与另一 pane；
7. 回归 b6：Work Records 中删除一个 running 成员，观察其标签与会话。

**理想结果**

- 步骤 2/4：对应标签直接消失，不出现 `[Session exited...]` 横幅残留；
  焦点迁移到相邻标签；
- 步骤 6：仅退出的 pane 消失，split 与另一 pane 保留；
- 步骤 7：成员会话终止、collection 移除，对应标签自动关闭，无误伤
  （b6 T6 语义不回退）。

**异常判定**

- 任一自退标签残留 exited 横幅 → fail；
- split 中退出一个 pane 导致整个标签或无辜 pane 关闭 → fail；
- `transport_error`（如杀掉 serve）应保留标签进入 disconnected 展示，
  若直接关闭标签 → fail（此为诊断通道）。

### 2026-10-14 T1 实测执行记录

**环境**

- 分支：develop `a0f28a6`（含 b7 修复提交 `ecddb2d`）；
- 本地 debug Workbench（`npm run tauri dev` + WebView2 CDP 127.0.0.1:9222）；
- 工作区：`E:\pt\b6-manual`，runtime 镜像复用；
- 原生确认框经 Win32 消息确认（插件对话框无法由 CDP 驱动）。

**本轮实测**

| 项 | 结果 | 证据 |
| --- | --- | --- |
| T1a bash `exit` 自退 | PASS | 单 bash 标签内执行 `exit` → 标签直接消失，无 exited 横幅残留，回到「没有打开的标签」空态。 |
| T1b codex `/quit` 自退 | PASS | codex 标签执行 `/quit` → 会话 exit 上报（stream 证据 `agent=codex exit_code=1`）→ 标签自动关闭；旁侧 bash 标签不受影响。 |
| T1c split 单 pane 退出 | PASS | bash 标签左右分屏（2 pane）后退出其一 → 该 pane 移除，标签与另一 pane 保留，无 dormant leaf。 |
| T1d b6 级联回归 | PASS | 恢复 collection 成员为 live 后删除 collection：`closeLiveConversationSessions` 关闭 live 成员 → user_close Exit → 标签自动关闭；无关 bash 标签未误伤；transcript 删除失败的成员（WinError 5 文件占用）由 b6 部分失败 UI 显式列出。 |

**异常记录**

- 无。`transport_error` 保留标签行为由单测覆盖（paneRuntime 套件 b7 用例），本轮未做实机断链。


## b8：Work Records UI 树状重构与历史合并（2026-10-14 追加）

### T7：历史并入、树状展示、符号化与右键操作

**前置准备**

- 本地 debug Workbench（分支 `2.1.15-b8-work-records-ui-tree`）；
- 工作区 runtime 正常，`explorer.conversations` 中至少有：一个 Codex parent session 及其 child/subagent session；一个已配置 Claude session；
- 保留一个可安全删除的测试 transcript，不使用重要工作会话。

**精确操作步骤**

1. 检查左侧 activity rail 与命令面板：确认没有独立「历史」入口；
2. 打开 Work Records → 点击「全部会话」，确认列表仍在 Work Records 模块内渲染；
3. 在「全部会话」搜索 parent / child / Claude 标题；
4. 观察同一 agent 下 parent/child 展示：默认只展开 parent 节点，child 折叠；点击 parent 的展开符后 child 可见；
5. 对同一条会话分别尝试：左键恢复、只读查看图标、右键菜单（查看 / 恢复 / 重命名 / 分支 / 删除）；
6. 对 Claude 会话执行右键 → 分支；确认新建 tab，源 transcript 不被续写，列表出现新会话；
7. 对 Codex 会话打开右键；确认「分支」禁用并能看到「Codex CLI 暂不支持 fork」原因；
8. 重命名一条测试会话后刷新；确认标题持久；
9. 删除一条测试会话；确认原生确认后从「全部会话」消失；
10. 回归 b6：新建/恢复一条会话加入 Work Record，再删除 collection，确认对应 live tab 自动关闭且无 delete failure。

**理想结果**

- 步骤 1：侧边栏、命令面板均无 History/conversations 模块入口；
- 步骤 2：「全部会话」是 Work Records 内部视图，不再切换到旧 tab；
- 步骤 3：搜索能命中 child；即使 parent 标题不匹配，child 也保留在 parent 路径下；
- 步骤 4：Codex child 只出现在 parent 下，默认折叠；孤儿 child 平铺兜底；
- 步骤 5：恢复/删除/重命名/查看能力全部保留；菜单项语义正确；
- 步骤 6：Claude fork 新建独立会话；source transcript 不增长；
- 步骤 7：Codex fork 明确禁用且有原因，不禁用整个菜单；
- 步骤 8/9：重命名与删除后列表立即刷新；
- 步骤 10：b6 T6 级联删除与 b7 自动关 tab 不回退。

**异常判定**

- child 作为独立顶层重复显示 → fail；
- 「全部会话」跳回旧历史 tab 或丢失搜索/重命名/删除/恢复/只读查看 → fail；
- Codex fork 可点击或 Claude fork 续写源 transcript → fail；
- Work Record 成员树把 child 放到 parent 外或删除时丢失成员 → fail。

### 2026-10-14 T7 实测执行记录

**环境**

- 分支：`2.1.15-b8-work-records-ui-tree`（R0+R3 后端 `da5e80a` + b8 实施工作区）；
- 本地 debug Workbench（`npm run tauri dev` + WebView2 CDP `127.0.0.1:9222`）；
- 工作区：`E:\pt\b6-manual`；dev CLI 临时 pin 到当前源码
  `.venv\Scripts\aisc.exe`，避免 10/13 旧 sidecar 掩盖 R0 字段；
- Codex fixture：parent `01a1384e-819d-75c0-a6c5-e7c12d9a45b0` /
  child `01a1384e-94b7-7012-8cd2-f1afa3dfbc76`。

**实机结果**

| 项 | 结果 | 证据 |
| --- | --- | --- |
| 历史入口移除 | PASS | activity rail 只有文件 / 工作记录 / 变更 / 服务 / 网络与用量 / 设置；命令面板视图组无 History/conversations 入口。 |
| 「全部会话」内嵌 Work Records | PASS | Work Records 顶部切换 `work-records-tab` / `all-sessions`；会话列表保留在 Work Records 面板内，无旧 tab 切换。 |
| Codex 子代理默认折叠 | PASS（修复后） | 初测发现 IPC 丢 `parent_thread_id`：Rust wire struct 未声明该字段，serde 丢弃后 child 提升为 root。补 Rust `ConversationSummary.parent_thread_id` 后，parent 带 `1` 折叠符，child 默认不可见；展开后 child depth 缩进为 20px。 |
| 搜索 child 保留祖先 | PASS（修复后） | 初测搜索先扁平过滤导致 parent 不在列表中；将过滤交给 tree builder 后，搜索 `CHILD_OK` 同时显示 parent（6px）与 child（20px）。已补组件回归测试。 |
| 右键菜单 | PASS | Codex 会话菜单显示查看 / 恢复 / 重命名 / 分支 / 删除；Codex「分支」禁用，tooltip 为「Codex CLI 暂不支持 fork」。 |
| 只读查看 | PASS | 「👁」与右键查看均打开只读回放，显示消息范围和「输入请恢复会话」，可关闭。 |
| 重命名 | PASS | 右键重命名 fixture 为 `b8 rename test`；刷新后 UI 与 CLI 列表均持久。测后已恢复原名。 |
| Claude fork | 受限 | 当前工作区无 Claude provider / transcript，未做实机 fork；全链路（前端 IPC / Rust validation / Python wrapper / CLI）由单测覆盖。 |
| 左键恢复 Codex fixture | 受限 | preflight PASS 且 store 返回创建 tab，但 Codex provider 会话立即退出，b7 的 process_exit 自动关 tab 使 tab 不残留；无法在本轮维持 live tab。恢复/查看能力未丢失。 |
| 删除会话 | 受限 | 右键删除能打开原生「删除历史对话」确认；自动化驱动确认键在该 Tauri 对话框上不可靠，fixture 文件同时被进程占用（WinError 5）。删除 IPC / store 刷新 / Rust & Python 删除链路由单测覆盖，未记 PASS。 |
| Work Record 临时创建 / 符号化 | PASS | 新建 `b8 regression` 后操作展示为 ✎ / ◎ / 🗄 / ✕，未归档会话加入为 ＋；测后临时 collection 已删除。 |
| b6/b7 回归 | 单测 PASS | T6 级联删除与 b7 自动关 tab 已有既有实机记录；本轮新增成员树折叠与 runtime tab 单测通过。因 Codex fixture 无法维持 live，未重复 T6 实机删除。 |

**缺陷修复范围**

- Rust `conversation::ConversationSummary` 增加 `parent_thread_id`，防止
  CLI→IPC 反序列化丢弃父子链；新增 wire 反序列化测试。
- ConversationsPane 不再先按搜索扁平过滤，再交给 tree builder；搜索使用
  全量会话，让 child 命中保留 ancestor 路径；新增 All Sessions 搜索测试。

**门禁**

- Python：1350 tests OK，62 skipped（输出含既有 AGGREGATE/演示 FAIL 文本，进程 exit 0）。
- Frontend：`npm run build` PASS；`npx vitest run` 74 files / 565 tests PASS。
- Rust：`cargo test -p workbench --lib` 347 passed / 1 ignored。
- `git diff --check` PASS。
