# v2.1.17 b6 — Services 与 caveman 默认态执行计划

> 执行 agent：使用 superpowers:executing-plans 逐项执行；沿用已授权连续流程，不逐批请求审批或用户手测。

**目标：** Services 注册服务与宿主工具同类可见；caveman 新安装默认双端开启，升级保留用户关闭选择。
**架构：** 复用 runtime.webServices 与现有 Services UI；默认态在安装/注册阶段写入 cc-switch SSOT，UI 只读事实。
**技术栈：** Vue/Pinia/Vitest、Python/SQLite/pytest、Docker、cc-switch CLI。

## 开工与源码

- 依据：`README.md` b6、`decisions.md` **D-3**、`DEVELOP_WIKI.md` §1.2–1.4。从前批已集成的 `develop` 建 `2.1.17-b6-service-caveman-defaults`，核对 target/账本。
- Services：`workbench/src/features/workspace-explorer/WorkspaceExplorer.vue`（`servicesSupported`、`serviceLabel`、services panel）、同目录 `HostToolsServicePanel.vue`、`workbench/src/stores/runtime.ts`、`workbench/src/lib/webServices.ts`。
- caveman：`container/cc_switch_skills.py`（`_load_skill_states`、`sync_required`、`_register_skills`、`synchronize`）、`container/entrypoint.sh`、`container/Dockerfile`；复核 `container/aisc-extensions-adapter` 安装/更新的开关保留逻辑。
- 测试：`workbench/src/features/workspace-explorer/__tests__/servicesPanel.test.ts` / `servicesHostTools.test.ts`、`workbench/src/stores/__tests__/runtimeWebServices.test.ts`、`tests/test_preview_factory_skills.py` / `test_cc_switch_runtime.py` / `test_extensions_adapter.py`。双语字段修改 `workbench/src/i18n/zh-CN.ts` / `en-US.ts`。

## D-3 精确合同

- Services 视图在“宿主工具（F2）”后显示“注册服务”分组；只取 `runtime.webServices.services`，按数字端口升序。label 为非空 `name`，空/纯空白则“端口 {port}”；协议与状态走 zh-CN/en-US i18n；capability 缺失显示 unsupported 文案，宿主工具仍可见。
- caveman 工厂镜像、全新默认工作区、卸载重装、缺行重建均以 `enabled_claude=1`、`enabled_codex=1` 落库；已有用户显式 off 的升级路径逐字段保留 off，不能为了双开而覆盖已有行。
- 现有 `_register_skills` 已有 `INSERT OR IGNORE` 默认 1/1，先定位哪条工厂/启动/重装链绕过或覆盖默认态；不要为修复默认值增加每次启动强制 enable。

## 任务与 TDD 验收

- [x] **RED / Services：** 构造 services 输入顺序 5173、3000，断言分组顺序“宿主工具（F2）→注册服务”、行顺序 3000→5173；分别测有名、空名、空白名、协议/状态双语、零条目、gateway 非 ready、capability 缺失。先跑 targeted 确认缺分组等业务断言失败。
- [x] **实现 Services：** 用排序后的派生数组，不原地 mutate runtime 数据；保留 URL 复制/打开动作，unsupported 不渲染假注册行。deferred 测工作区 A→B→A 的迟到轮询/错误/finally 不覆盖 B 或新一轮 A，沿用 runtime 代际守卫。
- [x] **RED / caveman：** SQLite 夹具覆盖全部 13 个 caveman 子技能：空库首次安装→1/1；删除行后重建→1/1；卸载重装→1/1；已有 1/0、0/1、0/0 在内容升级/容器重启后逐项不变；混合现有 off 与缺行时只补缺行双开。断言新行时间/目录/identity 与既有规则一致，不误改 grill-me 或用户自建项。
- [x] **定位并修复安装链：** 分别核对 Docker factory、entrypoint 首次同步、marker 命中、bundle revision 改变与 adapter 重装。缺行必须触发同步，已有 off 不应触发“修复开启”；双开状态在安装成功返回前落库并同步到对应 Claude/Codex 路径，失败不写成功 marker。复用既有 SQLite 注册边界和官方 sync，不扩散私写数据库逻辑。
- [x] **一致性/竞态：** 失败后重试、两个启动同步竞争锁、marker 存在但行缺失均不会跳过注册；同一技能不会重复建行。更新安装与 UI 切换 runtime 并发时，旧刷新不得把新 runtime 的开关改回 on。
- [x] **GREEN：** 重跑 targeted，真实镜像中新默认工作区核对 DB 与路径；再将一个 caveman 的 Codex 设 off，重建/升级并核对仍 off。安装默认态与升级保留态分别留证，小提交闭环。

