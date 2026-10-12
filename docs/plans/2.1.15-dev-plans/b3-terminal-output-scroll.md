# v2.1.15 b3：CLI 输出后的终端滚动稳定性

> For agentic workers: 本文件是 b3 批次实施记录。执行须遵守分支先行、根因先行、
> TDD、本地门禁与远程 CI 全绿后并回 develop。行为裁决 D-2：不预设「输出结束
> 强制滚到底」，实现「不干扰手动滚动 + 可预测恢复跟踪」。

## 目标

修复「Codex CLI 运行一轮后视口跳到顶端/历史消失」：用户手动回看历史时输出不得
强迫视口；退出回看/TUI 后恢复跟踪的行为可预测。只改前端滚动所有权与 xterm 解析
层守卫，不动 PTY/会话/Rust。

## 反馈与证据

- 反馈：F2「偶尔 AISC 的 UI 在 CLI 运行一轮后滑轮（视口）跳到顶端」，severity `low`。
- 用户补充：该问题主要出现在 **Codex CLI** 使用过程中。
- 实机抓包（远程 runtime，`codex-cli 0.154.0`）确认：
  - Codex 启动/重绘时没有 `CSI ?1049h`；
  - 启动序列包含 `CSI H + CSI 2J + CSI 3J`；
  - 退出序列附近有 `CSI ?1004l`、`CSI 1;1H + CSI J`，随后回到 bash prompt；
  - `CSI 3J` 是 xterm 的 Erase in Display (ED3)：从 normal buffer 裁掉全部
    scrollback，并把 `ybase`/`ydisp` 一起重置。实机 200 行历史清空后，滚动条
    从部分高度变回全屏，用户看到的就是“跳回顶部、历史没了”。
- 实机补充（远程 runtime 意外升级到 `codex-cli 0.162.1`）确认：
  - 该版本会切到 alt-screen，并同时启用 application cursor/keypad；
  - 启用 focus/协议查询后，xterm 会把 focus report、cursor position、primary DA
    和 OSC 颜色报告经 `onData` 返回；这些字节是终端协议响应，不是用户键入；
  - 因此 `onTermData` 需要过滤这类整包协议响应，否则回看态会被误当成“用户
    回到现场”；
  - alt-screen 退出时，xterm 在解析期间先恢复 normal-buffer 的旧视口，
    同一个 write callback 立即 `scrollToBottom()` 过早，需要延后到宏任务执行。
  - 本次测试环境里 `0.162.1` 进程已启动并改变 terminal mode，但 TUI 长时间
    未渲染；因此该版本只作为协议响应/alt-screen 边界证据，不作为 ED3 主根因
    的通过判据。

## 根因调查

### 已核对行为

1. xterm 6 输出跟随规则：只有视口已在底部时新输出才推动视口；用户上滚后正常
   输出不再打扰——该层是健康的，不是「拉顶」来源；
2. `loadEarlier` 的 `term.scrollToTop()` 仅按钮触发（回看分页的故意的落点），
   与本 bug 无关；
3. `rebuildTerminal`（渲染器/字体切换）重放后视口随光标在底部，非本轮触发；
4. **Codex 主根因**：Codex 0.154 不切 alt-screen，而是启动时用 `CSI 3J`
   清掉 xterm scrollback。xterm 默认语义立即裁剪历史并重置视口索引；即使用户
   原来在跟流，也会表现为视口跳顶，后续退出 Codex 时历史已经丢失；
5. **Claude/vim 等全屏 TUI 的次级行为**：`CSI ?1049h/l` 会保存并恢复进入前的
   normal-buffer 视口，可能停留在旧位置。该路径仍需滚动所有权处理，但它不是
   Codex 主问题的解释；
6. **Codex 0.162 次级路径**：该版本切 alt-screen，焦点/协议查询会让 xterm 经
   `onData` 返回协议响应；同时 alt-screen 退出恢复视口的时机早于 write callback，
   需要协议响应过滤和延迟落底配合。

### 结论

按 D-2 实现两层可组合策略：

- **Codex ED3 守卫**：在 xterm parser 注册最新 `CSI J` handler；仅当参数为 3
  时返回 true，阻止 xterm 默认裁剪 scrollback。ED0（erase below）和 ED2
  （清屏/重绘 TUI）继续交给 xterm，避免破坏 Codex 或 `clear` 的正常画面；
- **显式滚动所有权**：用户滚离底部 → 回看态；回看态敲键 → 先回底部；alt-screen
  退出 → 跟流态落底，回看态不打扰。

## 修复范围

