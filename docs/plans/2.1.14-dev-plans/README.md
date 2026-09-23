# 2.1.14 开发计划

> 2026-09-23 开池（Workbench 版本线 bump 2.1.13 → 2.1.14，随批 1 落地）。
> 同日用户指示开题：「阅读 todo 中给 2.1.14 版本 target，以及
> aisc-issues-feedback 下搜集的问题，重新整理 2.1.14 的 todo，并按规约制定
> 开发计划」。当日完成立项研究（ultracode workflow：10 研究员 + 14 独立
> 证据/替代根因核验 + 1 完备性批评，两轮 39 子 agent；含一次 StructuredOutput
> 空转中断处置与一次 429 限流重试，两份首轮核验裁决已从 journal 抢救回灌）。
> 范围 = todo 8 条转期/预置项 + 反馈站 4 条（D-1）。开发严格以本文档集为准
> （DEVELOP_WIKI §1.1）。

## 交付状态（开题基线）

| 批 | 内容 | 分支 | 终态 |
| --- | --- | --- | --- |
| 1 | 开池版本 bump + 自更新三项（/R 静默拉起 / staging 目标版本命名 / PATH REG_EXPAND_SZ） | 2.1.14-b1-selfupdate-polish | 计划待验收 |
| 2 | provider 新建保真合批（保存漂移 + 模型拉取，含容器侧端点数据修复） | 2.1.14-b2-provider-add-fidelity | 计划待验收 |
| 3 | UI 对齐三小项（高级槽位间距 / 历史页徽标 / 关于弹窗超高） | 2.1.14-b3-ui-align-fixes | 计划待验收 |
| 4 | Ctrl+/ 终端键盘修复（xterm 6.0 映射缺口；含分屏导航悬账同批裁决） | 2.1.14-b4-ctrl-slash-key | 计划待验收 |
| 5 | 顶栏「关闭工作区」回 picker（复用 closeWorkspace 链，三入口） | 2.1.14-b5-close-workspace | 计划待验收 |
| 6 | 构建网络：宿主 TUN 代理下构建失败（yazi 预置 + 保守分支 glob + 超时 + GH_PROXY 通道 + 失败诊断） | 2.1.14-b6-build-network | 计划待验收 |
| — | 「工作记录」需求问询（不占批次，用户裁决后排期） | — | 问询材料已备 |

统一手测清单：[HANDTEST.md](HANDTEST.md)（批 1-6，按 §1.3 四要素书写；核验员
证伪项均已回灌预期，见各批「异常判定」）。

## 计划文档索引

| 文档 | 条目 | 状态 |
| --- | --- | --- |
| [decisions.md](decisions.md) | 阶段裁决日志（D-1 用户范围裁定；D-2~D-9 立项规划裁定；U-1~U-7 待用户裁决） | 持续更新 |
| [selfupdate-polish.md](selfupdate-polish.md) | 批 1：自更新三项 | 计划待验收 |
| [provider-add-fidelity.md](provider-add-fidelity.md) | 批 2：provider 新建保真（保存漂移 + 模型拉取合批） | 计划待验收 |
| [ui-align-fixes.md](ui-align-fixes.md) | 批 3：UI 对齐三小项 | 计划待验收 |
| [ctrl-slash-key.md](ctrl-slash-key.md) | 批 4：Ctrl+/ 切换 btw/main | 计划待验收 |
| [close-workspace.md](close-workspace.md) | 批 5：关闭工作区回 picker | 计划待验收 |
| [build-network.md](build-network.md) | 批 6：构建网络（反馈 #1 履约） | 计划待验收 |
| [worklog-questionnaire.md](worklog-questionnaire.md) | 「工作记录」六组歧义问询材料 | 待用户作答 |
| [HANDTEST.md](HANDTEST.md) | 批 1-6 统一手测清单 | 随批滚动 |

## 阶段范围

`docs/todo.md`「v2.1.14-target」：8 条既有排期项（2.1.13 转期三项 + provider
两条 + UI 两条 + 工作记录概念）+ 4 条反馈站项（2026-09-22 反馈：构建网络 /
Ctrl+/ / 徽标对齐 / 关闭工作区，按 D-1 用户指示纳入）。

## 悬账清单（开题提请用户裁决，不默认入版）

- `docs/todo.md:191`（2.1.13 尾巴）：workbench 内 docker 管理「破坏性操作
  边界」裁决未立计划（批 7 docker-management 已按清单外不做收口，此为
  后续扩张的操作面边界裁决）；
- `docs/todo.md:81`（20260810）：分屏键盘导航 Ctrl+Shift+hjkl / Ctrl+方向键
  （WebView2 加速器拦截，COM 方案已放弃）——与批 4 同域同病根，建议随批 4
  一并裁决（入批或显式转期）；
- `docs/todo.md:150`（2.1.11）：picker 窄窗持续挤压（width-clamp 进 zoom），
  此后未入任何 target。

## 流程项

- preview 发布形态沿用 D-8（2.1.13）规约：阶段收口时发 `v2.1.14-preview.1`
  （`.devN` 形态、CI 版本戳已生效）；final 发布仅经用户明确要求。
- 反馈站 4 条回复：立项后统一回执（U-7）——三条「已收到」按「已排入
  v2.1.14 + 一句话修法方向」口径；构建网络条追加研究结论摘要，把「排查
  和修复」校准到具体交付物（预置/参数修复/引导，非根治宿主 TUN 覆盖）。
