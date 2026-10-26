# v2.1.17 b1 — 无代理扩展安装/更新完整性与诊断 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox
> (`- [ ]`) syntax for tracking.

**Goal:** 宿主机无代理时，多子技能 skill 组安装/更新要么完整成功，要么给出可诊断
失败并明确部分安装状态，不再只显示一个半安装项或泛化的“ AISC CLI错误”。

**Architecture:** 以 container adapter 为网络与官方 CLI 边界，新增组级安装/更新
预检与单一镜像源复用；Python bridge 只透传结构化 itemized result；Workbench 组操作
改为调用组级 API 并展示每个子项的完成/失败原因。默认安装继续显式启用 Claude 与
Codex，不启用宿主系统代理。

**Tech Stack:** Python 3.12 script adapter + unittest, aisc application bridge,
Vue/Pinia + Vitest, real Docker/container smoke。

---

## Task 0：清理误触 b1 历史

**Files:**
- Modify: `container/aisc-extensions-adapter`
- Modify: `src/aisc/application/extensions.py`
- Modify: `workbench/src/stores/extensions.ts`
- Modify: `workbench/src/features/workspace-explorer/ExtensionsView.vue`
- Modify: tests and plan records affected by `7534863` / `f9af814`

- [x] 在 `develop` 执行 `git pull --ff-only`，确认 `git status --short` 为空；
      从该点创建 `2.1.17-b1-proxyless-extension-reliability`。
- [x] 按提交时间倒序分别撤销误触记录，不允许一个命令留下半撤销状态：
      1. `git revert --no-edit f9af814`（先撤销 b1 smoke 记录）；
      2. `git revert --no-edit 7534863`（再撤销实现）。
      若冲突仅由 `1d9e2b9` 已重写/改名同一阶段计划文档引起，则以当前重启版
      README / b1 计划为准并删除旧 `b1-market-metadata-and-update-signals.md`；
      其它冲突仍立即 `git revert --abort` 并报告，不得提交半 revert。
- [x] Post-revert 门：
      - `git diff --exit-code e91d1fe -- src/aisc/VERSION docs/releases/v0.1.10.dev0.md tests/fixtures/cli/envelope-version.json`
        必须无输出，证明阶段开题与 CLI 版本保留；
      - `git log --oneline -4` 必须显示两个独立 revert commit；
      - `git status --short` 必须为空。
- [x] `. scripts\dev-env.ps1` 后运行
      `python -m pytest tests/test_extensions_adapter.py tests/test_extensions_bridge.py -q`。
      PASS：36 passed（回到误触前基线）。

## Task 1：RED — 组安装必须预检全部子技能

**Files:**
- Modify: `tests/test_extensions_adapter.py`

- [x] 新增测试：伪造 Git clone 返回 `skills/cavecrew` 与 `skills/caveman-commit` 两个
      `SKILL.md`，输入组 specs 包含两个目录；现有实现只处理传入目录/重复网络探测，
      应先失败于缺少组级 API。
- [x] 断言期望行为：
  - 每个 spec 的 source skill 都能被解析；
  - 任一子技能缺失时，不执行任何 `cc-switch skills install`；
  - 全部存在时，才按顺序 install 两个 spec。
- [x] 运行 `python -m pytest tests/test_extensions_adapter.py -q`。
      RED 已确认，原因是 `skill_install_group` / 全量预检不存在。

## Task 2：GREEN — adapter 组级安装与镜像源复用

**Files:**
- Modify: `container/aisc-extensions-adapter`
- Test: `tests/test_extensions_adapter.py`

- [x] 实现最小 `skill_install_group(specs: list[str]) -> dict`：
  - 校验非空、去重并保留顺序；
  - 对 unique repo 只做一次 archive/Git source 选择；
  - mirror clone 后一次性枚举所有有效 skill 目录；
  - 全部预检通过后逐个执行官方 install；
  - 默认对每个目录执行 Claude/Codex enable；
  - 返回 `{total, completed, items: [{spec, status, error}]}`。
- [x] 保持单个 `skill_install` 行为兼容，不在本任务引入缓存。
- [x] 运行 `python -m pytest tests/test_extensions_adapter.py -q`：34 passed。
- [x] Commit: `feat(extensions): preflight skill group installs`（`1908dfa`）。

## Task 3：RED — Python bridge 透传组级结构化结果

**Files:**
- Modify: `tests/test_extensions_bridge.py`
- Modify: `src/aisc/application/extensions.py`

- [x] 先扩展 bridge 测试：`skill-install-group` 校验 specs 数组，透传 adapter 的
      total/completed/items，并把 adapter error 转为用户可读 technical detail。
- [x] 运行 `python -m pytest tests/test_extensions_bridge.py -q`：RED，原因是 op 不存在。
      Expected: FAIL，原因是 op 不存在。
