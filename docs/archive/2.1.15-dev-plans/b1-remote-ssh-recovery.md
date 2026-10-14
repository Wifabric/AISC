# v2.1.15 b1：SSH 远程会话启动阻塞排查修复

> For agentic workers: 本文件是 b1 批次实施记录。执行须遵守分支先行、根因先行、
> TDD、本地门禁与远程 CI 全绿后并回 develop。

## 目标

修复用户选择远程电脑后无法进入 CLI bash、或提示打开会话报错的阻塞问题。b1 只处理
本批可证实的启动链路缺陷，不借机调整无关 PTY/UI 或会话模型。

## 反馈与证据

- 反馈：F5「SSH 远程电脑之后卡在 CLI bash 界面」，severity `blocker`。
- 用户现象：
  1. 本地 SSH 可正常连接；
  2. AISC 选择已配置远程电脑后卡在 bash 光标，或提示打开会话报错；
  3. 期望与本地一样进入可用 bash。
- 用户诊断包关键事实：
  - 版本 `2.1.13-preview.1`；
  - 平台 `windows-x86_64`；
  - 已配置 port 22 的远程机器；
  - 最近 UI 错误 4 次均为 `reconcile_block`，
    error code 为 `AISC_ERR_ACTIVE_WORKSPACE_LEASE`；
  - 诊断包中没有可直接证明 SSH 握手或 PTY 失败的日志。
- 结论：workspace lease 冲突是诊断包中唯一反复出现的阻塞信号；远程 lease 心跳的
  target 解析必须继续核查，不能直接假设 SSH/PTY 有缺陷。

## 根因调查

### 已核对链路

- `lease_claim` 通过 window-scoped target 执行；
- `lease_release` 也应作用于 claim 时的 target；
- 但后台 `LeaseSupervisor` heartbeat 使用 global target 解析；
- heartbeat 的 direct-write 判定同样使用 global target；
- Workbench 已明确支持 per-window target：remote window 和 local window 不应互相影响。

### 假设 A（本批主要待验证缺陷）

remote window 的 lease heartbeat 在后台回落到 global target：

1. claim 写到远程机器的 lease 文件；
2. 后台 heartbeat 判定/执行时读取 global target；
3. 若 global 为空或另一台机器，远程 lease 不刷新；
4. 45 秒 TTL 过期；
5. reconcile / 下一次打开被 `AISC_ERR_ACTIVE_WORKSPACE_LEASE` 阻塞。

该假设与诊断包错误码和时间线吻合，但必须由失败测试证明后才能修。

### 假设 B / C（继续排查条件）

- B：远端 CLI 与 serve protocol 不配对；
- C：远端 shell / PTY / session.open 链路自身异常。

若假设 A 测试后不能解释阻塞，或修复后仍复现，则回到 serve handshake、session argv、
PTY 输出与远端 CLI 版本继续取证，不在 b1 内混合修改。

## 修复范围

- 让 lease claim、heartbeat、release 共享同一个 claim 时的 target snapshot；
- remote heartbeat 继续通过原 remote target 执行 CLI heartbeat；
- local heartbeat 维持既有 direct-write 和本地 CLI fallback 行为；
- 不改 lease schema、TTL、reconcile 判定、SSH transport、PTY 协议或 UI 流程。

## 实施步骤

1. 新增目标快照辅助函数，使 window machine 可供 lease 模块消费；
2. 为 remote target snapshot 写失败测试：
   - heartbeat 不得做 direct-write；
   - heartbeat 不得回落到 global/local target；
   - release 必须使用 claim target snapshot；
3. 运行目标测试并确认失败；
4. `LeaseBeat` 保存 `Option<RemoteMachine>`；
5. heartbeat / release 从快照构造 target；
6. 重跑目标测试、Rust 测试、前端测试和本地门禁；
7. 更新本记录与 HANDTEST 结果；
8. 提交、推送并等远程 CI；
9. CI 全绿后按纪律并回 develop，并更新阶段账本。

## 测试计划

自动化：

- Rust lease tests：
  - remote snapshot 禁止 direct heartbeat；
  - remote snapshot 生成 remote CLI target；
  - local snapshot 保留 local target 语义；
  - heartbeat interval 契约保持不变。
- `cargo test`；
- `npm test`；
- `powershell -File scripts\\local-gates.ps1`，预期 `LOCAL GATES: ALL GREEN`。

手测：见 `HANDTEST.md` b1 节。

## 风险与回滚

- 风险：错误地把 local direct-write 改成 CLI，会增加 15 秒级开销。
  缓解：只有 remote snapshot 强制 CLI；local direct-write 行为不变。
- 风险：target snapshot 与用户后续切换窗口 target 不一致。
  缓解：lease 属于 runtime 所在机器，release/heartbeat 必须跟随 runtime 的原机器；
  新 claim 会创建新的 snapshot。
- 回滚：本批只回滚 lease target snapshot 相关代码与测试。

## 执行状态（2026-10-12）

- 已在 `2.1.15-b1-remote-ssh-recovery` 分支实施假设 A 的最小修复。
- `LeaseBeat` 现在保存 claim 时的 `Option<RemoteMachine>` snapshot；
  heartbeat / release 均从该 snapshot 构造 target，不再读取 global `ActiveTarget`。
