# v2.1.16 开发计划（2026-10-17 反馈驱动开题）

> 2026-10-17 按用户指示读取反馈站公开内容，把 3 条新反馈与 1 条新需求纳入
> v2.1.16 开发计划。本文档是 v2.1.16 阶段索引；各批实施须按《DEVELOP_WIKI》
> §1.2 开工纪律切独立分支，并按批次计划、TDD、本地门禁、远程 CI 和实机手测闭环。

## 交付状态

| 批 | 内容 | 建议优先级 | 分支（实施时创建） | 终态 |
| --- | --- | --- | --- | --- |
| b1 | 容器内 codex/claude 自动更新 EEXIST 修复 | P1 | `2.1.16-b1-container-tool-update` | 已完成（PR #26；T1–T4 预复测通过） |
| b2 | Work Records UI 可用性五项 | P1 | `2.1.16-b2-work-records-usability` | 已完成（T5–T9 预复测通过） |
| b3 | Docker 资源面板信息层级与「清理构建缓存」 | P2 | `2.1.16-b3-docker-resource-ui` | 已完成（T10–T12 预复测通过） |
| b4 | 技能/插件/MCP 统一管理调研与方案 | P2 | `2.1.16-b4-skill-plugin-mcp-research` | 调研完成；2026-10-18 裁定 D-1–D-4 |
| b5 | 扩展统一管理实施（rail 入口 + Provider 迁移 + 三资产生命周期） | P1 | `2.1.16-b5-extensions-management` | 已完成（T13–T15 预复测通过） |
| b6 | 用户手测四项修复（TabBar 残留 / services 泄漏 / 租约阻断） | P0 | `2.1.16-b6-handtest-fixes` | 已完成 |
| b7 | MCP 卸载 PTY 修复 + 更新跨重启持久 + 扩展商城 | P0 | 2.1.16-b7-mcp-delete-and-market | 已完成（R5–R8 预复测通过） |
| b8 | 复测第三轮四项修复（噪音日志/缓存语义/ops 数组/工厂遮蔽） | P0 | 2.1.16-b8-handtest-round3 | 已完成（R9–R12 预复测通过） |
| b9 | 扩展 UX 统一 + 缓存全量裁定 + 手测第四轮八项 | P0 | 2.1.16-b9-extensions-ux-and-cleanup | 已完成（R13–R16 预复测通过） |
| b10 | MCP 市场/进度动画/终端复制/工厂清空 | P0 | 2.1.16-b10-market-progress-copy | 已完成（预复测 R17–R20 通过） |
| b11 | 恢复 b10 重写中丢失的终端选区自动复制 | P0 | develop 直接提交 `bdfa797` | 已完成 |
| b12 | Docker 冷启动轮转、官方插件商城、Codex 普通拖选 | P0 | develop 直接提交 `29ddd9e` | 已完成（预复测 R21–R24 通过） |
| b13 | Smithery 403、Codex 更新锁、Skill 仓库分组、缓存全清 | P0 | develop 直接提交 `3620298` | 已完成（预复测 R25–R28 通过） |

2026-10-24 用户宣布进入下一阶段。b1–b13 开发、本地门禁、develop CI 与关键链路
预复测全部闭环；阶段计划归档，进入 `v2.1.16-preview.1` 发布验证窗。后续用户
实机复测如发现回归，在 `docs/plans/2.1.16-preview-fixes/` 另开 preview 修复批，
不回写已归档批次计划。

批次数量、实现顺序和范围以用户逐轮裁决为准；本阶段 b6/b8/b9/b11/b12/b13 为
develop 直接修复批，其余实施批均从最新 `develop` 创建、本地门禁与远端 CI 全绿
后并回。b4 为调研批次，产出管理模型、cc-switch 对接与 UI 形态方案后经用户裁
决再进入 b5 实施。

## 反馈来源与范围

- 来源：`https://feedback.alanevergarden.xyz`
- 抓取时间：2026-10-17 22:30
- 新反馈：3 条 + 新需求 1 条（首轮回复前 status 均为 `submitted`，当前均为 `replied`）
- 明细、初步归因和首轮回复见 [feedback-intake.md](feedback-intake.md)。
- 20260922 / 20261012 两批反馈已在 v2.1.14 / v2.1.15 解决，本周期不重复处理。

## 阶段范围（草案）

1. **P1 修复**：容器内 codex CLI 自动更新时报 `npm EEXIST /usr/local/bin/codex`
   更新失败；修复 codex/claude 自动更新链路，保证覆盖安装顺利完成。
2. **P1 UX**：Work Records 五项可用性——左键只读预览会话内容、拖动父节点带子
   节点、「创建会话」「分支会话」入口并即时刷新、「引用缺失」占位不再闪现、
   删除会话级联同名未显示会话。
3. **P2 UX**：Docker 资源扫描结果信息层级重排、Build Cache 等术语中文化、补充
   资源信息；「重新构建镜像」右移，原位置新增「清理构建缓存」按钮，清理前后
   数据正确刷新。
4. **P2 调研**：基于内置 cc-switch 统一管理 skill / plugin / MCP——初始化、安装、
   查看、卸载、更新、删除；先方案后实施。

## 反馈站回复处置

2026-10-17 22:35 已按 `Wifabric/aisc-issues-feedback` 根目录 README 的开发者工作流，
为 3 条新反馈与 1 条新需求追加首轮回复，并将状态从 `submitted` 更新为 `replied`。
反馈数据仓库提交为 `4e39e00 feedback: reply to 2026-10-17 reports`，已推送到 `main`。

回复正文和各条目标状态见 [feedback-intake.md](feedback-intake.md)。`索引.md` 由
反馈站自动维护，未手动修改；站点列表和详情缓存按 README 承诺在 5 分钟内刷新。
