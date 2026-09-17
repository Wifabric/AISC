# P0 开池前置批——存量入库 · 版本基线 · 计划生效 · 收口卫生

> 状态：待做。目标：把 0.1.0 周期开在一个干净的工作树上。全部为 docs/配置/版本号操作，无功能代码。

## 范围（scope）

1. 工作树存量分批提交（约 10 个未提交文件，D-16）。
2. 四件套 bump `0.1.0.dev0`（D-1）。
3. `docs/plans/0.1.0-dev-plans/` 六文件入库 + `docs/plans/README.md` 指向修正（D-20②）。
4. 2.1.11 收口卫生回填：archive README 两行陈旧「待做」+ devlog 补记 v2.1.11-dev 发布条目（D-20①）。
5. todo.md 整备：[x] 四条核对回填、todo:72 关闭、V0.1.0-target 段按 R1-R8 补注（D-16/D-21）。

明确不做：DEVELOP_WIKI §11 发版流程校正（归 A8，指南 3.5.3）；任何功能代码；Slurm/PBS（阻塞不排期）。

## 契约（contracts）

- 四件套同步不变式：根 VERSION == tauri.conf.json version 的 PEP 440 归一化 == tests/fixtures/cli/envelope-version.json 三字段（:7,:11,:12）== `docs/releases/v<VERSION>.md` 存在（封版提交 0db2b13 文件面即清单；devlog.md:138-141）。
- `v0.1.0.dev0.md` 为占位 notes：h1 `# AISC v0.1.0.dev0` 逐字保留 + 一段「开发周期开启」声明；周期末 final 另建 `v0.1.0.md`。
- tauri.conf.json 沿 dash 格式（`0.1.0-dev`，语义是 Workbench 应用版本），归一化比对由 A6 check-version-sync 兜底（指南 3.4.2）。
- dot tag `v0.1.0.dev0` 本批**不推送**：tag 是 pypi-publish 的 dispatch 输入而非 bump 附件，随 A6 首次 TestPyPI 上传时推送（D-26）；本批只落四件套。
- todo.md 语义：[x] 只允许指向已有交付证据的行。

## 实施顺序

1. **批 1 docs**：DEVELOP_WIKI §2 开发环境重写（+189 行）、pypi-release-guide.md（同目录）（未跟踪新文件）、docs/todo.md（V0.1.0-target 整备 + [x] 核对）。提交前完成 D-16 的四条核对。
2. **批 2 scripts/环境**：scripts/dev-env.ps1、scripts/dev-env.sh、scripts/local-gates.ps1（dev-env 激活 + 短 TEMP）、.gitignore（新增 `/containers.json`）；删除仓库根游离 containers.json（内容为空 registry，运行时泄漏）。
3. **批 3 workbench UI**：SettingsForm.vue（远程机器表格列）、i18n zh-CN.ts/en-US.ts（machines 词条）、workbench/src-tauri/Cargo.toml。
4. **批 4 tests**：tests/features/test_streaming_captured_cross_platform.py、tests/test_serve_fs.py（Windows 裸机修复）。
5. **批 5 版本与计划**：四件套 bump + 本目录六文件 + docs/plans/README.md 指向修正 + archive/2.1.11-dev-plans/README.md:11,14 回填 + devlog 补记（开池条目 + v2.1.11-dev tag/Release 发布补记，新到旧排序）。

## 验收（acceptance）

- 批 1 后：`bash tools/check-docs.sh` 通过。
- 批 2/4 后：`python -m pytest tests/ --ignore=tests/integration -q` 通过（local-gates 第一门）。
- 批 3 后：`pnpm vitest run` + `pnpm vue-tsc --noEmit` + `cargo test --lib`（在 workbench/src-tauri 下）通过。
- 批 5 后：`git status` 干净；`cat VERSION` 输出 `0.1.0.dev0`；`jq -r .version workbench/src-tauri/tauri.conf.json` 输出 `0.1.0-dev`；`python -m pytest tests/packaging/ -q` 通过（envelope fixture 一致性）；`git tag --list 'v0.1.0*'` 为空（dev0 tag 未推送，D-26）；手测：先关闭 Workbench（运行中 aisc.exe 锁文件，DEVELOP_WIKI §2.3/2.7），跑 `scripts/build-cli.ps1` 重建 sidecar，启动后 `aisc version --format json` 三字段均 0.1.0.dev0。
- 最终：`scripts/local-gates.ps1` 四硬门全绿。

## 风险

| 风险 | 证据 | 缓解 |
| --- | --- | --- |
| i18n 两文件已有未提交改动，分批时误拼 | git status（zh-CN.ts/en-US.ts modified） | machines 词条整体归批 3 一次提交 |
| bump 后 sidecar 未重建致 version 契约红 | tests/fixtures/cli/envelope-version.json:7,11,12 | 批 5 含 build-cli + 重启 Workbench 手测 |
| todo [x] 回退引发异议 | git diff docs/todo.md:163-183 | 逐条附证据（D-16），留用户复核 |
| 提前推 dev0 tag 造成后续 devN 错位 | tag 是 pypi-publish dispatch 输入（指南 3.4.1） | 契约锁定本批不推 tag（D-26） |

## 决策引用

D-1、D-16、D-20、D-21；tag 推送时点另见 D-26（见 decisions.md）。

## 回滚（rollback）

全部为 docs/配置/版本号操作，无运行时行为变化（除 sidecar 版本串）；任一批独立 `git revert`。四件套回退=反向改回四文件（无门拦截），但会直接阻塞 A6 的 TestPyPI 迭代基线——回退前须知会。
