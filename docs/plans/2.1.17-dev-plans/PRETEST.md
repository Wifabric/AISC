# v2.1.17 Computer Use 预测试记录

> 执行环境：Windows 11；早期会话 Computer Use 可用，2026-10-27 续跑会话未暴露 Computer Use / JavaScript 工具。按 DEVELOP_WIKI §1.4，本文件先于用户
> 统一手测记录 agent 预测试；`PASS` 不替代用户最终手测。

## 状态总览

| 批次 | 实现状态 | 预测试 | 说明 |
| --- | --- | --- | --- |
| b1 | 已实现 | UI 关键路径 PASS | H1 安装、H4 更新状态保留已用真实 Workbench UI 执行 |
| b2 | PR #41 已合并 | 早期 UI PASS；最终补丁 NOT RUN | 续跑工具清单无 Computer Use；自动化与 debug 构建通过 |
| b3 | PR #42 已合并 | NOT RUN | 本轮没有 Computer Use；Docker 引擎启动后无响应，已恢复停止态 |
| b4 | PR #43 已合并 | NOT RUN | 当前会话无 Computer Use，Docker 引擎不可用 |
| b5 | PR #44 已合并 | 数据面 PASS / UI NOT RUN | 冻结 CLI 配对通过；CU 不可用，Explorer/NSIS 未点击 |
| b6 | PR #45 已合并 | 容器 PASS / UI NOT RUN | caveman 五路径通过；CU 不可用，Services/开关 UI 未点击 |
| b7 | 实现/审查/本地门禁通过，产物验证中 | 进行中；UI NOT RUN | 新镜像与 caveman/Services 数据面 PASS，三轮扩展冒烟运行中；CU 不可用 |

## b1 预测试（2026-10-26）

### 运行标识

- Workbench：分支 `2.1.17-b1-proxyless-extension-reliability` 的
  `workbench/src-tauri/target/debug/workbench.exe`
- Explicit CLI：同分支 `workbench/src-tauri/target/debug/aisc.exe`
  （避免 worktree `.venv` editable 指回主 checkout）
- 镜像：`super-claude:latest @ sha256:c2a0790a297b214c360158ac957683b43c8bc571f97e7adb6d0a61087f6bc352`
- 工作区：`C:\Users\wangyu\AppData\Local\Temp\AISC-217-B1-CU-45b44292155c44c0b6424306cd3452e8`

### 发现并修复

1. **Explicit CLI 优先级破坏**
   - 现象：即使 `workbench.exe --aisc-cli <branch-cli>` 启动，本地 target/serve 仍
     复用已安装版 `C:\Users\wangyu\AppData\Local\AISC Workbench\aisc.exe`，
     导致 `skill-install-group` 以空 stdout 被 serve 报
     `cli op got non-envelope output: ''`。
   - 根因：`session::resolve_cli()` 只读 saved pin，未优先读取 `CliArg`。
   - 修复：`resolve_cli_choice(explicit, pin)` 让 explicit path 先于 saved pin；
     新增 Rust 回归 `explicit_cli_path_outranks_saved_pin`。
2. **Market repo 大小写漂移**
   - 现象：skills.sh 返回 `juliusbrussee/caveman`，SSOT 已登记
     `JuliusBrussee/caveman`；cc-switch 对同目录报
     `SKILL_DIRECTORY_CONFLICT`。
   - 根因：组安装未按 directory 对齐已注册 repo 的 owner/name 大小写。
   - 修复：`_canonical_skill_spec()` 在 group dedup 前按 SSOT directory 匹配
     casefold 相同的已注册 repo，并用已登记大小写执行官方 install；新增
     `test_skill_group_reuses_registered_repo_casing`。
   - 注意：adapter 位于容器镜像内，修复后必须重建 Docker 镜像；仅重建 sidecar
     不够。本轮已重建镜像并用新 runtime 复测。

### H1 UI 安装路径 — PASS

Computer Use 实际操作：

1. 通过最近工作区打开预测试 workspace。
2. 等待预检结果：Docker / 工作区 / 镜像 / 网络 / 运行时冲突均显示“通过”。
3. 点击“启动”，等待状态“就绪”。
4. 点击左侧“扩展”。
5. 在“搜索技能商城（skills.sh）”输入 `caveman` 并点击“搜索”。
6. 观察市场结果：`juliusbrussee/caveman · 13 个技能`。
7. 点击该行“安装全部”。
8. 操作期间窗口树出现状态：`安装中 / 0/13 / juliusbrussee/caveman`，
   全部操作按钮禁用；当前组级 IPC 非流式，0/13 保持到完成符合已文档化行为。
9. 约 6.5 分钟后操作状态消失，按钮恢复可用，未出现错误 alert。
10. 数据面复核：13 个 `JuliusBrussee/caveman` 子技能均存在，且
    `enabled_claude=true, enabled_codex=true`。

