# v2.1.15 b4：顶部状态栏拖拽边界 + 历史/工作记录模型调研

> For agentic workers: 本文件是 b4 批次计划与执行记录。F1 是实施项，按分支先行、
> TDD、本地门禁、远程 CI 与实机手测闭环；F3 是调研项，遵守 decisions.md D-2，
> 只产出数据模型、映射、迁移与展示方案，不实施数据迁移或 UI 重构，方案交用户裁决。

## 目标

1. **F1（实施）**：顶部 bash/codex/claude 状态栏不再参与上下拖动；只保留
   Explorer 侧边栏拖拽和终端 PaneTree 分屏边界拖拽。
2. **F3（调研）**：基于 v2.1.13 已落地的 worklog 数据层与 v2.1.8 conversation
   薄读层，梳理「AISC 工作记录 ↔ runtime 子记忆空间 ↔ CLI resume 会话」的
   身份、生命周期、展示和兼容方案；列出开放裁决点。

## 范围与裁决依据

- D-1：F1/F3 属于 v2.1.15 反馈计划。
- D-2：历史/工作记录模型必须先调研出数据模型与迁移方案；未经裁决不得实施。
- 分支：`2.1.15-b4-ui-history-model`。
- Out of scope：F3 的 Workbench/CLI 行为改造、历史数据迁移、runtime_id 回填、
  聊天视图输入、provider transcript 写入。

---

## F1：顶部状态栏拖拽边界

### 现象与代码证据

反馈 F1：顶部 bash/codex/claude 状态栏不应支持上下拖动。

当前 `workbench/src/features/workspace/WorkspaceView.vue` 在 TabBar 下方渲染
`.tab-divider`，该元素带：

- `role="separator"` / `tabindex="0"`；
- `@pointerdown="onTabDividerDown"`；
- `@keydown="onTabDividerKey"`；
- `cursor: row-resize` 与 6px 可命中共。

`onTabDividerDown` 会以 `clientY` 差值调用 `panelLayout.setTabbarHeight`。
因此整个顶部 TabBar 下的分隔条会把状态栏变成上下 resize 热区，且旧拖拽高度
还会持久化到 `aisc-wb-panel-layout-v1`。

### 修复方向

1. 移除 `.tab-divider` 的 pointer / keyboard / separator 交互；
2. 将其退化为纯视觉边框，或直接并入 TabBar 底边框；
3. 删除 TabBar 高度状态、setter、样式绑定和旧持久化消费；旧 localStorage 里的
   `tabbarHeight` 读取后直接忽略，下次持久化自然消失；
4. 保留 `dock-handle`（Explorer 左右拖拽）和 PaneTree split divider（分屏拖拽）；
5. 更新既有 source contracts 与 i18n，避免保留误导性的 tabbar resize 标签。

### F1 验收

- 顶部状态栏与底部视觉边框不可拖拽，键盘 Tab 停留也不再呈现 separator；
- Explorer dock handle 可左右拖，PaneTree 分屏 divider 可拖；
- 重启 Workbench 后 TabBar 保持自然高度；
- 切 tab、已有 split pane、多 workspace 不回归；
- vitest / vue-tsc / 本地全门禁 / 远程 CI 全绿。

---

## F3：历史/工作记录模型调研

### 现有数据层盘点

#### 1. Workbench 工作区历史

类型入口：`workbench/src/types/index.ts`。

- `WorkbenchHistory` 是跨工作区启动历史，不是工作记录聚合；
- `WorkspaceRecord` 以 `path` 为身份，保存最近使用、pinned、最后 agent、
  `RuntimeRef` 和 UI `Layout`；
- `RuntimeRef` 只有 `runtime_id/image/network/scope`，用于恢复便利；
- `Layout` 只恢复 tab 结构，不保存 runtime session id 或 provider conversation id。

#### 2. runtime 子记忆空间

- runtime 容器是执行生命周期；`runtime_id` 只标识容器/运行实例，不是历史身份；
- 项目态 workspace 的 host data root 位于
  `workspaces/<workspace_hash>/`，并把 provider 记忆目录挂进容器：
  - `claude/projects/`：Claude transcript；
  - `codex/sessions/`：Codex rollout transcript；
  - `runtime/`：AISC 自有小状态（conversation titles、worklogs）。
- 因此 runtime 关闭、重启或删除后，持久记忆仍在 host data root；temporary
  scope 没有 data-root 持久承诺。

#### 3. CLI 原生 resume 会话

类型入口：`ConversationSummary`；实现入口：
`src/aisc/application/conversation.py`。

- 一文件 = 一个 provider conversation；
- `conversation_id` 来自文件名，是 provider 原生身份；
- CLI 提供只读 list/read/preflight/rename/delete；
- resume 走 Workbench 两步：`conversation_preflight` →
  `open_session(..., resume_conversation_id)`；
- Workbench live tab 有临时 `resumeConversationId`，用于 `findLiveResumeTab`
  防重复 resume，但它不进入工作区持久历史。

