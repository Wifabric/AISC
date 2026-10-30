# v2.1.17 b3 — 扩展操作恢复执行计划

> 执行 agent：使用 superpowers:executing-plans 逐项执行；用户已授权按 b3→b7 连续完成，不逐批请求审批或用户手测。

**目标：** Skills / MCP / Plugins 安装、更新、卸载失败后可诊断、可单项重试；组操作保留成功项。
**架构：** 沿用 Vue/Pinia → IPC → Rust runtime → Python bridge → 容器 adapter → cc-switch 官方操作链；SSOT 刷新确认最终事实，操作日志仅存内存。
**技术栈：** Vue 3、TypeScript、Vitest、Python/pytest、Rust。

## 范围与开工门

- 依据：本目录 `README.md` b3、`decisions.md` D-0/D-1、`DEVELOP_WIKI.md` §1.2–1.4；承接已集成 b1/b2，不重写市场元数据。
- 从已完成前批门禁的 `develop` 建 `2.1.17-b3-extension-operation-recovery`；核对 README / todo / decisions / feedback-intake 编号与 target。保留其他会话未提交工作，不在其脏工作树中实施。
- 不引入后台自动重试、磁盘日志或第二份安装状态库；组级 IPC 当前非流式，不伪造逐项实时进度。

## 源码落点

| 文件 | 任务 |
| --- | --- |
| `workbench/src/stores/extensions.ts` | `runOperation`、`runSkillGroupOperation`、`contextToken`、`setContext`；保留结构化结果和重试快照 |
| `workbench/src/features/workspace-explorer/ExtensionsView.vue`、`skillGroups.ts`（同目录） | 失败项入口、组结果、日志与诊断复制；沿用 `skillUpdateSpec` |
| `workbench/src/lib/ipc.ts`、`workbench/src-tauri/src/runtime.rs`、`src/aisc/application/extensions.py` | 核对结构化错误/结果透传，不丢弃 item 明细 |
| `container/aisc-extensions-adapter` | `_skill_group_operation` 的 `total/completed/items[{spec,status,error}]` 及单项操作契约 |
| `workbench/src/i18n/zh-CN.ts`、`en-US.ts`（同目录） | 恢复、部分失败、复制成功/失败文案 |

## 任务与 TDD 验收

- [ ] **先 RED：** 新增 `workbench/src/stores/__tests__/extensionsOperationRecovery.test.ts`；扩展现有 `extensionsSkillGroups.test.ts`、`workbench/src/features/workspace-explorer/__tests__/extensionsView.test.ts`、`tests/test_extensions_adapter.py` / `test_extensions_bridge.py`。先执行下列 targeted 命令，确认业务断言失败后再实现。
- [ ] **保存结果：** 每次操作记录 operationId、捕获的 workspace/runtime、kind/action、identity/spec、attempt、起止时间、状态与错误；成功、失败、未执行分别呈现。组结果 `a=installed,b=failed,c=installed` 必须保留 2/3 成功和 b 的原因；SSOT 刷新失败不能把原操作错误覆盖掉。
- [ ] **单项恢复：** 点击 b 的“重试”只调用 b 的原动作/原参数；不得重新执行 a/c 或重跑整个 repo 组。若提供“重试失败项”，仅遍历明确失败项；`blocked/pending/unknown` 单独展示，不自动归入失败重试。安装、更新、卸载均测成功/失败，重复点击只发一次；更新保留原 Claude/Codex 开关。
- [ ] **卸载部分失败：** 逐项捕获并记录删除结果，明确哪些已删除、哪些失败、哪些未执行；已删除条目不再重试。传输超时且结果未知时先重新读取 SSOT，不把未知结果当失败后直接重复提交。
- [ ] **异步竞态：** 用 deferred Promise 测 A→B、A→B→A、同 runtime 新操作覆盖旧操作、切换资产页签；旧 success/catch/finally、列表刷新及 toast 均不得改写新上下文。上下文使用递增 generation，调用闭包固定 workspace/runtime；离开 A 后不得把旧组后续项发往 B；重试旧记录必须验证上下文仍匹配。
- [ ] **内存日志：** 每会话最多 100 条操作记录、每条诊断最多 8 KiB，超限 FIFO/截断并标记；不写 localStorage/文件、不保留完整 stdout。记录 direct/mirror 尝试、错误码和结果；复制前去除 token/凭据，保留定位所需 identity、时间和版本。测试第 101 条淘汰、超长文本、复制内容及剪贴板拒绝后的反馈；可复用 `DoctorDialog.vue` 的 clipboard-manager 模式。
- [ ] **GREEN：** 最小实现后重跑 targeted；完成三类资产的失败恢复 UI 与 zh-CN/en-US 断言。每个闭环小提交只包含本批文件。

