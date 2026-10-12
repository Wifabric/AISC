# v2.1.15 b3：CLI 输出后的终端滚动稳定性

> For agentic workers: 本文件是 b3 批次实施记录。执行须遵守分支先行、根因先行、
> TDD、本地门禁与远程 CI 全绿后并回 develop。行为裁决 D-2：不预设「输出结束
> 强制滚到底」，实现「不干扰手动滚动 + 可预期恢复跟踪」。

## 目标

修复「CLI 运行一轮后视口偶发跳到顶端」：用户手动回看历史时输出不得打扰视口；
退出回看/TUI 后恢复跟踪的行为可预期。只改前端滚动所有权，不动 PTY/会话/Rust。

## 反馈与证据

- 反馈：F2「偶尔 AISC 的 UI 在 CLI 运行一轮后滑轮（视口）跳到顶端」，severity `low`。
- 公开回复承诺：区分「用户正在回看历史」与「终端自动跟随输出」，避免输出刷新
  把视口拉顶；滚动策略可预期。

## 根因调查

### 已核对行为

1. xterm 6 输出跟随规则：只有视口已在底部时新输出才推动视口；用户上滚后输出
   不再打扰——该层是健康的，不是「拉顶」来源；
2. `loadEarlier` 的 `term.scrollToTop()` 仅按钮触发（回看分页的故意的落点），
   与本 bug 无关；
3. `rebuildTerminal`（渲染器/字体切换）重放后视口随光标在底部，非本轮触发；
4. **主嫌疑（与「偶发 + 运行一轮后」吻合）**：claude/codex CLI 是全屏 TUI，
   进入时 `CSI ?1049h` 切 alt-screen（xterm 保存 normal buffer 视口位置），
   退出时 `?1049l` 恢复**进入前的旧视口位置**——TUI 运行期间 normal buffer
   可能已变化，恢复点停在旧位置（往往是顶部方向），用户感知为「跳到顶端」。
   这是标准终端语义，但在 AISC 的「跑完一轮 agent 回到 bash」场景里违背直觉。

### 结论

按 D-2 实现显式滚动所有权，而不是逐个猜 TUI 的序列组合：

- 用户滚离底部 → 进入「回看」态：输出不打扰（xterm 默认已保证），
  `scrollOnUserInput` 的滚底也不触发（用户没在输入）；
- 用户在回看态敲键 → 先回底部再输入（标准的「输入即回现场」）；
- TUI 退出（`?1049l`）→ 若用户进入 TUI 前在跟流（非回看态），落在底部
  （新输出即现场）；若本来就在回看，不碰（保留其回看位置）。

## 修复范围

1. 新增 `scrollOwnership.ts` 纯状态机：`onUserScrollAtBottom/away`、
   `onUserInput`、`onAltScreenExit`、`shouldFollowOutput`；
2. 新增 alt-screen 切换探测器：扫描 writeChunks 的字节流找
   `ESC[?1049h` / `ESC[?1049l`（纯函数，可单测）；
3. `Terminal.vue` 接线：
   - viewport DOM `scroll` 事件 → 维护回看态（底部阈值内 = 跟流态）；
   - `onTermData`（用户键入）→ 退出回看 + 落底；
   - `writeChunks` 完成回调里检测到 `1049l` 且非回看态 → `scrollToBottom()`；
4. 不改 `loadEarlier` 的落顶语义（那是回看功能的故意的阅读起点）；
5. 不改 Rust / PTY / 会话层。

## 实施步骤

1. 失败测试：`scrollOwnership.test.ts`（状态机全迁移路径）+
   alt 探测器测试（h/l/无序列/分片跨块）；
2. 实现 `scrollOwnership.ts` + 探测器；
3. Terminal.vue 接线（scroll 监听 / onTermData / writeChunks 回调）；
4. 全量门禁（vitest / vue-tsc / cargo / local-gates）；
5. Windows 实机手测（见下）；
6. 提交推送 → PR CI 全绿 → 并回 develop。

## 手测计划（四要素）

**前置**：Workbench 运行，bash pane；`claude`（或任意全屏 TUI，如 `vim`）可启动；
回滚区有历史内容。

**步骤**：
1. bash 里 `printf '%s\\n' {1..200}` 生成回滚，确认视口在底部；
2. 滚轮上滚 10 行回看 → 等待 5 秒（无输出时视口不动）；
3. 运行 `claude`（TUI 进 alt-screen）→ 完成一轮退出回 bash →
   视口应落在 bash 最新提示符处（不跳顶）；
4. 重复步骤 2 后运行 `vim`（不退出）确认回看态下视口不被打扰，
   `:q` 退出 → 视口落底；
5. 回看态下敲任意键 → 视口回底部（输入即回现场）。

**理想结果**：3/4 不跳顶；5 回底部；2 期间视口纹丝不动。

**异常判定**：视口跳顶 / 回看态被打断 / 敲键不回底 → 记录复现序列报批。

## 风险与回滚

- 风险：`1049h/l` 检测误报（序列跨 chunk）。缓解：跨块用 7 字节滑窗缓存
  尾部；纯函数单测覆盖跨块切分。
- 风险：回看态误判（阈值内抖动）。缓解：底部阈值 8px + 状态机只在
  「明确离开底部」时进回看。
- 回滚：revert 单 commit；Rust/CLI 零改动。
