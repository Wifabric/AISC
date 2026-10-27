# v2.1.17 b7 — 稳定工具刷新与发布就绪执行计划

> 执行 agent：使用 superpowers:executing-plans 逐项执行；本批完成发布准备与统一验收材料，不把准备完成等同已发布。

**目标：** 按 D-4 刷新镜像内置依赖，完成高频冒烟、版本/产物配对及 preview 准备。
**架构：** 发布时查询官方稳定来源 → 固定版本与可追溯校验 → 构建 sidecar/bundle/镜像 → 自动化与真实 UI 证据矩阵。
**技术栈：** Python/pytest、Docker、npm、Rust/Tauri、PowerShell、GitHub CI。

## 范围与源码

- 依据：`README.md` b7、`decisions.md` **D-4**、`DEVELOP_WIKI.md` §1.2–1.4（发布角色另遵循 §1.1）。b1–b6 集成后，从 `develop` 建 `2.1.17-b7-release-readiness`，核对 target/账本。
- 版本/构建：`config/versions.env`、`container/Dockerfile`、`scripts/stage-npm.sh`、`src/aisc/application/tool_versions.py` / `cc_switch_resolver.py`、`src/aisc/domain/cc_switch_release.py`。更新实际消费这些 pin 的默认值与离线包，不能只改文本版本号。
- 产物/门禁：`scripts/build-cli.ps1`、`scripts/verify-sidecar.py`、`packaging/artifact.py`、`tools/vendor-refresh.sh` / `vendor-verify.sh`、`scripts/local-gates.ps1`；核对 `.github/workflows/cli-sidecar.yml` / `workbench-ci.yml` / `nsis-installer.yml` / `bundle-linux-macos.yml` / `artifact.yml`。
- 验证：`tests/test_tool_versions.py` / `test_build_base_image.py` / `test_cc_switch_resolver.py` / `test_cc_switch_release.py` / `test_toolchain.py` / `test_verify_sidecar.py`，以及 `tests/packaging/`。实施时更新阶段 HANDTEST/PRETEST、decisions、todo/devlog；本文件只是待执行计划。

## D-4 稳定依赖合同

| 依赖 | 发布准备时的官方选择规则 |
| --- | --- |
| Node.js | 默认查 nodejs.org 当时 **Active LTS**；本次依 D-5 用户裁定使用最新已发布 LTS **24.22.1** 的官方 `node:24.22.1-slim`，固定镜像 digest；开发宿主仍用 Node 22 |
| Codex CLI / Claude Code CLI | 分别查 `https://registry.npmjs.org/@openai%2Fcodex`、`https://registry.npmjs.org/@anthropic-ai%2Fclaude-code` 的 `dist-tags.latest`；不追 prerelease/beta/canary，不能以最高任意 semver 代替 latest |
| cc-switch-cli | 查现有 resolver 的 `UPSTREAM_REPO` 所指官方 GitHub Releases，排除 draft/prerelease 后选最高稳定 semver；沿用 resolver，不信本地旧 pin 就是最新 |
| Mihomo / geodata / yazi 等其余已声明依赖 | 逐项核实官方稳定 release 并同步刷新；geodata 必须从浮动 `latest` 改为可追溯 dated release，三份数据同一 release |

每项在版本证据表记录查询时间、来源 URL、所选版本、资产/digest、SHA256（可获取时；不可得写具体原因）、回退版本、兼容性结果。兼容性失败时在 decisions 写明原因、替代版本、回退版本、SHA256 与验证证据；涉及行为取舍按 D-4 留待用户裁定，不能静默降级或自行改变稳定定义。

## 任务与 TDD 验收

- [ ] **RED：** 先补稳定源/版本消费回归：Node Active LTS 来源与官方 slim 组合、npm latest 排除预发布、cc-switch 稳定 semver 选择、geodata dated pin、在线/离线包主包与伴生包配对。按需新增 `tests/test_release_readiness.py`；网络响应使用固定 fixture，不让单测依赖当天最新版。
- [ ] **取证与最小刷新：** 现场查询上述官方来源，填证据表并更新全部声明依赖；同步 Docker ARG、国内镜像对应版本、digest、`stage-npm.sh` 离线包与伴生包，清理明确过期的同名前缀包，避免 Docker glob 混装。验证 cc-switch resolver 实际 receipt 与新 pin，不把故障回退缓存记作最新核查成功。
- [ ] **兼容性：** 核验 npm `engines.node`、目标架构/原生 companion、cc-switch CLI/SQLite schema、b1/b6 安装与默认态，以及 b5 CLI/bundle manifest。失败保留旧可用产物和回退记录，发布门保持关闭；新增行为取舍不得混进普通依赖刷新。
- [ ] **构建与 GREEN：** targeted 通过后重建 sidecar、stage/verify bundle、vendor refresh/verify、无缓存镜像和 Workbench/NSIS；用实际二进制与镜像内 `node --version`、`codex --version`、`claude --version`、`cc-switch --version` 对照证据表，记录 commit、SHA256、image digest。用户 pin 保留，出厂版本与用户覆盖分开记。
- [ ] **高频冒烟：** 无代理隔离工作区重复 3 轮“市场搜索→三类推荐→安装→更新/检查→卸载”，至少一轮多子技能组及受控单项失败→仅失败项重试；日志≤100 条且单条≤8 KiB、诊断可复制。另测 Services 注册/打开、caveman 新装双开/升级保留 off、direct 失败 mirror 成功与全失败、D-2 ready/取消/显式退出更新。记录实际版本源 unsupported，不伪造 Skills/MCP 可更新状态。
- [ ] **异步回归：** 重跑 b3–b6 deferred 场景，重点 A→B→A、搜索乱序、旧 finally、旧下载 progress、确认期间目标改变；观察无跨 runtime 操作、无旧包启动和成功项重复执行。
- [ ] **发布材料：** 汇总 b1–b7 PASS/FAIL/NOT RUN、剩余风险及 HANDTEST 操作/理想字段/前置/异常判据。全部需要 UI/实机的批次已预测试或有具体阻塞后，仅发起一次统一用户手测；FAIL 先修复重跑，不交给用户排错。