## 门禁与预测试

在仓库根激活 `scripts/dev-env.ps1`；Python 用当前 worktree 的环境，避免 editable 指向旧 checkout。

```powershell
python -m pytest tests/test_extensions_adapter.py tests/test_extensions_bridge.py tests/test_extensions_dispatch.py -q
Push-Location workbench
npx vitest run src/stores/__tests__/extensionsOperationRecovery.test.ts src/stores/__tests__/extensionsSkillGroups.test.ts src/features/workspace-explorer/__tests__/extensionsView.test.ts
npx vue-tsc --noEmit
Pop-Location
powershell -File scripts/local-gates.ps1
git diff --check
```

- [ ] targeted 与全门禁 exit 0（全门禁输出 `LOCAL GATES: ALL GREEN`）；改 CLI 重建 sidecar/bundle，改容器重建镜像并 `bash tools/vendor-refresh.sh` / `bash tools/vendor-verify.sh`，不得只更宿主二进制。
- [ ] 真实隔离容器注入可控单项失败，验证成功项完整、仅失败项重试、卸载结果与 SSOT 一致；注入和实网结果分别记录。必要远端 CI 通过后并回 `develop`，继续 b4。
- [ ] **CU 前置：** Windows + Computer Use + 本批 Workbench/CLI + ready 的测试 runtime。**操作：** ①扩展→Skills→测试组安装；②展开失败项→重试；③打开操作日志→复制诊断。**理想：** 首轮 2/3、重试仅 b、完成 3/3；复制有错误码/来源且无凭据。**异常：** 成功项重装、跨工作区污染、错误被刷新清空或日志无上限均 FAIL。
- [ ] 写入阶段 `PRETEST.md`：时间、commit、Workbench/sidecar/镜像 digest、步骤、字段级理想/实际、截图或窗口树、PASS/FAIL。无 CU 写 `NOT RUN — b3 失败项重试/日志复制 UI：当前 agent 无 Computer Use`；无窗口/runtime/Docker 则写对应具体缺项。不得把单测当 UI PASS；继续不依赖该环境的后批，统一用户手测留到全部批次预测试后。

## 实施与验证（2026-10-27）

- 已实现：三类资产操作日志与失败单项重试、部分组卸载继续、原错误保留、原参数重放、上下文与重复提交守卫；超时/协议/取消按结构化错误码归为未知而不盲重试。
- 组结果按 repo 大小写归一对齐；source_failed/missing/state_unavailable 为已知失败，blocked/pending 保留未确认原因。日志内存 100 条 FIFO、UTF-8 8 KiB 上限与完整引号凭据脱敏，双语 UI 与复制反馈。
- RED/GREEN：14 个恢复回归用例；含市场/组/日志 UI targeted 通过，审查复核无剩余问题。
- 最终全门禁：Python 1498 passed / 57 skipped / 140 subtests；Rust 368 passed / 1 ignored；Vitest 679 passed；vue-tsc 通过。debug Workbench 构建通过；未改 CLI/container，无需刷新镜像源码。
- Computer Use 与真实容器预测试 NOT RUN：本轮无 CU 工具；Docker 启动无响应已恢复停止态。详见 PRETEST 与 HANDTEST。上述实机门仍保留待验证，不能标作 PASS。