#### 4. AISC worklog 账本（关键既有资产）

v2.1.13 `history-worklog` 批 1/2 已落地：

- 存储：`<workspace data root>/runtime/worklogs.json`；
- schema：`aisc.worklog/v1`；
- worklog 节点：`worklog_id/title/created_at/last_opened_at/state/sessions[]`；
- session 条目：`terminal_session_id/agent/conversation_id/
  resume_of_conversation_id/opened_at/closed_at/exit_code/inferred`；
- 写入时机：`build_session_exec` 开启 PTY 会话时新增 worklog；
  `terminate_session` 关闭对应 session；
- `aisc worklog reconcile` 会把未关联 provider transcript 收容进
  「未归档会话」；
- CLI 已有 list/rename/archive/delete/reconcile；
- 账本只保存 provider transcript 引用，不写 provider transcript；
- 失败策略 fail-open：账本异常不阻塞会话开/关。

当前缺口：Workbench 前端没有消费 worklog；历史入口仍主要展示
`ConversationSummary` 扁平列表。批 3 的「工作记录 / 全部会话」分段、CRUD、
拖挂/解挂、存量收编 UI 未实施。

### 推荐身份模型

```text
Workspace identity
  = path_identity_key(workspace path)
    -> host data root: workspaces/<workspace_hash>/
       -> runtime/worklogs.json      # AISC Work Record 聚合层
          worklog_id                 # Work Record ID
             sessions[]
               terminal_session_id   # 临时 PTY 生命周期，弱引用
               agent
               conversation_id       # provider transcript，弱引用
               resume_of_conversation_id
       -> claude/projects/**/*.jsonl # provider 原生会话本体
       -> codex/sessions/**/*.jsonl  # provider 原生会话本体
```

原则：

1. **Work Record 是 AISC 聚合身份，不是 runtime 身份**；
2. `runtime_id` 只能作为 provenance，不能作为 Work Record 主键；
3. `terminal_session_id` 与 `conversation_id` 都是弱引用；引用消失时 Work Record
   仍可显示状态级条目；
4. provider transcript 仍由 provider/CLI 薄读层所有，Work Record 不复制正文；
5. runtime 重启不改变 Work Record；容器删除也不应删除 Work Record 或 transcript。

### 生命周期

| 事件 | Work Record 行为 |
| --- | --- |
| 打开 PTY agent/bash 会话 | worklog 钩子新增 session 条目；agent 会话可带 resume_of |
| resume 已有 conversation | session 记录 `resume_of_conversation_id`；provider 通常续写原 transcript |
| provider 新建 conversation | 先只有临时 PTY session 条目；后续 reconcile 补 `conversation_id` |
| runtime 停止 / 重启 | Work Record 不变；session 只按已知关闭时机更新 |
| runtime / container 删除 | Work Record 与 provider transcript 保留在 host data root |
| transcript 被外部删除 | UI 降级为“引用缺失/不可 resume”，不自动删 Work Record |
| worklog 文件损坏 | 沿用 fail-open：隔离损坏文件并显示空/降级状态 |

### 推荐展示模型

历史页按两层聚合，workspace 边界不跨：

```text
Workspace
  └─ Work Record（active / archived）
       └─ Session / Conversation 条目
            ├─ agent + 时间
            ├─ terminal session 状态
            ├─ conversation 状态：可查看 / 可 resume / 缺失 / 超限 / malformed
            └─ 操作：查看、resume、改名、归档、删除引用或记录
```

- 主视图：工作记录；
- 保留现有 `ConversationSummary` 扁平视图作为「全部会话」过渡；
- 批 3 原计划与当前反馈一致：先并存，手测通过后再由用户裁决 flat 视图下线。

### 候选方案

#### A. 最小接入：消费既有 worklog（推荐）

- Rust IPC 暴露 `aisc worklog list/rename/archive/delete/reconcile`；
- Workbench 增加 worklog 类型和分组视图；
- 列表加载时或用户显式刷新时触发 reconcile；
- 不改 `aisc.worklog/v1` schema，不迁移数据；
- 旧 provider conversation 继续可从 flat 视图访问；
- 未关联项先进入「未归档会话」，后续可人工整理。

优点：复用已验收数据层，风险最小，符合 D-2。
缺点：自动分组的语义仍可能产生一个大的「未归档会话」。

#### B. Schema v2：显式任务/项目聚合

- worklog v2 增加显式父子关系、标签、runtime provenance、排序和引用状态；
- 支持 move/link/unlink、自动分组合并、删除级联确认；
- 需要 v1 → v2 迁移、锁/并发和冲突处理。

优点：长期模型更完整。
缺点：迁移面大，应等 A 方案 UI 和用户语义裁决后再做。

#### C. CLI/provider 层合并历史

- 修改或替代 provider transcript 结构，把多会话合并成一个任务流。

优点：概念上与 provider 历史一致。
缺点：违反 provider transcript 只读边界，破坏 resume、升级兼容与外部 CLI 行为，
不建议。

