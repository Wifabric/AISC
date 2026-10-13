# v2.1.15 b5：PTY 输出流断流修复

> For agentic workers: 本文件是 b5 批次计划。执行须遵守分支先行、根因先行、
> TDD、本地门禁与远程 CI 全绿后并回 develop。

## 目标

修复 Workbench bash 会话中 PTY 输出流在初始输出后停止、但输入仍可达的断流
问题。b5 只处理远端 serve 进程的 PTY pump 链路，不借机调整 lease、reconcile
或 UI 会话模型。

## 现象与证据（b1 手测期间发现）

- 现象：Workbench session 输出流在收到首批输出（约 249 bytes）后死亡；
  输入仍到达容器（`touch /tmp/WORKBENCH_INPUT_OK` 在容器内生效）。
- 新开的 split pane / 新 session 输出正常；只有旧 session 断流。
- 远端排查证据：
  - Docker socket `Recv-Q` 持续积压（2543+ bytes 无人读取），
    说明 serve 进程侧不再消费 exec socket；
  - 直连 `aisc serve --stdio` 协议测试输出正常；
  - SSH 手动 PTY 测试输出正常；
  - 仅 Workbench 长驻 session 复现。
- 临时 instrumentation（`AISC_PTY_PUMP_DEBUG`，手测后已移除）显示 pump
  线程在首块输出后进入退出路径。

## 根因

`InteractiveStreamHandle._pump_loop()` 把任何读异常都当作 stream 死亡。
upgraded Docker exec socket 可能继承 read timeout；空闲读抛出的
`socket.timeout` / `TimeoutError`，以及可重试的 `InterruptedError`，都不是
EOF。pump 提前退出后 socket 无人读取，后续 PTY 输出滞留，但 stdin 仍可写。

## 修复方向

1. 为 pump 循环补最小失败测试：模拟多帧到达，断言 pump 持续消费到 EOF；
2. 修正退出条件判定，保证：
   - 只有真实 EOF / resize 错误 / 显式 stop 才退出；
   - 帧边界不触发伪 EOF；
3. 回归 HANDTEST：长会话（>70s，多次输出）输出流不中断；
4. 不改 lease / session / UI 代码。

## 验收形态

- 新增 pytest 覆盖 pump 多帧消费与伪 EOF 不退出；
- 手测：Workbench 打开 bash，持续输出 >70s 无断流；输入回显正常；
- 全量本地门禁 + 远程 CI 全绿。

## 分支

`2.1.15-b5-pty-output-stream`（从 develop 切出）。

## 执行状态（2026-10-13）

**已完成（分支内实现与验证）**

- 分支：`2.1.15-b5-pty-output-stream`（从 `42f3d03` / develop 切出）。
- 修复：`src/aisc/adapters/docker_gateway.py` 的 pump 循环单独捕获
  `(socket.timeout, TimeoutError, InterruptedError)` 并继续读；只有零字节读
  才视为 EOF。`kill()` 的显式 stop 路径保持不变。
- TDD 红：新增 `tests/test_docker_gateway_pty_stream.py`，修复前 timeout /
  EINTR 两个场景失败，均只收到 `b"first\n"`；EOF 与 `kill()` 场景通过。
- TDD 绿：修复后该文件 4 passed。
- 相关回归：`tests/test_docker_gateway_query.py tests/test_serve.py`
  55 passed。
- 全量本地门禁：`scripts/local-gates.ps1` 全绿；Python 1357 passed /
  53 skipped，cargo lib 通过，vitest 71 files / 536 tests passed，
  vue-tsc 通过。
- transport 级实机长流：source Python 直接调用
  `SdkGateway.open_pty_stream()`，对真实 Docker exec PTY 发送 15s 间隔
  marker。90.72s 内 12 chunks / 1077 bytes，7 个 marker（6 个间隔 marker +
  final）全部到达，bash exit 0，`pump_eof: true`。进程退出后的 Windows
  Npipe `(109, 'ReadFile', '管道已结束。')` 是 post-exit close 语义，不是
  断流。

**Workbench UI 长流验证**

- 环境：重建并同步 Windows sidecar 后启动 debug Workbench；连接
  `wsl-base` / runtime `4f7750f4-fe83-4842-a946-e1cdf869d63e`；新建 bash
  tab，真实 Workbench Rust / SSH / remote serve / PTY / spool / store 链路。
- 输入驱动说明：CDP 自动化无法可靠注入自然键盘 xterm `onData`；命令下行通过
  页面内 `invoke("write_session")` 提交。这正是 `Terminal.onTermData` 调用的
  同一 Tauri command，因此验证的是 Workbench UI 会话数据面，但不声称完成
  自然键盘输入 UX 手测。
- 远端 CLI `0.1.3` 原版代码复测时观察到间歇性 prompt 后停流；因此为验证本
  批次修复，临时通过 `/tmp` SSH launcher wrapper 把
  `InteractiveStreamHandle._pump_loop` 替换为本分支同一逻辑，只影响新建验证
  会话；验证后立即还原 launcher，并确认 size/mtime 与备份一致。
- 结果：echo ready 后发送 24 个 3s marker。75.25s 时 cursor 140、
  Workbench pane buffer 2608 bytes，`B5_FIXED_MARKER_1..24` 与 final 全部
  到达；UI store 解码后 `hasFinal=true`。远端 pump 日志同样记录 final chunk。
- 结论：本分支 pump 修复在 Workbench UI 数据面验证 PASS。生产远端 CLI 仍为
  `0.1.3` 原版；待该修复随远端 CLI 常规发布后，应对未打补丁路径做常规
  复测。
