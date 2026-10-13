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
