# Workbench 2.2.0 阶段计划

- **状态**：阶段 2（计划）· 进行中

## 目标

把 10 项已裁定反馈（7 新 + 3 悬账）转变成 Workbench 2.2.0 的可验收交付：修 4 个阻断 bug、重组 4 处 UX、给终端加基础富文本渲染、给标签卡住加可观测性、清 Windows 升级脚本竞态。

## 人工门位置

- 默认：预览验证阶段的交付确认（只有主开发）。

## 切片

| 切片 | Owner | 范围 |
|---|---|---|
| A 扩展市场+安装/镜像 | wangyuncepu | D-1 / D-3 / D-10 |
| B Provider | wangyuncepu | D-2 |
| C 侧边栏+工作记录+网络 | wangyuncepu | D-4 / D-5 / D-6 / D-7 |
| D 终端渲染+可观测性 | wangyuncepu | D-8 / D-9 |

## 批次

| 批次 | 切片 | 标题 | blocking edges | 状态 |
|---|---|---|---|---|
| b1 | A | 扩展市场整组安装修复 | — | 待开工 |
| b2 | A | 镜像默认产物清空 | — | 待开工 |
| b3 | A | Windows 升级脚本清理竞态 | — | 待开工 |
| b4 | B | Provider 官方直连切换/刷新 | — | 待开工 |
| b5 | C | 侧边栏刷新 + 实时 push | — | 待开工 |
| b6 | C | 网络节点 UI 重组 | — | 待开工 |
| b7 | C | 工作记录超链接报错 | — | 待开工 |
| b8 | C | 工作记录预览 UI 拆解 | — | 待开工 |
| b9 | D | 标签卡住可观测性 | — | 待开工 |
| b10 | D | 终端富文本渲染基础 | — | 待开工 |
| b11 | D | 命令折叠 | b10 | 待开工 |
| b12 | D | 路径点击 | b10 | 待开工 |

## 共享写冲突检查

| 共享文件 / 契约 | 涉及工单 | 处理 |
|---|---|---|
| `workbench/src/stores/workRecords.ts` | b5 / b7 / b8 | 串行（b7 → b8 → b5，归主开发） |
| `workbench/src/features/workspace-explorer/WorkRecordsView.vue` | b7 / b8（b5 可能） | 串行，归主开发 |
| 终端渲染管线 | b10 / b11 / b12 | 串行（b11/b12 blocked by b10） |
| `workbench/src/features/terminal/`（b9 探针 vs b10 渲染） | b9 / b10 | 建议串行或主开发协调，切片落定时复查 |
| 版本事实源（`tauri.conf.json` / `VERSION`） | 无（阶段 5 才 bump） | 主开发独占 |

## 链接

- INTAKE：`docs/plans/2.2.0-dev-plans/INTAKE.md`
- SPEC：`docs/plans/2.2.0-dev-plans/SPEC.md`
- decisions：`docs/plans/2.2.0-dev-plans/decisions.md`
- HANDTEST：`docs/plans/2.2.0-dev-plans/HANDTEST.md`
- DELIVERY：（阶段 5/6 产出）
