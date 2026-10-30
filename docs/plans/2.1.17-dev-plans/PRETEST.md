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
- 实测完成后，本机 `super-claude:latest` 已指向同一 b7 image ID，供统一手测默认使用；旧 `3ad54ca4…` 保留为 `super-claude:2.1.17-pre-b7-rollback`。仅本地重打标签，未推送镜像。
- 本地门禁最终：Python 1650 passed / 53 skipped / 181 subtests；Rust 398 passed / 1 ignored；Vitest 770 passed；vue-tsc 通过，LOCAL GATES: ALL GREEN。文档检查 39/0/0，vendor 1533 checksums 通过；sidecar smoke、bundle stage/verify 通过。
- sidecar SHA256 `59a7ef15d76104915577387385832678c74de654bdd39ba54abe3cbfd7b3fb61`，12,974,618 字节；实际 doctor 的 host.checks[name=cli-bundle-pairing] 为 pass，manifest-allows-running-cli，实际 debug CLI 与本批 bundle 路径均在 worktree 内。
- **PASS — 新镜像 caveman 数据面**：复跑 b6 五路径，全部满足 13 子技能默认双开、已有 off 保留、缺行/重装恢复双开；旧 DB schema 升级风险见依赖证据，未触碰用户真实配置。
- **PASS — Services 真实运行态**：用本批冻结 CLI 创建 temporary/direct 隔离 runtime `465ab5f3-5766-433e-8152-d5a31c0a4dee`，注册 5173 后注册有名 3000；返回 services 端口 3000→5173、名称 docs preview/空，gateway.state=ready。通过宿主 loopback 与 Host 路由实际请求两端口，均返回测试文件。容器已停止移除；证据目录 `C:\pt\aisc-217-b7-services-6c646f1a`。首轮夹具文本换行与预期不同，改用固定 LF 字节重跑通过，不是产品失败。
- **PASS — 三轮扩展分类阶段 9/9**：每轮实际 Skills 搜索/双子技能安装/更新保留 off/卸载，MCP 远端元数据导入/更新检查/删除，Plugins 真实安装/更新/卸载全部通过；无超时。插件首轮实际从 6.0.3 更新到 7.0.0。Skills/MCP 返回 unsupported（无可比较版本），Plugins 返回 unsupported（marketplace metadata unavailable），未冒充“已最新”。MCP 未测握手/认证，插件搜索为工厂 marketplace 的新 CLI 查询，不证明在线目录刷新。
- **受控夹具修正后 PASS**：原主运行 exit 1 / 1815.739 秒保留，唯一失败为裸 `caveman-help` 经上游小写 repo 查找与工厂 repo 大小写冲突。完整 spec `JuliusBrussee/caveman:caveman-help` 独立实跑得到 1 成功/1 失败，仅重试无效项后成功项完整 SSOT 行不变；补充运行 exit 0 / 103.483 秒。未修复或宣称裸名称冲突消失；UI 市场使用完整身份。详细阶段表及覆盖边界见 [smoke-evidence.md](smoke-evidence.md)，原始两次结果均保留在 `C:\pt\aisc-217-b7-*-results-*`，不将合并证据写成单次 exit 0。
- **NOT RUN — b7 全批 UI/显式更新实机点击**：当前工具未暴露 Computer Use 或发现入口。计划的三类推荐、日志复制/重试、Services 分组及 Explorer/NSIS/退出顺序需按 HANDTEST 一次统一用户复核；不以容器或注入测试冒充 UI PASS。

### 本地安装与统一手测产物

