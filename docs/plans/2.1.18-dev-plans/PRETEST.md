# 实测与证据账本

截至 2026-11-02，b1/b2 已实现；D-8 后 b2 已执行 Windows CU，发现子菜单遮挡误移并修复复测；b3–b6 未实施。独立的 2.1.17 个人功能整合验证不计入本表。

| 批次 | 定向/自动化 | 真实数据面 | 候选构建 | Windows CU | 用户验收 | 原因 |
| --- | --- | --- | --- | --- | --- | --- |
| b1 | Rust PASS：415 passed / 2 ignored；前端 840+1 复测通过 | PASS：Windows 普通 NTFS 文件/目录；其他环境 NOT RUN | PASS：debug Workbench；前端修正版 build PASS | 改名/刷新/重入/不覆盖 PASS；冲突提示初测 FAIL，修后复测 NOT RUN | 未本人复测；D-6/D-7 明确进入 b2 | PR #63 打开、不合并；未补远端 CI 结论 |
| b2 | PASS：最终定向 45 项；前端全套 852 项 | PASS：实际改名/移入目标及无误移核对 | PASS：vue-tsc/Vite | 初测误移 FAIL；修后已执行路径 PASS，覆盖边界见下 | NOT RUN | D-9：PR #64 打开，依赖 #63；无远端 CI PASS 结论 |
| b3 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施；U-1 |
| b4 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施；U-2 |
| b5 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施；U-3/U-4 |
| b6 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施；依赖 b5/U-3 |

本轮文档检查结果单独记 [PROGRESS](PROGRESS.md)，不填成上表功能 PASS。

## b1 / R-1 / H1 — 2026-11-02

- 实施分支：`codex/2.1.18-b1-case-rename`；起点 develop `1d26f237`，本地依赖 PR #62 的 `1926b5a1`。b1 产品改动记录于本分支提交，新增测试仅保留在工作树；尚无 b1 PR/远端 CI。
- 仅改 Rust `workspace.rs::rename_entry`；候选仍显示 Workbench 2.1.17 / CLI 0.1.10，是 2.1.18 b1 开发构建，不是 2.1.18 发布版。CLI/bundle 复用已验证的整合候选，前端由同内容的整合工作树 Vite 服务提供。
- 本机候选：b1 工作树 `workbench/src-tauri/target/debug/workbench.exe`；SHA256 `B3F728E6C0413C78BB24BB6EB9D3F9E525D3FBF26BE3640104A5B4CE5D871DB0`。
- RED：修复前，既有测试增加目录枚举断言后失败，实际 entries 为 `["Folder", "readme.md"]`，没有请求的 `README.md`。原始日志 `b1-red.log`。
- GREEN：`cargo test --lib`，415 passed / 0 failed / 2 ignored，日志 `b1-rust.log`。覆盖文件/目录大小写往返、实际名称及内容、完全相同名称、原有冲突/名称/路径保护。大小写敏感 siblings 测试在普通 NTFS 上条件返回，不能算执行了独立 Area/AREA 断言。
- 构建：`cargo build` PASS，日志 `b1-build.log`。本次未改前端或 CLI，不重新计入历史门禁结果。
- 范围外/未测：Linux、macOS、Windows 大小写敏感目录、真实 SSH 均 NOT RUN；本次没有两阶段暂名和恢复分支。
- 日志在本机工作树外 `.aisc-integration-work` 保存；新增测试及本机数据不上传。CU 操作与用户结论待下方补录，自动化结果不代替它们。

### Windows CU 实际记录

以下为首轮记录；后续补测已完成其中大部分，历史工具失败保留，不覆盖为 PASS。

- 工具 `@oai/sky`，截图可见窗口 2560×1392（系统缩放未独立测量）；目标为本机独立 `AISC-b1-QA-64b486cf`，含 Area.txt / Folder/child.txt / Occupied.txt，内容分别 qa-file / qa-child / keep-me。
- 实际路径：工作区选择填写 QA 路径 → 下一步 → 启动摘要五项通过 → 启动 → 就绪 → 文件侧栏右键 Area.txt → 重命名。已看到内联“重命名”编辑框和选中的 Area。
- 工具异常：主截图边界返回 15×15，相关截图为 2560×1392；索引点击没有可靠命中，改用相关截图坐标后可进入菜单。编辑框 set_value 随后报 `事件无法调用任何订户 (0x80040201)`；刷新树后编辑框消失，仍显示 Area.txt。停止自动输入，避免误落到相邻终端。
- 结论：启动/文件树/菜单可观察，**完整 H1 NOT RUN**，没有成功执行 GUI 改名、刷新/重入及 GUI 冲突测试。此为 CU 工具未完成，不记成产品 PASS 或用户验收。客户端保留 QA 工作区供用户操作。
- 用户验收 NOT RUN；下一批未获裁定。真实文件系统测试与此记录分别记账。