- remote snapshot 强制 CLI heartbeat；local snapshot 保留 direct-write。
- 新增 target snapshot Rust tests。首跑因 helper 未实现而编译失败，实现后 3 项通过；
  这构成 red→green 证据。
- 发现并修复既有本地门禁阻塞：`envelope-version.json` 未随 CLI v0.1.3 发布更新，
  只同步 `meta.version`、`data.cli_version`、`data.bundle_version` 三个版本字段。
- 自动化验证（fresh run）：
  - `python -m pytest ...`：1350 passed，53 skipped；
  - `cargo test --lib`：335 passed，1 ignored；
  - `npx vitest run`：69 files / 518 tests passed；
  - `npx vue-tsc --noEmit`：通过；
  - `powershell -File scripts\local-gates.ps1`：`LOCAL GATES: ALL GREEN`。
- 剩余门：按 `HANDTEST.md` 完成实机 T1–T3；推送后远程 CI 全绿；用户确认后并回 develop。

## T2 复测修复计划（2026-10-12 手测后返工）

### 手测发现

HANDTEST T2 第 7 步「关闭窗口 1 的 runtime」后，远端 `runtime-lease.json`
持续 fresh，直到整个 Workbench 进程关闭才过期。T2 字段级理想结果要求
「关闭 runtime 后远端 `runtime-lease.json` 不再是 fresh，或被明确 release」，
当前行为不满足，b1 不能按原状态收口。

### 根因

`stop_runtime`（`workbench/src-tauri/src/runtime.rs`）只调用 CLI
`runtime stop` 停止容器，不调用 `lease_release`。`lease_release`
（`workbench/src-tauri/src/lease.rs`）功能正常，但当前唯一调用点是
app 关闭时 `session.rs::release_all_leases`——与手测观察吻合：
只有关进程才释放。

### 修复方案

1. `stop_runtime` 成功执行 CLI stop 后，追加调用
   `crate::lease::lease_release`（同一 workspace）；
2. release 使用 `stop_runtime` 已解析的 target（b1 已保证 claim/heartbeat/
   release 共享 claim-time snapshot，不需要额外改动）；
3. release 失败不阻塞 stop 结果返回——容器已停，lease 会按 45s TTL 过期，
   记录 warning 即可（与 shutdown 的 best-effort 语义一致）；
4. 不改 lease schema、TTL、reconcile 判定、SSH transport、PTY 协议。

### 测试计划

自动化：

- Rust 测试：验证 `stop_runtime` 在 CLI stop 成功后触发 lease release
  （可用 mock/assert 函数调用顺序或抽 release 调用为可注入依赖）；
- 既有 `cargo test --lib` 全量通过（回归）。

手测复测：

- 重跑 HANDTEST T2 第 7–8 步：stop runtime 后远端 lease 立即不再 fresh
  （或文件被明确删除）；
- T1 / T3 不受影响（无需重跑，lease_release 路径不变）。

### 范围边界

- 只改 `stop_runtime` 的 lease 释放调用与对应测试；
- 不改 `remove_runtime`（remove 语义是否也需要 release 另行裁决）；
- 不动 PTY / session / UI 代码。

### 执行状态（2026-10-12 T2 返工）

- 新增 `release_lease_best_effort` helper + `stop_runtime` 接入，red→green 证据：
  - red：2 项测试因 helper 不存在编译失败；
  - green：实现后 2 项通过（验证 workspace 传递正确、release 失败被吞不阻塞 stop）。
- 全量门禁（fresh run）：
  - `cargo test --lib`：337 passed，0 failed，1 ignored；
  - `scripts/local-gates.ps1`：`LOCAL GATES: ALL GREEN`（pytest 1350 passed / cargo / vitest 518 passed / vue-tsc）。
- 实机复测：见下方 T2 复测记录。

### T2 复测记录（2026-10-12 23:12 实机，修复后 fresh run）

环境：`2.1.15-b1-remote-ssh-recovery` 分支 debug 构建（含 stop release 修复），
远端 `wsl-base`（172.21.90.157），工作区 `/home/wangyu/aisc-b1-t1`。

| 步骤 | 结果 |
| --- | --- |
| target_set/get → `wsl-base` remote | ✅ |
| reconcile | ✅ `stale_registry`，`can_proceed=true` |
| lease_claim | ✅ `claimed_stale`，`lease_id=4637c821…` |
| start_runtime | ✅ `running/ready` |
| heartbeat 采样 ×2（间隔 17s） | ✅ 均 fresh（age 5.5s / 7.8s） |
| **stop_runtime（修复点）** | ✅ `stopped`；**远端 lease 文件被明确删除（explicit release）** |
| stop 后 docker ps | ✅ 无运行容器 |
| stop 后 reconcile（原 step 8 等价） | ✅ `can_proceed=true`，无 `AISC_ERR_ACTIVE_WORKSPACE_LEASE` |

对照修复前：stop 后 lease 保持 fresh 直到整个 Workbench 进程关闭；
修复后 stop 即明确 release，T2 字段级理想结果「关闭 runtime 后
`runtime-lease.json` 不再是 fresh，或被明确 release」完全满足。

T1 / T3 不受影响（`lease_release` 路径与 claim-time snapshot 未变，
仅新增 stop 时的显式调用），无需重跑。