- 实现提交 `cbb6e5a`，PR #46；该提交远端 Workbench CI `40510587355` frontend/Rust/CLI 均 SUCCESS。最终文档提交与合并提交另由 PR 记录核对。
- 正式版本本地构建和已验证 bundle 保存在 `release-staging/2.1.17-b7/`（Git 忽略，未发布）。源码 Workbench 版本 2.1.17，CLI/bundle 0.1.10.dev0。
- `AISC-Workbench-2.1.17-setup.exe`：371,123,902 字节，SHA256 `3a90496d0b6b132dd861e9d9714446099681e4c2274a8f31fbbe8caee39b6d88`。生产编译成功；首次 NSIS 遇 worktree MAX_PATH，用临时 `subst P:` 短路径重打包成功，映射已移除。第二次打包提示既有 bundle marker，未影响成功生成安装器；真实安装界面仍 NOT RUN。
- `AISC-Workbench-2.1.17.exe`：24,600,576 字节，SHA256 `5063fd8dfa68338b6108b95ebd063e2b7708431c98d52b8cfb79f7566c11e832`。
- `AISC-UpdateFlow-Test.exe`：24,600,576 字节，SHA256 `0df41817875fb13a64f7dfa248d8f7acaee15bd4a6fdcdf37aae43c8fb90963d`。同源码临时配置版本 0.0.0/独立 productName 和 identifier；用于现有正式 release 的真实下载与退出更新测试，不是发布产物。构建后 target/release/workbench.exe 为此测试副本，统一手测必须使用保存目录内有明确名称的 exe。
- `start-handtest.ps1` PowerShell 语法解析 PASS；常规/`-UpdateFlow` 分别绑定独立数据根和显式 CLI/bundle。未打开真实窗口，启动与关于版本显示仍由统一用户手测复核。启动命令见 HANDTEST；文件大小/hash 记录见同目录 artifacts.json。

### 统一用户手测入口

b1 关键 CU 路径有历史 PASS；b2 早期 CU PASS、最终补丁 NOT RUN；b3–b7 因当前 agent 无 CU，UI 均 NOT RUN。b7 新镜像已补真实扩展与服务数据面，不能追记成此前窗口点击通过。所有批次已有实际预测试结果或具体阻塞，可按 HANDTEST 发起一次统一手测；用户验收、preview 发布与阶段收尾仍未完成。

### 合并后跨平台出包检查与修正

- PR #46 最终 head `b69d075`，Workbench CI `40513932370` 三项 SUCCESS，合并 develop `1fd0219`。合并后 Workbench CI `40514460328` SUCCESS。
- sidecar `40514460514` 三平台均在 doctor parity 失败，编译成功；仅新报告的 cliPath/cliEntrypoint 按 pip/冻结入口不同。比较器现仅归一化此指定检查中的两个非空来源路径，保留路径缺失/空/无效类型、bundlePath、版本、schema、兼容列表、状态和原因。新增用例先 RED 后 GREEN；原三平台原始响应回放均通过，本机真实 pip/冻结 CLI 全 25 命令矩阵 PASS。
- 本机 parity 使用 `AISC_ROOT` 指向当前源码 checkout，pip 模块路径经确认位于该 worktree，冻结 CLI 使用保存的 b7 aisc.exe。PowerShell dev-env 的 PYTHONUTF8=1 只影响 pip，冻结 help 仍输出本机 ANSI；本次仅对 parity 进程设 PYTHONUTF8=0，使两轨及比较器同用宿主编码，未改生产编码或安装器。
- Bundle Linux/macOS `40514460311`：Linux 成功；macOS 只准备 arm64 导致已跟踪 x64 yazi 被完整族替换移除，vendor verify 正确失败。三个出包 workflow 改为显式准备双架构，wrapper/Python 实现都进入 push 触发路径；5 个 workflow 合同用例先 RED。没有降低或跳过 checksum 校验。
- 审查发现 NSIS pwsh 原生命令失败可能被后续 packaging 成功覆盖；staging 后新增立即退出守卫，独立 RED/GREEN 验证。
- 修正仅涉及验证脚本、测试与出包 workflow，产品源码和已备 Windows 本地产物字节不变。聚焦 parity/sidecar 34 PASS，parity/workflow/staging 初轮 89 PASS；完整 Python 1682 passed / 69 skipped / 181 subtests（新增退出守卫前），守卫及远端最终结果见下文。原失败 run 保留，不能用重跑覆盖历史结论。

### b7 最终集成结果

修正提交 `b0e7b734fde1d4f7dc4cc2ef313c46fbd9e1c14f`：聚焦 parity/workflow/staging 最终 **90 PASS**，文档检查 **39/0/0**，独立代码/CI 审查均 PASS。以下四个 workflow 均在该精确提交完成 SUCCESS：

| 检查 | Run ID | 实际结果 |
| --- | --- | --- |
| Workbench CI | 40518027973 | frontend/Rust/CLI 全 SUCCESS |
| CLI sidecar build | 40518028450 | Linux x64、Windows x64、macOS arm64 全 SUCCESS；parity/clean-room/SBOM 通过 |
| Bundle Linux/macOS | 40518035077 | deb/dmg 全 SUCCESS；双架构 staging 与 vendor/bundle 校验通过 |
| NSIS installer build | 40518044281 | NSIS 构建、安装/PATH/数据保留冒烟 SUCCESS；发布 job SKIPPED |

