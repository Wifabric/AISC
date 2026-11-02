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
