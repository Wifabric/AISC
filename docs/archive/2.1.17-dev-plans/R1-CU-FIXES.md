# v2.1.17 R1 CU 修复轮：长扩展操作不阻塞控制面

> 2026-10-29 用户裁定：根据统一 CU 预手测结果先修复一轮。本文是 R1 的范围、
> 根因与验收结果；遵循 DEVELOP_WIKI §1.2 分支先行与 §1.4 CU 复测门。

## 背景

CU 预手测在 b1/b7 组安装执行期间切到 Services，首次服务读取出现
`AISC CLI 响应超时`；组操作结束后同一列表自动恢复。这不是 Services 数据面
失败：同一 runtime 的网关、HTTP 3000/5173 与 CLI 查询之后均通过。

## 根因定位

- Workbench 侧 `ServeSession.request` 已用 request id 多路复用，可同时发送
  多个请求。
- Python `aisc serve --stdio` 的 `_serve_loop` 逐行读取并在主循环内同步执行
  `_run_op`；代码中的既定约束是 “R1 is strictly serial”。
- `skill-install-group` / `skill-update-group` 可能运行数分钟，因此占住唯一
  resident serve 会话；并发的 `runtime services` 等 UI 控制面请求排队直至
  30 秒超时。

## 修复方案

暂不把 Python serve 改为并发执行：`_op_cli` 会替换进程级 `sys.stdin/stdout`
和 `AISC_RUN_ID`，并发后需要重新审计全部 CLI handler 的线程安全性，风险过大。

R1 在 Rust 路由层为两个长扩展组操作建立独立传输通道：

- `extensions skill-install-group` 与 `extensions skill-update-group` 不走
  全局 pooled serve；
- Local 直接 per-op spawn 保存的 pinned CLI；
- Remote 使用一次性 SSH argv（现有 `run_control_inner`），不建立第二条常驻池；
- 普通短控制面请求仍严格复用现有 pooled serve，保持性能与协议行为。

## TDD / 验收

1. 在 `workbench/src-tauri/src/cli.rs` 先添加路由分类单测：长组操作必须选择
   direct transport，`version/ps/runtime services/普通 extensions` 仍选择
   pooled transport；先运行确认 FAIL。
2. 实现最小路由 helper 并让 `run_control_target` 使用它；单测转 GREEN。
3. 运行 `cargo test --lib` 中 cli/serve 相关测试，确认未破坏现有 pooled 行为。
4. 重新构建保存产物同源的 Workbench/CLI，使用隔离数据根复测：启动 13 项组
   安装，在运行期间切换 Services 并刷新；理想为不再出现 30 秒 CLI 超时，HTTP
   服务行可读。若仍超时，保留原始输出并回到根因定位，不做投机改动。
5. CU 复测后更新 PRETEST / devlog / todo；不把未复测路径写成 PASS。

## 实施与验证（2026-10-29）

- TDD 先红后绿：`long_extension_group_ops_bypass_the_pooled_serve` 锁定
  `skill-install-group` / `skill-update-group` direct、`version` / `runtime services` /
  普通 `extensions list` pooled；实现 `is_long_extension_group_op`，并由
  `control_transport_for` 做 target-aware 路由。
- `run_control_target` 与 `run_control_input_target` 共用 target-aware
  `control_transport_for`：Local 与 Remote 的长组操作均走既有 per-op transport；
  Local `--events` 保持 direct，Remote `--events` 保持 pooled（与 R1 前一致）；
  普通短请求不变。
- Remote direct 命令前缀 shell-safe 的 `AISC_RUN_ID=<run_id>`，避免 OpenSSH 不转发
  环境变量时丢失 Workbench app log、CLI envelope 与 `cli_exit` 的同一 run_id。
- 本地门禁：Rust lib **400 passed / 1 ignored**、Workbench Vitest **770 passed**、
  文档检查 **39 passed / 0 warnings / 0 failures**；审查后最终生产
  `npm run tauri build -- --no-bundle` 通过。
- CU 复测 Workbench：
  `release-staging/2.1.17-r1/AISC-Workbench-2.1.17-R1.exe`，
  SHA256 `046fea420ff1756684bbfe7f8bbbabaa29aba4f1004ff25ced78da68731f7ea3`；
  显式复用 b7 CLI/bundle，镜像 `610cd7ebfa39…`。审查修复后最终生产副本为
  `AISC-Workbench-2.1.17-R1-final.exe`，SHA256
  `c74d1d1d0572f745fed0f5c089903e24953616643be07730c670ec9452885546`。
- Local CU 复测 PASS：真实 UI 发起 13 项 caveman 组安装后，宿主进程可见 direct
  `extensions skill-install-group`（父子两个 pinned CLI 进程是 bootstrap 形态，不是两次
  操作）。安装期间用真实命令面板切入 Services，`宿主工具（F2）`、`注册服务`、
  `docs preview :3000` 与端口 5173 立即可读，没有 30 秒 CLI 超时；同期 runtime services
  轮询约 5 秒一次，单次 250–297ms。组操作 exit 0，耗时 131297ms，13 个子技能
  Claude/Codex 均默认开启。
- 测试工具边界：默认宽度下市场组“安装全部”按钮被面板裁剪，CU 仅临时把 UI 字号缩放
  调至 0.8 并在复测后恢复为 1.0；这是测试操作适配，不判产品 FAIL。Remote direct 路径
  未做真实 SSH UI 复测，不能写成 PASS。
- 独立代码审查首轮发现 Remote direct `run_id` 与 Remote `--events` 语义问题；上述
  target-aware 路由、`AISC_RUN_ID` 前缀与回归测试已补齐。复审确认 Critical/Important
  均为 0；剩余“未直接执行 async dispatch 分支”的测试加固机会不阻塞合并。
- PR #48 已合并 develop `157473d1349d71e8620890d3ac1f26a694da2c21`。PR head 的
  frontend/rust/cli checks 全部 SUCCESS；develop 触发的 Workbench CI
  `40810806036`、Bundle Linux/macOS `40810806024`、NSIS `40810806048` 最终均为
  SUCCESS。Bundle 首轮 macOS job 因上游 npm registry HTTP 403 rate limit 失败，仅重跑
  该 failed job 后通过；Linux 首轮与 NSIS 均直接通过，未改源码。

## 非目标

- 不在本轮实现 Python serve 全并发。
- 不改变组操作 timeout、组进度语义或 Services UI。
- 不把 H1 未捕获 toast 判为产品 FAIL；现有 store 已有成功 toast 逻辑，除非
  新测试能复现缺失，否则不改。
