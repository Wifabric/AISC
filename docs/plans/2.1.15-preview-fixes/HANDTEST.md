# v2.1.15 Preview Fixes 手测清单

> 每项先满足前置准备，再按步骤执行；只有全部理想结果满足才记 PASS。异常时记录时间、安装版本、目标机器、窗口标题和截图/日志。

## b9-T1：本地 bash / 会话恢复不再触发 fork_session 崩溃

### 前置准备

- 安装包含 b9 修复的下一跳 Workbench preview；
- 本机 Docker 可用；
- 准备一个可启动 runtime 的本地工作区；
- Workbench 内至少存在一条 resumable codex/claude 会话（若无，先创建并退出一条）。

### 操作

1. 打开工作区并启动 runtime；
2. 新建 bash tab，等待 10 秒；
3. 在终端输入 `echo B9_BASH_OK`；
4. 打开 Work Records → 全部会话；
5. 点击一条 resumable 会话的恢复按钮。

### 理想结果

- 步骤 2：出现容器 shell prompt（如 `/root/app#`），不出现 Python traceback；
- 步骤 3：输出精确 `B9_BASH_OK`；
- 步骤 4：会话行恢复按钮可用；
- 步骤 5：创建对应 provider tab，不出现 `open_session() got an unexpected keyword argument 'fork_session'`。

### 异常判定

- 任何 Python traceback / process_exit 立即关闭 tab → fail；
- 无 prompt 且输入不可达 → fail；
- 恢复按钮无响应或 preflight 失败 → fail。

## b9-T2：Windows 远端旧 CLI 拒绝配对，新 CLI 可进入 bash

### 前置准备

- 本机安装包含 serve protocol 4 的 Workbench preview；
- 远端 A 为 Windows，安装旧 CLI `0.1.3`（serve protocol 3）；
- 远端 B 为同一 Windows 机器升级到包含 b9 的 CLI/Workbench `0.1.4.dev0`（serve protocol 4）；
- 两轮远端 Docker 均可用，SSH 均可直连。

### 操作

1. Workbench 添加/选择远端 A，打开工作区并启动 runtime；
2. 新建 bash tab，等待 handshake 错误或 30 秒；
3. 在远端 A 安装包含 b9 的 CLI/Workbench；
4. Workbench 重新选择远端 A（此时为远端 B 状态），刷新/重试；
5. 新建 bash tab，等待 prompt；
6. 输入 `echo B9_REMOTE_WINDOWS_OK`。

### 理想结果

- 步骤 2：旧远端在握手阶段出现明确 serve protocol mismatch / 升级远端 AISC 提示，不出现长时间无提示光标；
- 步骤 5：出现 `/root/app#` prompt；
- 步骤 6：输出精确 `B9_REMOTE_WINDOWS_OK`；
- 远端 CLI 诊断显示 `cli_version=0.1.4.dev0`、`serve_protocol=4`。

### 异常判定

- 旧远端无错误提示且 bash 永久无输出 → fail；
- 新远端仍无 prompt → fail；
- WSL 远端可用但 Windows 远端不可用 → 保留远端 Windows Docker/CLI 诊断包，继续专项排查。

## b9-T3：Work Records 树状 UI、溢出与恢复

### 前置准备

- 使用包含 b9 修复的 Workbench preview；
- 工作区内有 Codex parent + subagent child 两条 transcript，且均已进入 conversation scan；
- 将 parent 与 child 加入同一个 Work Record；
- 另保留至少一对 parent + child 未加入任何 Work Record；
- 将一条长标题（不少于 120 字符）会话加入 Work Record。

### 操作

1. 打开 Work Records 默认页；
2. 查看含 parent/child 的 Work Record；
3. 点击 parent 左侧折叠符；
4. 查看未归档会话区；
5. 点击未归档 parent 左侧折叠符；
6. 查看长标题行右侧恢复/移出按钮；
7. 点击一条 resumable 成员的恢复按钮。

### 理想结果