最终远端 CLI Python job：**1721 passed / 27 skipped / 185 subtests**（Linux，含平台专属用例）；日志已核对。该计数与本机 Windows 的平台跳过项不同，不能混记为同一次执行。

PR #47 合并 develop `1c43091566ced3050c1c186061839d07c5a59aa2`，PR #40–#47 覆盖的开发实现全部集成。管理 worktree 取该 develop 基线并补纯文档最终账本；未修改 `E:\Projects\AISC` 旧主 checkout。重复的合并触发构建不作为新的产品改动或新的 UI 证据。

已核对 `src/aisc`、Workbench 前后端、container/config/vendor 的 Git tree 与本地实际构建的 `cbb6e5a` 完全一致；CI 修正不改变已准备的 exe/安装包。统一用户手测按 HANDTEST 文首启动保存产物，b5 使用专用 0.0.0 副本。真实 UI 仍为 NOT RUN，用户验收与发布尚未发生。

## 全批 Computer Use 补测（2026-10-28，尚未完成）

本节追加最终集成产物的真实窗口观察；上文各批工具不可用结论保留为历史，不能视为本次已全量通过。源码基线 `cb19fb4`，使用保存的 `AISC-Workbench-2.1.17.exe` 与冻结 CLI/bundle 0.1.10.dev0、b7 镜像 `25f42e51…`，未修改旧主 checkout。测试工作区为 `C:\pt\aisc-217-cu-20261027\workspace-a`，容器 `3e8098c18e20 / aisc-wb-aef55f54`；其他已有容器未操作。

| 项目 | 真实操作与观察 | 本次结论 |
| --- | --- | --- |
| 前置 / b4 | 首页选择 A、只读预检通过、启动至“就绪”；扩展显示 caveman / Context7 / superpowers 三类卡片，中文理由、身份及来源可读 | 此路径 PASS；离线与英文分支待测 |
| H1 / b2 / b4 | 点击 caveman 推荐“搜索市场”，Skills 输入变为 caveman，结果 `juliusbrussee/caveman · 13 个技能`，显示“已刷新 / 上次成功：2026/10/28 00:13:50”；点击安装全部，截图见 `安装中 0/13` 和 spinner | 搜索及开始进度 PASS；安装终态、toast、13 子行状态未观察，H1 整体未完成 |
| H2 / H3 | 前轮宿主 WinHTTP direct、ProxyEnable=0，github / ghfast / gh-proxy 的 443 均可连接 | NOT RUN：不满足真实故障网络前置，未改系统网络伪造 |
| b6 Services | 仅在 A 容器启动 HTTP 3000/5173，先注册 5173，再注册 `3000 --name "docs preview"`；UI 先显示“宿主工具（F2）”、再显示“注册服务”，3000→5173、docs preview / 端口 5173、HTTP / 已注册、网关就绪 `:47001` | 分组、名称、顺序和状态 PASS |
| b6 服务读取恢复 | 组安装执行期间首次服务读取显示 `AISC CLI 响应超时`，随后自动恢复正确列表；当时容器仍有 skill-install-group 与官方安装子进程 | 保留瞬时超时证据；因果尚未证实，不能称已修复 |
| b6 复制 / 打开 | 点击复制尚未完成本地编辑器粘贴验证；点击打开后窗口清单出现 Chrome `Directory listing for /`，绑定浏览器时被工具终止 | 复制内容与网页正文 NOT RUN；仅窗口标题不作 HTTP 内容 PASS |
| b7 版本 | 设置→关于与更新→检查后显示 GUI 2.1.17、内置 CLI 0.1.10.dev0，远端 GUI 2.1.16 / CLI 0.1.9；仅通过 shell 核对 A 容器的 Node 24.22.1、Codex 0.164.0、Claude 2.1.311、cc-switch 5.11.3、Mihomo 1.19.33、yazi 26.9.1 | 关于页版本 PASS；容器版本是数据面证据，不冒充终端 UI |

前轮 Computer Use 原始停止原因：`could not determine the current browser URL on Windows with enough confidence to enforce policy`。收到停止指令后终止本轮，没有重置工具绕过。