1. 新增 `scrollOwnership.ts` 纯状态机：`onUserScrollAtBottom/away`、
   `onUserInput`、`onAltScreenExit`、`shouldFollowOutput`；
2. 新增 alt-screen 切换探测器：扫描 writeChunks 的字节流找
   `ESC[?1049h` / `ESC[?1049l`（纯函数，可单测）；
3. 新增 ED3 判定 `isEraseScrollbackRequest`：只有显式参数 3 返回 true，
   空参数/ED0/ED2 均放行；
4. `Terminal.vue` 接线：
   - mount 和 renderer/font rebuild 后都注册 Codex ED3 guard；
   - capture 阶段监听真实用户 wheel（xterm 6 的 viewport DOM 不再暴露可靠
     scroll metrics）维护回看态；
   - `onTermData`（用户键入）→ 退出回看 + 落底；但 focus report、cursor
     position、primary DA、OSC 10/11 颜色报告和 DCS 响应属于终端生成的整包
     协议响应，不得视作用户键入；
   - `writeChunks` 完成回调里检测到 `1049l` 且非回看态 → 先延迟到宏任务，
     再 `scrollToBottom()`，避免抢在 xterm 恢复 normal-buffer 视口前执行；
5. 不改 `loadEarlier` 的落顶语义（那是回看功能的故意的阅读起点）；
6. 不改 Rust / PTY / 会话层。

## 实施步骤

1. 失败测试：
   - ownership 状态机全迁移路径；
   - alt 探测器 h/l、无序列、分片跨块；
   - ED3 判定以及真实 xterm parser 收到 ED3 后保留 buffer；
   - Terminal.vue 实际注册 CSI J guard，且 ED0/ED2 不被吞；
2. 实现 `scrollOwnership.ts` + 探测器 + ED3 guard；
3. Terminal.vue 接线（wheel / onTermData / writeChunks 回调 / parser guard）；
4. 全量门禁（vitest / vue-tsc / cargo / local-gates）；
5. Codex / 终端协议实机手测（见下）；
6. 提交推送 → PR CI 全绿 → 并回 develop。

## 手测计划（四要素）

**前置**：Workbench 运行，远程 bash pane；`codex` 可启动；回滚区有历史内容。

**步骤**：
1. bash 里 `printf '%s\n' {1..200}` 生成回滚，确认视口在底部；
2. 滚轮上滚 10 行回看 → 等待 5 秒（无输出时视口不动）；
3. 启动 Codex → 完成一轮并退出回 bash：
   - 视口应回到最新 bash 提示符，不跳到顶部；
   - 先前历史仍可回看（例如仍能找到生成的行号）；
4. 重复步骤 2 后运行 `vim`（验证 alt-screen 回归）：回看态启动时视口不被输出
   强迫，`:q` 退出且之前处于跟流态 → 视口落底；
5. 回看态下敲任意键 → 视口回底部（输入即回现场）。

**理想结果**：3 不跳顶且历史保留；4 alt-screen 退出跟流态落底；5 回底部；
2 期间视口纹丝不动。

**0.162/协议补充验证记录**：

- 回看态下延迟发送 xterm 协议查询（`CSI 6n`、primary DA、OSC 11 query），
  xterm 经 `onData` 返回响应后，`shouldFollowOutput()` 仍为 false，视口索引
  保持不动；
- 回看态下回放 Codex `0.154` 启动序列 `CSI H + CSI 2J + CSI 3J`：ED3 被
  parser guard 拦截，`length`/`baseY` 未被裁剪重置，视口仍留在回看位置；
- `0.162.1` 实机进程启动后切 application cursor/keypad，但该次远程环境 TUI
  未完成渲染；其 alt-screen/协议响应行为由单测与上述协议查询实机验证覆盖，
  ED3 主路径以 `0.154` 精确序列验证。

**异常判定**：Codex 退出跳顶 / 200 行历史被清空 / 回看态被打断 / 敲键不回底 →
记录复现序列报批。

## 风险与回滚

- 风险：ED3 守卫改变用户显式 `clear -x` 的 xterm 默认历史清理语义。缓解：这是
  AISC 的刻意取舍——保留会话历史优先；ED2 画面清屏仍正常，可用回滚或 revert
  单 commit 恢复标准语义。
- 风险：`1049h/l` 检测误报（序列跨 chunk）。缓解：跨块用 7 字节滑窗缓存
  尾部；纯函数单测覆盖跨块切分。
- 风险：回看态误判（阈值内抖动）。缓解：状态机只在「明确离开底部」时进回看。
- 回滚：revert 单 commit；Rust/CLI 零改动。
