# 2.1.13 开发计划（已收口 2026-09-22，归档于 docs/archive/2.1.13-dev-plans/）

> 2026-09-19 开池（Workbench 版本线 bump 2.1.12 → 2.1.13）。同日用户定稿阶段范围
> （docs/todo.md「v2.1.13-target」）并作裁决：D-1 Pi/opencode 本阶段不做（同日澄清）、
> D-2 docker 检测精细化（不自动清理）、D-3 局域网暂缓；随后验收计划时确认 D-4（CI 版本戳）
> 与 D-6（变更页仿 vscode git 页、纯显示零操作）。当日完成立项研究（ultracode workflow：
> 研究员 + 独立证据核验）并落全部计划文档。开发严格以本文档集为准（DEVELOP_WIKI §1.1）。
>
> **收口（2026-09-22，用户宣布）**：十二批次全部交付、手测全部 PASS；v2.1.13-preview.1
> 发布（D-8 形态）；自更新 E2E 实测通过（2.1.12-preview.1 → v2.1.13-preview.1 全链）。
> 「工作记录」（history-worklog.md 批 3）经用户裁决移入待解决池（待需求捋清再立项）。
> 自更新体验三项观察（静默拉起/staging 文件名/PATH REG_EXPAND_SZ）转期 v2.1.14。

## 交付状态（终态：全部交付 + 手测 PASS，随 v2.1.13-preview.1 发布）

| 批 | 内容 | 分支 | 终态 |
| --- | --- | --- | --- |
| 1 | 发布链准备（CI 版本戳 + 文案三处 + run 防重入） | 2.1.13-b1-release-chain | 已发布；自更新 E2E 验证版本戳生效 |
| 2 | zip 恢复工作区 | 2.1.13-b2-zip-restore | 手测 PASS |
| 3 | 远程 CLI 配对提示 | 2.1.13-b3-remote-pairing | 手测 PASS（UI 提示正确，用户确认） |
| 4 | docker 检测精细化 | 2.1.13-b4-docker-inspect | 手测 PASS（镜像类已可见） |
| 5 | 变更页（git 双源+树+diff）+ D-11 预览移除 | 2.1.13-b5-changes-page | 手测 PASS（2026-09-22 用户确认） |
| 6 | 拖图/粘贴图给 agent | 2.1.13-b6-image-drag | 手测 PASS |
| 7 | Docker 资源管理（容器/镜像操作，D-12） | 2.1.13-docker-management | 手测 PASS |
| 8 | worklog 账本 + 终端恢复链闭环 | 2.1.13-b8-* | 手测 PASS（T1-T4 + 早期输出全链） |
| 9 | 历史页按 agent 分组 | 2.1.13-b9-history-grouping | 手测 PASS |
| 10 | provider 切换后 resume 修复 | 2.1.13-b10-resume-provider | 手测 PASS（镜像重建后全链验证） |
| 11 | 聊天式只读对话查看器 | 2.1.13-b11-chat-view | 手测 PASS（T1-T3） |
| 12 | 资源管理器滚动修复 | 2.1.13-b12-explorer-scroll | 手测 PASS |

统一手测清单：[HANDTEST.md](HANDTEST.md)（批 1-12 全部收口）。

## 计划文档索引（终态）

| 文档 | 条目 | 终态 |
| --- | --- | --- |
| [decisions.md](decisions.md) | 阶段裁决日志（D-1~D-3 用户裁定；D-4~D-10 立项规划裁定） | 闭环 |
| [selfupdate-e2e.md](selfupdate-e2e.md) | 自更新端到端实测 + CI 版本戳修正 | 已验收（2026-09-21 实测通过；D-4 版本戳随批 1 落地） |
| [remote-cli-pairing.md](remote-cli-pairing.md) | 远程 CLI 版本配对「需更新」提示 | 已验收（用户确认 UI 正确） |
| [long-conversation-repro.md](long-conversation-repro.md) | 长对话恢复 bug 取证协议 | 闭环（根因在批 8/10 链路修复中落地，无需复现样本） |
| [history-worklog.md](history-worklog.md) | 历史会话重构（工作记录 + 只读聊天视图） | 批 2 已交付；批 3「工作记录」用户裁决移入待解决池 |
| [changes-page.md](changes-page.md) | 变更页（git 双源 + 变更树 + diff） | 已验收（2026-09-22 用户确认） |
| [workspace-zip-restore.md](workspace-zip-restore.md) | 导出 zip 恢复工作区到新路径 | 已验收 |
| [docker-scan-fidelity.md](docker-scan-fidelity.md) | docker 资源检测精细化 | 已验收 |
| [pi-opencode.md](pi-opencode.md) | （已作废）agent 加上 Pi/opencode | 作废备查 |
| [HANDTEST.md](HANDTEST.md) | 批 1-12 统一手测清单 | 全部收口 |
| [image-drag-to-agent.md](image-drag-to-agent.md) | 拖动图片给 agent（含剪贴板粘贴） | 已验收 |
| [docker-management.md](docker-management.md) | Docker 资源管理（容器/镜像操作，D-12） | 已验收 |

流程项：**final 发布时机**——按 D-8 规约仅经用户明确要求（本阶段发布止于 v2.1.13-preview.1）。

## 阶段范围与状态（终态：docs/todo.md「v2.1.13-target」全部 [x]，2026-09-22 收口）

全部条目闭环，勾选记录见 todo；「设备性能受限稳定运行」按 2026-09-19 裁决以既有 PERF
基础（v2.1.9 P1-P9）为底线通过，专项深化（P6b/P10、存量容器限额、低配实测）留待需要时立项。

## 转期与移出（收口终态）

- **转期 v2.1.14**（2026-09-22 用户裁决）：自更新体验三项——静默装后自动拉起新版 /
  staging 文件名改目标版本 / PATH REG_EXPAND_SZ。
- **移入待解决池**：「工作记录」概念（批 3，待用户捋清需求再立项）。
- **暂缓/移出**（2026-09-19 定稿，维持）：局域网通信（D-3）、Pi/opencode（作废备查）、
  旧卷迁移实测、r2 computer use（观察）、Slurm/PBS（等用户提供工作流）、provider 页
  遗留小项、协作文档/飞书知识库。
