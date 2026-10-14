# v2.1.15 b10：远端 target 路由与 workspace 绑定修复

## 用户确认的根因

Workbench 没有走远端 serve；`start_runtime` / `open_session` 实际取得
`CliTarget::Local`。已核实的风险面：

1. workspace 在 target 切换前已按本地模式打开，后续命令继承错误路由；
2. `WindowTargets` 以 window label 为键，调用来自另一个 WebviewWindow 时无法命中；
3. `workspace_watch_start`、Explorer mutation、`runtime_poll_light` 仍读取
   process-global `ActiveTarget`，没有使用 per-window target。

## 方案

1. 新增 **workspace target binding**：runtime 第一次对某个 workspace 执行
   `start_runtime` 时，把当时解析出的 Local/Remote 目标绑定到该 workspace。
2. 所有携带 workspace 的 runtime/session/conversation/work-record/workspace 命令
   优先按 workspace binding 路由；无绑定时才退回当前 window target，再退回 global。
3. `workspace_watch_start` 与 `runtime_poll_light` 增加 window 参数或改用
   workspace binding，禁止远端窗口误走本机 Docker / notify watcher。
4. Explorer mutation 的 `is_remote` 从 global target 改为 window/workspace target。
5. start/open 记录 target route 日志（不写敏感路径/密钥），实机可验证 machine name、
   window label、workspace binding 与 Local/Remote 判定。

## TDD 与验收

- Rust 红灯：
  - workspace binding 优先于 window/global；
  - Local workspace binding 不得被 remote global 抢走；
  - workspace key 保持 POSIX 大小写，同时归一 Windows 分隔符/盘符大小写。
- 命令层验收：
  - remote workspace 的 start → session 全链路生成 Remote target；
  - 同 workspace 从另一 WebviewWindow 调 session/open 仍命中 Remote；
  - local workspace 与 remote workspace 并存时互不污染；
  - watcher/mutation/poll 不再读 global target。
- 手测：Windows 远端升级 CLI `0.1.4.dev0` 后，start/runtime/bash prompt 全链路走远端。

## 非目标

- 不改 serve protocol；
- 不改远端 CLI 语义；
- 不恢复多 workspace 共享一个 target 的旧行为。
