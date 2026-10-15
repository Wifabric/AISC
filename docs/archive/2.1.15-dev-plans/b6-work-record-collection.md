# v2.1.15 b6：Work Record / Collection 完整语义实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 provider conversation 之上新增轻量 Work Record / Collection 层，完整落地自动收容、手动整理、归档可见性与物理级联删除语义。

**Architecture:** provider transcript 与现有 CLI 薄读层保持原生资产不变；AISC 新增单 workspace 的 `work-collections.json` 聚合账本。CLI 负责数据一致性和 provider transcript 删除编排，Rust/Tauri 只做 target-aware pass-through IPC，前端提供 Work Records 与 All Sessions 并存视图。

**Tech Stack:** Python CLI / application layer、Rust Tauri command pass-through、Vue 3 Pinia store、Vitest / vue-tsc / pytest。

---

## 当前状态

- 已实施并 ff-only 合入 `develop`：PR [#9](https://github.com/Wifabric/AISC/pull/9)，合并 HEAD `dd0dfa8`。
- 本地门禁、PR CI、develop CI 与实机手测记录见 `HANDTEST.md`。

## 目标

1. Work Record / Collection 采用「会话记录 + 轻量集合层」：一次 provider
   conversation 仍是一条底层记录，Collection 只聚合成员关系与元数据。
2. active Collection 可自动收容新建 provider conversation；用户可手动加入、
   移出和移动成员。
3. Collection 支持 active / archived；archived 默认隐藏，可显式显示和恢复。
4. 删除 Collection 时普通确认后直接级联删除成员 provider transcript；失败必须
   明确提示，不得静默。
5. Work Record 视图与现有「全部会话」flat 视图并存；`bash` / `cc-switch`
   不进入 Work Record。

## 用户裁决记录（D-3 摘要）

| 裁决点 | 结论 |
| --- | --- |
| 粒度 | C：会话记录 + 轻量集合层；不合并 provider transcript |
| 进入集合 | B：active Collection 自动收容新建 provider conversation，不按时间窗猜测；可手动调整 |
| bash / cc-switch | A：不进入 Work Record 视图，继续留在全局 session 历史 |
| flat 视图 | B：过渡期保留「全部会话」，不隐藏、不迁移旧数据 |
| 删除确认 | C：级联删除成员，普通确认即可；不输入名称、不逐项勾选、不二次强确认 |
| 删除范围/失败 | A + D：先终止运行中 provider session，再物理级联删除；删不干净必须提示失败项 |
| runtime provenance | B：member 增加可选 `runtime_id`，仅溯源，不做身份、合并、去重、恢复或运行时绑定 |
| 实施范围 | C：完整语义一次做完，不做只读最小版 |

## 非目标

- 不迁移、不改写、不重命名 provider JSONL；除用户裁定的删除路径外不修改其内容。
- 不迁移现有 `worklogs.json`，不引入 `aisc.worklog/v2`。
- 不把 `bash` / `cc-switch` 会话收进 Collection。
- 不跨 workspace 聚合。
- 不长期下线「全部会话」flat 视图；是否下线另行裁决。
- 不用 `runtime_id` 恢复会话、绑定运行时或推断身份。
- 本批次计划提交不实施任何代码、UI、IPC 或数据迁移。

## 现有代码锚点

实施前以这些入口为准；如行号漂移，以符号名为准。

### CLI / Python

- `src/aisc/cli/main.py`
  - `worklog` parser：约 558 起；
  - `_cmd_worklog` dispatch：约 2064 起；
  - top-level dispatch：约 2921 起。
- `src/aisc/cli/commands/worklog.py`
  - `_registry(workspace)` 返回 `<workspace data root>/runtime`；
  - `_ws_dir(workspace)` 返回 workspace data root。
- `src/aisc/application/worklog.py`
  - 存储：`<workspace data root>/runtime/worklogs.json`；
  - schema：`aisc.worklog/v1`；
  - 现有语义：一次 PTY open 一条 worklog，session 引用 provider conversation；
  - `save()` 使用 tmp + `os.replace` 原子写；
  - `load()` 对损坏文件隔离后 fail-open；
  - 不写 provider transcript。
- `src/aisc/application/session.py`
  - `build_session_exec()` 在 PTY 打开时调用 `worklog.record_open`；
  - `terminate_session()` / 会话关闭链路调用 `worklog.record_close`。
- `src/aisc/application/conversation.py`
  - `list_conversations()` 是 provider conversation 唯一列表来源；
  - `delete_conversation()` 已实现精确 conversation 物理删除，并清理 title
    override；
  - transcript 查找按 agent + conversation id。

### Rust / Tauri

- `workbench/src-tauri/src/conversation.rs`
  - `conversation_list / preflight / delete / rename / read` 都是 target-aware
    CLI pass-through；
  - argv builder 是 pure function，已有单测模式；
  - IPC result struct 与 `workbench/src/types/index.ts` 镜像。
- `workbench/src-tauri/src/lib.rs`
  - handler 注册约 139 起。
- `workbench/src-tauri/src/session.rs`
  - Workbench 内运行 session 的 `close_session(session_id)` 已存在；
  - Collection 删除前应优先复用该能力终止本 Workbench 可见的运行中 session。
- `workbench/src-tauri/src/runtime.rs`
  - 有 runtime stop 能力，但 Collection 删除不得把 `runtime_id` 当运行时绑定；
    默认只按 member conversation 对应的 live PTY session 处理。

### 前端

- `workbench/src/types/index.ts`
  - `Agent`；
  - `ConversationSummary`；
  - `ConversationListResult`。
- `workbench/src/lib/ipc.ts`
  - `conversationList / conversationDelete / conversationRename / conversationRead`。
- `workbench/src/stores/workspaceExplorer.ts`
  - `ExplorerKind`；
  - `conversations`；
  - `loadConversations()`；
  - `resumeConversation()`；
  - `renameConversation()`；
  - `deleteConversation()`。
- `workbench/src/features/workspace-explorer/WorkspaceExplorer.vue`
  - 历史/会话列表入口；
  - 现有 agent grouping；
  - resume / rename / delete。
- `workbench/src/features/history/ConversationViewer.vue`
  - 只读 conversation viewer，应被 Collection 成员复用。
- 既有测试：
  - `tests/test_worklog.py`；
  - `tests/test_conversation.py`；
  - `workbench/src/features/workspace-explorer/__tests__/conversationsGrouping.test.ts`；
  - `workbench/src/stores/__tests__/workspaceExplorer.test.ts`。

---

## 数据模型草案

新增文件：

```text
<workspace data root>/runtime/work-collections.json
```

Schema：

```json
{
  "schema_version": "aisc.work-collections/v1",
  "active_collection_id": null,
  "observed_provider_keys": [],
  "collections": []
}
```

Collection：

```json
{
  "id": "uuid-v4",
  "title": "用户可读名称",
  "status": "active",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "archived_at": null,
  "members": [
    {
      "member_key": "codex:uuid-v4",
      "agent": "codex",
      "conversation_id": "uuid-v4",
      "runtime_id": null,
      "source": "manual",
      "added_at": "ISO8601"
    }
  ]
}
```

约束：

1. `member_key = "${agent}:${conversation_id.toLowerCase()}"`。
2. `agent` 只允许 `claude | codex`。
3. Collection 不复制 transcript 正文，只保存弱引用。
4. 同一 Collection 内 `member_key` 唯一；同一 provider conversation 可否属于多个
   Collection？**第一版禁止**，避免删除时二义性和 UI 状态重复。
5. `runtime_id` 可为 null；缺失、删除或失效都不影响成员身份。
6. transcript 缺失时成员仍保留，UI 显示「引用缺失/不可 resume」降级状态。
7. `observed_provider_keys` 是自动收容基线，保存最近一次 reconcile 已看到的
   provider conversation keys；不作为用户数据展示。
8. `active_collection_id` 全 workspace 最多一个；可为 null。
9. archived Collection 不参与自动收容。
10. 所有时间使用 UTC ISO8601。

### 「未归档会话」计算

```text
all_provider_conversations =
  aisc conversation list 的 claude + codex 结果

all_member_keys =
  所有 active + archived Collection.members[].member_key

unfiled =
  all_provider_conversations 中 member_key 不在 all_member_keys 的记录
```

- 「未归档会话」是计算结果，不是物理 worklog、不是删除队列。
- `bash` / `cc-switch` 不参与计算。
- transcript 缺失的 member 仍留在 Collection，但不进入 unfiled。
- flat `All Sessions` 继续展示完整 provider conversation list，不做 member 过滤。

### active 自动收容规则

1. 用户创建或选择一个 active Collection 后，它成为 `active_collection_id`。
2. 进入 active 状态时，以当前 provider conversation list 初始化 / 更新
   `observed_provider_keys`；历史未整理会话不倒灌进 active Collection。
3. 后续 reconcile 发现一个 provider key 不在 `observed_provider_keys` 且不属于任何
   Collection 时：
   - 若 `active_collection_id` 存在且目标 Collection 是 active，自动加入；
   - `source = "active_auto"`；
   - 再把 key 加入 `observed_provider_keys`。
4. 已属于任意 Collection 的 provider conversation 不重复加入。
5. resume 已有成员 conversation 时不新增成员；provider 通常续写原 transcript。
6. resume 未收容的历史 conversation 时，它仍是 unfiled；是否手动加入由用户决定。
7. Workbench 进入 Work Records、手动刷新、session 关闭和 conversation list reload 后，
   先调用 reconcile，再读取 Collection 与 provider conversation 列表。
8. reconcile 顺序固定为：scan provider conversations → auto add → refresh
   observed keys → atomic save。
9. 账本损坏时隔离为 `work-collections.corrupt-<timestamp>.json`，返回空账本并
   不阻塞 conversation list / resume；UI 显示降级提示。

---

## 技术分层

### 1. CLI / 数据层

新增 `src/aisc/application/work_collection.py`，不塞进现有 `worklog.py`。

要求：

- 常量：`WORK_COLLECTION_SCHEMA = "aisc.work-collections/v1"`。
- 文件：`collections_path(registry_root) -> Path`。
- 容错：
  - missing → empty document；
  - corrupt → quarantine + empty document + 降级标记；
  - 任何 open hook 失败都 fail-open，不阻塞 PTY / conversation。
- 写入：
  - tmp + `os.replace`；
  - 简短进程内 lock 串行化同进程调用；
  - 跨进程使用 lock 文件 + bounded retry；锁不可用时返回明确冲突错误，
    不做静默 last-writer-wins 覆盖。
- 基础操作：
  - `load()`；
  - `save()`；
  - `list_collections()`；
  - `create()`；
  - `rename()`；
  - `set_active()`；
  - `archive()` / `restore()`；
  - `add_member()` / `remove_member()`；
  - `delete_collection()`；
  - `reconcile()`。
- reconcile 复用 `conversation.list_conversations()`，不重新实现 transcript 扫描。
- 删除复用 `conversation.delete_conversation()`，不直接 unlink provider JSONL。

新增 CLI 子命令 `aisc work-record`：

```bash
aisc work-record list --workspace <ws>
aisc work-record create --workspace <ws> --title <title>
aisc work-record rename --workspace <ws> --id <id> --title <title>
aisc work-record activate --workspace <ws> --id <id>
aisc work-record deactivate --workspace <ws>
aisc work-record archive --workspace <ws> --id <id>
aisc work-record restore --workspace <ws> --id <id>
aisc work-record add --workspace <ws> --id <id> --agent <claude|codex> --conversation-id <uuid> [--runtime-id <uuid>]
aisc work-record remove --workspace <ws> --id <id> --agent <claude|codex> --conversation-id <uuid>
aisc work-record delete --workspace <ws> --id <id>
aisc work-record reconcile --workspace <ws>
```

`list` 返回：

```json
{
  "schema_version": "aisc.work-collections/v1",
  "workspace": "...",
  "active_collection_id": null,
  "collections": [],
  "unfiled": []
}
```

- `collections[].members` 返回 Collection 弱引用；
- 前端负责与 `ConversationSummary` join；
- 若 CLI 侧已有可复用 summary join，可返回 joined model，但不得复制 transcript 正文。

`delete` 返回：

```json
{
  "deleted": true,
  "collection_id": "...",
  "terminated_session_ids": [],
  "deleted_members": [],
  "failed_members": [
    {
      "member_key": "codex:uuid",
      "agent": "codex",
      "conversation_id": "uuid",
      "stage": "terminate|delete",
      "reason": "short reason"
    }
  ]
}
```

### 2. Rust / Tauri IPC 层

新增 `workbench/src-tauri/src/work_record.rs`，沿用 `conversation.rs` 模式。

Commands：

```text
work_record_list
work_record_create
work_record_rename
work_record_activate
work_record_deactivate
work_record_archive
work_record_restore
work_record_add_member
work_record_remove_member
work_record_delete
work_record_reconcile
```

要求：

1. 每个 command 都通过 `resolve_target_for()` 支持 local / remote target。
2. argv builder 是 pure function 并加单测，断言 workspace / id / agent /
   conversation-id / title / format 参数完整。
3. 删除 command 使用较长 bounded timeout，因为可能串行删除多个 transcript。
4. 所有 wire struct 加 `#[serde(default)]`，避免旧 CLI / 新前端或新 CLI / 旧前端
   在字段增补时硬崩。
5. `lib.rs` 注册全部 handler；不把逻辑写进 Rust。

### 3. 前端层

新增 Work Record 状态与视图，不重构现有 conversation store 的 flat 语义。

类型：

```ts
export type WorkRecordMemberSource = "manual" | "active_auto";

export interface WorkRecordMember {
  member_key: string;
  agent: "claude" | "codex";
  conversation_id: string;
  runtime_id: string | null;
  source: WorkRecordMemberSource;
  added_at: string;
}

export interface WorkRecordCollection {
  id: string;
  title: string;
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  members: WorkRecordMember[];
}

export interface WorkRecordListResult {
  schema_version: string;
  active_collection_id: string | null;
  collections: WorkRecordCollection[];
  unfiled: ConversationSummary[];
}

export interface WorkRecordDeleteResult {
  deleted: boolean;
  collection_id: string;
  terminated_session_ids: string[];
  deleted_members: WorkRecordMember[];
  failed_members: WorkRecordDeleteFailure[];
}
```

Store / UI：

- 在 workspace explorer 增加 `work-records` 入口，与现有 `conversations` 并存。
- 顶部或侧栏提供两个稳定视图：
  - `Work Records`；
  - `All Sessions`。
- `All Sessions` 复用现有 flat conversation list、agent grouping、搜索、resume、
  rename、delete，不隐藏、不迁移。
- `Work Records` 默认只显示 active Collection 和 `未归档会话`。
- 提供 `显示已归档` 开关；开启后显示 archived Collection，但 archived 不自动收容。
- Collection 操作：
  - 新建；
  - 改名；
  - archive / restore；
  - set active / clear active；
  - delete。
- 成员操作：
  - 从 unfiled / All Sessions 手动加入指定 Collection；
  - 从 Collection 移出；
  - 在多个 Collection 间移动时按「先 remove 再 add」执行，UI 保证失败时提示，
    不假装已完成移动。
- 点击成员复用现有 `ConversationViewer`；
- resume 复用现有 `conversationPreflight` → tab → `openSession` 链路；
- transcript 缺失时禁用 resume，显示降级状态。
- active Collection 明确标识；新建 provider conversation 自动进入该 Collection。
- 删除确认和失败提示见下节。

---

## 删除语义

### 删除范围

用户确认删除一个 Work Record / Collection 时：

1. Collection 元数据；
2. Collection ↔ member 关系；
3. member 对应 provider conversation 记录引用；
4. member provider transcript 物理文件；
5. conversation title override（由现有 `conversation.delete_conversation()` 一并
   清理）。

不删除：

- `bash` / `cc-switch` 状态级会话；
- 其他 Collection；
- 其他 provider transcript；
- runtime/container 本体；
- `worklogs.json` 历史账本。

### 删除流程

1. 用户点击删除 Work Record。
2. 前端显示普通确认框：
   - 标题：删除工作记录；
   - 正文：Collection 名称、成员数量、「将终止运行中成员会话并永久删除成员
     provider transcript」；
   - 按钮：取消 / 删除。
   - 不要求输入名称，不显示逐项勾选，不二次强确认。
3. 前端先找出本 Workbench 中与成员 conversation 匹配的 live PTY tab/session，
   逐个调用现有 `close_session()`；结果进入 `terminated_session_ids`。
   - 安全匹配依据是 tab 的 `resumeConversationId`；`runtime_id` 不参与匹配。
   - 新开 provider tab 在 `open_session` 前记录该 agent 的 provider
     conversation 快照；Work Records 刷新后，只有当同一 agent 恰好有一个待关联
     live tab、且快照外恰好新增一个 provider conversation 时，才把该 tab 关联到
     新 conversation。出现任何歧义（0 或多个新增、多个待关联 tab、快照失败）
     一律不关联，也不关闭。
   - 该关联只存在于当前 Workbench 会话内存中，用于删除编排；不持久化、不使用
     `runtime_id`，也不改变 provider transcript。
4. 调用 `work_record_delete`。CLI 不用 `runtime_id` 反查或终止 session。
5. CLI 按成员顺序：
   - transcript 已不存在时按“已删除”处理，只移除弱引用，不算失败；
   - transcript 存在时调用 `conversation.delete_conversation()` 物理删除；
   - 单个成员失败不中断整批，继续处理后续成员。
6. 成员删除完成后删除 Collection 元数据和全部成员关系，并清空
   `active_collection_id` 若其指向该 Collection。
7. 返回成功成员与失败成员。
8. 全部成功：UI 显示删除成功并刷新 Work Records / All Sessions。
9. 存在失败：Collection 仍被删除，未删除的 transcript 会回到「未归档会话」；
   UI 明确显示失败成员的 agent、conversation title/id、失败阶段和短原因。
10. 关闭 Collection 时若 active Collection 指向它，`active_collection_id` 置 null。
11. `runtime_id` 只随成员元数据展示溯源；不用于终止决策。

### 错误与降级

| 场景 | 行为 |
| --- | --- |
| 账本 missing | 空列表，可正常创建 |
| 账本 corrupt | 隔离损坏文件，显示空/降级，不阻塞 conversation list |
| transcript 缺失 | Collection member 显示缺失；手动删除该成员只移除弱引用 |
| 自动收容写账本失败 | fail-open，不阻塞 provider session |
| 手动 CRUD 失败 | UI 明确错误，不乐观提交 |
| reconcile 冲突 | bounded retry；仍失败则提示重试 |
| 删除个别 transcript 失败 | 继续删除其他成员；完成后显示失败项 |
| 运行 session 终止失败 | 记录失败；若 transcript 仍因占用无法删除，也进入失败项 |

---

## 自动化测试计划

### Python / 数据层

新增 `tests/test_work_collection.py`，先红灯后实现。

必须覆盖：

1. empty / corrupt / valid document load；
2. atomic save 后可重读；
3. create / rename / activate / deactivate；
4. archive / restore；
5. add member 去重、非法 agent 拒绝、非法 UUID 拒绝；
6. remove member；
7. active Collection 不存在时 reconcile 只刷新 observed keys；
8. active Collection 存在时，新 provider key 自动加入；
9. 基线中已有 / 已收容 key 不重复加入；
10. archived Collection 不自动收容；
11. unfiled 计算排除所有 active + archived member；
12. bash / cc-switch 永不进入 unfiled 或 member；
13. delete 成功时移除 Collection、members，并调用 conversation delete；
14. delete 单个失败时继续处理其他成员，metadata 仍删除，result 包含失败项；
15. active collection 指向被删对象时置 null；
16. `runtime_id` 持久化但仅作为普通字段。

### Python / CLI dispatch

扩展 CLI 测试：

1. `work-record list/create/rename/activate/deactivate/archive/restore/add/remove/delete/reconcile`
   参数解析；
2. JSON envelope 输出；
3. 缺少 workspace / id / title / agent / conversation-id 的 usage error；
4. human 输出可见状态和失败项。

### Rust / IPC

新增 `workbench/src-tauri/src/work_record.rs` 单测：

1. 每个argv builder 的完整参数顺序；
2. delete argv 不携带 prompt/force 类参数；
3. wire struct 能容忍缺省字段；
4. envelope error 正确转成 `WorkbenchError`。

### 前端

新增 / 扩展：

1. `workbench/src/stores/__tests__/workRecords.test.ts`
   - load / create / rename / archive / restore / activate；
   - add / remove member；
   - unfiled join；
   - delete 成功与 partial failure；
   - workspace 切换清空；
   - fail-open 不影响 conversations。
2. `workbench/src/features/workspace-explorer/__tests__/workRecordsView.test.ts`
   - 默认隐藏 archived；
   - 开关后显示 archived；
   - active 标识；
   - 普通删除确认只出现一次；
   - 确认框包含成员数和永久删除说明；
   - partial failure 列表可见；
   - transcript 缺失时 resume 禁用。
3. 保留并扩展 `conversationsGrouping.test.ts`：
   - `All Sessions` 行为不回归；
   - bash / cc-switch 不出现在 Work Records；
   - Work Record 视图不改变 flat list 数据源。

---

## 实施任务

> 所有 checkbox 保持未勾选；实施时按顺序完成，任何一步失败先修复再前进。

### Task 1：分支与红灯

**Files:**
- Create branch: `2.1.15-b6-work-record-collection`
- Create: `tests/test_work_collection.py`

- [ ] 从最新 `develop` 创建实施分支。
- [ ] 确认 `git status` 无无关 tracked 变更。
- [ ] 写 schema / storage / CRUD / reconcile 的失败测试。
- [ ] 运行 `python -m pytest tests/test_work_collection.py -q`，预期新测试失败。

### Task 2：Collection 数据层

**Files:**
- Create: `src/aisc/application/work_collection.py`
- Modify: `src/aisc/application/conversation.py`（只导出复用，不改 transcript schema）

- [ ] 实现 schema、load / save / atomic write / lock / quarantine。
- [ ] 实现 Collection CRUD、member CRUD、active 状态、archive / restore。
- [ ] 实现 unfiled 计算与 reconcile 自动收容。
- [ ] 运行 `python -m pytest tests/test_work_collection.py -q`，预期 PASS。
- [ ] 运行 `python -m pytest tests/test_worklog.py tests/test_conversation.py -q`，
      预期旧语义 PASS。
- [ ] Commit: `feat(cli): add work collection ledger`。

### Task 3：CLI 命令

**Files:**
- Create: `src/aisc/cli/commands/work_record.py`
- Modify: `src/aisc/cli/main.py`
- Modify: `tests/test_work_collection.py` 或新增 CLI dispatch 测试

- [ ] 先写 CLI parser / dispatch 失败测试。
- [ ] 实现 `aisc work-record` 子命令与 JSON envelope。
- [ ] `delete` 编排 terminate + provider transcript delete + metadata delete。
- [ ] human 输出显示失败成员。
- [ ] 运行目标 pytest，预期 PASS。
- [ ] Commit: `feat(cli): add work record commands`。

### Task 4：Tauri IPC

**Files:**
- Create: `workbench/src-tauri/src/work_record.rs`
- Modify: `workbench/src-tauri/src/lib.rs`

- [ ] 写 argv builder / serde 容错失败测试。
- [ ] 实现 target-aware pass-through commands。
- [ ] 注册 handler。
- [ ] 运行 `cargo fmt --check`、`cargo test`，预期 PASS。
- [ ] Commit: `feat(workbench): add work record ipc`。

### Task 5：前端类型 / IPC / store

**Files:**
- Modify: `workbench/src/types/index.ts`
- Modify: `workbench/src/lib/ipc.ts`
- Create: `workbench/src/stores/workRecords.ts`
- Create or extend: `workbench/src/stores/__tests__/workRecords.test.ts`

- [ ] 先写 store 失败测试。
- [ ] mirror wire types。
- [ ] 实现 IPC wrapper。
- [ ] 实现 load / CRUD / member operations / partial failure state。
- [ ] workspace 切换时清空 Work Record 状态。
- [ ] 运行 `npx vitest run workbench/src/stores/__tests__/workRecords.test.ts`，
      预期 PASS。
- [ ] Commit: `feat(workbench): add work record store`。

### Task 6：Work Records 视图

**Files:**
- Modify: `workbench/src/features/workspace-explorer/WorkspaceExplorer.vue`
- Modify: `workbench/src/stores/workspaceExplorer.ts`（仅接入入口，不改变 flat 语义）
- Create: `workbench/src/features/workspace-explorer/__tests__/workRecordsView.test.ts`
- Modify i18n dictionaries as needed

- [ ] 先写 UI 失败测试。
- [ ] 增加 Work Records / All Sessions 入口。
- [ ] 默认隐藏 archived，提供显示开关。
- [ ] 显示 active 状态、unfiled、成员、缺失 transcript。
- [ ] 接入新建 / 改名 / archive / restore / add / remove。
- [ ] 实现普通删除确认和 partial failure 展示。
- [ ] resume / read 复用现有链路。
- [ ] 补齐中英文 i18n 和 accessibility label。
- [ ] 运行 workspace-explorer 目标测试，预期 PASS。
- [ ] Commit: `feat(workbench): add work record history view`。

### Task 7：全量本地门禁

- [ ] `. scripts/dev-env.ps1`
- [ ] `python -m pytest`
- [ ] `cd workbench && npx vitest run && npx vue-tsc --noEmit`
- [ ] 回到 repo root：`powershell -ExecutionPolicy Bypass -File scripts/local-gates.ps1`
- [ ] 确认输出 `LOCAL GATES: ALL GREEN`。
- [ ] Commit remaining docs/tests if any: `test(workbench): cover work records`。

### Task 8：实机手测与合并

- [x] 启动 debug Workbench。
- [x] 按 b6 手测清单执行；通过后将清单同步到 `HANDTEST.md`。
- [x] 推送分支并创建 PR。
- [x] PR CI 全绿。
- [x] ff-only 合回 `develop`。
- [x] 观察 develop CI 全绿。
- [x] 更新 README / todo / b6 执行状态后，用纯 docs commit 收口。

---

## 实机手测计划草案

实施启动后再同步到 `HANDTEST.md`；本节只是验收范围。

1. **基础视图**
   - 打开 workspace 历史区可见 `Work Records` / `All Sessions`；
   - `All Sessions` 显示既有全部 provider conversation；
   - bash / cc-switch 不出现在 Work Records。
2. **新建与自动收容**
   - 新建 Work Record，设为 active；
   - 当前已有会话不倒灌，出现在 unfiled；
   - 新开 provider conversation 自动进入 active Work Record；
   - resume 已有成员不产生重复成员。
3. **手动整理**
   - 手动加入 unfiled；
   - 移出成员；
   - 移动到另一个 Collection；
   - 刷新后成员关系正确。
4. **归档**
   - archive 后默认不可见；
   - 打开「显示已归档」可见；
   - restore 后恢复 active；
   - archived 期间新 provider conversation 不自动进入。
5. **删除成功**
   - 删除含多个成员的 Collection；
   - 普通确认一次；
   - Collection、成员关系、provider transcript、conversation title override 消失；
   - flat list 刷新后对应 conversation 消失。
6. **删除运行中**
   - Collection 内一个 provider conversation 正在运行；
   - 删除后 session 先终止，transcript 消失，UI 无残留 live tab。
7. **删除失败可见**
   - 构造 transcript 只读 / 占用失败；
   - 可删除成员继续删除；
   - Collection 删除；
   - UI 明确列出失败成员、阶段和原因；
   - 未删除 transcript 出现在 unfiled / All Sessions。
8. **损坏账本**
   - 手工写坏 `work-collections.json`；
   - Workbench 不崩溃；
   - 显示空/降级；
   - provider conversation list 和 resume 仍可用。
9. **远程 target**
   - 对 remote workspace 执行 list / create / add / archive / delete；
   - CLI pass-through 行为与 local 一致；
   - 删除失败提示仍可见。

---

## 执行状态

- [x] Task 1：分支与红灯。
- [x] Task 2：Collection 数据层。
- [x] Task 3：CLI 命令。
- [x] Task 4：Tauri IPC。
- [x] Task 5：前端类型 / IPC / store。
- [x] Task 6：Work Records 视图。
- [x] Task 7：全量本地门禁。
- [x] Task 8：实机手测与合并。
- [x] README / todo 收口：README 已补充 Work Records 使用面与 CLI 参考；仓库无独立 TODO 文件。

> 截止点：本文档入库即停止。不得在本次计划任务中继续实施 Task 1。