### 13:24 CST 恢复检查

用户要求重试后，Computer Use 已能枚举应用及浏览器（当前无 Chrome 窗口），正常测试副本重新启动，窗口 `2425736`，首页 AX 可读取最近工作区 A。点击 A 时返回 `GetCursorPos failed: 拒绝访问。 (0x80070005)`；重新枚举、绑定窗口后截图全黑，未再发送输入。可能涉及锁屏或远程会话断开，尚未确定具体原因；已请用户确认桌面解锁及会话连接。没有更改安全/隐私/远程桌面设置。

本次全批补测仍未完成：H1 终态/H4、b2 剩余市场与缓存、b3 日志/重试/复制、b4 其余推荐/隔离/英文、b5 专用副本的显式更新/诊断、b6 开关/重装/隔离、b7 三轮真实 UI 冒烟均待继续。不得用历史数据面或自动化结果补记 UI PASS；尚未发起最终用户验收或发布。

### 用户确认解锁后的重试

用户明确回复“已解锁，可以重试”。重新枚举并绑定同一测试窗口，AX 仍正常，截图仍全黑；点击最近工作区 A 再次返回 `GetCursorPos failed: 拒绝访问。 (0x80070005)`。随后执行一次 `cua_repl.js_reset`，在全新 JS 会话重新枚举、绑定并重试一次，仍为同一错误；停止继续发送输入。不能再把锁屏当作已确定原因，也不能声称工具已恢复。当前阻塞位于 Computer Use 的桌面输入访问，尚未到达 Workbench 控件事件；没有新增 UI PASS，没有更改安全设置或改用其他注入方式。

### 16:46 CST 输入通道诊断与 H1 数据面终态

- 同一会话内 `app.click`、`setValue`、`pressKey` 均在发送前失败：`GetCursorPos failed: 拒绝访问。 (0x80070005)`。只读诊断显示 Workbench 与 `codex-computer-use` 均在用户 `wangyu` 的 Active RDP session 2，helper 为 Medium 完整性；重建 JS 与 helper 进程后仍复现。该错误发生在输入层，未到达 Workbench 控件事件，不能记产品 FAIL。
- 上轮 UI 发起的 caveman 组安装最终在数据面完成：A 容器 `skills` 表 13 行 `aisc:caveman*` 全部 `enabled_claude=1 / enabled_codex=1`，且 `/root/.claude/skills` 与 `/root/.codex/skills` 各存在同名 13 个 `SKILL.md`（合计 26 个）。
- 因未能在真实窗口观察安装完成 toast、列表刷新与 13 个子行开关，H1 仍不能记 UI PASS；以上仅补充终态数据面证据。待用户在 AISC 窗口内完成一次物理点击以恢复交互桌面后，继续 CU 测试。

## 2026-10-29 全批 CU 补测最新账本

本节是当前权威状态；上文“输入通道阻塞 / 尚未完成”保留为历史过程。继续使用保存的最终产物、冻结 CLI/bundle 0.1.10.dev0 与隔离数据根。期间发现本机镜像漂移：`super-claude:latest` 曾被 Node 22 镜像 `628502412e88` 覆盖且 b7 标签丢失。已把覆盖镜像保留为 `super-claude:cu-overwrite-628502`，按 b7 bundle `--no-cache` 重建并重指 `super-claude:2.1.17-b7` 与 `latest`，新 ID `sha256:610cd7ebfa39e4ef9a9273041d9c123c8fc304cc21195eeb5463ddee77f82053`。该 ID 与原 `25f42e51…` 不同；镜像内 Node 24.22.1、Codex 0.164.0、Claude 2.1.311、cc-switch 5.11.3、Mihomo 1.19.33、yazi 26.9.1 已逐项实测。保存的 Workbench/CLI 字节不变。

