# v2.1.15 b14：preview.5 字段反馈修复

## 用户反馈（2026-10-15，preview.5 实测后）

1. 设置 → 磁盘提示「AISC CLI 协议不对」，缺少可行动的具体原因。
2. 第一次进入远程 Workbench / workspace 后，左侧文件导航为空，手动刷新后才显示真实目录。
3. 第二次进入远程服务端时点击最近工作区，看起来按本机启动，没有按记录机器直接进入。
4. Docker 镜像构建后出现 `docker.1ms.run/library/node` 与 `node` 两条几乎相同的记录，ID 相同，用户质疑是否有必要重复展示。

## 根因取证（2026-10-15）

- 当前配置了两台远端：
  - `win-test` = `admin@10.147.20.7`，CLI `0.1.7.dev0` / serve protocol 4。
  - `wsl-base` = `wangyu@172.21.90.157`，CLI `0.1.3` / serve protocol 3。
- preview.5 Workbench 硬门禁为 serve protocol 4。选择 `wsl-base` 后，磁盘 / 诊断类命令在 pooled serve 握手阶段失败，这是「协议不对」的直接原因；该远端需要升级 CLI。
- Rust `handshake()` 已生成明确 detail：`serve protocol mismatch: client 4, remote 3 — upgrade ...`，但 Settings store 多处只取 `message`，丢弃 `technical_detail`，用户只看到泛化的「AISC CLI 输出不符合协议」。
- 远程 Explorer 首空存在确定时序竞态：App watcher 可能先把 `explorer.workspace` 设为路径；WorkspaceExplorer 自身 watcher 再收到同一 workspace 时因 `explorer.workspace === ws` 跳过 `refreshRoot()`。如果组件 onMounted 时 workspace 尚未就绪，本次就没有任何首载，直到手动刷新。
- history 中远端记录当前为 `machine_name="admin@10.147.20.7"`，而配置名是 `win-test`。根因在 `start_runtime()` 调用 `bind_workspace_target()`：`CliTarget::Remote(SshTarget)` 已丢失配置机器名，`target_binding()` 用 SSH host 伪造 `RemoteMachine.name`。后续 `workspace_machine()` 读这个绑定并持续写入 `admin@...`；Recent 点击时按该名字找不到配置机器，回退/切换失败。
- Docker 输出证实 `docker.1ms.run/library/node:22-slim` 与 `node:22-slim` 是同一 image ID 的两个 repo tag。磁盘占用不会重复，但 Settings 管理列表按 tag 展开成两行，造成重复观感；应按 image ID 聚合展示，retag 使用首个规范 ref，删除仍按 image ID。

## 方案 / 任务

### Task 1：Settings 错误保留协议 detail

- Settings store 增加统一错误提取 helper：优先 `message`，附加 `technical_detail`。
- `cacheUsage`、`cacheCleanup`、`dockerScan`、`dockerCleanup`、`dockerRebuild`、`cacheInspect` 错误均保留完整原因。
- 测试覆盖 `WB_ERR_CLI_PROTOCOL + technical_detail` 时 UI/store 错误包含 client/remote 协议号和 upgrade 提示。
- 实机操作：`wsl-base` 升级 CLI `0.1.7.dev0` 后协议错误消失；未升级前至少能明确看到需要升级的目标。

### Task 2：远程 Explorer 首载竞态

- WorkspaceExplorer 的 workspace watcher 在收到非空 workspace 时：
  - 若 explorer workspace 不同则 `setWorkspace(ws)`；
  - 无论是否刚被 App watcher 预先设置，都执行一次 `refreshRoot()`。
- 组件测试模拟“onMounted 时无 workspace → App watcher 先 setWorkspace → 组件 watcher 后收到同一 workspace”的竞态，断言无需手动刷新即调用 root listing。

### Task 3：Recent 记录使用配置机器名

- `start_runtime()` 不再用丢失配置名的 `CliTarget` 直接绑定 workspace；改用当前 window/global 的 configured `RemoteMachine` 身份绑定。
- history 保存时将历史中的 SSH host 形式机器标识归一为 settings 中匹配的机器名（如 `admin@10.147.20.7` → `win-test`）。
- Recent 打开时如果旧记录的 `machine_name/machine_host` 能匹配配置机器，则使用配置名路由，避免已有坏记录继续回本机。
- 测试覆盖：
  - runtime start 绑定保留 `win-test`；
  - legacy `admin@host` 记录路由到 `win-test`；
  - 同路径本机与 `win-test` 仍不合并。

### Task 4：Docker image tag 聚合展示

- Settings 的可管理 image 列表按 `id` 聚合：
  - 展示名合并为 `node:22-slim, docker.1ms.run/library/node:22-slim`；
  - 删除继续按 image ID；
  - retag 的默认 repository 使用第一条 ref。
- 测试覆盖同一 ID 两个 tag 只渲染一行，操作仍保留 ID 与可 retag 的 ref。

### Task 5：门禁 / 发布

- 目标测试 → full local gates。
- PR CI 全绿 → ff-only merge develop。
- develop Workbench / CLI sidecar / Linux+macOS bundle / NSIS 全绿。
- 本批预计发布 Workbench `v2.1.15-preview.6`；CLI 若无 Python 变更则维持 `0.1.7.dev0`。

## 验收

- 选择未升级的 `wsl-base` 时，设置页明确显示 serve protocol 3 vs 4 与升级指引；升级后磁盘页可正常扫描。
- 远程 workspace 第一次打开即显示远端文件；空目录显示空态。
- Recent 的远端记录显示并路由 `win-test`；第二次点击直接打开远端，不再落回本机。
- 同一 image ID 的多个 repo tag 在 Settings 中只显示一行。
- 本地门禁与 CI 全绿。

## 执行状态（2026-10-15）

- `d65de2b` 计划落盘；`0e16ed8` 保留 CLI protocol `technical_detail`；
  `70ba253` 修复远程 Explorer 首载竞态；`f562f8a` 保留配置机器名并迁移
  `admin@host` history alias；`409261c` 聚合同 ID Docker image tags。
- 本地门禁：Python 1403 passed / 53 skipped；Rust lib 359 passed / 1 ignored；
  Vitest 75 files / 590 tests；vue-tsc 通过，`LOCAL GATES: ALL GREEN`。
- 远端取证与处理：`wsl-base` 原 CLI `0.1.3` / serve protocol 3，确认为
  协议错误来源；已从 TestPyPI 升级 CLI 到 `0.1.7.dev0`，ready banner 现为
  protocol 4，`maintenance cache-usage` 可用。其旧 aisc-bundle 目录仍显示
  `0.1.3`，不影响本批协议 / 磁盘命令，后续随远端安装器或 bundle 更新。
- 下一步：push 分支 → PR CI → ff-only merge develop → develop 全路径 CI →
  Workbench `v2.1.15-preview.6` → 用户复测。
