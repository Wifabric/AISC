# v2.1.15 裁决记录

## D-1（2026-10-12 用户指示，开题）

**问题**：v2.1.14 收口后无活动开发阶段；反馈站新增 5 条 `submitted` 反馈，需要
回执并纳入下一版计划。

**裁定**：

1. 以 Workbench 下一版本线 `v2.1.15` 建立反馈驱动开题计划。
2. 本轮只落计划与回复草案，不直接实施代码。
3. 五条反馈全部纳入计划范围：SSH 阻塞、工作区路径大小写、终端滚动跳顶、顶部
   状态栏可拖拽、历史/工作记录模型。
4. 实施前按“分支先行”纪律再开批次分支；文档账本更新可直接落 `develop`。

**影响面**：`docs/plans/2.1.15-dev-plans/`、`docs/todo.md`、后续反馈数据仓库。

## D-2（2026-10-12 规划裁定，反馈回复边界）

**问题**：SSH 反馈带诊断附件，公开回复不能复述可能含环境细节的内容；终端滚动
反馈的期望（运行后强制回到最底）可能与“用户正在回看历史”冲突。

**裁定**：

1. 公开回复只写处理状态、优先级和下一步，不复述诊断包内部数据。
2. SSH 项先按 blocker 排查，定位结论以仓库文档为准。
3. 终端滚动不预设“任何输出结束后强制滚到底”，先实现“不干扰手动滚动 + 可预期
   恢复跟踪”的行为；若确要无条件强制底端，另行用户裁决。
4. 历史/工作记录模型先调研出数据模型与迁移方案，经裁决后才实施。

**影响面**：反馈站回复口径、b1/b3/b4 实施范围。

## D-3（2026-10-13 用户裁决，F3 Work Record / Collection）

**问题**：b4 已确认 Work Record 需要建立在 provider conversation 之上的轻量聚合层，
但 8 个开放点未裁决，不能实施。

**裁定**：

1. Work Record / Collection 采用「会话记录 + 轻量集合层」；底层继续一次 provider
   conversation 一条记录，Collection 只保存成员关系和元数据，不合并、迁移或改写
   provider transcript。
2. active Work Record 自动收容新建 provider conversation，不做时间窗猜测；用户可
   手动加入、移出、移动；archived Collection 不自动收容。
3. `bash` / `cc-switch` 不进入 Work Record，继续留在现有全局 session 历史。
4. 过渡期保留「全部会话」flat 视图；Work Record 视图与其并存，是否下线另行裁决。
5. 删除 Work Record 时普通确认后直接级联删除成员；不要求输入名称、逐项勾选或
   二次强确认。
6. 删除范围包括 Collection 元数据、成员关系、provider conversation 记录和 provider
   transcript 物理文件；运行中 provider session 先终止；个别 transcript 删除失败时
   继续删除可删部分，并必须明确提示失败项。
7. member session 增加可选 `runtime_id`，仅作 provenance / 溯源；不用于 Work Record
   身份、合并、去重、恢复或运行时绑定。
8. archived 默认隐藏，提供「显示已归档」开关；归档可逆，不删除、不移动、不改写
   provider transcript。
9. 第一版按完整语义实施：存储、IPC、视图、未归档会话、CRUD、active 自动收容、
   terminate + 物理级联删除、失败提示和 optional runtime provenance。

**影响面**：新增 `work-collections.json` / `aisc work-record` / Tauri work-record
IPC / Workbench Work Records 视图；实施移交 b6。