## 门禁命令

仓库根使用本 worktree 的 Python 环境及 `scripts/dev-env.ps1`；以下都是实施时执行，本文不宣称已通过。

```powershell
python -m pytest tests/test_tool_versions.py tests/test_build_base_image.py tests/test_cc_switch_resolver.py tests/test_cc_switch_release.py tests/test_toolchain.py tests/test_verify_sidecar.py tests/packaging -q
bash scripts/stage-npm.sh --yazi --all-arches
bash tools/vendor-refresh.sh
bash tools/vendor-verify.sh
powershell -File scripts/build-cli.ps1
python scripts/verify-sidecar.py smoke workbench/src-tauri/binaries/aisc-x86_64-pc-windows-msvc.exe --triple x86_64-pc-windows-msvc
python packaging/artifact.py stage --root . --output workbench/src-tauri/nsis/bundle
python packaging/artifact.py verify --bundle workbench/src-tauri/nsis/bundle/aisc-bundle
powershell -File scripts/local-gates.ps1
git diff --check
```

- [ ] 用本批 CLI 执行 `aisc build --no-cache` 并在隔离工作区运行新镜像；必须真正执行 bundle verify。全门禁要求 exit 0 / `LOCAL GATES: ALL GREEN`，重建后再测真实路径；必要远端 CI 全绿、并回 `develop` 并核对实际 commit。
- [ ] **CU 前置：** Windows/CU、当前构建与新镜像、隔离工作区、NSIS 测试包。**操作：** ①打开工作区→扩展执行三轮冒烟；②Services 核对分组；③设置→下载更新→取消→再确认；④诊断→复制健康报告。**理想：** 每轮安装/卸载 SSOT 对齐，无遗留 busy/旧错误、只重试失败项、显式更新顺序满足 D-2。**异常：** 崩溃、跨上下文污染、静默安装、版本与证据表不同均 FAIL。
- [ ] `PRETEST.md` 写时间、commit、Workbench/sidecar/镜像 digest、逐项理想/实际、截图/窗口树及结论。无 CU 写 `NOT RUN — b7 统一 UI 冒烟：当前 agent 无 Computer Use`；无 Docker 写 `NOT RUN — b7 新镜像三轮数据面冒烟：Docker daemon 不可用`；无 NSIS 写 `NOT RUN — b7 真实更新冒烟：缺少本批 NSIS 测试产物`；来源无法查询写 `NOT RUN — D-4 <依赖> 最新稳定版本核查：<具体 URL/错误>`。不能将这些项勾为通过或以旧产物冒充新产物。
- [ ] 最终状态为“preview 准备就绪”或带具体阻塞的“未就绪”；阶段收尾仍由用户宣布。准备 `.devN` preview 版本/Release Notes 与配对清单，不自动合并 main、打 tag、发布或清理分支/Release；正式流程另遵循开发手册，连续批次授权不等同发布授权。

## 实施前版本规则细化（2026-10-27）

- Node：用户已明确批准 D-5 的 LTS 24.22.1 例外；回退版本为既有 Node 22，不能先行把 10-28 才进入 LTS 的 Node 26 当作本次稳定基线。
- geodata：上游只有可变 `latest` 发布和被 force-push 的 `release` 分支，没有 dated release tag。采用 AISC 日期快照 `20261027`，固定数据 commit `02ae05ac06e8c9287916fbabfe61ef5c8591407f`，记录上游 release ID 与三文件 SHA256；本地 vendor 持有字节，不把日期伪装成上游 tag。Docker fallback 用 commit-pinned raw URL 并验证三文件 checksum，缺失/不匹配必须失败。
- 离线包必须按版本及目标架构精确选择；npm 主包与 native companion 同代并先验证 registry integrity，不能让残留旧包通过 glob 覆盖新 pin。遵循既有 Git 策略：native companion 仅进入分发 bundle，不纳入 Git。

## 实施边界补充（2026-10-27）

- 从 b6 PR #45 的 develop merge `7d2c7a2` 建 `codex/2.1.17-b7-release-readiness`。
- bundle 验证补查未入 Git 的 npm native companions：随包文件必须与 factory 主包 optionalDependencies 的真实包名/版本相符（含 Codex npm alias），旧版本/改名旧包/损坏包均失败；缺少 companion 仍允许既有在线 pin fallback，不把 repo 的小预置误判为完整离线闭包。
- 最新查询只接受 `latest` 指向的稳定三段版本；遇到 beta/canary/无效 metadata 返回未知，不推广预发布版。
- Node 官方 index digest 已经由 dockerproxy.net 镜像成功拉取并匹配；docker.1ms.run 与 daocloud 在本次探测中超时，未绕过 digest。
- cc-switch 选择器此前按发布时间排序，可能选择后发旧分支补丁；依 D-4 改为稳定 semver 数值排序并补回归，不改变 draft/prerelease/缺 digest 排除规则。
- 本批本地 Workbench 构建标识更新为 2.1.17（`tauri.conf.json` 为 Workbench 版本源）；CLI 仍为本阶段 0.1.10.dev0。preview 发布号/发布文件另准备，未授权发布前不创建 tag 或 Release。
- 新 geosite.dat 的 protobuf 字节被 Git 自动文本探测误判；明确将 downloads 数据库/压缩包标为 binary，避免换行归一化损坏官方 checksum，并在暂存后重新核对 index 字节。