### H4 UI 更新状态保留 — PASS

Computer Use 实际操作：

1. 展开 `JuliusBrussee/caveman` 已安装组。
2. 点击子技能 `caveman` 的 `X`（Codex 启用/停用）。
3. 观察 toast/status：`切换完成：caveman`。
4. 点击父组“更新全部”。
5. 操作期间窗口树出现 `更新中 / 0/13 / JuliusBrussee/caveman`；
   当前组级 IPC 非流式，0/13 保持到完成符合已文档化行为。
6. 约 6.5 分钟后操作状态消失，按钮恢复可用，未出现错误 alert。
7. 数据面复核：
   - `caveman`: Claude=true，Codex=false；
   - 其余 12 个 caveman 子技能：Claude=true，Codex=true。
   - 用户显式关闭状态未被更新覆盖。

### 未执行的 H2/H3 UI

- H2 UI 的“direct 失败 + mirror 可用”未在本轮 UI 重构后重复执行；此前的当前
  数据面 H2 证明已记录于 HANDTEST。若统一用户手测前需要完整 UI H2，可在容器
  `/etc/hosts` 屏蔽 `github.com` 后重复 H1。
- H3 前置条件仍不满足：ghfast 与 gh-proxy 均可访问；不得伪充实网全失败结果。

## b2 预测试（2026-10-27）

### 运行标识

- Workbench：分支 `2.1.17-b2-market-metadata-update-signals` 的
  `workbench/src-tauri/target/debug/workbench.exe`
- Explicit CLI：同分支 `workbench/src-tauri/target/debug/aisc.exe`
- 镜像：`super-claude:latest @ sha256:f7f313cd301f9483d41897e99dbe9b927164d9f04eb36d10a35aa3928c2bc76f`
- Runtime：`29c6daac-f6c3-4715-bc24-6a4f73f029ce`
- 工作区：`C:\Users\wangyu\AppData\Local\Temp\AISC-217-B2-CU-b9ae99f64dde4a4db3f13047090d9d27`
- 预测试后 container `956b12973cc3` 已 stop/remove。

### 发现并修复

1. **updates-check 覆盖 envelope schema**
   - 现象：Workbench 执行更新检查后收到 schema 错误；inner result 的 `schema`
     覆盖 adapter envelope 顶层 `schema`。
   - 修复：合并前移除 inner `schema`，并新增 adapter envelope 回归测试。
2. **MCP 搜索未暴露 cache metadata**
   - 现象：Skills/Plugins 搜索能显示“已刷新 / 缓存结果”，MCP envelope 缺少
     cache 字段。
   - 修复：MCP handler 改用统一 `mcp_search_result()` wrapper，并补三资产
     envelope 测试。

### UI 关键路径 — PASS

1. 以 explicit branch CLI 启动真实 Workbench，等待 Runtime “就绪”。
2. 进入“扩展”，确认顶部出现“检查更新”按钮。
3. 点击“检查更新”，操作完成且无 schema / adapter 错误。
4. 展开 installed `JuliusBrussee/caveman` 组，13 个子技能均显示
   “暂无可靠版本源”，与 skills.sh 无可比版本字段的裁定一致。
5. Skills 市场搜索 `caveman`，返回 `juliusbrussee/caveman · 13 个技能`，
   cache chip 显示“已刷新”。
6. 切到 MCP 市场搜索 `pdf`，Smithery 返回结果，cache chip 显示“已刷新”。
7. 搜索清空后市场结果与缓存状态同步清空。

### 验证证据

- Targeted：adapter / bridge / dispatch Python `61 passed + 11 subtests`；
  extensions Vitest `25 passed`；vue-tsc 通过；Rust `368 passed`。
- Vendor：`1532` checksums 全部通过。
- Sidecar / NSIS bundle / Workbench debug exe 已重建并验证。
- Docker image 重建为
  `sha256:f7f313cd301f9483d41897e99dbe9b927164d9f04eb36d10a35aa3928c2bc76f`。
- Full local gates：Python `1492 passed, 57 skipped`；Rust `368 passed,
  1 ignored`；Vitest `648 passed`；vue-tsc 通过，输出
  `LOCAL GATES: ALL GREEN`。
## 后续批次

b2–b7 完成实现与自动化验证后，逐批追加 Computer Use 预测试记录。全部批次均达到
PASS 或记录具体阻塞后，才发起用户统一手测窗口。

### 修复后验证

- Targeted：adapter / bridge / dispatch Python `57 passed + 10 subtests`，extensions
  Vitest `21 passed`，vue-tsc 通过，Rust `367 passed`。
