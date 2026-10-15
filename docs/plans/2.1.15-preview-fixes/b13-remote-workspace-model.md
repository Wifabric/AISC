# v2.1.15 b13：远程工作区模型升级

## 用户反馈（2026-10-15，preview.4 实测后）

1. 选择远程主机后希望像本机一样使用系统资源导航；不应只能从 `C:/Users/admin` 开始，应能选择权限内所有盘符/目录。
2. 最近工作区必须标注驱动机器；不同机器上的相同路径是不同工作区。
3. Workbench 的 provider、cc-switch 配置、聊天记录、runtime 信息等工作区数据面应使用远端。
4. 远程工作区打开后侧边栏文件应为远端 workspace 内容，不应为空。
5. 帮助菜单「检查更新」必须有 checking / 已最新 / 可更新 / 失败反馈；可更新时进入安装引导。
6. 帮助菜单「文档」应打开使用文档。

## 根因与边界（开工前取证）

- SSH 远端无法调用本机 Windows 的原生 folder dialog 浏览对端本地磁盘；远端 Explorer GUI 也不会显示在本机。b13 采用 Workbench 内建 SSH-native 文件导航，能力对齐 Explorer：盘符/根目录、目录分页、面包屑、上一级、刷新、隐藏文件、搜索。
- 当前 `remote_browse_core()` 把 ready banner 的 `home` 当作唯一 root，并用 `normalize_under_root()` 拒绝 home 外路径；这是只能看到 `C:/Users/admin` 的直接原因。
- 远端 CLI 需要新增 `fs.roots`：Windows 返回所有可访问盘符，POSIX 返回 `/`；`fs.list` 已能对任意绝对 root 列目录。
- `WorkspaceRecord` 目前只有 path，history upsert/dedupe/remove 也只用 path identity，无法区分本机与远端或两台远端的相同路径。
- provider / cc-switch / conversation / work-record / runtime 的现有调用面已经带 workspace 或 window target；日志显示 remote runtime、conversation、work-record 成功。b13 不把控制端设置（remoteMachines、窗口、主题）搬到远端，而是补机器身份、路由日志和回归测试，确保 workspace 数据面全部按远端执行。
- 实机 `fs.list` 对 `C:/Users/admin` 返回大量条目；用户选择的 `E:/test` 与 `C:/Users/admin/test-ws` 在远端本身就是空目录。侧边栏修复仍需自动化回归：非空远端目录必须显示远端条目，空目录显示明确空态而非异常。
- `MenuBar.vue` 文档使用旧仓库 URL 与 WebView 内 `window.open`，Tauri 环境应使用 `@tauri-apps/plugin-opener/openUrl`。
- 菜单检查更新只处理 available 分支，checking / none / error 均无反馈。

## 任务

### Task 1：Help 菜单可用性（TDD）

- 新增 `MenuBar` 组件测试：
  - docs 调用 `openUrl("https://github.com/Wifabric/AISC#readme")`；
  - update checking / none / available / error 四分支都有 toast，available 额外打开 Settings。
- 实现 `openUrl`、正确文档 URL、更新结果 toast 与 UI action 取证。

### Task 2：远端 roots 与全盘导航（TDD）

- Python：新增 `fs.roots` op 测试与实现；Windows 返回所有可访问 drive-letter roots，POSIX 返回 `/`。
- Rust：
  - `RemoteBrowseResult` 增加 `roots` / `home`；
  - `remote_browse_core` 先取 roots，再按任意绝对路径列目录，不再把 home 作为 containment 上限；
  - path normalize 保持拒绝 relative / `..` escape；Windows root 到 drive root、POSIX root 到 `/`；
  - 旧远端不支持 `fs.roots` 时降级为 home 所在根，不阻断 manual path。
- Frontend：
  - 远端 browse 增加盘符/根选择、面包屑、上一级；
  - roots 可切换 `C:/`、`D:/`、`/`；
  - 保留搜索、隐藏目录、双击进入、选择确认。
- CLI 变更发布为 `0.1.7.dev0`，serve protocol 4 additive 兼容。

### Task 3：Recent workspace machine identity（TDD）

- Rust history：
  - `WorkspaceRecord` 增加 optional `machine_name` / `machine_host`；
  - identity / upsert / dedupe / remove 从 path-only 改为 `machine + normalized path`；
  - 同 path 不同机器保留两条；同机器同 path 才合并；
  - `save_history` 在窗口/workspace target 解析后补机器字段。
- Frontend：
  - recent 行显示本机/具体远端机器 badge；
  - 点击 recent 按记录的机器开新窗口并绑定 target；
  - dead recent / remove 请求携带 machine，避免误删同名本机记录；
  - existing workspace focus 匹配 machine + path。

### Task 4：远端数据面与文件侧边栏审计（TDD / 实测）

- 为 remote `workspace_list` 的路径归一、分页映射和错误传播补测试。
- 为 provider / cc-switch / conversation / work-record / runtime 路由补 target-aware 回归测试或日志断言，确保 workspace 数据面使用远端 CLI 与远端 data root。
- 控制端设置（remoteMachines、UI 偏好）保持本机，并在文档中记录边界。
- 实机验收：远端非空目录显示条目、空目录显示空态；远端 provider / cc-switch / conversation / work records 与本机隔离。

### Task 5：门禁与发布

- 本地：Python 目标测试 → full local gates。
- 远端：PR CI 全绿 → ff-only merge develop → develop Workbench / CLI sidecar / Linux+macOS bundle / NSIS 全绿。
- 发布：CLI `0.1.7.dev0` / TestPyPI，Workbench `v2.1.15-preview.5`。
- 实机手测：全盘导航、机器标注 recent、远端数据面、侧边栏非空/空目录、Help 文档与更新反馈。

## 验收

- 选择远程机器后能从任一盘符/根开始浏览并选择 workspace，不依赖手输路径。
- Recent 中相同路径按机器区分，恢复时打到正确机器。
- 远端工作区文件树来自远端；workspace runtime / provider / cc-switch / conversation / work records 均路由远端；控制端设置仍留在本机。
- 帮助文档可打开；检查更新四个状态均可见，可更新时进入 Settings 下载/安装。
- 所有自动化与 CI 门禁通过。

## 执行状态（2026-10-15）

- `678fee8` 计划落盘；`b75ca4d` Help 文档 opener 与更新四态反馈；
  `8904151` `fs.roots` / 全盘 SSH-native 导航 / CLI `0.1.7.dev0`；
  `3ff0562` history 与 Recent 的 machine identity；`bcb410f` Windows 远端
  watcher root/path 归一及 cc-switch target_route 取证。
- 实机取证：远端 `fs.list C:/Users/admin` 返回目录；用户选择的
  `E:/test` 与 `C:/Users/admin/test-ws` 在远端均为空目录。非空目录应显示
  条目，空目录保留明确空态。
- 本地门禁：Python 1403 passed / 53 skipped；Rust lib 357 passed / 1 ignored；
  Vitest 75 files / 585 tests；vue-tsc 通过，`LOCAL GATES: ALL GREEN`。
- 下一步：push 分支 → PR CI → ff-only merge develop → develop 全路径 CI →
  Workbench `v2.1.15-preview.5` / TestPyPI `0.1.7.dev0` → 用户实机复测。