| 批次 | 真实 UI / 容器内核对 | 当前结论 |
| --- | --- | --- |
| H1 | caveman 市场搜索返回 13 项并显示刷新时间；UI 点击“安装全部”出现 `安装中 0/13`；随后真实列表刷新为 `JuliusBrussee/caveman · 13 个技能`，容器 SSOT 与 Claude/Codex 双端文件均为 13 项且默认双开 | 进度与终态 PASS；完成 toast 未捕获，H1 不能记完整 PASS |
| H4 | UI 将 `caveman`、`caveman-commit` Codex 显式关闭并多次重启；真实 UI 点击组“更新全部”显示 `更新中 0/13`，完成后按钮恢复；原路径 SQLite/WAL 终态两项仍 1/0，其余 11 项 1/1 | PASS |
| b2 | Skills `caveman`、MCP `pdf`、Plugins `superpowers` 均真实搜索成功；Plugin 详情显示中文简介、安装量、仓库与“市场原文”；关于页版本分开比较 | 搜索/详情 PASS；断网缓存、清空与工作区隔离 NOT RUN |
| b3 | 不存在插件安装超时后展开操作日志，显示 identity、动作、第 1 次尝试、起止时间、`AISC CLI 响应超时`；未显示盲目重试按钮；“复制诊断”剪贴板 JSON 含身份/动作/时间/错误 | 超时未知与防盲目重试、复制诊断 PASS；第 2 次可重试失败 NOT RUN |
| b4 | 三类推荐中文与英文界面均显示完整理由、身份、来源与 `Search market`；推荐搜索路由到对应资产页 | PASS；未启动 runtime 的禁用按钮 NOT RUN |
| b5 | 0.0.0 关于页正确；下载 279.5MB 并校验通过；退出更新取消后应用保持运行；重命名包确认后显示 `staged setup not found` 并保持运行；最终确认后 Workbench 退出、Explorer 打开目录并选中 1 个 279MB `workbench-setup-2.1.16.exe`，NSIS 显示欢迎界面，进程命令行无 `/S`，随后在欢迎页取消且未安装 | 显式更新主路径 PASS；诊断竞态 NOT RUN；诊断健康报告在常规副本复制 PASS |
| b5 诊断 | 真实诊断显示 0 fail / 1 warning / 1 skip / 15 pass；CLI/bundle pairing pass 且实际路径/版本/manifest reason 完整；更新网络“尚未探测”、容器扩展网络未探测；“复制健康报告”剪贴板 JSON 完整 | PASS；请求竞态与重开覆盖 NOT RUN |
| b6 Services | 中文/英文均显示 `宿主工具（F2）` 与 `Registered services`；3000→5173、docs preview、HTTP、Registered、Gateway ready；复制按钮剪贴板为 `http://p3000.localhost:47001/`，打开出现 `Directory listing for /`，curl 直连返回 HTML | PASS |
| b6 caveman | 13 默认双开；显式 off 多次重启保留；UI 子项卸载使列表减少并记录成功日志，`caveman-stats` 重装后列表回到 13 且 stats/setup 均 1/1，既有 off 未被覆盖 | PASS；A→B→A 服务隔离 NOT RUN |
| b7 | 关于页 GUI 2.1.17 / CLI 0.1.10.dev0；重建镜像六项工具版本逐项匹配；H4 组更新真实 UI PASS | 版本与关键更新 PASS；三轮完整 UI 冒烟 NOT RUN |

### 真实边界与测试工具干扰

- 早期从宿主直接打开挂载中的 `cc-switch.db` 后，容器内下一次写入可能报 `unable to open database file`；重启容器内 cc-switch daemon 后恢复。该行为由测试工具干扰 Docker Desktop 文件共享/WAL 引起，未作为产品 FAIL，后续核对均改在容器内原路径或官方 CLI 执行。
- 只复制 SQLite 主文件会漏掉 WAL 最新状态，曾误判更新覆盖 off。以原路径 `mode=rw` 只读查询或 `cc-switch skills info` 为准。
- Chrome 绑定曾因工具无法确定 URL 被强制停止；后续仅用窗口标题和 curl 验证打开结果，不再绑定该 Chrome 窗口。
- b6 UI 卸载坐标实际移除了 `caveman-stats` 与相邻 `caveman-setup`，两个测试项均已被重装并恢复默认双开；操作日志保留两次卸载与 stats 添加成功记录。

### 仍需用户统一手测或后续 CU 补测

H2/H3 真实故障网络、b2 缓存回退/清空/隔离竞态、b3 第二次可重试失败、b4 未启动禁用态、b5 诊断请求竞态、b6 A→B→A、b7 三轮完整 UI 冒烟。不要把上表局部 PASS 记为全批 PASS；发布和阶段收尾仍未发生。

## 2026-10-29 R1 CU 修复复测