## 门禁与预测试

```powershell
python -m pytest tests/test_preview_factory_skills.py tests/test_cc_switch_runtime.py tests/test_extensions_adapter.py tests/test_web_services.py -q
Push-Location workbench
npx vitest run src/features/workspace-explorer/__tests__/servicesPanel.test.ts src/features/workspace-explorer/__tests__/servicesHostTools.test.ts src/stores/__tests__/runtimeWebServices.test.ts
npx vue-tsc --noEmit
Pop-Location
bash tools/vendor-refresh.sh
bash tools/vendor-verify.sh
powershell -File scripts/local-gates.ps1
git diff --check
```

- [ ] 容器源码变更后重建镜像；CLI 有变更时重建 sidecar/bundle；targeted/全门禁与必要远端 CI 通过后并回 `develop`。容器验证包括新建、重启、升级、重装四路径，不能仅看 UI 开关。
- [ ] **CU 前置：** Windows/CU、当前构建和新镜像、隔离 ready runtime，已注册 3000/5173 两服务。**操作：** ①Services→观察两分组与服务行；②扩展→展开 caveman→查看 C/X；③关闭一个 X→重启/升级；④卸载测试子技能→重装。**理想：** 分组及端口升序，有名用名称、空名“端口 5173”；新装/重装 C/X 均 on，升级后已有 X=off 仍 off。**异常：** 服务混入宿主工具、off 被覆盖或 DB/UI 不一致均 FAIL。
- [ ] `PRETEST.md` 记时间、构建/sidecar/镜像 digest、操作、字段级理想/实际、截图/窗口树和 PASS/FAIL。无 CU 写 `NOT RUN — b6 Services 分组/caveman 开关 UI：当前 agent 无 Computer Use`；无 Docker/新镜像写 `NOT RUN — b6 工厂及升级数据面：Docker 不可用/缺少本批重建镜像`，明确实际原因。继续 b7，不逐批请用户手测。

## 实施前核查（2026-10-27）

- 从已合入 PR #44 的 origin/develop（3c05c59）建本批 codex 分支。
- Docker 已恢复响应。旧 b2 镜像隔离 HOME/config 首次调用安装 helper，真实 SQLite 13 个 caveman 子技能及 grill-me 均为 1/1；现有 `_register_skills` 已实现新行双开，不能无依据地每次启动强制 enable。
- 重点补齐此前误标 factory-cleared 而跳过的同步回归，并在真实 cc-switch 上验证缺行、重装与用户 off 保留。若现有链条满足合同，保留正确实现并补防回归证据；发现安装成功但数据/目标未对齐则在同一安装边界修复。

## 执行记录（2026-10-27）

- Services 双语分组、名称回退、端口派生排序与 capability/空态已实现，打开/复制保留。runtime 代际失效防 A→B→A 污染，等价 Windows 路径写回不误失效；清缓存释放旧轮询所有权，旧 finally 不解锁新请求。新增业务回归先 RED 后 GREEN。
- caveman 现有安装链满足 D-3，无需修改生产容器 helper；恢复四个被错误 skip 的出厂同步用例，补全 13 子技能首装、缺行、重装、off 保留与失败重试证据。真实镜像五条路径 PASS，见 PRETEST。
- 全门禁输出 LOCAL GATES: ALL GREEN：Python 1540 passed / 53 skipped / 181 subtests；Rust 398 passed / 1 ignored；Vitest 770 passed；vue-tsc 通过。targeted Python 143 passed / 1 skipped / 85 subtests；文档检查 39/0/0；前端生产/debug Workbench 构建通过。
- 本批未改 CLI/container，无需重新冻结或构建镜像；UI 因 CU 工具不可用 NOT RUN，用户最终验收保持未勾选。