- Vendor：`1532` checksums 全部通过。
- Sidecar / bundle / Workbench debug exe 已重建。
- Full local gates：Python `1487 passed`、Rust `367 passed`、Vitest `644 passed`、
  vue-tsc 通过，输出 `LOCAL GATES: ALL GREEN`。

## b2 最终复核补充（2026-10-27）

先前 UI PASS 绑定上文 f7f313 镜像，保留历史证据，不用新镜像冒充已点击。最终镜像为 `sha256:3ad54ca40373bdb1f2a91d4e4c1f3d1131fdfeb7f5bf5f6c8ef5a797003eb3d2`，adapter SHA256 为 `657ddecc1881a6be5ce986199647f91766d8472fd7876760263505f058db8174`；冻结 sidecar 真实容器实测两类市场搜索、无已安装插件的更新检查立即返回 unsupported（避免不必要 marketplace 超时）。runtime `4dddf0a3-d4b7-47ac-b5f7-01f0fd448b2a` 已清理。

本次门禁：Python 1498 passed / 57 skipped / 140 subtests，Rust 368 passed / 1 ignored，最终前端 Vitest 657 passed，vue-tsc 和 debug 构建通过；vendor 1532 checksums 通过。审查后补充上下文状态恢复、独立资产字典与单项徽标失效测试，均先 RED 后 GREEN。最终补丁 UI NOT RUN：当前可调用工具只有 shell、文件与子代理等，未暴露 Computer Use 或可加载它的工具发现入口。暂不请求逐批用户手测，继续后续批次；全局 settings.json 已从 b2-backup 恢复。

## b3 预测试阻塞（2026-10-27）

- Workbench/sidecar：本 worktree `workbench/src-tauri/target/debug/`；b3 仅前端/store 变更，沿用 b2 冻结 CLI 与镜像标识，不宣称新镜像。debug Workbench 构建成功。
- 计划操作：扩展→组安装部分失败→操作日志→失败项单独重试→复制诊断；理想为成功项保留、仅失败项重试、复制内容脱敏。
- 实际 UI：NOT RUN。当前 agent 未暴露 Computer Use / JavaScript 工具；Docker Desktop 启动后 docker info/ps 不响应（8 秒定时探测超时），正常关闭请求也超时，已停止此次启动进程恢复原先无引擎状态。无法创建本批真实 runtime。
- 自动化：TDD 复现并验证三类操作恢复、部分卸载继续、中文结构化超时归为未知、上下文切换、100 条 FIFO、8 KiB 诊断、完整引号凭据脱敏、repo 大小写对齐；UI 测试覆盖日志/复制/重试与双语。具体最终门禁计数见批计划。
- 结论：受阻项明确保留，不用单测冒充 UI PASS，不请求逐批用户手测，继续 b4。

## b4 预测试阻塞（2026-10-27）

- 测试产物：本 worktree debug Workbench（b4 前端），沿用 b2 CLI/镜像；不声明已创建本批 runtime。
- 计划操作：扩展→三类推荐→搜索→真实结果详情/安装，离线查看精选；理想为三类始终可见、理由/来源可读、搜索框及资产类型匹配、安装沿用既有恢复管线。
- 实际 UI/容器：NOT RUN。当前 agent 没有 Computer Use 工具，Docker 启动阻塞已记 b3；无法创建 ready runtime。不是产品通过结论。
- 自动化：推荐模型/面板与发现 store 测试，latest-query-wins、清空搜索、工作区切换、插件列表独立错误/请求代次；最终门禁见批计划。MCP `upstash/context7-mcp` 经 Smithery 查询确认，Plugin identity 来自已打包官方 marketplace；推荐安装必须以实际市场结果为准。

## b5 预测试与数据面（2026-10-27）

- 基线：`b809842` 后 b5 分支；Workbench/sidecar 均为本 worktree `workbench/src-tauri/target/debug/` 构建。CLI `0.1.10.dev0`，实际 bundle 为 `workbench/src-tauri/nsis/bundle/aisc-bundle`。本批不改镜像。
- 冻结 CLI：设置 `AISC_ROOT` 为该 bundle 后执行 `aisc.exe doctor --format json`；`cli-bundle-pairing` 为 pass，cliPath/cliEntrypoint 为实际 debug aisc.exe，bundleVersion/cliVersion 均 `0.1.10.dev0`，manifestSchema=1，compatibleCliVersions 包含运行版本，reason=`manifest-allows-running-cli`。bundle stage/verify 均 PASSED。
- 真实 HTTP 自动化：loopback direct=403、mirror=200 保留两个按序观测；direct 超时、mirror=503 三轮共六条。`headers-received` 只确认响应头，不声称完整下载或安装成功；body 失败在更新页显示。缓存快照不联网、不刷新 checkedAt，容器链为 unknown/not-probed。
- UI 操作：设置→检查→下载→ready→退出更新→取消→再确认；核对 Explorer 选中包、正常 NSIS 界面、Workbench 退出；缺失包/UAC 拒绝须保持应用；诊断复制与切工作区复核。理想/异常判据见 HANDTEST b5。
- **NOT RUN — b5 Explorer/NSIS/退出顺序 UI：当前工具未提供 Computer Use，也无工具发现入口可加载；未实际点击真实安装器，不以 OS 注入测试冒充实机 PASS。** Docker 现已恢复，可继续后续数据面；无需逐批用户手测。
- 最终自动化及构建计数见 b5 执行记录；ready/取消/失败保留、确认身份变化、requestId 和迟到响应均有回归。

