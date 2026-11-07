# v2.1.18 开发计划

状态：**b1–b7 已合入 develop；b8 GitHub MCP 配置完成本地验证，准备 PR；b9–b10 待实施。** b4 PR #68 的精确 head `80e90919` 三项 CI 全部 PASS，合并 `1efe0904`。真实平台 GUI 和用户验收按 D-15 留到统一 Preview；U-4 默认成员按 D-16 暂留待批准。

本阶段原收录 F1–F4，D-11 后新增 F5–F8，共八条反馈、十个批次。D-12–D-16 授权连续实施、统一 Preview 验收；U-1–U-3 已确认，U-4 具体成员待提案。未实施或未验收部分不预记完成。

## 基线与执行模式

- 独立 clone 的发布基线：`v2.1.17` / `bf95ce0aa9eaca0439b52679f97b91c46a25adeb`，CLI `0.1.10`。
- 计划起点：`codex/2.1.18-planning`，来自 `origin/develop` 的 `1d26f237206ef27dd263df6725e27383b3848174`。该 develop 相对发布基线仅补 todo/devlog 收口记录，产品代码相同。
- **本轮执行模式（D-12）**：每批实现及必要验证 → PR/CI/集成 → 下一批；整合 issue 与协作流程后统一 Preview 和用户验收。保留每批证据与真实未测状态；用户最新授权取代本阶段原逐批等待门。
- 本目录范围为 F1–F8；个人功能直接合入 2.1.17 副本，属于独立整合工作，不列入本版需求或批次。后续发布按开发手册另行执行。
- 跨前端、Rust、CLI、Docker、扩展适配器和持久化，采用 Full 文档结构；各小批以本目录 `b*.md` 为具体执行规格。沿用仓库 `PROGRESS.md` / `LESSONS.md` 命名，不另建重复进度账本。

## 阅读与维护顺序

1. [feedback-intake](feedback-intake.md)：原始问题、观察与推断、归属批次。
2. [代码阅读地图](reading-map.md)：本版反馈的相关实现与测试入口。
3. [decisions](decisions.md)：已确认范围 D 项、未确认产品语义 U 项。
4. [PRD](PRD.md)、[APP_FLOW](APP_FLOW.md)：用户目标、边界、验收编号及使用流程。
5. [TECH_STACK](TECH_STACK.md)、[FRONTEND_GUIDELINES](FRONTEND_GUIDELINES.md)、[BACKEND_STRUCTURE](BACKEND_STRUCTURE.md)、[DESIGN](DESIGN.md)：实现约束和界面方案。
6. [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md)、下表批次方案：实施顺序、依赖、文件与验证。
7. [HANDTEST](HANDTEST.md)、[PRETEST](PRETEST.md)、[PROGRESS](PROGRESS.md)、[LESSONS](LESSONS.md)：验收步骤、实际证据、进度及经验。
8. [PR_INTAKE](PR_INTAKE.md)：PR #64 的目标提交、自审、CI 与待验收状态。

## 批次总表

| 批次 | 范围 | 来源 | 前置依赖/待裁定 | 当前状态 |
| --- | --- | --- | --- | --- |
| [b1](b1-case-rename.md) | 文件/目录仅改变大小写的重命名 | F1 | D-5/D-6 | PR #63 已合入 develop；历史验证边界见 PRETEST，D-7 允许进入 b2 |
| [b2](b2-work-record-menu.md) | 工作记录右键菜单避让窗口边界 | F2 | D-7/D-8/D-9/D-10 已授权 | 本轮前端 841 项、构建、已执行 CU 和 PR CI PASS；[PR #64](https://github.com/Wifabric/AISC/pull/64) 已合入 develop；用户验收状态仍待确认 |
| [b3](b3-image-name.md) | 镜像自定义名称、默认名称与校验 | F3.1 | U-1 已确认 | PR #67 已合入；自动化/真实 Docker/CI PASS；GUI/用户验收待 Preview |
| [b4](b4-image-rebuild.md) | 镜像行/启动摘要重建、预检查和流式进度 | F3.2–4 | b3、U-2 已确认 | PR #68 已合入；自动化/真实 Docker/冻结 CLI/CI PASS；GUI/用户验收待 Preview |
| [b5](b5-extension-modules.md) | 推荐模块定义、成员编辑与持久化 | F4 | U-3 已确认；U-4 默认清单待批准 | PR #69 已合入 d3798c06，三项 CI PASS；默认清单与 GUI/用户验收待定 |
| [b6](b6-module-operations.md) | 模块应用/卸载、共享成员保护、失败恢复 | F4 | b5、U-3 | PR #70 已合入 ffc84885，自动化/真实 Docker/冻结 CLI/CI PASS；GUI/用户验收待 Preview |
| [b7](b7-plugin-install.md) | 插件安装超时与结果核对 | F5 | D-11/D-12 | PR #71 已合入 61c70540，本地/真实 Docker/冻结 CLI/CI PASS；GUI 待 Preview |
| [b8](b8-github-mcp-auth.md) | GitHub MCP 首次认证配置入口 | F6 | D-11/D-12 | 本地门禁/双引擎真实配置/冻结 CLI PASS，准备 PR；真实授权和 GUI 待 Preview |
| [b9](b9-skill-details.md) | grill 搜索结果简介与子技能详情读取 | F7 | D-11/D-12 | PLANNED |
| [b10](b10-failure-dismiss.md) | 关闭当前失败提示、保留历史与新失败提示 | F8 | D-11/D-12 | PLANNED |

剩余实施顺序：**b3 → b4 → b5 → b6 → b7 → b8 → b9 → b10**（D-14）；编号稳定，每批独立记录实现及验证，统一 Preview 验收。

PLANNED 只表示计划落档；按已确认方案实施，不把计划或自动化通过写成用户验收通过。

范围的总账是 [todo](../../todo.md)，方案以本目录为准；[devlog](../../devlog.md) 只记录实际完成的工作。历史阶段的通过或免测结论均不继承为本阶段 PASS。
