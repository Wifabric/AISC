# 开发协作流程更新：PR 接入与职责分工

## 目标与范围

保留 DEVELOP_WIKI 已有的 Issue 收集、开发人员提议、版本计划、验收和发布方式，增加贡献者 PR → TODO／批次 → 审查 → 修正复审 → 合入验证的完整路径。已有实现进入审查和集成，不重复开发。

本次为独立文档 PR，基于 develop `1d26f237206ef27dd263df6725e27383b3848174`。仅增加流程正文、配套说明、历史自查／演练记录及文档索引与账本；不包含产品代码、README 改版、截图、安装产物、产品问题审查报告或本机 output 数据。没有合入 #62、#63、#64，也不替它们批准产品版本范围。

## 交付内容

| 内容 | 入口 | 作用 |
| --- | --- | --- |
| 开发手册 | [DEVELOP_WIKI §1.5–§1.6](../../DEVELOP_WIKI.md) | 接入版本循环和角色入口 |
| 主开发人员流程 | [PR intake](../workflows/pr-intake.md) | 全仓收集、去重、依赖、批次、审查与集成证据 |
| 职责划分 | [开发职责 v1.0](../workflows/development-roles.md) | 16 类开发工作及双方交接 |
| 任务开发人员流程 | [贡献者工作流](../workflows/contributor-workflow.md) | 承接、方案、实现、自测、PR、返修与交接 |
| 历史讨论 | [v0.1 讨论稿](../workflows/development-responsibilities-draft.md) | 保留分工形成过程；实际执行使用 v1.0 |
| 规则自查 | [流程评审](../reviews/develop-wiki-workflow.md) | 静态场景和交接检查，非独立评审 |
| 本地演练 | [隔离仓库记录](../reviews/local-workflow-trial.md) | 单代理角色模拟的实际返修、冲突处理与集成；非真实多人验收 |

## 迁移约束

- 以远端 develop 为底稿，只新增 §1.1 的 PR 输入说明和 §1.5–§1.6；保留原有 §1.1–§1.4 正文与第 2 节之后内容。
- 尤其保留远端 2026-11-01 的两种验收模式：开发阶段逐批验收、preview 迭代整体实测。新增流程引用当前有效模式，不覆盖或豁免原门禁。
- 保留 develop 上的活动计划、历史 TODO 和 devlog，仅增加独立文档专题，不恢复本地旧阶段状态。
- AI 按既有授权推进收集、规划、检查与执行；有明确决定时直接引用，未决范围与真正影响行为的取舍才交有权负责人裁定。

## 验证与边界

提交前核对文件白名单、原文保留、Markdown 本地链接／锚点、代码围栏与补丁空白问题。发布后核对 PR 的 base、提交父节点和远端文件清单，确保没有产品改动。

历史记录中的 39 项文档检查和演练中的 7 项测试属于此前本机验证，不能冒充本次最新 develop 上的完整检查或 GitHub CI。此 PR 不运行产品 GUI、容器或发布测试；远端检查以对应提交的实际结果为准。真实多人交接与用户验收仍待进行。

## 下一步：使用真实 PR 试用

文档合入 develop 后，让执行者直接读取新手册推进已授权任务，观察是否还需要外部补充步骤。

2026-11-05 只读快照：[#62](https://github.com/Wifabric/AISC/pull/62) → [#63](https://github.com/Wifabric/AISC/pull/63) → [#64](https://github.com/Wifabric/AISC/pull/64) 为依赖链，三者均 open。执行前重新获取 base/head、范围和 CI；父 PR 合入后重新核对子 PR 差异和证据。该快照仅用于说明测试对象，不代表已完成审查、修复或合并。

按真实任务记录不清楚的交接、遗漏与返工，再修订项目流程。验证成熟后提炼通用小团队开发元 Skill。

## 参考原则

- [karpathy-guidelines](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/skills/karpathy-guidelines/SKILL.md)：明确假设、最小改动、可验证结果；该仓库是第三方整理。
- [grill-me](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md)：沿关键决策澄清问题；能从代码和记录查明的事实先自行核对。

以上仅作为流程设计参考，没有自动安装或执行这些 Skill。