### 兼容与迁移策略

推荐 A 方案的零迁移路径：

1. 首次打开工作记录视图时调用 reconcile，把历史 transcript 收容到
   「未归档会话」；
2. 老 worklog/v1 原样读取；缺失字段按当前 fail-open 语义补默认；
3. 不移动、重写或重命名 provider JSONL；
4. flat conversation list 继续保留；
5. worklog 缺失或损坏时不阻塞 conversation list 和 resume；
6. 后续如果采纳 B，再引入 `aisc.worklog/v2` 与只增迁移，不把该责任塞进 A。

### 开放裁决点

1. **Work Record 粒度**：沿用当前“一次 PTY 会话 = 一个 Work Record”，还是
   批 3 增加人工合并后按“任务/项目”聚合？
2. **自动分组**：是否允许按时间窗把新建 provider conversation 自动并入打开时
   的 Work Record？还是只做 reconcile 到「未归档会话」+ 人工拖挂？
3. **bash / cc-switch**：是否在 Work Record 视图显示状态级 bash/cc-switch 条目？
4. **flat 视图**：「全部会话」是否长期保留？批 3 手测通过后是否下线？
5. **删除语义**：删除 Work Record 是否只删聚合记录？删除 conversation 是否仍
   保持现有 provider transcript 文件删除确认？
6. **runtime provenance**：是否值得为 Work Record session 增加 `runtime_id`
   可选字段？推荐仅作 provenance，不做身份。
7. **归档可见性**：archived Work Record 默认隐藏、折叠还是同列表展示？
8. **实施顺序**：是否下一批先做 A（IPC + 分段只读列表），把拖挂/合并留到
   之后的 B/UI 批？

---

## F1 实施任务

### Task 1：先写失败测试

- 修改：`workbench/src/features/workspace/__tests__/panelLayout.test.ts`；
- 修改：`workbench/src/lib/__tests__/panelLayout.test.ts`；
- 断言 `WorkspaceView.vue` 不存在 `onTabDividerDown/onTabDividerKey`；
- 断言 `.tab-divider` 不再有 pointerdown/keydown/tabindex/role separator；
- 断言 `panelLayout.ts` 不再暴露或消费 `tabbarHeight/setTabbarHeight`；
- 保留 dock handle 交互与 PaneTree divider 的既有测试。

### Task 2：实现最小修复

- 修改：`workbench/src/features/workspace/WorkspaceView.vue`；
- 修改：`workbench/src/lib/panelLayout.ts`；
- 修改相关 i18n key；
- `.tab-divider` 只保留视觉边界；
- 不改 TabBar 本体、终端 PaneTree 和 Explorer dock 行为。

### Task 3：自动化验证

```powershell
. scripts/dev-env.ps1
cd workbench
npx vitest run
npx vue-tsc --noEmit
cd ..
powershell -ExecutionPolicy Bypass -File scripts/local-gates.ps1
```

### Task 4：实机手测

见 `HANDTEST.md` b4 节；通过后再提交/推送并走 PR CI。

---

## 执行状态

- [x] F1 根因定位：TabBar 下方 `.tab-divider` 是可交互 resize 边界。
- [x] F3 现有模型盘点：Workbench history、runtime data root、conversation、
  worklog v1 已梳理；确认 Workbench 尚未消费 worklog。
- [x] F3 推荐 A 方案与开放裁决点已入档。
- [x] F1 红灯测试：修改目标测试后先见 2 files / 6 failed / 15 passed。
- [x] F1 实现：移除 `.tab-divider` 及 TabBar 高度状态；保留 Explorer handle 和
  PaneTree divider。
- [x] F1 自动化门禁（2026-10-13）：`LOCAL GATES: ALL GREEN`；Python 1357 passed /
  53 skipped；Vitest 71 files / 536 tests；目标测试 3 files / 28 tests；
  `vue-tsc --noEmit` 通过。
- [x] F1 实机手测（2026-10-13，debug Workbench，CDP 真实鼠标事件；窗口
  1037x638、zoom 1）：Bash+Codex 双 tab 下状态栏内部与底边上下拖 20–40 px 后
  `.tabbar` 高度/位置均保持 39 px/28 px；无 `row-resize`，`.tab-divider` 不存在；
  切 tab 后不漂移；重启后旧 `tabbarHeight` 为 null 且仍自然高度。
- [x] b4-T2 实机手测：Explorer panel 拖动被夹在 240–600 px（可见 dock 含 40 px
  rail 为 280–640 px）；双击折叠/rail 展开恢复；左右分屏后 divider 拖动
  first pane 宽度变化约 -79 px，键盘微调 +29 px；同进程切 tab 无新增回归。
  进程重启重开 workspace 按 O9 r2 进入全新单 Bash；HANDTEST 已同步该既有裁决，
  不把自动恢复布局列为 b4 门禁。
- [ ] PR CI 全绿并 ff-only 合回 develop。
- [ ] README / todo 账本收口。
