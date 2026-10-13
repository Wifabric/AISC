# v2.1.15 b8：Work Records UI 树状重构与历史合并

> For agentic workers: 本文件是 b8 批次计划。执行须遵守分支先行、TDD、
> 本地门禁与远程 CI 全绿后并回 develop。R2 fork 语义与 R3 父子链数据
> 先做小调研再实施，调研结论记入本文件执行状态。

## 目标

用户裁定（2026-10-14，收尾前修复批次），Work Records 模块四项 UI 重构：

- R1（反馈 #2）：操作符号化——恢复 / 删除 / 加入等动作改用图标符号，
  整体视觉简化。
- R2（反馈 #2）：会话条目右键菜单——重命名、分支（fork）。
- R3（反馈 #3+#4）：子代理会话折叠与树状组织——child session 只在
  parent 下折叠展示，同一工作记录内会话按树状结构组织。
- R4（反馈 #5）：历史并入——移除侧边栏历史（conversations）模块入口，
  Work Records 的「全部会话」直接在模块内展示全部会话。

## 现状与技术要点

- UI：`features/workspace-explorer/WorkRecordsView.vue`（当前平铺列表），
  历史列表在 `WorkspaceExplorer.vue` conversations tab +
  `features/history/ConversationViewer.vue`。
- 后端：`src/aisc/cli/commands/work_record.py` 与成员扫描目前没有
  parent-child 关联数据（已核实无 parent_thread 类字段）。
- fork：CLI 目前无 fork 能力（已核实）。Claude 侧 `--resume <id>
  --fork-session` 原生支持待核实版本；Codex 侧 fork 支持待调研。

## 实施顺序

1. **R0 小调研（先行，只读）**：
   - Codex rollout / Claude transcript 中父子 thread 关联字段的落点；
   - 两引擎 fork 的 CLI 形态与风险。结论回填本文件。
2. **R3 后端**：会话扫描补 parent_thread_id（缺失时置 null，UI 按
   平铺兜底）；`aisc work-record list` / IPC 输出带上该字段。
3. **R4 历史合并**：Explorer 移除 conversations 入口；Work Records
   「全部会话」复用会话列表渲染展示全部会话（含恢复/删除）。
4. **R1+R2 UI**：动作符号化；右键菜单（重命名、fork——fork 依赖 R0
   结论，若某引擎不支持则该引擎菜单项禁用并提示）。
5. **R3 UI**：树状展示与子会话折叠（默认折叠，可展开）。

## 约束

- 不使用 runtime_id 做身份匹配（b6 铁律延续）。
- 删除/恢复/加入既有语义与确认保护不变，仅呈现层符号化。
- b6 HANDTEST 用例不回退；R4 移除历史入口后原 conversations 能力
  （搜索、重命名、删除、恢复）必须在「全部会话」中可用。

## 验收形态

- 单测：parent_thread_id 解析与平铺兜底；树状分组；conversations 能力
  迁移后的 store 行为。
- 手测：新增 T7（Work Records 树状展示 + 右键菜单 + 历史并入）写入
  HANDTEST 并 PASS。
- 全量本地门禁 + 远程 CI 全绿。

## 分支

`2.1.15-b8-work-records-ui-tree`（从 develop 切出）。