- [x] 将 op 加入 allowlist 并实现参数/result 透传。
- [x] 重跑 bridge 测试。Expected: PASS。
- [x] Commit: `feat(cli): bridge skill group install results`（`3d0d8c0`）。

## Task 4：RED — Workbench 组操作展示逐项结果

**Files:**
- Modify: `workbench/src/stores/extensions.ts`
- Modify: `workbench/src/stores/__tests__/extensions*.test.ts`
- Modify: `workbench/src/features/workspace-explorer/ExtensionsView.vue`
- Modify: i18n dictionaries and view tests as needed

- [x] 先写 Vitest：
  - market group install 调用 `skill-install-group`，不是 N 个独立调用；
  - itemized failure 保留 technical detail，不折叠成“AISC CLI错误”；
  - 失败后刷新列表，已安装组显示已安装/缺失子项。
- [x] 运行 `npm run test -- extensions`：RED，组调用仍被拆成多次。
- [x] 实现 store 组级调用、operation progress 与错误详情。
- [x] UI 已安装/市场组显示 `x/y` 和可复制错误文本。
- [x] 重跑 targeted Vitest 与 `npx vue-tsc --noEmit`。Expected: PASS。
- [x] Commit: `feat(workbench): report skill group install progress`（`7634d2f`）。

## Task 5：更新链路与默认开启回归

**Files:**
- Modify: `tests/test_extensions_adapter.py`
- Modify: `container/aisc-extensions-adapter`

- [x] RED：先新增
      `test_skill_update_group_preflights_all_and_preserves_enable_state`，调用
      不存在的 `A.skill_update_group([...])`，并断言两个子技能先全量预检、
      按原 Claude/Codex 状态恢复、新安装默认双引擎开启。
      Run: `python -m pytest tests/test_extensions_adapter.py -k skill_update_group -q`
      Expected: FAIL，原因是 `AttributeError: module ... has no attribute
      'skill_update_group'`。
- [x] GREEN：实现 `skill_update_group`，复用组级 source/preflight，不复制网络
      逻辑；安装与更新分别验证默认开启/保留状态。
- [x] 运行 adapter + bridge tests。Expected: PASS。
- [x] Commit: `fix(extensions): preserve skill enablement during group update`（`0e7f971`）。

## Task 6：验证与手测记录

- [x] `python -m pytest tests/test_extensions_adapter.py tests/test_extensions_bridge.py tests/test_extensions_dispatch.py -q`：当前 56 passed + 10 subtests
- [x] `cd workbench && npm run test -- extensions && npx vue-tsc --noEmit`：21 passed + typecheck 通过
- [x] `powershell -File scripts/build-cli.ps1`：sidecar 构建并同步成功
- [x] `bash tools/vendor-verify.sh`：1532 checksums passed
- [x] 按 [HANDTEST.md](HANDTEST.md) 收集真实容器结果：H2/H4 数据面 PASS；
      H1/H2 UI 与 H3 按前置条件记录 NOT RUN，未用单元测试替代。
- [x] `powershell -File scripts/local-gates.ps1`：ALL GREEN（Python 1486 / Rust 366 / Vitest 644 / vue-tsc）
- [x] 更新本文件勾选、HANDTEST 结果、README 状态与 `docs/devlog.md`；并回
      develop 前等待 Workbench UI 手测与远程 CI。




## 审查修正（2026-10-26）

- [x] direct / mirror 组源均执行一次全子技能 source preflight；实际 clone 体失败时按
      selected → direct → ghfast → gh-proxy 重试，并保留每个来源的诊断。
- [x] `--specs` 全链路改为 JSON 数组，避免逗号拆分 externally sourced skill id。
- [x] repo/directory 解析集中在 subprocess 前校验；空目录、`.`、`..`、绝对/反斜杠
      路径和控制字符拒绝。
- [x] 组更新前逐项读取 enable state；任一不可读则整组 0/N，不执行 install。
- [x] 本地/非 GitHub 组安装默认双引擎开启；更新使用组预检捕获的状态，不再二次读取。
- [x] Python bridge 与 Rust Tauri 使用同公式组级超时预算
      `30 + 450*unique_repos + 240*children` 秒，避免 30 秒 generic timeout。
- [x] `scripts/dev-env.ps1` 将当前 checkout `src` 移到 `PYTHONPATH` 首位，隔离
      worktree 不再误导入主 checkout。
- [x] CLI text 输出为 `completed/total` 与逐项 `spec/status/error`。
- 当前验证：targeted Python 56 + subtests、extensions Vitest 21、vue-tsc、Rust 366、
  vendor 1532、sidecar/bundle 重建、真实容器 H2/H4 数据面 PASS；全门禁 ALL GREEN
  （Python 1486 / Rust 366 / Vitest 644 / vue-tsc）。
