# Issue tracker: GitHub

工单与 spec 落在 GitHub（Wifabric/AISC），用 gh CLI 操作。

## 入口

- **用户反馈**：经反馈站 `Wifabric/aisc-issues-feedback`（文件式，`索引.md` + `issues/`）。它是开题阶段的输入来源，不是这里的工单。
- **实现工单 / 批次**：以 GitHub PR 承载（历史批次 PR #109–#122）；需要单独工单时用 `gh issue`。

## 约定

- 建工单：`gh issue create --title "..." --body "..."`（多行正文用 heredoc）。
- 读工单：`gh issue view <number> --json number,title,body,labels,comments`。
- 列工单：`gh issue list --state open --json number,title,body,labels --jq '[.[] | {number, title, body, labels: [.labels[].name]}]'`。
- 建 / 读 PR：`gh pr create` / `gh pr view <number>` / `gh pr diff <number>`。

## PR 作为三态面

**PRs as a request surface: no.**

## 何时说「发布到工单跟踪器」

创建 GitHub issue（或对应批次 PR）。