使用 R1 专用 Workbench `release-staging/2.1.17-r1/AISC-Workbench-2.1.17-R1.exe`（SHA256 `046fea420ff1756684bbfe7f8bbbabaa29aba4f1004ff25ced78da68731f7ea3`），显式复用 b7 CLI/bundle `0.1.10.dev0` 与镜像 `610cd7ebfa39…`。隔离项目为 `C:\pt\aisc-217-r1-cu-project`，隔离数据根为 `C:\pt\aisc-217-r1-cu-data`；未覆盖 b7 保存产物。

真实 UI 从市场结果发起 13 项 caveman 组安装，出现 `安装中 0/13`。宿主进程观测到 pinned CLI direct 执行 `extensions skill-install-group`（父子同 argv 为 bootstrap 形态，不是重复操作）。安装期间通过命令面板真实切入 Services：`宿主工具（F2）` 与 `注册服务` 立即可见，网关 `:47000`、`docs preview :3000`、端口 `5173`、HTTP/已注册均正确；未出现 `AISC CLI 响应超时`。同一时段 CLI 日志中 runtime services 约每 5 秒成功返回，单次 250–297ms。

组安装 exit 0，耗时 131297ms；容器内官方 CLI 逐项核对 13 个 caveman 子技能，Claude/Codex 均默认开启。完成后 Services 仍显示两分组与两服务。默认宽度下市场组安装按钮被裁剪，CU 临时把 UI 字号缩放调为 0.8 以完成点击，复测后已恢复 1.0；该测试适配不判产品 FAIL。

**结论：R1 Local 核心场景 PASS。** 审查后补齐 target-aware 路由与 Remote direct `AISC_RUN_ID` 前缀回归，最终生产副本 SHA256 `c74d1d1d0572f745fed0f5c089903e24953616643be07730c670ec9452885546`。Remote direct 真实 SSH UI 仍为 NOT RUN；本结果不替代用户统一手测，也不改变 H2/H3 等既有 NOT RUN 边界。PR #48 已合并 develop，Workbench CI / Bundle / NSIS 最终全绿；Bundle macOS 首次 job 因上游 npm registry HTTP 403 rate limit 失败，单独重跑后通过。


## 2026-10-29 R2 扩展 UI 重设计预测试

使用 R2 Workbench `AISC-Workbench-2.1.17-R2-CU.exe`、当前源码冻结 CLI
`aisc-r2-cli.exe`（SHA256 `84df81eaf89e42d3041b6a33bca6d3d1d858e387fd46c04fddd682507c120079`）、
b7 bundle 与派生 CU 镜像 `super-claude:2.1.17-r2-cu @ c0472956…`。该镜像仅在 b7 镜像上替换当前
`aisc-extensions-adapter`，用于验证新增数据面 op；未做 R2 从头全镜像构建；远端 sidecar/bundle/NSIS CI 只验证出包，不构建 Docker 镜像。

| 项目 | 真实 UI 观察 | 结论 |
| --- | --- | --- |
| 主视图布局 | 已安装技能分组可见；顶部为 技能/MCP/插件、检查更新、扩展市场；无精选推荐块、无操作日志、无市场表单 | PASS |
| 分类推荐 | 扩展市场弹窗显示 科学研究/教育学习/知识文档/数据可视化/写作表达/开发工程；科研与教育均显示 10 条；热度来源显示 `skills.sh 热榜` / `Smithery 热榜` / `官方目录` 且不重复 | PASS |
| 推荐详情 | 教育类 Microsoft Learn 打开详情，先显示中文简介，再显示类型/来源/安装量，动作未触发前不修改搜索 | PASS |
| 搜索结果 | Microsoft Learn 推荐搜索加载真实 Smithery 结果并显示已刷新/时间；单击 Hugging Face 后详情标题与中文 fallback 更新 | PASS |
| 技能组安装 | 市场搜索结果保留仓库分组和“安装全部”；组件测试断言调用 `installSkillGroup(group)` 并传全部子项 | UI 结构 PASS；真实组安装复用 R1 已验证链路 |
| 来源管理 | 技能仓库列出 4 条 branch/enabled；插件市场列出 built-in 与 official；MCP 说明 Smithery 内置且已安装 MCP 从列表维护 | PASS |
| 删除保护 | 技能仓库删除先出现确认，明示“不会卸载已安装技能”；取消后仓库保留 | PASS；实际 add→delete 留给统一手测 |
| CU 发现并修复 | 无热度标签重复、`market-mcp` fallback 误称技能、来源页残留详情、市场技能组缺“安装全部”；均已补测试并重建复测 | PASS |

