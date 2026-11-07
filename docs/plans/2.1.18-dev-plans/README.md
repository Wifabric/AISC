# v2.1.18 开发计划

状态：**b1 已由 PR #63 合入 develop；b2 本地集成验证及本轮已执行 CU 路径通过，待用户批次验收；b3–b6 未实施。** 更新：2026-11-08。

本阶段把反馈站四条新增反馈转为可验证的修复/功能方案。用户已明确“根据 develop wiki 和计划进行 2.1.18 的更新”（D-5）；按逐批模式启动 b1。后续批次产品规则 U-1–U-4 及用户逐批验收仍按原计划执行。

## 基线与执行模式

- 独立 clone 的发布基线：`v2.1.17` / `bf95ce0aa9eaca0439b52679f97b91c46a25adeb`，CLI `0.1.10`。
- 计划起点：`codex/2.1.18-planning`，来自 `origin/develop` 的 `1d26f237206ef27dd263df6725e27383b3848174`。该 develop 相对发布基线仅补 todo/devlog 收口记录，产品代码相同。
- **开发阶段逐批模式**：实施及必要数据面验证 → Windows CU 预测试 → 用户本批验收/裁定 → 下一批。依据 [DEVELOP_WIKI §1.4](../../../DEVELOP_WIKI.md)。本阶段不是 preview 批量修复模式。
- 本目录只计划四条反馈；个人功能直接合入 2.1.17 副本，属于独立整合工作，不列入本版需求或批次。后续发布按开发手册另行执行。
- 跨前端、Rust、CLI、Docker、扩展适配器和持久化，采用 Full 文档结构；各小批以本目录 `b*.md` 为具体执行规格。沿用仓库 `PROGRESS.md` / `LESSONS.md` 命名，不另建重复进度账本。

## 阅读与维护顺序

1. [feedback-intake](feedback-intake.md)：原始问题、观察与推断、归属批次。
2. [代码阅读地图](reading-map.md)：四条反馈的相关实现与测试入口。
3. [decisions](decisions.md)：已确认范围 D 项、未确认产品语义 U 项。
4. [PRD](PRD.md)、[APP_FLOW](APP_FLOW.md)：用户目标、边界、验收编号及使用流程。
5. [TECH_STACK](TECH_STACK.md)、[FRONTEND_GUIDELINES](FRONTEND_GUIDELINES.md)、[BACKEND_STRUCTURE](BACKEND_STRUCTURE.md)、[DESIGN](DESIGN.md)：实现约束和界面方案。
6. [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md)、下表批次方案：实施顺序、依赖、文件与验证。
7. [HANDTEST](HANDTEST.md)、[PRETEST](PRETEST.md)、[PROGRESS](PROGRESS.md)、[LESSONS](LESSONS.md)：验收步骤、实际证据、进度及经验。

## 批次总表

| 批次 | 范围 | 来源 | 前置依赖/待裁定 | 当前状态 |
| --- | --- | --- | --- | --- |
| [b1](b1-case-rename.md) | 文件/目录仅改变大小写的重命名 | F1 | D-5/D-6 | 核心 CU PASS；提示复测未执行；PR #63 打开，D-7 允许进入 b2 |
| [b2](b2-work-record-menu.md) | 工作记录右键菜单避让窗口边界 | F2 | D-7/D-8/D-9 已授权 | 修后 852 项、构建及已执行 CU 路径 PASS；[PR #64](https://github.com/Wifabric/AISC/pull/64) 打开，依赖 #63；用户验收待定，未测项见 PRETEST |
| [b3](b3-image-name.md) | 镜像自定义名称、默认名称与校验 | F3.1 | U-1 | PLANNED |
| [b4](b4-image-rebuild.md) | 镜像行/启动摘要重建、预检查和流式进度 | F3.2–4 | b3、U-2 | PLANNED |
| [b5](b5-extension-modules.md) | 推荐模块定义、成员编辑与持久化 | F4 | U-3、U-4 | PLANNED |
| [b6](b6-module-operations.md) | 模块应用/卸载、共享成员保护、失败恢复 | F4 | b5、U-3 | PLANNED |

PLANNED 只表示计划落档，不表示允许绕过方案确认或逐批验收门。

范围的总账是 [todo](../../todo.md)，方案以本目录为准；[devlog](../../devlog.md) 只记录实际完成的工作。历史阶段的通过或免测结论均不继承为本阶段 PASS。
