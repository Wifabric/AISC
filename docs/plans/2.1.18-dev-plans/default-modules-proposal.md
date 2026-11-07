# U-4 首发默认模块提案（待用户批准）

建议首发两个可复制编辑的精简模块，共四个技能；继续保留现有六类单项推荐。默认清单仍为空，此提案没有启用、安装到用户目标或改变用户模块定义。

| 模块 | 安装 identity | 用途 / 来源 |
| --- | --- | --- |
| 科研基础 | `google-deepmind/science-skills:literature_search_arxiv` | arXiv 文献检索；[固定来源](https://github.com/google-deepmind/science-skills/blob/4de6786171f1479026da5d3a00f110703c8ba35e/skills/literature_search_arxiv/SKILL.md) |
| 科研基础 | `google-deepmind/science-skills:literature_search_openalex` | 学术作品、作者与引用线索；[固定来源](https://github.com/google-deepmind/science-skills/blob/4de6786171f1479026da5d3a00f110703c8ba35e/skills/literature_search_openalex/SKILL.md) |
| 开发基础 | `obra/superpowers:systematic-debugging` | 按证据定位问题；[来源](https://github.com/obra/superpowers/tree/main/skills/systematic-debugging) |
| 开发基础 | `obra/superpowers:test-driven-development` | 功能及修复的测试流程；[来源](https://github.com/obra/superpowers/tree/main/skills/test-driven-development) |

安装 identity 使用实际目录，显示名可用自然语言。Science Skills 的目录为下划线，frontmatter/市场名称为连字符；S7 修正将现有推荐中四个同源条目的安装标识改为实际目录，显示名保持不变。B9 整合修正已让两种拼写读取到唯一正确详情，但详情别名不代表安装目录别名。默认提案不增加 MCP 认证或整包插件，也不把技能自身要求的外部服务授权视为已完成。

## 已验证与边界

2026-11-08，在自建隔离容器用候选冻结 CLI 执行模块计划和逐项操作：四项全部 `installed`，随后四项全部 `removed`，状态闭环通过，容器已清理。实际科研详情读取和来源核验通过，开发技能简介读取通过；证据在本机候选目录 `output/verification/default-members-install.json`、`real-research-details.json` 和来源核验记录。

上述为资产安装/卸载和元数据验证，不是科研任务或模型工作流验收。OpenAlex 技能包含外部服务配额、可选 API key 与运行依赖，具体任务执行仍须按其来源说明配置；未使用用户凭据、未查询付费服务、未执行下载技能中的指令。默认成员没有获批时，现有用户自建模块功能照常可用，F4 的首发默认清单仍保持未完成。

## 次日需批准的具体内容

批准上表四项作为“科研基础 / 开发基础”首发默认成员后，落入 `moduleCatalog.ts`，补内置模块显示/复制回归并重建候选。若调整成员，只替换对应条目，复验该成员安装与移除；不重开已确认 U-1–U-3 的产品规则。
