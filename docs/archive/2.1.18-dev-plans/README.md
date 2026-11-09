# v2.1.18 开发计划

## 当前状态：Workbench 已发布，反馈回写完成

2026-11-09：用户明确批准发布，Workbench [2.1.18 正式 Release](https://github.com/Wifabric/AISC/releases/tag/v2.1.18) 已上线并设为 Latest，源码 `52a5de6ed4fe47fb44b6caedfa14e80624122bc6`，随包 CLI 0.2.0。正式下载、SHA-256、发布说明和安装构建验证通过，真实公开更新数据经旧版与本版生产解析逻辑验证通过。产品与 Preview.13 用户验收已完成；本轮为单代理开发/自查，不称独立评审。

CLI 0.2.0 的正式 PyPI 渠道继续单独跟踪，本轮未操作该渠道。2026-11-09 用户确认权限已授予并要求完成回写；复核账号具有写权限后，以[反馈提交](https://github.com/Wifabric/aisc-issues-feedback/commit/d7a4592f39204d9ccb746ae59d046acab6ba4ed8)更新本版八条状态及最终回复。站点列表和八条详情均已回读：七条“已解决”、一条“已上线”，修复说明和 2.1.18 正式链接完整。只改 status/updated_at 并追加回复，原文、附件、投票和历史内容保留，自动索引未手改。功能开发及已完成交付材料归档，外部待办继续在 [TODO](../../todo.md) 和本目录 [发布记录](release-readiness.md) 中保留；归档不代表整版外部闭环完成。整版成果及 leader 确认入口见 [DELIVERY](DELIVERY.md)。

已验收候选为 **Preview.13**；S16 经 #98 集成，随后用户确认通过。正式版本配对与发布准备见 [release-readiness](release-readiness.md)。

## 当前增补范围（D-17，2026-11-08）

用户明确要求“补齐这张图的全部要求，然后再进行之前的流程”。本轮先完成下列三层产品能力，再重建统一 Preview；下方原范围和候选记录作为历史，不表示新范围已完成。此前排除个人功能的限制及 U-4 等待门由此取代。执行与自查仍由同一开发代理负责，S11–S14 已经 #95 集成，后续远程缺陷修复经 #97 集成；当前状态以本文及 PROGRESS 为准。

| 增补 | 实施与验收 | 当前状态 |
| --- | --- | --- |
| S12 离线通用基础 | 核验 caveman、grilling、Karpathy 来源；随离线 bundle 安装，固定来源和校验值；全新容器能发现技能，原用户文件不被升级覆盖 | 已实现；开发者验证及用户验收通过 |
| S13 在线场景模块 | 启用科研基础、开发基础四项已核验成员；内置定义可复制编辑；成员在线补装，卸载遵守归属保护，成员载荷不纳入离线包 | 已实现；开发者验证及用户验收通过 |
| S14 个人迭代与注入 | 初始模板市场→个人副本→编辑规则/技能→记录反馈及版本→启停注入；工作区隔离，Claude/Codex 新会话读取保存的版本，旧会话不被暗改；主题实践记录继续复用 | 已实现；保存/历史/真实进程注入验证通过，本人模型效果验收已报告通过 |

S14 采用工作区持久化的个人能力库，与既有主题工作坊并存；提供通用协作、科研阅读、开发复盘初始模板。版本记录包括修改原因与验证结果，支持从历史恢复为新版本。启用只影响该工作区之后创建的 Claude/Codex 会话，不覆盖引擎全局配置或预装技能；不把模型能读取配置写成模型任务已通过。

相关自动化、真实容器验证和同版 CLI、Workbench、容器及安装包已完成；S15 后续候选只更新宿主 CLI/Workbench，容器内容保持一致。剩余条件见 PROGRESS。本人认证与用户验收已由用户报告通过；正式发布批准单独保留。

状态：**本版功能、流程与 Skill 已整合并获用户验收；Workbench 已发布，外部两项待办暂缓，完整清单见 DELIVERY。** 见 [交付说明](DELIVERY.md)。

本阶段范围为 F1–F8、十个批次，以及 D-17 确认的 S12–S14。D-12–D-16 授权连续实施、统一 Preview 验收，不把开发者验证记成用户验收。


## 基线与执行模式

- 独立 clone 的发布基线：`v2.1.17` / `bf95ce0aa9eaca0439b52679f97b91c46a25adeb`，CLI `0.1.10`。
- 计划起点：`codex/2.1.18-planning`，来自 `origin/develop` 的 `1d26f237206ef27dd263df6725e27383b3848174`。该 develop 相对发布基线仅补 todo/devlog 收口记录，产品代码相同。
- **本轮执行模式（D-12）**：每批实现及必要验证 → PR/CI/集成 → 下一批；整合 issue 与协作流程后统一 Preview 和用户验收。保留每批证据与真实未测状态；用户最新授权取代本阶段原逐批等待门。
- 本目录当前范围为 F1–F8 及 D-17 的三层能力；原先排除个人能力的边界已被用户后续明确要求取代。后续发布按开发手册及已有授权执行。
- 跨前端、Rust、CLI、Docker、扩展适配器和持久化，采用 Full 文档结构；各小批以本目录 `b*.md` 为具体执行规格。沿用仓库 `PROGRESS.md` / `LESSONS.md` 命名，不另建重复进度账本。

## 阅读与维护顺序

1. [feedback-intake](feedback-intake.md)：原始问题、观察与推断、归属批次。
2. [代码阅读地图](reading-map.md)：本版反馈的相关实现与测试入口。
3. [decisions](decisions.md)：已确认范围 D 项、未确认产品语义 U 项。
4. [PRD](PRD.md)、[APP_FLOW](APP_FLOW.md)：用户目标、边界、验收编号及使用流程。
5. [TECH_STACK](TECH_STACK.md)、[FRONTEND_GUIDELINES](FRONTEND_GUIDELINES.md)、[BACKEND_STRUCTURE](BACKEND_STRUCTURE.md)、[DESIGN](DESIGN.md)：实现约束和界面方案。
6. [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md)、下表批次方案：实施顺序、依赖、文件与验证。
7. [HANDTEST](HANDTEST.md)、[PRETEST](PRETEST.md)、[PROGRESS](PROGRESS.md)、[LESSONS](LESSONS.md)：验收步骤、实际证据、进度及经验。
8. [PR_INTAKE](PR_INTAKE.md)：本版产品批次及整合修正的提交、自查、CI 与合入记录。

## 批次总表

| 批次 | 范围 | 来源 | 前置依赖/待裁定 | 当前状态 |
| --- | --- | --- | --- | --- |
| [b1](b1-case-rename.md) | 文件/目录仅改变大小写的重命名 | F1 | D-5/D-6 | PR #63/#97 已合入；本机及 Preview.12 SSH 文件/目录改名、冲突不覆盖、刷新重入通过；用户验收已报告通过 |
| [b2](b2-work-record-menu.md) | 工作记录右键菜单避让窗口边界 | F2 | D-7/D-8/D-9/D-10 已授权 | PR #64 已合入；Preview.5/.6 追加键盘、窄短窗口、改名/移动及滚动/缩放验证，具体边界见 PROGRESS |
| [b3](b3-image-name.md) | 镜像自定义名称、默认名称与校验 | F3.1 | U-1 已确认 | PR #67 已合入；本机、部分失败/重试及 Preview.12 远程指定 tag 改名通过；用户验收已报告通过 |
| [b4](b4-image-rebuild.md) | 镜像行/启动摘要重建、预检查和流式进度 | F3.2–4 | b3、U-2 已确认 | PR #68、整合 #83/#91 已合入；完整无缓存 GUI、Preview.7 缓存取消及受控残留回收通过，具体边界见 PROGRESS |
| [b5](b5-extension-modules.md) | 推荐模块定义、成员编辑与持久化 | F4 | U-3/U-4、D-17 已确认 | PR #69/#87/#95 已合入；定义、冲突、恢复、科研在线补装及默认模块管理已实测 |
| [b6](b6-module-operations.md) | 模块应用/卸载、共享成员保护、失败恢复 | F4 | b5、U-3 | PR #70 已合入；Preview.5 技能执行/恢复/共享/预装/修改保护通过，MCP/插件保护和双存活目标切换也已补测，详见 PROGRESS |
| [b7](b7-plugin-install.md) | 插件安装超时与结果核对 | F5 | D-11/D-12 | PR #71 已合入；Preview.4 正常安装实测通过，受控超时、unknown、恢复及跨目标迟到响应也已补测，详见 PROGRESS |
| [b8](b8-github-mcp-auth.md) | GitHub MCP 首次认证配置入口 | F6 | D-11/D-12 | PR #72 已合入；自动化/合成数据面通过，GUI 已补测，本人授权和使用验收已报告通过 |
| [b9](b9-skill-details.md) | grill 搜索结果简介与子技能详情读取 | F7 | D-11/D-12 | PR #73、整合 #76 已合入；Preview.6 离线错误/显式恢复/来源通过，受控迟到成功响应与跨工作区隔离也已补测，详见 PROGRESS |
| [b10](b10-failure-dismiss.md) | 关闭当前失败提示、保留历史与新失败提示 | F8 | D-11/D-12 | PR #74 已合入；Preview.3 关闭/焦点/新失败/重挂载子集通过，unknown 和跨目标隔离也已补测，详见 PROGRESS |

b3 → b10 的连续实施顺序已执行完成。隔离安装与本人验收已完成，当前保留公开发布和反馈闭环条件，分项通过/未测及依赖见 [当前进度](PROGRESS.md)。

PLANNED 只表示计划落档；按已确认方案实施，不把计划或自动化通过写成用户验收通过。

范围的总账是 [todo](../../todo.md)，方案以本目录为准；[devlog](../../devlog.md) 只记录实际完成的工作。历史阶段的通过或免测结论均不继承为本阶段 PASS。


本版流程整合与角色安排见 [team-workflow](team-workflow.md)；本轮由同一代理兼任执行与技术自查，用户已完成统一 Preview 验收，真实多人协作试用未执行。