### 用户委托补测（2026-11-02）

- 用户要求“你直接帮我测试之后告诉我结果”。恢复普通窗口至 803×631，用实际键盘输入替代 UIA set_value，解决首轮输入失败；仍使用同一 Rust 候选。
- 文件：右键 Area.txt → 重命名 → 输入 AREA → Enter，树与成功提示均为 `AREA.txt`，磁盘精确枚举 PASS，内容 `qa-file` 保留。
- 目录：右键 Folder → 重命名 → FOLDER → Enter，成功提示“已重命名：FOLDER”；磁盘名称精确，子文件内容 `qa-child` 保留，PASS。
- 刷新文件树后，关闭 QA 工作区、结束本次临时运行环境，从最近工作区重入并启动；树仍包含 `FOLDER`、`AREA.txt`、`Occupied.txt`，PASS。
- 重名：将 AREA.txt 改成 Occupied.txt 并提交。操作被拒绝，磁盘仍精确只有三个条目，文件内容为 `qa-file` / `qa-child` / `keep-me`，不覆盖 PASS；但 UI alert 没有可见文案，提示验收 FAIL。
- 根因与修复：重命名行未建立定位上下文，`.name-error` 绝对定位提示不在可见行下。b1 内补规格后，在 `WorkspaceExplorer.vue` 仅对正在重命名的行复用 `name-input-row`；现有冲突断言通过，vue-tsc/Vite build PASS。
- 用户随后取消界面自动操作，立即停止全部 CU 输入；**修正版错误提示可见性复测 NOT RUN**。没有重启客户端或切换其 Vite 服务，因此当前已打开窗口仍是修正前前端，不将构建通过写成界面通过。
- 前端首轮 840 passed / 1 failed：唯一失败为快照测试找不到 python3（ENOENT），不是断言失败；配置本地现有 venv 后该 1 项单独复测 PASS，合计覆盖 841 项，不声称一次全量全绿。日志 `b1-frontend-test.log`、`b1-frontend-build.log`、`b1-frontend-retry.log`。
- 本轮没有新增 GUI 测试文件；实际窗口树、截图、只读磁盘断言留在会话工具记录。用户委托执行不伪装为用户本人验收，b2 未启动。

## b2 / R-2 / H2 — 2026-11-02

- 分支 `codex/2.1.18-b2-work-record-menu`，develop 起点 `1d26f237`，本地快进至依赖 `cb528cad`。远端 PR #62/#63 均保留，不合并；b2 仅本地提交，无 PR/远端 CI。
- 仅改前端 `WorkRecordsView.vue` 与计划；新行为回归留在本地测试文件，不上传。Rust/CLI/容器未改，不把旧门禁重复写为本批 PASS。
- RED：四角边界、子菜单左展/焦点、visual viewport 短屏、外部滚动等 7 项回归在原实现全部失败，日志 `b2-red.log`。
- GREEN：最终该组件 44 项 PASS（含新增 10 项本地测试）；还覆盖显示后才聚焦、键盘导航/重开、点击外部关闭、旧异步 move 不关闭新菜单以及监听器卸载。日志 `b2-targeted-final.log`。
- 最终完整前端 98 文件 / 851 项 / 0 failed，日志 `b2-final-gates.log`；vue-tsc/Vite build PASS，日志 `b2-build-final.log`。构建原有大 chunk 提示保留，不作为测试失败。
- 前端产物 `workbench/dist`，主资源 `index-GdwSeNbZ.js` / `index-Dow_fdWT.css`；组件 SHA256 `FA2162877E3B0328750BB287121AB944D6AF05C06440322EDFC7FA6B245516D2`。尚未发布、安装或切换运行中的客户端。
- 验证边界：测试为 jsdom 中模拟 rect/viewport 的行为验证；真实 Windows 缩放、滚动、视觉遮挡及实际点击仍 **NOT RUN**。用户停止 CU 后没有任何桌面输入，也未用测试替代用户验收。
- 后续按 H2 恢复实机验证须由用户允许；b3 未启动，U-1 仍未裁定。

