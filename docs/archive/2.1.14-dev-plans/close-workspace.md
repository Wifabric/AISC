# 批 5：顶栏「关闭工作区」回 picker

> 状态：计划待用户验收（2026-09-23 立项）
> 来源：反馈站 20260922-关闭工作区-重新选-Alan（「顶栏操作按钮增加关闭当前
> 工作区的按钮，点下后关闭工作区、窗口不关闭、回到 picker 页面；场景：开错
> 工作区重选；现状替代：新建窗口重选再关旧窗口」；D-1 纳入）
> 方法：ultracode workflow（研究员 + 首轮 evidence 核验 verdict=corrected
  ——恢复轮核验员 429 阵亡，首轮裁决从 journal 回灌；last_used_at 硬修正
  已并入本稿）
> 对应 target：docs/todo.md「v2.1.14-target」反馈 #4 条目

## 1. 现状：能力缺口，非缺陷

- W3「一窗一工作区」改造（WorkspaceBar 退役）后，工作区内唯一「关闭本
  工作区」入口退化为右缘 ⓘ 状态抽屉里的「停止 Runtime」按钮
  （RuntimeSidebar.vue:216；全仓 grep 证实 closeWorkspace 的 UI 调用仅此
  一处，抽屉 detailsOpen 默认 false 收起）；顶栏「操作」菜单
  （MenuBar.vue:227-303）只有四条「打开」方向条目（newWindow/openFolder/
  openRecent/openRemote，无 closeWorkspace/关闭 命中）；命令面板
  `app.picker`（commands.ts:115）只把 launcher 调前台，**不是关闭**。
- **关闭链路本身完整存在且经手测**：`closeWorkspace`（workspaces.ts:262-321）
  = confirm（268）→ flushSave（276）→ 视觉即时移除 + activate 邻居
  （284-285）→ 后台 closeSession（400ms 竞速，288-297）→
  teardownRuntimeAndRelease（305：stop→verify→remove→leaseRelease；
  workspaceRuntime.ts:1728-1751 leaseRelease 对 not_found 幂等）→ dispose。
  **零生命周期代码改动，只加入口。**

## 2. 方案（D-7）

- **三入口**（同一动作同一门控）：
  1. 「操作」菜单末尾新增「关闭当前工作区」（MenuBar.vue）；
  2. 菜单栏右端 mb-status 旁独立图标按钮（用户原话「顶栏操作按钮」，
     一步可达）；
  3. 命令面板 `app.closeWorkspace`（commands.ts + App.vue paletteCtx，
     与 app.picker 形成开/关对）。
- **门控**：activeRuntime 为已物化工作区且 status∈{ready,error} 时可用；
  picker/启动链各态不显示（那些态已有 backToPicker/cancel 路径；且
  closeWorkspace 对无 runtimeId 的 starting 实例只清 UI、不
  cancelRuntimeStart，会后台物化容器——竞态必须靠门控规避）。
- **误触保护**：confirm（容器删除不可撤销，用 confirm 而非 undo）；文案
  含活动会话数 / 「工作区文件不受影响」。
- **语义对齐**：RuntimeSidebar「停止 Runtime」与新入口统一 i18n 文案与
  动作（U-4）。
- **不纳入**：「重开秒回」（runtime 原地保留）——与 runtime-lifecycle-ux
  Stage 3 ephemeral 裁决相抵，记观察项；picker 复选体验——
  **核验修正**：closeWorkspace 不写 last_used_at（全函数零命中；唯一写入点
  在 workspaceRuntime.ts:956/997 的打开路径 buildPatch），刚关工作区只在
  「恰是最近打开」时居首、时间戳停在打开时刻——无需额外代码，也不预期
  「关闭刷新时间戳」。

## 3. 风险

- 同窗多工作区（palette 加开的罕见态）：关当前后 activate 邻居工作区而非
  picker——接受该偏差（U-4 顺带确认）；
- error 态（runtimeId 残留）已由 teardown 幂等覆盖；错误工作区的「关闭」
  含清障语义，文案是否区分随验收定。

## 4. 验收

见 [HANDTEST.md](HANDTEST.md) T5（confirm 两形态文案、<1s 回 picker 字段
核对、docker 无残留容器、lease 释放、重开走全链、X 退出原路回归、
vitest 基线）。
