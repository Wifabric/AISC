# 实测与证据账本

> 证据性质：本文保留相应候选的测试步骤与当时结果，不重写旧的 FAIL/NOT RUN。用户已确认整版与 Preview.13 通过，隔离安装已另行完成；当前提交/发布边界见 [发布准备](release-readiness.md)。

### S15 已集成：当前候选 Preview.12

真实 SSH 续测发现远程同名改名会覆盖目标，已修复并重建统一候选。[PR #97](https://github.com/Wifabric/AISC/pull/97) 已合入 develop `20df2af8e5afa1322ddb4dd4129f6144c3ce8b05`；最终 head `9f988fd7806d5dde850bab827f609330cd72779b` 的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/42460238475) 三项、[跨平台矩阵](https://github.com/Wifabric/AISC/actions/runs/42460237430) 九项均成功。Windows/Linux/macOS × Python 3.11/3.12/3.13 全部执行，修正测试环境后没有跳过失败项。单代理自查，不称独立评审。

当前二进制对应 `813225cffc50dcddbf21220910ffbd88ab840b75`；后续提交只改既有测试、CI 和计划，产品树不变。[NSIS CI](https://github.com/Wifabric/AISC/actions/runs/42459492494) 在该产品提交完成真实静默安装、重装、PATH 与卸载数据保留验证。完整本地 Python 1833 passed / 58 skipped / 218 subtests，Rust 422 passed / 2 ignored，前端 893 passed；新增 Linux 11 项回归仅留本地，文档门禁 51 PASS。

Preview.12 真实 GUI / SSH 已通过：同名冲突提示且两文件不变；文件/目录大小写改名；关闭、重入、刷新后精确名称和子文件保持；镜像仅替换选中旧 tag；远程重建入口明确禁用。专用 SSH/Docker 目标、导入镜像 tar 和临时私钥已清理，known_hosts 恢复原始哈希，原用户平台与容器保持运行。证据见 `output/verification/s15-merge.json`、`remote-qa/s15-final-data.json` 和 [preview-gui](preview-gui.md)。

剩余条件分别记录：隔离 Windows 交互安装 GUI 仍缺可用桌面环境，属于开发者阻塞，不能移交为用户代测；真实 GitHub/提供者本人认证及模型效果、最终用户验收、收尾与公开发布未执行。反馈仓库权限再次核实为只读，草稿已更新但未发送、未关闭 F1–F8。自然慢网/导出竞态没有自然复现，已有受控故障覆盖，不能称自然场景 PASS。当前没有未合并的本版产品 PR，也没有把 TODO 标为整版完成。

## 历史分批验证记录

以下保留各轮原始状态；当前汇总以上方及 PROGRESS 为准。

## 2026-11-08 S11 整合分支验证

镜像升级覆盖插件登记已复现并修正：Linux 实跑旧代码 6 failed / 5 passed，修后 11 passed；Windows 运行初始化/作用域/预装技能/cc-switch 关联 92 passed / 3 skipped / 41 subtests。完整资源包 1534 项校验通过，仅 entrypoint 一项 checksum 更新。冻结 CLI 构建完整修复镜像并启动受控旧版本 QA 目标，升级、重启及正常停止成功；14 个文件状态、两份其他工作区登记和模块定义均不变。GUI/新候选/精确 head 远端 CI 仍待，详情和验证入口修正见 [preview-gui](preview-gui.md#s11--已有工作区切换新镜像时登记被覆盖)。本轮不重复运行无关前端/Rust 测试，不把历史数字写为新源码全量门禁通过。

截至 2026-11-08，b1–b7 已合入 develop，b8 已实现并完成本地验证，b9–b10 待实施。下方按日期保留历史现场记录，当前状态以本表及最新批次记录为准。D-15 将后续 GUI / 手动验收统一留到 Preview；自动化和真实 Docker 不等于 GUI PASS。

| 批次 | 定向/自动化 | 真实数据面 | 候选构建 | Windows CU | 用户验收 | 原因 |
| --- | --- | --- | --- | --- | --- | --- |
| b1 | Rust PASS：415 passed / 2 ignored；前端 840+1 复测通过 | PASS：Windows 普通 NTFS 文件/目录；其他环境 NOT RUN | PASS：debug Workbench；前端修正版 build PASS | 改名/刷新/重入/不覆盖 PASS；冲突提示初测 FAIL，修后复测 NOT RUN | 未本人复测；D-6/D-7 明确进入 b2 | PR #63 打开、不合并；未补远端 CI 结论 |
| b2 | PASS：最终定向 45 项；前端全套 852 项 | PASS：实际改名/移入目标及无误移核对 | PASS：vue-tsc/Vite | 初测误移 FAIL；修后已执行路径 PASS，覆盖边界见下 | NOT RUN | D-9：PR #64 打开，依赖 #63；无远端 CI PASS 结论 |
| b3 | PASS：前端 846、Rust 414、Python 1734 及定向复验；PR #67 三项 CI PASS | PASS：真实 Docker 重命名/标签保留/冲突保护 | 前端构建 PASS；新版 GUI 候选待统一构建 | NOT RUN | NOT RUN | 已合入 c0f9ab11；详见 b3 |
| b4 | PASS：Python 1749、前端全套 851 加修后 26 项、Rust 414 加新增 argv 单测；PR #68 三项 CI PASS | PASS：真实 Docker 运行引用拒绝/缓存双向/成功/失败/取消/旧 ID 保留 | PASS：前端构建、冻结 CLI 命令 smoke；GUI 候选待统一构建 | NOT RUN | NOT RUN | 已合入 1efe0904；详情和证据路径见 b4 |
| b5 | PASS：前端 858 及修后 29 项；Rust 420 / 2 ignored | PASS：Rust 真实临时文件持久化、损坏保护、并发冲突和备份恢复；三类安装不在本批范围 | 前端生产构建 PASS；GUI 候选待统一构建 | NOT RUN | NOT RUN | PR #69 三项 CI PASS，已合入 d3798c06；U-4 默认成员保留待批准 |
| b6 | PASS：Python 1763 及最终定向 109、前端 865 及构建、Rust 420 / 2 ignored | PASS：真实 Skill/MCP/Plugin 应用、共享保护、卸载及运行标识 | 冻结 CLI 模块闭环 PASS；GUI 候选待统一构建 | NOT RUN | NOT RUN | PR #70 三项 CI PASS，已合入 ffc84885；详细证据及未测边界见 b6 |

| b7 | PASS：Python 全套 1774 及最终定向 112、前端 869 及构建、Rust 420 / 2 ignored | PASS：官方精确插件安装；受控 35 秒慢安装、断连、并发拒绝与超时清理 | 前端构建 PASS；GUI 候选待统一构建 | NOT RUN | NOT RUN | PR #71 三项 CI PASS，已合入 61c70540；详见 b7，真实上游故障慢网与 SSH 未测 |

| b8 | PASS：Python 1782 及最终定向 101、前端 874 及构建、Rust 420 / 2 ignored | PASS：合成令牌双引擎配置、真实客户端读取、开关/重新同步；真实授权 NOT RUN | 冻结 CLI 全链 PASS；GUI 候选待统一构建 | NOT RUN | NOT RUN | PR/CI 待执行；不将保存或合成令牌写成连接通过 |

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


## 2026-11-08 b9 本地及真实容器验证

上游 `mattpocock/skills:grill-me` 位于多层目录 `skills/productivity/grill-me/SKILL.md`，原三个浅层路径均无法覆盖。保留浅层快速读取，未匹配时读取受大小限制的 GitHub tree，唯一目录匹配后按 blob SHA 读取；拒绝歧义、截断 tree、超大内容和身份不符，五分钟有界缓存避免重复 tree 请求。仅解析简介，不执行文档指令。真实来源固定为 [4ae2317d](https://github.com/mattpocock/skills/blob/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/productivity/grill-me/SKILL.md)。

搜索后后台串行补充至多三条缺失摘要，其余按需读取；上下文和查询代数隔离。详情区区分有效空简介、加载和失败，显式重试保留已有摘要并显示来源。监听稳定身份，避免摘要回写引发自动无限重试；非技能条目不继承技能缓存。Rust 详情读取预算 60 秒且使用独立通路。

- Python 全套 1789 passed / 54 skipped / 207 subtests；适配器定向 85 passed / 11 subtests。
- 前端全套 876 passed（新增组件用例前）；最终描述与真实组件回归 7 passed，最终类型与生产构建 PASS。Rust 420 passed / 2 ignored。
- 真实隔离 Docker 搜索 `grill` 包含准确 `grill-me`；读取 4.00 秒，重复 2.14 秒，返回准确简介及固定提交来源。QA 容器已清理。证据在本机 `output/verification/real-details.json` 及测试日志。
- 自查完成，无独立评审；GUI/H9、SSH 尚 NOT RUN，按 D-15 留到统一 Preview。真实上游成功不代表人为断网 GUI 已验证。


## 2026-11-08 b10 实现验证

失败卡片新增中英文可访问关闭按钮，关闭后焦点返回“扩展市场”按钮。store 按 operationId 记录当前及此前失败的展示关闭状态，最新错误关闭后不回退显示旧错误；同次操作的重复错误文案按来源同步隐藏。后续独立列表/搜索错误不受影响，新失败照常显示。关闭不删除日志、不改变终态、不改变安全重试权限；结果未知仍不可重试。状态随同一 store 保留，组件重新挂载不会重显；目标变化时与原日志生命周期一起清空，最多保留现有 100 条日志范围的关闭标记，不新增磁盘偏好。

前端全套 882 passed / 105 files；生产类型检查发现 ES 目标不支持 Array.at，改为兼容访问后最终受影响回归 48 passed，类型与生产构建 PASS。真实页面组件回归覆盖关闭卡片和重复文案、焦点、重挂载与新失败；store 回归覆盖旧记录/复制诊断/重试保留、旧点击不吞新错误、独立读取错误、目标隔离与未知状态。证据在本机 output/verification/frontend-*.log。纯前端变更，无新增 Docker/CLI/Rust 行为，本批不重复跑其本地全套；远端 CI 另记。自查完成，无独立评审；DOM 自动化不记真实 GUI/H10 PASS，按 D-15 统一 Preview。


## 2026-11-08 整合候选发现与修正

S1：完整 stage 首次失败，适配器/default_mcp 两项校验值过期且新 github_mcp_auth 未纳入。按当前 Git 跟踪容器文件的规范打包字节重建 1534 项清单，仅三项变化；复验 PASS。S2：U-4 来源核对发现 science-skills 的目录使用下划线、frontmatter/市场名称使用连字符，B9 精确目录/身份检查仍拒绝合法来源。作为 F7 读取恢复的整合修正，增加仅限下划线/连字符的唯一匹配，歧义和不同名称仍拒绝；不启用任何默认成员。修正后补回归与真实读取再打包。

首轮 Windows 主程序编译 PASS，NSIS 因工作树绝对路径过长失败；以短路径 junction 引用相同 bundle 重试，未改变产品资源。冻结 CLI 与实际打包资源的模块应用/卸载、双引擎合成配置、grill-me 读取已通过，QA 容器已清理；合成令牌不代表真实授权。最终候选标识与修后验证另记。

S2 修后：适配器 87 passed / 11 subtests；完整 Python 1791 passed / 54 skipped / 207 subtests。真实容器 arXiv/OpenAlex 详情和重复读取 PASS，固定来源 4de67861。U-4 四项提案分别通过模块 installed→removed，QA 容器已清理。修后完整 bundle 校验 PASS；Windows 最终安装包正在重新生成，结果另记。CLI SHA256 `165b5ff38fc555eed02b551a5c90fa54ee2b315e06b111bdf5c3857c7c1f9f44`。


最终候选记录：PR #76 head be39b2a9 的 Workbench CI run 42411011239 三项 PASS，合入 develop 41d046d9。含最终资源修正的 Windows NSIS 构建 PASS，复制后的独立 bundle 再校验 PASS；候选启动与 About 实机检查 PASS，仅覆盖基础启动，完整 H1–H10/SSH/真实授权及安装升级仍 NOT RUN。候选窗口检查后关闭，原平台保留。产物、哈希、启动脚本和验证边界见 [DELIVERY](DELIVERY.md)。

## 2026-11-08 统一 GUI 复测与 S3

真实候选已完成工作区预检/启动和 H5 创建、重新读取、编辑保存子集。H6 发现模块预检约 47 秒占住共享 CLI 通道并造成工作记录同步超时，已改为独立通道；Rust 定向 35 passed，修后真实候选和 CI 另记。测试隔离、旧镜像上候选适配器部署及未测边界见 [preview-gui](preview-gui.md)。

2026-11-08 Preview.3：#78/#79 三项 CI 通过并合入；真实窗口的中文模块计划成功，预检期间 12 次 topic/runtime 短请求均成功，H5 追加重启持久化/删除保留说明通过，H9 真实摘要/来源子集通过。最终 NSIS 构建及冻结 CLI 多语言预检通过。具体候选、数据部署和未测范围见 preview-gui.md / DELIVERY；不将部分实测记为完整 H1–H10 或用户验收通过。

2026-11-08 Preview.3 追加：本机 H1 文件/目录大小写、刷新重入、冲突不覆盖及底部非法名称提示 PASS，正常键盘输入解决此前 UI Automation 行内输入限制。H10 可控失败的键盘/鼠标关闭、焦点返回、新失败再次出现、切换视图不重显 PASS；故障调用计数与插件清单证明关闭没有隐式重试或安装变更。仅为隔离 QA 容器故障注入，不能替代 H7 安装或 H10 跨目标/未知结果等未执行路径。逐项证据、部署恢复及重入回收提示的未定位观察见 [preview-gui](preview-gui.md)。

2026-11-08 Preview.3 镜像命名：H3 本机默认名/取消、显式旧标签选择、完整引用改名、其他标签保留、非法及冲突拒绝、registry port 保留均通过真实 GUI + Docker inspect。两个独立 scratch QA 镜像与标签已精确清理；候选产品没有变化。H4 重建、SSH、部分失败 GUI 未由本轮覆盖，详见 preview-gui。

2026-11-08 H4/S6：真实 GUI 通过运行引用阻止、显式停止后预检、默认无缓存参数和失败日志/旧镜像保留。构建触发首选镜像源 EOF，定位 guarded_rebuild 缺少普通构建的基础镜像回退和 digest 准备；现共用 prepare_build_argv。定向 52、全套 Python 1796/54 skipped/207 subtests 通过；修后冻结 CLI 使用完整 bundle 真实重建成功，新 ID 发布到所选 tag、其他 tag 和停止容器保留。当前标准 Preview.3 未含 S6，重打包、修后 GUI 及未测项见 [preview-gui](preview-gui.md)，不预记整体通过。

2026-11-08 Preview.4：#83 精确 head CI 42417635698 三项 success，合入 24d03cd3。重新冻结/NSIS 打包并更新独立候选；真实 GUI 设置与启动摘要两入口的缓存重建分别 12.2/12.5 秒完成，无缓存构建 19.3 秒取消且镜像未替换，实际参数与 Docker 状态核对通过。“帮助 → 关于”显示 Preview.4 / CLI/Bundle 0.1.10。缓存取消尝试遇到先完成，未记取消通过；Remote、完整无缓存 GUI 成功与安装升级等剩余边界见 preview-gui。候选哈希以 DELIVERY 为准。

2026-11-08 H7/S7：Preview.4 真实插件 mattpocock-skills 安装、重复点击禁用、磁盘版本与刷新回读通过。H6 发现科研推荐安装 identity 与实际目录不符；修正现有四项推荐为实际下划线目录，保留显示名，不迁移用户定义或启用 U-4。前端 28 passed、类型/生产构建通过，四项均由当前冻结 CLI 在独立临时目标 installed→removed 并回读通过，容器已清理。旧候选 GUI 的部分失败与预装项保留如实记录；新版 GUI、精确提交 CI 与候选重建另记，详见 preview-gui。

2026-11-08 Preview.5：#85 head d06b3269 的 CI 42420724178 三项 success，合入 5467c9cf。Workbench/NSIS 重建通过；真实 GUI arXiv/OpenAlex 安装、research 预装保护、当前项完成后停止、重新预检仅补缺项及切换视图后终态保持通过，三侧 SKILL.md 与记录一致。H2 的 Home/上下/End/Left/Escape/Shift+F10、647×593 子菜单左展与内部滚动、实际改名和移动均补充实测；磁盘对比只有指定会话变化。详情及未测边界见 [preview-gui](preview-gui.md)，不代表完整验收或本人认证通过。

2026-11-08 H5/S8：真实双窗口同时编辑 QA-C，revision 9→10 后旧稿保存拒绝且磁盘不变，重新读取保留草稿，明确保存后 revision 11；目标容器断网时本地定义保存成功，网络已恢复。实测暴露底部保存看不到上方冲突提示，补错误渲染后的最小滚动定位与连续空名称验证；13 项相关模块回归、类型/生产构建通过。修后候选和 CI 待补记，旧 Preview.5 不代表错误可见性已修正，详见 preview-gui。

2026-11-08 Preview.6：#87 精确 head 195ff2b6d 的 CI 42425026074 三项 success，合入 5677a6e6；Workbench/NSIS 重建并实机 About 核对通过。S8 空名称重复提交提示和故障注入的保存冲突均自动滚入视野，重新读取保留草稿，明确保存后保留外部修改；revision 11→12→12→13 和文件比对 PASS。H2 追加菜单外侧栏滚动、818×669→646×669 原生缩窄后菜单关闭，24 个集合/30 条未归档记录保持不变。详细证据与未测范围见 [preview-gui](preview-gui.md)，U-4/真实授权/完整用户验收不据此通过。

2026-11-08 Preview.6 H9：仅断开 QA 容器网络后，grill 搜索使用带失败说明的缓存，详情明确失败并保留来源/重新读取入口。恢复网络后的首次重试仍失败，随后同容器公开接口 200，再次显式重试成功；重新打开来源指向固定提交 4ae2317d。普通查询切换与摘要缓存通过，1,545 个技能文件前后不变。市场陈旧 batch-grill-me 条目明确拒绝；真实迟到响应/跨工作区 GUI 未补齐，不扩写 PASS。网络已恢复，详见 [preview-gui](preview-gui.md)。

## 2026-11-08 H4/S9 取消后的临时 tag 回收

Preview.6 完整无缓存 GUI 123.8 秒成功，其他 tag 与引用原镜像的停止容器保留。缓存第二次取消 9.8 秒终止，但发现临时 tag 残留；原候选取消清理不记 PASS。新增精确临时 tag 回收协议及 Windows 强制结束后的恢复处理。Python 关联 103 passed / 19 subtests（其中重建 27 项）、Rust 重建协议 2 passed；源码 CLI 实际回收该 QA 残留并核对其他资源未变。冻结 CLI 构建通过；修后候选 GUI、精确 head CI 待后续补记。单代理自查，无独立评审。详情见 [preview-gui](preview-gui.md)。

## 2026-11-08 Preview.7 修后候选

#91 精确 head 5414a099192da1372380426fa2006b0f58c28016 的 [CI 42429010839](https://github.com/Wifabric/AISC/actions/runs/42429010839) frontend/rust/cli 三项 success，合入 3b26609e7f0aef9f5eec449a91638c11eadb048e。重新冻结 CLI、NSIS 构建与四项产物哈希通过，About 版本实机核对通过。真实 GUI 缓存取消 9.5 秒、无缓存构建加受控临时 tag 后取消 27.5 秒均通过，原资源保留且临时 tag 清空；后者实际验证 Workbench 强杀后的回收，非手动事后清理。冻结 CLI 精确回收及幂等也通过。自然导出竞态未在修后重复撞中，不将受控测试写成自然复现；逐项边界见 [preview-gui](preview-gui.md)。

## 2026-11-08 H7/H10 与 S10

Preview.7 真实操作锁下 unknown/no-retry、关闭失败提示不改变安装/运行状态通过。释放锁后的首次安装暴露工厂空对象登记与当前目录安装器不兼容；只升级精确空对象并修正新镜像初始格式。部署修复到隔离容器后，真实 GUI 安装当前目录插件成功，磁盘版本/manifest 和冻结 CLI 一致，另一工作区登记不变。相关 94 passed / 16 subtests；完整门禁、精确 head CI 和标准候选重打包另记。测试部署与标准 Preview.7 严格区分，详见 [preview-gui](preview-gui.md)。

S10 本地完整门禁：Python 1812 passed / 54 skipped / 212 subtests；Rust 422 passed / 2 ignored；前端 888 passed，类型与生产构建通过。首次 pytest 未指定 tests 范围而误收集第三方重复插件测试，按仓库 tests 范围修正后通过，不归为产品失败。资源清单 1534 项，仅 Dockerfile/适配器两项变化；批量 Git 读取采用 vendor-refresh 的未改文件索引字节策略，与原脚本已完成 572 行一致。QA 窗口正常退出、专用容器已清理，原平台进程保留。远端 CI、标准候选和新镜像仍另记。

## 2026-11-08 Preview.8 完整资源候选

#93 精确 head 43f59340 的 [CI 42432013590](https://github.com/Wifabric/AISC/actions/runs/42432013590) 三项 success，合入 e5c17c3eb7eb13bebf2a42db0556caea92b77633。新镜像 factory v2 和最终 adapter 哈希通过；首轮 Preview.8 GUI 在全新工作区无手工修补安装成功，其他两工作区登记不变。剔除 QA 临时文件后重新完整校验与打包，最终标准候选重启显示安装版本、About 版本正确，四项产物哈希通过。首次 GUI 与最终标准二进制哈希分别记录，完整边界见 [preview-gui](preview-gui.md)。

## 2026-11-08 Preview.9 H7/H10 超时与恢复

标准 Preview.9 / S11 完整镜像，在专用空工作区仅延迟选定原生安装调用 195 秒，产品原有 180 秒超时未改。真实界面安装按钮禁用、单次调用持锁；超时后进程消失、锁释放、列表为空，明确提示未安装并提供重试。重试延迟改为 35 秒，在进程仍运行时由真实界面正常关闭工作区并切到 fresh8，旧状态未带入，三个已有工作区登记不变。重新打开原工作区的新容器无夹具、原生安装器哈希恢复一致，真实安装成功并回读版本 1.2.3-c55ee46073ed。三次 QA runtime 正常移除，候选四项哈希与原用户平台核对通过。证据 h7-timeout9-{deployment,running,timed-out,retry-running,switched,final,result}.json 和对应 gui 文本；详见 [preview-gui](preview-gui.md)。此为受控超时与关闭切换，不代表自然慢网或模块执行中切换；本轮没有产品代码变化，不新增 PR。

## 2026-11-08 Preview.9 H9 迟到响应与切目标

在隔离容器中延迟真实详情响应，GUI 的新 caveman 查询已显示时，旧 grill-with-docs 成功响应仍等待交付；随后原样交付，界面未串结果。grill-me 首次响应早于该交叠，分别记账。另一详情加载期间正常关闭旧工作区再同窗切目标，新目标查询/加载/错误状态独立，重新读取 grill 三项简介和固定来源正常。四个 QA 工作区 1,942 项技能文件/插件登记、候选四项哈希不变，临时运行环境正常结束。证据 h9-preview9-* 与 gui-h9-preview9-*；受控透明响应入口、上游陈旧 caveman 条目返回 NOT_FOUND、关闭旧 runtime 的覆盖边界详见 [preview-gui](preview-gui.md)。不声称自然网络竞态或用户验收通过。
