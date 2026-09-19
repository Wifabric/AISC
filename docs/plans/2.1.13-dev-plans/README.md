# 2.1.13 开发计划

> 2026-09-19 开池（Workbench 版本线 bump 2.1.12 → 2.1.13）。同日用户定稿阶段范围
> （docs/todo.md「v2.1.13-target」）并作裁决：D-1 Pi/opencode 本阶段不做（同日澄清）、
> D-2 docker 检测精细化（不自动清理）、D-3 局域网暂缓；随后验收计划时确认 D-4（CI 版本戳）
> 与 D-6（变更页仿 vscode git 页、纯显示零操作）。当日完成立项研究（ultracode workflow：
> 研究员 + 独立证据核验）并落全部计划文档。开发严格以本文档集为准（DEVELOP_WIKI §1.1）。

## 计划文档索引

| 文档 | 条目 | 状态 |
| --- | --- | --- |
| [decisions.md](decisions.md) | 阶段裁决日志（D-1~D-3 用户裁定；D-4~D-10 立项规划裁定，可逐条否决） | 持续更新 |
| [selfupdate-e2e.md](selfupdate-e2e.md) | 自更新端到端实测 + CI 版本戳修正 | 计划待验收 |
| [remote-cli-pairing.md](remote-cli-pairing.md) | 远程 CLI 版本配对「需更新」提示 | 计划待验收 |
| [long-conversation-repro.md](long-conversation-repro.md) | 长对话恢复 bug 取证协议 | 待用户提供复现样本 |
| [history-worklog.md](history-worklog.md) | 历史会话重构（工作记录 + 只读聊天视图） | 计划待验收 |
| [changes-page.md](changes-page.md) | 变更页（git 双源 + 变更树 + diff） | 计划待验收 |
| [workspace-zip-restore.md](workspace-zip-restore.md) | 导出 zip 恢复工作区到新路径 | 计划待验收 |
| [docker-scan-fidelity.md](docker-scan-fidelity.md) | docker 资源检测精细化 | 计划待验收 |
| [pi-opencode.md](pi-opencode.md) | agent 加上 Pi/opencode（免安装） | **已作废**（用户澄清本阶段不做，备查） |
| [image-drag-to-agent.md](image-drag-to-agent.md) | 拖动图片给 agent（含剪贴板粘贴） | 计划待验收 |

流程项（无开发计划文档）：**final 发布时机**——按 D-8(2.1.12) 规约仅经用户明确要求。

## 阶段范围与状态（= todo「v2.1.13-target」，2026-09-19 用户定稿 + 当日裁决）

**发布与更新**
- 自更新端到端实测（实测目标 = v2.1.13-preview.1；先落 CI 版本戳，见 selfupdate-e2e.md）
- 远程机器 CLI 版本配对与更新（一期提示 + 复制命令，见 remote-cli-pairing.md）
- final 发布时机（流程项，经用户明确要求）

**会话 / 工作区**
- 长对话无法恢复（bug；等复现样本，协议见 long-conversation-repro.md）
- 历史会话重构：工作记录 + 只读聊天界面（四批交付，批 0 探针前置）
- 变更页：git 双源 + 变更树 + diff（git 严格只读）
- 导出的工作区 zip 恢复为工作区，且指向新路径（按新路径重算 hash 落新目录）

**运行质量**
- docker 资源检测精细化（D-2 改裁：不自动清理；只读深扫 + 逐项徽标）
- 设备性能受限情况下稳定运行（v2.1.9 PERF P1-P9 为既有基础；待专项立项——P6b/P10 backlog、存量容器限额、低配实测验收三方向，见下「待立项」）

**agent 生态**
- 拖动图片给 agent（落盘+路径引用；剪贴板粘贴同批）

**小项（用户 2026-09-19 入「# 待处理」，计划随首批顺带）**
- cli run 在存在容器的情况下禁止使用（防重入守卫，CLI 单点）

**暂缓（2026-09-19 用户裁定移出）**
- 局域网通信增强（D-3：退回后备池；重启先决 = 场景澄清 + serve TCP 传输安全裁定）

## 待立项（范围内但计划文档未落）

- 设备性能受限稳定运行：本批立项研究未含（低配 PERF 基础已在案），下次补研究后立文档。

## 已移出 target（用户 2026-09-19 定稿裁剪，退回后备/观察）

- **agent 加上 Pi/opencode**（同日澄清：本阶段不做；pi-opencode.md 作废备查，重启时「免安装」路线可复议）
- 旧卷迁移实测（等真实旧容器升级场景）
- r2 computer use 转观察（上游 openai/codex#20851 契约稳定再评估）
- Slurm/PBS 远程调用（阻塞：等用户提供实际工作流）
- provider 页「显示异常」（模板化后未再报告，观察中）
- provider 页遗留小项（编辑拆两个 / api-key 获取提示 / agent 对话框补全）
- 协作文档、飞书知识库