### D-8 Windows CU 与修复复测（2026-11-02）

- 基线 `18195640`，仍为本地 b2 分支；复用 b1 Rust 客户端（本批没有 Rust/CLI 变化），将 localhost:9000 的前端服务从整合工作树切到 b2。HTTP 返回组件已核对包含 b2 定位实现；重新进入隔离 QA 工作区启动，非旧前端验收。
- 工具 `@oai/sky`，Windows 本机；截图窗口尺寸依次包含 803×631、533×631、533×334、331×334、331×184，最后恢复最大化 2560×1392。应用随窗口自动缩放；系统 DPI/缩放百分比未独立测量，未改变系统设置。
- 数据：仅准备 30 条中性 QA provider JSONL 会话和 24 个 QA 工作记录，末目标带长名称。测试脚本、基线 JSON、日志和新增测试留本机，不上传；未输入模型/终端指令。
- 初测 PASS：列表底部右键主菜单向上避让；24 项子菜单可内部滚动，End 到末项；方向键/Home/End 导航，右方向键展开、左方向键返回、Escape 返回原会话，Shift+F10 从该行重新打开。焦点以截图的焦点框及后续键盘行为验证，UIA 的 focused_element 只报告 Web 根节点，不能单凭它判断丢焦点。
- 改名 PASS：菜单将 QA Session 01 改为带 Renamed 后缀；实际 CLI 列表与 30 条基线逐项比较，只有这条标题变化，其余 29 条保持。
- **真实 FAIL 保留**：533×334 下长子菜单两侧均放不下，原算法直接 clamp，覆盖“移入工作记录”触发按钮。鼠标移动到按钮后展开，随后的 click 命中了下面的第 09 个目标；实际账本确认 QA Session 02 被意外移入 Collection 09。
- 修复：优先选择能完整容纳的右/左侧；两侧都不足时选剩余空间较大的一侧，将子菜单 min/max-width 限制到该侧并换行，重新测量后定位，避免覆盖触发按钮。补本地回归，修前 expected left >= 260 / actual 8 为 RED（`b2-overlap-red.log`），修后 45 项 PASS（`b2-overlap-green.log`）。
- 修后 CU PASS：相同 533×334 鼠标点击展开仅打开子菜单，账本未新增移动；End 可滚到长名称末项，文字完整换行且没有窗外裁切。实际点击最后目标只把 QA Session 03 移到 Collection 24，CLI 核对精确目标/会话。
- 修后 CU PASS：331×334 的右下方触发主菜单向左向上避让，子菜单缩窄换行且不覆盖触发按钮；331×184 下主菜单自身出现内部滚动，滚到“移入工作记录”后仍能展开独立子菜单。侧栏外部滚动关闭菜单；通过系统窗口尺寸调整改变视口时关闭菜单；Escape 可关闭并返回原行。
- 最终门禁：首轮完整前端 851 PASS / 1 环境失败，原因是沙箱不能启动已有 Python 解释器；允许读取解释器后重新完整执行 **98 文件 / 852 PASS / 0 FAIL**（`b2-cu-final-tests-elevated.log`，原失败日志 `b2-cu-final-tests.log` 保留）。vue-tsc/Vite PASS（`b2-cu-final-build.log`），原有大 chunk 警告保留。
- 最终组件 SHA256 `8B8858DAED606EE8344ECB6D5410C407B98DC25349B18C85E1B271D295FC5045`；dist 主资源 `index-DmNEga2J.js` / `index-DLDRgy47.css`。修复已通过 Vite 热更新到实际测试窗口；不是安装包/发布版验收。
- 覆盖边界：本次实机覆盖本机 Windows、应用自动缩放与上述尺寸。修后子菜单向左展开的独立几何用例由定向回归覆盖，未单独重做 GUI 左展；其他系统 DPI、多显示器、macOS/Linux、Remote、模型恢复/分支实际运行、安装包均 NOT RUN。原 b1 提示复测不在本次完成项中。用户本人验收、b2 PR/远端 CI 仍未完成，b3 未启动；历史 FAIL/NOT RUN 不覆盖为 PASS。
- 截图与逐步操作在本次会话工具记录；本机日志保存在工作树外 `.aisc-integration-work`。QA 改名和有意移入结果保留供复查；误移记录通过“移出到未归档”还原，最终账本另作只读核对。