- 步骤 2：child 默认不可见，parent 行显示 child 数量折叠符；
- 步骤 3：child 只出现一次，位于 parent 下方并有缩进/树状引导线；
- 步骤 4：未归档 child 默认不可见，parent 显示折叠符；
- 步骤 5：未归档 child 只出现一次并呈树状缩进；
- 步骤 6：长标题省略号截断，恢复/移出按钮保持在 Work Record 卡片右边界内；
- 步骤 7：恢复走 preflight 并创建对应 provider tab。

### 异常判定

- child 同时作为顶层与子级重复出现 → fail；
- 所有层级视觉上仍完全平铺 → fail；
- 按钮越过所属卡片右边界或被挤出可视区 → fail；
- 成员恢复无响应 / traceback → fail。

## b10-T1：workspace target 绑定与远端路由

### 前置准备

- 本机与 Windows 远端均使用包含 b10 的构建；远端 CLI 为 `0.1.5.dev0`。
- 远端已有可用工作区与 Docker runtime。
- 本机打开诊断页可查看 `target_route` 事件。

### 操作

1. 通过远端机器入口打开 Windows 远端工作区（新窗口 URL 带 `machine`）；
2. 启动 runtime；
3. 新建 bash 并输入 `echo B10_REMOTE_OK`；
4. 查看 `target_route` 事件；
5. 再打开一个本机本地工作区并启动 bash。

### 理想结果

- 步骤 2 的 `runtime.start` 事件 `kind=remote`，machine 为 Windows 远端；
- 步骤 3 的 `session.open` 事件 `kind=remote`，输出 `B10_REMOTE_OK`；
- 步骤 5 本地 workspace 的路由保持 `kind=local`；
- 两个 workspace 并存时远端/本地互不切换、互不回收。

### 异常判定

- 任一远端命令记录 `kind=local` 或落在本机 Docker → fail；
- 本地 workspace 被远端 target 劫持 → fail；
- bash 无 prompt 且日志显示错误 target → 保留日志并 fail。

## b11-T1：Work Records 排序、菜单、树与自动刷新

### 前置准备

- 使用包含 b11 的 Workbench；
- 工作区至少两个 Work Record、一条 Codex 父会话与可通过 CLI `/fork` 产生的新会话；
- 一条标题超过 120 字符的会话；
- 顶部导航可切换不同 resume 会话。

### 操作

1. 在 Codex CLI 内执行 `/fork`，返回 Work Records 等待自动刷新；
2. 展开父会话，检查 fork/subagent child；
3. 拖动 Collection 卡片交换位置；
4. 拖动成员在同一 Collection 内交换顺序；
5. 拖动成员到另一个 Collection 与未归档区；
6. 右键会话，依次检查菜单项并执行移入/移出、重命名、恢复；
7. 点击 Collection 与会话重命名按钮，检查编辑框出现/提交后消失；
8. 检查超长标题行与未归档行视觉一致性；
9. 切换顶部导航到一个属于某 Collection 的运行/恢复会话。

### 理想结果

- 步骤 1：新 fork 会话自动出现，无需手动刷新；
- 步骤 2：child 只显示在 parent 下且默认折叠；
- 步骤 3-5：拖拽后的顺序/归属持久，刷新后不变；
- 步骤 6：菜单包含恢复、删除、重命名、移入/移出；动作生效；
- 步骤 7：编辑框只在点击后替换原名称，Enter/Esc/失焦后退出；
- 步骤 8：长标题 ellipsis，按钮不溢出，Collection 行与未归档行高度/样式一致；
- 步骤 9：所属 Collection 自动变为 Active；无 Active 时首个 active Collection 自动 Active。

### 异常判定

- Work Records 内仍出现 All Sessions 入口 → fail；
- child 顶层重复或父子关系丢失 → fail；
- 拖拽后刷新回跳或成员丢失 → fail；
- 重命名输入框常驻 → fail；
- 顶部会话切换未激活所属 Collection → fail。
