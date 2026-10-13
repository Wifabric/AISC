# v2.1.15 开发计划（2026-10-12 反馈驱动开题）

> 2026-10-12 按用户指示读取反馈站公开内容，把 5 条新反馈纳入下一版开发计划。
> 本文档是 v2.1.15 阶段索引；各批实施须按《AISC 开发流程交接》切独立分支，
> 并按批次计划、TDD、本地门禁、远程 CI 和实机手测闭环。

## 交付状态

| 批 | 内容 | 建议优先级 | 分支（实施时创建） | 终态 |
| --- | --- | --- | --- | --- |
| b1 | SSH 远程会话启动阻塞排查修复 | P0 | `2.1.15-b1-remote-ssh-recovery` | 已完成 |
| b2 | Windows 工作区路径大小写归一与历史去重 | P1 | `2.1.15-b2-workspace-path-identity` | 已完成 |
| b3 | CLI 输出后的终端滚动稳定性 | P1 | `2.1.15-b3-terminal-output-scroll` | 已完成 |
| b4 | 顶部状态栏拖拽边界与历史会话模型调研 | P2 | `2.1.15-b4-ui-history-model` | 已完成 |
| b5 | PTY 输出流断流修复（b1 手测发现） | P1 | `2.1.15-b5-pty-output-stream` | 已完成 |
| b6 | Work Record / Collection 完整语义 | P2 | `2.1.15-b6-work-record-collection` | 已完成 |

批次数量、实现顺序和范围调整以后续用户裁决为准；实施分支必须从最新 `develop`
创建，本地门禁与远端 CI 全绿后并回 `develop`。

2026-10-14 状态：b1–b6 全部并回 `develop`。b6 Work Record / Collection 已实施完成：
PR #9 已合并，本地门禁与 develop CI 全绿，T6 实机验证（真实 running session
确认删除 → session 终止、collection 与双引擎 transcript 级联消失、无误伤）PASS，
README 与 CLI 参考已补充 Work Records 用法，详见
[b6-work-record-collection.md](b6-work-record-collection.md) 执行状态。b3 的 Codex `0.154` ED3 主路径与终端协议响应已实机/自动化
验证；`0.162.1` 在该次远程环境中 TUI 未完成渲染，详见
[b3-terminal-output-scroll.md](b3-terminal-output-scroll.md) 执行状态。b5 的
pump timeout/EINTR 修复已通过 transport、Workbench UI 数据面 >70s 长流验证；
详见 [b5-pty-output-stream.md](b5-pty-output-stream.md) 执行状态。

## 反馈来源与范围

- 来源：`https://feedback.alanevergarden.xyz`
- 抓取时间：2026-10-12
- 新反馈：5 条（首轮回复前 status 均为 `submitted`，当前均为 `replied`）
- 明细、初步归因和首轮回复见 [feedback-intake.md](feedback-intake.md)。
- 现有 4 条 2026-09-22 反馈已在 v2.1.14 解决，本周期不重复处理。

## 阶段范围（草案）

1. **P0 稳定性**：SSH 远程会话进入 CLI bash 后光标卡住或打开会话报错；先消费
   反馈诊断包并复现，再定位远端 shell 启动、PTY、协议版本或凭据配置链路。
2. **P1 数据正确性**：Windows 下同一路径仅大小写不同时，工作区身份、历史记录和
   显示必须归一；不得破坏 Linux/macOS 的大小写敏感语义。
3. **P1 交互正确性**：CLI 输出运行期间用户手动回看历史时，输出流不得把视口强推
   到顶部；输出结束后的滚动策略要可预期。
4. **P2 UI 边界**：顶部 bash/codex/claude 状态栏不应作为上下拖拽/调整边界。
5. **P2 会话模型**：重新梳理 AISC 工作记录、runtime 子记忆空间与 CLI 原生
   resume 会话的映射，先产出调研与方案，经裁决后再实施。

## 反馈站回复处置

2026-10-12 16:35 已按 `Wifabric/aisc-issues-feedback` 根目录 README 的开发者工作流，
为 5 条新反馈追加首轮回复，并将状态从 `submitted` 更新为 `replied`。反馈数据仓库
提交为 `e597278 feedback: reply to 2026-10-12 reports`，已推送到 `main`。

回复正文和各条目标状态见 [feedback-intake.md](feedback-intake.md)。`索引.md` 由
反馈站自动维护，未手动修改；站点列表和详情缓存按 README 承诺在 5 分钟内刷新。