自动化：Vitest **95 files / 802 tests**、Python `pytest tests` **1691 passed / 69 skipped / 186 subtests**、
Rust **404 passed / 1 ignored**、`npm run build` 与 Tauri release no-bundle 均通过。
独立审查修复后另完成最终回归：vendor verify **1533/1533**、文档检查、`git diff --check`
与上述产品门禁全部通过；稳定 unsupported-op 分类、搜索失败 alert、目录/市场证据切换、
native 技能组标题、跨来源忙碌态与旧 SQLite schema 均有对应测试。此段是自动化证据，不冒充 UI PASS。

2026-10-30 复审修复 CU：使用 direct release
`AISC-Workbench-2.1.17-R2-REVIEW.exe`（SHA256 `5e4a79…93f`）与冻结 CLI
`review-dist-2/aisc.exe`（SHA256 `52ee1f…d93`）启动隔离项目。真实 UI PASS：native
caveman 组头展开后子项详情不收起且中文简介/市场原文正确；教育类 10 条；Microsoft Learn
显示“推荐依据（目录英文摘要）”；真实 Smithery 搜索后单击 Hugging Face，详情切换为中文
fallback +“市场原文”+“安装”，不再继承推荐证据或“搜索市场”。测试后已移除一次性容器并恢复
`super-claude:latest @ 610cd7ebfa39`。Arrow 键/焦点恢复、旧 runtime unsupported 横幅、
实际来源 add→delete、<720px 与 NSIS 形态仍未 CU，不以自动化冒充。

第三轮审查后另完成行级 native identity/sibling 修复、Rust envelope source-op guard、
unsupported alert 去重与空态焦点恢复；最终 direct binary
`AISC-Workbench-2.1.17-R2-FINAL.exe` SHA256
`5d9ee44a020f219691920eb72e67682919a5b47efbdd0bd943ea723fd42572f9` 仅以 Vitest/Rust/build
验证，未再做 CU。Arrow 键、焦点恢复、旧 runtime unsupported 横幅、实际来源 add→delete、
<720px 与 NSIS 形态仍未 CU，不以自动化冒充。

## 2026-10-30 最终产物准备与当前 CU 环境边界

- 最终 GUI/CLI 沿用上段 SHA256；新 bundle `release-staging/2.1.17-r2/handtest-stage/aisc-bundle` 独立校验 PASS，adapter SHA256 为 `97464109c7aec00d1721fb06716b9ce513b61c5fe97e669637a60f969a7e2c5f`。
- 派生最终镜像 `super-claude:2.1.17-r2-final @ sha256:2f54fad6d86c15468f0cf968535fc377c7ff11e9362f94dcb5f29e2ee6121556`：b7 加最终 adapter，镜像内 hash 与源码一致、语法检查 PASS。没有进行 R2 从头全镜像构建。
- `start-handtest.ps1` 已准备并通过 PowerShell 语法检查，绑定冻结 CLI/current bundle；不复用用户 R1 数据根，也不覆盖 `super-claude:latest`。
- 当前可调用工具中缺少 `node_repl`；已读取 Computer Use 的 SKILL/guidance/confirmations，无法初始化要求的 `@oai/sky`。本轮没有新增真实 UI 操作；实际来源 add→delete、<720px、键盘/焦点与旧 runtime 横幅保持 **NOT RUN（工具不可用）**。
- HANDTEST 已同步 R2 UI：搜索与推荐进入独立扩展市场、错误恢复使用最近失败区；历史日志/旧手动 identity 输入框不再是当前验收步骤。

### 最终来源数据面 smoke 与警告修复

