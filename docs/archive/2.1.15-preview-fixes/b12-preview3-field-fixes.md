# v2.1.15 b12：preview.3 字段反馈修复

## 用户反馈（2026-10-15）

1. Work Records 会话行长标题使左侧栏横向溢出；右键删除 transcript 后成员残留在 UI，显示「引用缺失」，还需手动移除。
2. Windows 远端 runtime 确认在远端 Docker 运行，但 bash 无 `root@…:~/app#` prompt，界面停在启动/空终端。
3. 远端工作区选择仍需手工输入路径；选择远端主机后应能浏览该机器目录。
4. 设置页「检查更新」按钮无明显动作，无法继续下载/安装。

## 已取证结论

- 远端主机：`admin@10.147.20.7`，CLI `0.1.5.dev0` / serve protocol 4。
- 远端 workspace：`C:\Users\admin\test-ws`；可启动 super-claude runtime。
- 直接保持 SSH stdin 打开并调用 `aisc serve --stdio` 时，ready banner 不到达本地；关闭 stdin 后 banner 才随进程退出出现。定位为 Windows PyInstaller frozen TextIO `reconfigure()` 在 SSH 管道下阻塞；同时保留低级 descriptor 写出作为输出硬化。
- Workbench 的 remote runtime start 多数仍是 one-shot SSH CLI，因此能确认远端 Docker；watch/browse/session 走 resident serve 时会暴露上述管道问题。
- remote browse 与 canonical workspace 假设 POSIX 绝对路径；Windows home/workspace 是 drive-letter 形态，导致浏览退化为手工输入，session open 的 canonical gate 也会拒绝。
- Work Records 行在 grid auto column 中未设置 `minmax(0,1fr)` / max-width，长内容把 grid 撑开。
- 右键删除只调用 conversation delete；按 D-3，ledger 成员记录需显式移除，因此残留「引用缺失」。
- Update store本身状态机有测试；设置页首次检查后按钮被 `v-else` 移除，用户无法重复检查，也无 UI action 取证。

## 方案

1. Work Records:
   - 所有卡片/行/标题设置 bounded width、`min-width:0`、ellipsis；
   - 右键删除 transcript 后同步 remove member 并刷新。
2. Remote serve:
   - 不再对 frozen stdin/stdout 调用 `reconfigure()`；stdin 按行读取 binary buffer 并按 UTF-8 解码。
- serve frame 输出改为 low-level `os.write(stdout.fileno(), ...)`（无 fileno 的测试 StringIO 走 fallback）；banner/PTY output 即时到达 SSH 管道。
3. Windows remote paths:
   - remote browse / workspace existence / canonical workspace 支持 POSIX 与 Windows drive-letter 绝对路径；
   - 内部统一显示为 slash 形态（如 `C:/Users/admin`），远端 Python 可解析；
   - picker 的“浏览”对 drive-letter 当前输入也打开远端目录树。
4. Update UI:
   - 检查后保留“再次检查”按钮；
   - 增加 UI action log，显示 checking/结果；
   - 网络失败保持错误与可重试状态。
5. CLI 修复需要新 dev 版本，下一跳 bump `0.1.6.dev0`，随 Workbench preview.4 分发/TestPyPI。

## 验收

- Python serve pipe 测试：保持 stdin 打开时 first frame 立即写入低级管道。
- Rust path 测试：Windows/POSIX remote path normalize/containment。
- Frontend tests：长标题 bounded row；右键删除同步移除；远端 drive-letter 打开 browse；update 可重复检查。
- 实机：Windows remote browse → start → bash prompt；Work Records 长标题不溢出、删除即消失；设置页可重复检查并显示结果。

## 执行状态（2026-10-15）

- 远端实机取証：`admin@10.147.20.7` / CLI fixed build / runtime
  `a592f644-567c-4ce6-b921-ed00f13441f8`。`session.open` 返回 ok，并收到
  `root@f4404b948589:~/app$` prompt；测试后 runtime 已 remove。`fs.list` 对
  `C:/Users/admin` 返回目录列表（含 `test-ws`）。
- CLI dev 版本升至 `0.1.6.dev0`，serve protocol 保持 4。
- Work Records bounded CSS、右键删除后同步移除 ledger member、Windows remote
  drive-letter browse、更新检查后保留“再次检查”均已实现。
- 目标验证：Python serve/work collection/conversation 51 passed；Rust browse/path
  3 passed；Frontend WorkRecords + picker + settings 37 passed；vue-tsc 通过。

- PR #16 frontend / cli / rust 全绿；develop Workbench、CLI sidecar、Linux/macOS bundle、
  NSIS 全绿，已 ff-only 合入 `45df391`。

- 发布：`v2.1.15-preview.4` NSIS workflow success，GitHub prerelease 资产
  就位；`cli-v0.1.6.dev0` PyPI workflow success，TestPyPI 版本索引可见。