## b6 预测试与真实安装数据面（2026-10-27）

- 基线：PR #44 / develop `3c05c59` 后的 b6 分支；Workbench debug 和前端生产构建已更新；CLI 仍是 b5 `0.1.10.dev0`，本批无 CLI/容器实现变更，不宣称重建镜像。
- 使用现有 `super-claude:latest @ sha256:3ad54ca40373bdb1f2a91d4e4c1f3d1131fdfeb7f5bf5f6c8ef5a797003eb3d2`，docker run --rm 隔离 `/tmp` HOME/config/bundle，调用真实 cc-switch 与安装 helper。无宿主用户配置写入。
- **PASS**：首次安装 13 个 caveman 与 grill-me，所有 DB 行 1/1 且双端 SKILL.md 存在；官方 CLI 关闭为 1/0、0/1、0/0 后重启及 bundle revision 升级均逐字段保留，目标路径一致；marker 存在但缺行时仅补缺行 1/1；官方卸载 caveman-stats 后重装为 1/1、双端文件恢复。
- 全门禁：Python 1540 passed / 53 skipped / 181 subtests，Rust 398 passed / 1 ignored，Vitest 770 passed，vue-tsc 通过；targeted Python 143 passed / 1 skipped / 85 subtests；文档检查 39 passed / 0 warnings / 0 failures。规范化写回、显式清缓存与 A→B→A 的旧响应/finally 均有回归。
- **NOT RUN — Services 分组、注册服务打开/复制、caveman 开关 UI：当前工具未提供 Computer Use，也无工具发现入口。** 未点击真实窗口，不把 Docker 数据面或 Vitest 当作 UI PASS。用户步骤见 HANDTEST b6，继续 b7 后统一复核。

## b7 预测试与最终产物（2026-10-27）

- 新镜像 `super-claude:2.1.17-b7 @ sha256:25f42e5157fd74eb7c2ae9add4d2857c6f83a46a59857b9a2b5730011a693f44`；本批冻结 CLI/bundle 0.1.10.dev0。镜像无缓存构建成功，软件实际版本与 dependency-evidence.md 全部一致。
- 本地门禁最终：Python 1650 passed / 53 skipped / 181 subtests；Rust 398 passed / 1 ignored；Vitest 770 passed；vue-tsc 通过，LOCAL GATES: ALL GREEN。文档检查 39/0/0，vendor 1533 checksums 通过；sidecar smoke、bundle stage/verify 通过。
- sidecar SHA256 `59a7ef15d76104915577387385832678c74de654bdd39ba54abe3cbfd7b3fb61`，12,974,618 字节；实际 doctor 的 host.checks[name=cli-bundle-pairing] 为 pass，manifest-allows-running-cli，实际 debug CLI 与本批 bundle 路径均在 worktree 内。
- **PASS — 新镜像 caveman 数据面**：复跑 b6 五路径，全部满足 13 子技能默认双开、已有 off 保留、缺行/重装恢复双开；旧 DB schema 升级风险见依赖证据，未触碰用户真实配置。
- **PASS — Services 真实运行态**：用本批冻结 CLI 创建 temporary/direct 隔离 runtime `465ab5f3-5766-433e-8152-d5a31c0a4dee`，注册 5173 后注册有名 3000；返回 services 端口 3000→5173、名称 docs preview/空，gateway.state=ready。通过宿主 loopback 与 Host 路由实际请求两端口，均返回测试文件。容器已停止移除；证据目录 `C:\pt\aisc-217-b7-services-6c646f1a`。首轮夹具文本换行与预期不同，改用固定 LF 字节重跑通过，不是产品失败。
- 三轮扩展实际数据面运行中，结果在完成后追加。
- **NOT RUN — b7 全批 UI/显式更新实机点击**：当前工具未暴露 Computer Use 或发现入口。计划的三类推荐、日志复制/重试、Services 分组及 Explorer/NSIS/退出顺序需按 HANDTEST 一次统一用户复核；不以容器或注入测试冒充 UI PASS。