### D-9 PR 交接（2026-11-02）

用户随后授权提 PR，已创建 [#64](https://github.com/Wifabric/AISC/pull/64)，head `codex/2.1.18-b2-work-record-menu`，base `codex/2.1.18-b1-case-rename`；测试对应产品提交 `247fbf97`，之后仅追加 PR 交接文档。现有 Workbench CI 的 PR 目标过滤为 develop/main，此依赖 PR 不自动触发，不计远端 CI PASS。新增本地回归/数据/日志未上传。此前“未创建 PR”为当时历史状态；用户验收仍待定，#62/#63 未合并，b3 未启动。

## 每次实测记录模板（新增记录时复制）

- 批次/需求/手测编号：
- 时间/执行者/操作系统/窗口尺寸与缩放：
- 实施分支、起点与测试提交 SHA、PR/CI 链接（尚无则明确未创建）：
- Workbench/CLI/bundle 版本、候选路径/哈希、镜像 ID/tag、目标机器/工作区（分享时脱敏）：
- 前置状态与实际执行的命令/点击：
- 预期字段/状态与实际结果：
- 结论 PASS / FAIL / NOT RUN；失败原始输出或 NOT RUN 原因：
- 日志/截图位置；修复提交与复测范围：
- 用户本批结论原意、日期、未测放行/转期项、是否允许下一批：

同一项只测部分环境时拆行记，例如 Local PASS、Remote NOT RUN；不要给整批一个含混的 PASS。不得在证据里存 API keys、真实私人主题内容或未经允许分享的对话。

## PR #63 定向复审 — 2026-11-06

- 输入：head `5740e01597802c3c7e7b1576359e67e02aaebc3f`；#62 已合入，目标改为 develop `b03e913181b5f97cfeefaf8edf2749a4d06deec3`。本轮修复为包含本条记录的提交；CI 需按该提交重新核验，历史 PASS 不自动沿用。
- H1 补充失败：浏览器布局引擎复现底部行错误被 explorer-body 裁切，视口 bottom=140，提示 top=142 / bottom=163；原实现新增两项组件回归均 FAIL，既有 36 项 PASS。
- 修复：错误节点渲染并恢复输入焦点后，nearest 滚动显示提示；即时非法名称反馈复用该逻辑，不改变重命名协议及文件操作。
- 修后验证：组件与 store 合计 57 PASS（含本机新增 2 项）；顶部/中部/底部、220/300px 宽和 120/240px 高的 12 组浏览器布局检查均 PASS，提示在视口内且焦点保留。使用生产 CSS 和提示滚动函数的合成 DOM，非真实 Workbench CU。
- Windows 普通 NTFS：从精确 head 提取并逐函数核对的 11 个生产函数通过 10 项真实文件系统探针；覆盖大小写往返、精确目录枚举、内容保留、同名不变、文件/目录冲突不覆盖、硬链接别名、非法名及缺失来源。该探针不是全量 Tauri/Rust 测试；大小写敏感 Windows 目录和真实 SSH 未执行。
- 类型检查与 Vite 生产构建 PASS。首次共享依赖缺包、离线安装缓存缺包；在隔离目录按 package-lock 在线安装完整依赖后构建及 57 项前端复验通过。保留失败日志，不算产品缺陷；构建仍有体积提示。
- Remote：本轮仅静态核对，serve_fs.py 与 develop 相同，沿用 os.replace；本地不覆盖测试不能推导 Remote 具备同等保护。该既有差异需另行跟踪，本批未扩展远端协议。
- Windows CU：NOT RUN。自动操作运行时两次初始化均报“failed to write kernel assets / os error 3”，尚未操作本轮真实客户端。用户验收 NOT RUN；本轮没有修改安装版本或声称旧窗口正在运行本轮代码。
- 原始测试、布局页面与结果、代码快照、失败及成功日志只保留本机，不上传新增测试用例。远端 CI 等本提交生成后核验；本条不提前宣称 CI PASS。

## 2026-11-07 单人流程续接：b2 集成候选复核

- 用户本轮授权按开发流程自动推进，至需要本人确认的节点；沿用 D-6/D-8/D-9，不重复实施已有 b2，不将历史授权记为本轮用户验收。
- 实时远端核查：develop `9db6f642d717fdefb3487d75936bd76868ca7245`，PR #63 已合入；唯一 open PR 为 #64，head `36314112739a646edbc5b781302258d401641820`，base 仍为 b1 分支。该 base 后续包含 #66，不能将其所有内容当成 develop 已集成内容。
- 独立工作树从上述 develop 建立，合入 b2 head 无冲突；产品差异仅 WorkRecordsView.vue。主目录未提交修改保留。当前是本地集成候选，未推送/合并远端 PR、未改其 base。
- 本轮为单代理自查，不是独立评审。前端 98 文件 / 841 项 PASS，vue-tsc PASS，Vite 生产构建 PASS；不包含历史仅留本机的 11 项新测试，不复用历史 852 数量。Rust 414 PASS / 2 ignored；release custom-protocol 构建 PASS。
- Python 首轮 1694 PASS / 27 FAIL / 55 skipped / 201 subtests PASS。问题为测试固定 Git Bash 路径与本机实际 D:/Git 不一致、默认 CP1252 编码。仅在本地 verification 插件中适配实际 Bash/Node 路径；26 项复测 25 PASS、1 编码 FAIL；启用 PYTHONUTF8=1 后剩余编码用例及模型目录用例 2 PASS。首轮失败全部得到复验，不声称一次全量全绿。packaging 单独 190 PASS / 9 skipped。未修改产品、测试断言或系统环境。
- CU NOT RUN：computer-use @oai/sky 初始化报 trusted Node process exited unexpectedly；备用 cua 也报 windows sandbox failed / setup refresh had errors。未进行本轮真实 UI 点击，不能沿用 11/02 的 CU 结果为本轮 PASS。
- 候选：工作树 output/candidate/workbench.exe，嵌入本轮生产前端。配套 CLI/bundle 复用已验证 02ebe060 构建；与本轮候选 src/container/config/vendor/Rust tracked 内容无差异。版本仍 Workbench 2.1.17 / CLI 0.1.10，不是 2.1.18 发布版。
- 冻结 CLI version 与隔离 QA work-record list PASS：24 collections / 30 unfiled。QA 采用合成数据，独立 AISC_DATA_ROOT；启动脚本 output/启动-b2-验收.ps1。尚未启动本轮窗口，未替换安装版。
- 原始日志、候选 SHA256、环境适配脚本在 output/verification，仅留本机。远端 CI 本轮 NOT RUN；不得记待合入。
- 当前确认点：用户是否接手本轮 H2 实机验收（CU NOT RUN 保留）或先恢复 CU。b3 的 U-1 仍未裁定，不启动 b3。

## 2026-11-07 用户修复自动测试环境后的重试

- 用户要求再次自动测试。本轮 @oai/sky 初始化、list_apps/list_windows、窗口激活、UIA 文本、前台截图与点击均实际执行成功；旧的初始化阻塞已解除。窗口被遮挡时截图有捕获前台内容的现象，显式激活候选后截图恢复对应，UIA 倒计时文本有滞后，采用可见截图核对。
- 运行候选 output/candidate/workbench.exe（本地集成提交 b109f1e7），以独立 AISC_DATA_ROOT 使用合成 QA 数据。选择最近工作区，进入真实启动摘要，工作区/网络/运行时冲突检查通过。
- Docker 与镜像检查失败 AISC_ERR_DOCKER_UNAVAILABLE；Workbench 自动尝试启动 Docker，约 120 秒后显示 Docker 引擎启动超时。
- Docker Desktop 实际错误：starting services: initializing Ingest server ... sailor-ingest.sock ... The file cannot be accessed by the system。只读 docker info 也确认 dockerDesktopLinuxEngine 管道不存在。socket 条目存在，属性 Archive/ReparsePoint；没有删除 socket、重置 Docker、修改安全设置或上传诊断。
- 已取消候选启动等待，返回工作区选择页；候选及 Docker 错误窗口保留供检查。
- 结论：自动操作基础通道恢复；b2/H2 菜单功能仍 NOT RUN，因为 Docker 引擎启动失败，尚未进入工作记录页。本轮不是 b2 功能 FAIL 或 PASS，用户验收未完成，不进入 b3。
- 下一步：Docker 引擎恢复后继续原候选 H2；无需因本次环境失败重跑已通过的代码测试。

## 2026-11-08 b2/H2 真实 Windows CU 续测

用户启动平台后明确要求继续。确认运行程序为本工作树 output/candidate/workbench.exe（产品来源 b109f1e7），窗口为 workspace · Bash · AISC Workbench，独立 QA 路径与 AISC_DATA_ROOT 不变。Docker 已就绪，工作记录页实际载入 24 个 Collection、30 个合成 Codex 会话，以及启动环境新增的 1 条 init/Claude 会话。没有向终端或模型输入指令。

本轮已执行路径 PASS：
- 1165×797 普通窗口：列表底部右键 QA Session 25，主菜单向上避让；End 到移入项、Right 展开子菜单、Left 返回主菜单、Escape 归还原会话焦点、Shift+F10 重新打开。焦点按可见焦点框及后续行为核实，UIA focused_element 仅报告 Web 根不作单独依据。
- 551×331：底部主菜单可见，点击“移入工作记录”仅展开右侧子菜单，不覆盖触发按钮。冻结 CLI 在展开后检查：24 个 Collection 均无成员，unfiled=31，未发生误移。
- 长子菜单 End 可达第 24 项，标题完整换行；实际点击末项后只有 QA Session 25 移入 QA Collection 24。CLI 检查只有该 Collection 有 1 个对应成员，unfiled=30。
- 332×331：右侧位置触发的主菜单保持可见，子菜单实际选择左侧展开，限制宽度并换行，没有覆盖触发按钮；在菜单外滚动侧栏后菜单关闭。
- 332×186：主菜单出现内部滚动；End 可滚到移入末项，Right 仍可展开独立、可滚动的子菜单。最大化到 2560×1392 后菜单关闭。
- 最大化后对 QA Session 01 右键→重命名，选中原名后输入 QA Session 01 Renamed 并 Enter。界面与 CLI 均显示新名；逐项比较 31 条初始记录，只有这一条标题变化，只有 QA Session 25 改变归属，其余条目保持。data_check_pass=true。

工具边界：初次拖动未命中边框、一次截图缓存失效、一次越界拖动被拒，均重新观察后继续；最大化截图主区域为 15×15、相关区域为 2560×1392，使用真实相关截图坐标；最大化状态的索引右键未命中，刷新后改坐标完成。没有把这些工具尝试当成产品失败。最后保留最大化 QA 窗口及有意改名/移动数据供用户核验。

覆盖边界：本轮未单独补测 Home/上下方向键、主菜单右边缘翻转、其他系统 DPI、多显示器、跨平台/Remote、模型恢复/分支执行、安装包升级与旧异步动作竞态。历史证据保持原有范围，不冒充本轮实测。系统 DPI 百分比未测，尺寸来自实际截图。没有产品代码变更，不重复已通过的代码门禁。

本地数据证据：output/verification/cu-before-move-20261108.json、cu-after-move-20261108.json、cu-final-records-20261108.json、cu-data-check-20261108.json。截图与点击过程保留在本轮工具记录；合成数据和日志不上传。

结论：Docker 阻塞已解除，本轮上述 b2 界面预测试 PASS；用户批次验收仍待确认，远端 CI 本轮 NOT RUN，PR #64 未合并。按 §1.4 在此交付用户验收，不进入 b3。U-1 仍待后续裁定。


## 2026-11-08 新增批次规划状态

| 批次 | 自动化/真实数据面/候选/CU/用户验收 | 说明 |
| --- | --- | --- |
| b7 / F5 | NOT RUN | D-11 已排期，未实施；不能沿用其他插件安装记录 |
| b8 / F6 | NOT RUN | D-11 已排期，未实施；默认安装通过不代表首次认证配置闭环 |
| b9 / F7 | NOT RUN | D-11 已排期，未实施；其他查询成功不覆盖 grill/grill-me |
| b10 / F8 | NOT RUN | D-11 已排期，只有静态入口核查，未进行关闭行为实测 |
