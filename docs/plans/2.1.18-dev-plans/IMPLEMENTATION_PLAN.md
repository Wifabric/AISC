# 实施顺序与门禁

状态：b1–b7 已由 PR #63/#64/#67/#68/#69/#70/#71 合入 develop；b8 MCP 配置通过本地验证，待 PR/CI，U-4 默认内容仍待批准；b9–b10 待实施。D-12–D-16 授权连续推进，真实 GUI 与手动验收统一留到 Preview；确需产品裁定的事项记账后先推进不受影响的工作。

## 从问题到闭环

`反馈 → intake 与来源 → todo target → PRD 验收点 → decisions 产品裁定 → b* 文件级方案 → 定向验证/必要数据面 → 本地门禁 → PR/CI/集成 → 统一 Preview 与用户验收`

实施分支从当时最新 develop 切出，记录起点 SHA。b5 从 `c0f9ab11` 建立后快进到 B4 合并基线 `1efe0904`；历史依赖分支关系以 PR_INTAKE 为准。每批记录本地门禁、远端 CI 和精确提交证据，不以本地绿替代远端绿。

## 批次顺序

| 批 | 实施分支建议 | 具体方案 | 完成证据 |
| --- | --- | --- | --- |
| b1 | `codex/2.1.18-b1-case-rename` | [文件大小写](b1-case-rename.md) | 实际条目名/内容、冲突与恢复、H1 |
| b2 | `codex/2.1.18-b2-work-record-menu` | [菜单边界](b2-work-record-menu.md) | 布局/键盘自动化及真实视口、H2 |
| b3 | `codex/2.1.18-b3-image-name` | [镜像命名](b3-image-name.md) | 同一 ID 的 tag 前后状态、冲突/失败、H3 |
| b4 | `codex/2.1.18-b4-image-rebuild` | [重建](b4-image-rebuild.md) | target/缓存 argv/事件/取消/旧 ID、H4 |
| b5 | `codex/2.1.18-b5-extension-modules` | [模块定义](b5-extension-modules.md) | 定义 schema/迁移、重启、成员表、H5 |
| b6 | `codex/2.1.18-b6-module-operations` | [模块执行](b6-module-operations.md) | 真实三类安装/失败/共享保护、H6 |
| b7 | `codex/2.1.18-b7-plugin-install` | [插件安装](b7-plugin-install.md) | 实际安装终态、超时后核对与重复操作、H7 |
| b8 | `codex/2.1.18-b8-github-mcp-auth` | [MCP 配置](b8-github-mcp-auth.md) | 双引擎认证状态、取消/失败保护与脱敏、H8 |
| b9 | `codex/2.1.18-b9-skill-details` | [技能详情](b9-skill-details.md) | 精确 grill 查询、详情来源及断网恢复、H9 |
| b10 | `codex/2.1.18-b10-failure-dismiss` | [失败提示](b10-failure-dismiss.md) | 当前关闭/历史保留/新失败与工作区隔离、H10 |

D-14 按用户最新纠正确定剩余实施顺序：**b3 → b4 → b5 → b6 → b7 → b8 → b9 → b10**。U-1–U-3 已确认；U-4 具体默认成员仍需核实后提出。b7/b9 可复用网络证据，不能合并两条需求的验收结果。

b1/b2 是可独立验证的小修复；b3→b4 共用镜像身份；b5→b6 先定数据与归属，再执行实际安装/卸载。D-12 允许连续实施；每批仍需必要测试，统一 Preview 不代表免测。

### 每批 PR 与集成

依据开发交接 §③ 与 DEVELOP_WIKI §1.2，每批独立分支，在分支上提交，完成本地门禁和远端 CI 后并回 develop。按历史实践以每批一个 PR 为默认，较大批次可拆多个 PR（2.1.17 b7 为 #46/#47）；不要求“每批恰好一个”，也不等整版完成才提交。纯账本文档可直接落 develop。PR 创建、CI 通过、合入及用户验收分别记账；main 合并/推送仍需负责人批准。历史 D-7/D-9 的依赖 PR 已由后续实际合并状态更新；当前 b3–b10 已完成 PR/CI/集成，develop 为 b548728b；随后按 [team-workflow](team-workflow.md) 整合本版协作流程并准备统一候选。

## 每批执行清单

1. 核对整体方案及当前批尚未决定的 U 项；更新批次状态、读取涉及文件的最新内容。已有授权不重复请求；reading-map 不是免读代码的豁免。
2. 建实施分支，先补能够揭示该问题的行为回归，再改相关实现。低影响纯文档调整不用制造产品测试。
3. 定向测试 → 必要真实文件系统/容器/模型/Remote 验证 → 受影响层全门禁。CLI/Rust/前端和打包的具体门禁按开发手册及当前 workflow，不运行正文中未准备的破坏性命令。
4. 在最终候选构建按 [HANDTEST](HANDTEST.md) 执行 Windows CU；记录产物、路径、实测状态及证据到 PRETEST。模拟 adapter/DOM 或历史构建不冒充真实 GUI/模型 PASS。
5. 保存每批结果及手测步骤；失败修复并复测相关范围，用户验收留到统一 Preview，未测仍 NOT RUN。
6. 按实际完成阶段更新 README/batch/PROGRESS/todo/devlog，按 D-12–D-14 连续推进下一批。发布及反馈关闭另按指南触发。

## 技术验证入口（实施阶段使用）

- 前端：在 `workbench` 使用 `npm test -- <实际测试路径>` 定向；受影响层门禁 `npm test`、`npm run build`。
- Rust：在 `workbench/src-tauri` 使用 `cargo test <实际测试过滤器>`；受影响层完整 `cargo test`。
- Python：项目 venv 执行 `python -m pytest <实际模块路径> -q`；完整套件遵循当前 CI 的 `python -m pytest tests -q` 及环境标注。
- sidecar/bundle/安装产物：b4 协议变更时按指南构建、stage/verify；本地原安装版不是新分支候选。
- 文档：链接/锚点、版本与命令、`git diff --check`。

## 未完成与收尾

本阶段不预先把“已规划”勾成“已实现”。用户调整范围时先改 decisions/todo/PRD/batch，再动码。全部完成或显式转期后由用户宣布收尾，准备 preview、正式 final 与归档；不能沿用 2.1.17 免测结论或主动关闭未解决反馈。
