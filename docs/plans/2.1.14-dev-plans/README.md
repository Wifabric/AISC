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
| 3 | UI 对齐四项（高级槽位间距 / 历史页徽标 / 关于弹窗超高 / picker 窄窗挤压〔D-12 收编 todo:150〕） | 2.1.14-b3-ui-align-fixes | 计划待验收 |
| 4 | 终端键盘域（Ctrl+/ 直发修复 + 分屏导航 Ctrl+Shift+hjkl〔D-10 收编 todo:81〕） | 2.1.14-b4-ctrl-slash-key | 计划待验收 |
| 5 | 顶栏「关闭工作区」回 picker（复用 closeWorkspace 链，三入口） | 2.1.14-b5-close-workspace | 计划待验收 |
| 6 | 网络保底构建（D-11 升级 + D-15 解耦铁律：npm 四包预置 + 全触点离线化 + 降级链设计；专项调研进行中） | 2.1.14-b6-build-network | 计划待验收 |

统一手测清单：[HANDTEST.md](HANDTEST.md)（批 1-6，按 §1.3 四要素书写；核验员
证伪项均已回灌预期，见各批「异常判定」）。

## 计划文档索引

| 文档 | 条目 | 状态 |
| --- | --- | --- |
| [decisions.md](decisions.md) | 阶段裁决日志（D-1/D-10~D-12 用户裁定；D-2~D-9/D-13 立项规划裁定；开放项 U-4/U-6/工作记录歧义） | 持续更新 |
| [selfupdate-polish.md](selfupdate-polish.md) | 批 1：自更新三项 | 计划待验收 |
| [provider-add-fidelity.md](provider-add-fidelity.md) | 批 2：provider 新建保真（保存漂移 + 模型拉取合批） | 计划待验收 |
| [ui-align-fixes.md](ui-align-fixes.md) | 批 3：UI 对齐四项（含 picker 窄窗） | 计划待验收 |
| [ctrl-slash-key.md](ctrl-slash-key.md) | 批 4：终端键盘域（Ctrl+/ + 分屏导航） | 计划待验收 |
| [close-workspace.md](close-workspace.md) | 批 5：关闭工作区回 picker | 计划待验收 |
| [build-network.md](build-network.md) | 批 6：网络保底构建（反馈 #1 履约 + D-11 升级） | 计划待验收 |
| [HANDTEST.md](HANDTEST.md) | 批 1-6 统一手测清单 | 随批滚动 |

## 阶段范围

`docs/todo.md`「v2.1.14-target」：既有排期项（2.1.13 转期三项 + provider
两条 + UI 两条）+ 4 条反馈站项（2026-09-22 反馈：构建网络 / Ctrl+/ /
徽标对齐 / 关闭工作区，按 D-1 用户指示纳入）+ 悬账收编项（D-12：picker
窄窗、分屏导航、docker 破坏性边界裁决）。「工作记录」概念已撤销（D-14）。

## 悬账清单（2026-09-23 用户裁定全部收编，D-12）

- `docs/todo.md:81` 分屏键盘导航 → **批 4**（D-10）；
- `docs/todo.md:150` picker 窄窗挤压 → **批 3**；
- `docs/todo.md:191` docker 管理破坏性操作边界 → **本版立边界裁决**（D-13
  代定草案：清单制 + owned-only + 三重不变量 + 永不触碰 aisc 外资产）。

## 流程项

- preview 发布形态沿用 D-8（2.1.13）规约：阶段收口时发 `v2.1.14-preview.1`
  （`.devN` 形态、CI 版本戳已生效）；final 发布仅经用户明确要求。
- 反馈站 4 条回复：**已回执**（2026-09-23，按反馈站 README 工作流改 md +
  push，status → in-progress；构建网络条已校准口径为「预置/参数修复/引导」
  并顺带追问成功前置操作）。
