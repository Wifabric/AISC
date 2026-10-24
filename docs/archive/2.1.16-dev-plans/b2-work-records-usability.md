# b2 — Work Records 可用性五项

> 反馈来源：`20261017-工作记录的UI出现使用不方便-Thomas`（反馈 #11，UX/normal）。
> 分支：`2.1.16-b2-work-records-usability`（从 `develop` 切出）。

## 1. 需求映射与现状

| # | 反馈 | 现状 | 方案 |
| --- | --- | --- | --- |
| 1 | 左键打开会话只读预览（富文本渲染，不是恢复） | 行无左键动作；只读 viewer 已存在（`explorer.openConversationViewer` + App 级 `ConversationViewer`，历史页在用） | member/unfiled 行左键直接打开 viewer；右键菜单加「预览」 |
| 2 | 拖动父节点时子节点一起移动 | drag payload 只带单个 member，drop 只搬单个 | payload 携带整个子树（源区顺序）；drop 批量 reorder/move |
| 3 | 「创建会话」「分支会话」对应 CLI /new /fork，操作后立即刷新 | `runtime.createTab(agent)`（新会话）与 `explorer.resumeConversation(c, true)`（fork）已存在，但 Work Records 无入口 | 右键菜单加「创建会话」「分支会话」；动作后 `refreshWorkRecords()` |
| 4 | 「引用缺失」占位不应闪现 | 标题 fallback 立即显示 `workRecords.missing`，会话列表异步加载完成后才变真实标题 | `conversationsLoading` 期间显示加载占位；仅加载完成且查找仍失败才显示「引用缺失」 |
| 5 | 删除会话应级联同名未显示会话 | `deleteConversation` 只删单条 | 删除确认收集同 agent+同标题的全部会话；确认后逐条删除并从所属记录移除，文案显示数量 |

## 2. 设计细节

### 左键预览
- `previewConversation(item)`：有 conversation 才开（缺失引用不可预览）。
- 行 `@click` + `cursor:pointer`；行内按钮已有 `.stop` 不受影响。
- 上下文菜单补「预览」项（与历史页行为一致）。

### 拖父带子
- `DragMemberPayload` 增加 `subtree: { memberKey, agent, conversationId }[]`
  （含被拖节点自身，按源区显示顺序）。
- 子树计算：同一记录树/unfiled 树中，被拖行之后 `depth` 更深且尚未回到
  被拖行深度的连续行集合；环路由现有 visit stack 防护。
- 同区 drop：一次 reorder 移除全部子树键并按序插到目标前。
- 跨区 drop：按子树顺序逐条 `moveMember` / `addMember`；顺序由目标区
  reorder 兜底。store 现有 per-member API 足够，不动 Rust 数据面。

### 创建 / 分支会话
- 菜单项仅对 conversation 存在的行可用；`创建会话` = `runtime.createTab(agent)`
  （等价 CLI /new 的空会话页签），`分支会话` = `resumeConversation(item, true)`
  （等价 /fork，preflight 复用既有链路）。
- 动作完成后 `refreshWorkRecords()`（反馈明确要求立即刷新）。

### 引用缺失闪现
- `memberTitle(memberKey)`：`explorer.conversationsLoading` → 加载占位
  （`explorer.loading` 文案）；非加载且查无 → `workRecords.missing`；
  命中 → 真实标题。仅改展示层，数据面不动。

### 删除级联同名
- `requestConversationDelete(item, collectionId)`：收集
  `explorer.conversations` 中 `agent` 相同且 `title.trim()` 相同的全部会话
  （含 item 自身）。pendingDelete 扩展 `conversations: ConversationSummary[]`。
- 确认文案新键 `workRecords.deleteConversationConfirm`
  （zh：「确定删除「{title}」？将永久删除 {count} 个同名会话（含未显示会话）。」）。
- 确认后：逐条 `explorer.deleteConversation`；对每条会话从其所属的全部记录
  `records.removeMember`；最后 `records.reload()`。
- 级联范围只按「同 agent + 同标题」判定——与反馈「同名会话都要删除」一致；
  不同 agent 的同名（claude/codex 标题撞名）不误删。

## 3. 不做

- 不改 Rust 数据面 / IPC 协议（五项全部可由前端编排现有能力完成）。
- 不把预览做成恢复入口（反馈明确「并不是恢复」）。
- 不改 Work Record 集合删除语义（b6 既有级联保留）。

## 4. 测试

- Vitest（`workRecordsView.test.ts` 追加）：
  1. member/unfiled 行左键打开只读 viewer（store.conversationViewer 断言）。
  2. 父行 dragstart payload 含子树键、顺序稳定。
  3. 右键菜单「创建会话」「分支会话」分别触发 createTab / fork resume，
     且随后刷新（workRecordList 再次调用）。
  4. conversationsLoading 期间不显示「引用缺失」而显示加载占位。
  5. 同名两条会话删除确认显示 count=2，确认后 conversationDelete 两条 id。
- 门禁：`npx vitest run workRecords`、`vue-tsc`（workbench 全量见提交前）。

## 5. 手测（并入 HANDTEST.md b2 节）

见 `HANDTEST.md` T5–T9。

## 6. 执行状态（2026-10-17）

已实施并验证。五项全部落在 WorkRecordsView.vue 展示/编排层 + i18n，未动
Rust 数据面与 IPC 协议。

- **TDD**：`workRecordsView.test.ts` 新增 6 条用例（左键预览 ×2、子树拖拽、
  菜单新建/分支 + 刷新、加载占位、级联删除），先 RED 后 GREEN。
- **门禁**：全量 Vitest 76 files / 605 tests 通过；`vue-tsc --noEmit` 通过。
- 既有 reorder 语义（drop-on-row = 取目标原槽位）在子树批次重写下保持兼容
  （既有 reorder 测试通过）。
