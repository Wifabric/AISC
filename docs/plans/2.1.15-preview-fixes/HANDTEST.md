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
