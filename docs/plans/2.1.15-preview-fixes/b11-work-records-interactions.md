# v2.1.15 b11：Work Records 交互与呈现一致性

## 用户裁定（2026-10-14）

1. Codex CLI 内部 /fork 后，新会话要及时进入 Work Records，并按 fork 来源挂到父节点下。
2. Collection 成员行与未归档行使用同一视觉规格；长标题截断，不横向溢出。
3. Collection 成员与未归档成员都支持拖拽排序。
4. 删除 Work Records 的「全部会话」入口；Work Records 只呈现 Collection + 未归档。
5. Collection 与成员重命名均不再常驻输入框；点击重命名后在原名称处进入编辑态。
6. Collection 行内动作与标题同行同高。
7. 会话行左键拖拽可排序，也可拖到其他 Collection / 未归档；右键菜单包含恢复、删除、重命名、移入/移出。
8. Collection 卡片可拖拽排序；顶部第一个 active Collection 默认为 Activate 状态。顶部导航当前运行/恢复的会话若属于某 Collection，则该 Collection 自动切换为 Active。
9. 删除「移入当前 Activate 工作记录」常驻选项，改为拖拽或右键菜单显式选择目标。

## 设计

### 数据层

- `aisc.work-collections/v1` 增加可选 `unfiled_order`（向后兼容，缺失为空）。
- 新增原子操作：
  - `reorder_collections(collection_ids)`
  - `reorder_members(collection_id, member_keys)`
  - `reorder_unfiled(member_keys)`
  - `move_member(from_collection_id, to_collection_id|unfiled, member_key)`
- reorder 请求必须与当前成员集合完全一致，防止并发拖拽造成丢项。
- `unfiled` 输出按 `unfiled_order` 排序；新扫描出的会话追加在既有顺序之后。

### Codex fork 识别

- conversation scan 除 subagent `parent_thread_id` 外，解析
  `session_meta.payload.history_base.thread_id` 作为 fork parent。
- 保留既有 subagent 优先级；两种来源均输出到 `parent_thread_id`，UI 不区分展示。

### 前端

- 移除 Work Records 内嵌 All Sessions tab。
- 抽出统一的 `WorkRecordRow` 行为：树状缩进、长标题 ellipsis、drag payload、
  context menu、inline rename。
- Collection 头部标题/动作同一 flex 行；重命名仅将标题节点替换为 input。
- 未归档区使用同一行组件和卡片化容器。
- HTML5 drag/drop：
  - member drop 到同级行 → reorder；
  - member drop 到其他 Collection → move；
  - member drop 到未归档 → move out；
  - Collection drop 到其他 Collection → collection reorder。
- 右键菜单动作直接复用既有 store/API，删除动作保留确认与级联语义。
- Active 联动：计算顶部导航当前 tab 的 active pane `resumeConversationId`；命中 member
  所属 Collection 时调用 activate。用户手动切换 target 仍由 activate API 写入账本。

## 验收

- Python：reorder/move/fork parser 红绿测试；旧 ledger 缺失 `unfiled_order` 兼容。
- Rust：IPC argv 与 wire struct 测试。
- Frontend：WorkRecordsView 测试覆盖 All Sessions 删除、行规格、inline rename、
  拖拽 reorder/move、右键菜单、active 联动。
- 手测：真实 Codex /fork 后刷新可见父子树；拖拽排序/移动持久；长标题不溢出。

## 执行状态（2026-10-14）

- 数据层：`unfiled_order` / reorder collections / reorder members /
  reorder unfiled / atomic move 已实现；旧 ledger 缺失字段保持兼容。
- Codex fork：`session_meta.payload.history_base.thread_id` 已输出为
  `parent_thread_id`；subagent 优先级保留。
- CLI/Rust IPC：新增 4 个 reorder/move 命令与 argv/wire 测试。
- UI：移除 Work Records 内嵌 All Sessions；Collection/会话 inline rename；
  Collection 卡片与成员/未归档行支持拖拽排序、跨 Collection/未归档移动；
  会话右键菜单支持恢复/删除/重命名/移入/移出；长标题与行样式统一；
  顶部当前 tab 的 resume conversation 自动激活所属 Collection。
- 刷新：conversation scan 数量变化时自动 reconcile Work Records，Codex /fork
  新 rollout 不再依赖手动刷新。
- 验证：Python 1398 passed / 53 skipped；Rust lib 351 passed / 1 ignored；
  Vitest 74 files / 572 tests；vue-tsc、frontend build、`cargo --no-run` 通过。

- PR #15 frontend / cli / rust 全绿；develop Workbench、CLI sidecar、Linux/macOS bundle、
  NSIS 全绿，已 ff-only 合入 `458432c`。
