# Active Planning

Active/in-progress implementation plans live here. Completed plans are archived
under `docs/archive/`: version-cycle plan sets as `docs/archive/<version>-dev-plans/`,
topical plans under their own directories.

## Workflow improvement

- [`pr-intake-workflow`](pr-intake-workflow.md) — 独立开发协作文档专题：PR 接入、职责分工与贡献者流程；本地自查和隔离演练已记录，真实团队试用待开展。

## Current active plan

- [2.1.19 正式发布准备](2.1.19-dev-plans/README.md)：PR #104、#105 已合入 develop；公开候选 Workbench 2.1.19-preview.1 / CLI 0.3.0.dev0 的回归、CI、桌面检查以及用户功能/安装手测已通过。偶发卡死暂缓；当前准备 Workbench 2.1.19 / CLI 0.3.0 的正式版本、main 集成、产物和渠道，尚未发布 Final。[整版交付](2.1.19-dev-plans/DELIVERY.md)、[正式说明准备稿](../releases/v2.1.19.md)、[操作参考](2.1.19-dev-plans/HANDTEST.md)。

- 2.1.18 的功能开发、验收及 Workbench 发布交付已完成，主体材料已[归档](../archive/2.1.18-dev-plans/README.md)。整版成果见 [DELIVERY](../archive/2.1.18-dev-plans/DELIVERY.md)；反馈站回写已完成；正式 PyPI 相关事项继续保留在 [TODO](../todo.md)。当前本地 CLI 已进入 0.3.0.dev0 功能开发，这不表示旧 PyPI 待办完成或新开发号已发布；不再沿用历史的“下一开发号尚未开启”描述。

## Previous stages and intake

- [`2.1.17-preview-fixes`](../archive/2.1.17-preview-fixes/) — 2026-10-31 preview 手测反馈六批已由 `v2.1.17` final 收口；preview.2 用户统一实测通过，计划已归档。
- v2.1.17 原阶段已完成 preview 收尾，见 [`2.1.17-dev-plans`](../archive/2.1.17-dev-plans/)（Workbench 2.1.17-preview.1 / CLI 0.1.10.dev0，原阶段 D-7 免补测放行，NOT RUN 保留）。
- [`terminal-experience-intake`](terminal-experience-intake.md) — 历史 intake：N5 的 Work Record 静态阅读已由 v2.1.17 R4 实现；实时终端继续字节穿透，其余方向不自动进入新版本。
- v2.1.16 开发计划与 preview 修复链已归档：
  - `docs/archive/2.1.16-dev-plans/`
  - `docs/archive/2.1.16-preview-fixes/`