- 冻结 CLI `52ee1f…d93`、final adapter `97464109…e2c5f`、派生镜像 `2f54fad6…`，一次性 runtime `1fc3fe95-05b4-4e2c-9134-65df1f336223`，项目 `C:\pt\aisc-217-r2-final-project`。使用 direct CLI，未启动 GUI。
- 技能仓库：初始 4 条；添加 `wshobson/agents` 后 5 条、branch main/enabled true；删除后恢复原 4 条，PASS。
- 插件市场：初始 2 条；本地 fixture `aisc-r2-handtest` 添加后 3 条，安装 `aisc-r2-demo@aisc-r2-handtest` 后插件列表 1 条；删除市场后来源回到 2 条、插件回到 0 条。官方 CLI 数据面 PASS，旧“不会自动卸载插件”确认文案判 FAIL。
- 修复：先改 R2 规格，再修改中英卸载警告；两语确认/取消与列表刷新 targeted 16/16、全前端 803 tests、vue-tsc/Vite/Tauri direct release PASS。独立增量审查 Critical=0/Important=0。未做新 GUI CU，警告视觉与来源按钮完整链路仍 NOT RUN。
- 修正后的 GUI：`AISC-Workbench-2.1.17-R2-ACCEPTANCE.exe`，SHA256 `9ae03cc2234f3ce9ea41c618c51c188f5271d9db2fda29c50e1321f6db1fbda5`。启动器及 artifacts.json 已指向此文件；旧 FINAL 只作历史证据。
- 数据 smoke runtime 已停止；用户 R1 容器 `4ac8ca6c9a97` 与 `latest @ 610cd7ebfa39` 保持原状。后续真实交叉市场补验：两个本地市场各安装一个测试插件，删除 aisc-r2-handtest 后插件数 2→1，保留 aisc-r2-other-plugin@aisc-r2-other 及其来源；PASS，证据 cross-market-smoke.jsonl。两个一次性容器均已停止/删除。

最终集成：PR #49 → develop `6133eef`；合入后的 Workbench `40927944987`、三平台 sidecar `40927944984`、Bundle `40927944792`、NSIS `40927944887` 最终全部 SUCCESS。Bundle macOS attempt 1 依赖 staging HTTP 403 限流，单独重跑后通过；不隐去首轮失败。本段为远端自动化证据，未改变 GUI NOT RUN 或用户验收状态。

## 2026-10-30 R3 扩展市场批次修复预测试

- 根因证据：R2 手测数据根 `C:\\pt\\aisc-217-r2-handtest-data` 的 history/log 显示实际运行时为 `super-claude:latest @ 610cd7ebfa39…`（b7 旧 adapter），不是 R2/R3 adapter 派生镜像。旧 adapter 以 argparse usage 退出，Python 原先把它归为普通 `AISC_ERR_EXTENSIONS_EXEC_FAILED`。
- TDD 与自动化：旧 argparse 分类、空态按钮、推荐内联展开均先失败后通过。审查修复源 `7482301` 全门禁 Python 1694/53/191 subtests、Rust 404/1 ignored、Vitest 95 files/808、vue-tsc 全绿；ARIA 收敛提交 `ed3ed71` 后 targeted 22/22、vue-tsc 与生产 Tauri build 通过，Python/Rust 源相对全门禁修订不变。
- 真实数据面：R3 冻结 CLI + 旧 b7 镜像，`skill-repos-list` exit 1 且错误码为 `AISC_ERR_EXTENSIONS_UNSUPPORTED_OP`，消息为“当前运行环境不支持扩展来源维护，请升级或重建运行时镜像”；R3 adapter 镜像同 op exit 0，返回 4 条技能仓库。两个一次性 runtime 均已停止，证据见 `release-staging/2.1.17-r3/*image*result*.json`。
- 产物：最终 GUI `AISC-Workbench-2.1.17-R3-FINAL.exe` SHA256 `73ec51edce9fcf699a3c2c7413763590232c2251d8f4474c65f5a9b284676942`；最终 CLI `aisc-r3-final.exe` SHA256 `1f6032257026537bfd7840965c1087f96c4028f8005fc3d9b5b82bf38552107f`。
- CU：已读取 Computer Use SKILL/guidance/confirmations，但当前会话无 `node_repl`，无法初始化要求的 `@oai/sky`。来源管理提示、空态视觉、推荐卡片内联展开/键盘/焦点、<720px 均为 **NOT RUN（工具不可用）**。独立审查初轮发现的 Close/焦点、native button 内容模型、测试覆盖与五 op 覆盖均已修复；ARIA 复审项亦已修复。最终审查 Critical=0/Important=0，PR #50 精确产品头 Workbench CI `40989333294` SUCCESS。最终 CLI 对旧 b7 镜像复测仍稳定返回 unsupported。本批等待用户按 HANDTEST R3 验收，不能进入下一批。
