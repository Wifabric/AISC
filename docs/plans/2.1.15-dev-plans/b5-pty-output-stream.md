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

## 根因假设

`src/aisc/adapters/docker_gateway.py` 的 PTY pump 循环在首块输出后错误地
触发退出条件（疑似 `_stopped`/EOF 判定与帧边界处理交互），线程退出后
socket 无人读取，Recv-Q 积压，后续输出全部滞留。

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
