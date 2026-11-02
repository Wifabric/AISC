# 实测与证据账本

截至 2026-11-02，b1 已实现并执行 Windows Rust 验证及候选构建；其余批次未实施。独立的 2.1.17 个人功能整合验证不计入本表。

| 批次 | 定向/自动化 | 真实数据面 | 候选构建 | Windows CU | 用户验收 | 原因 |
| --- | --- | --- | --- | --- | --- | --- |
| b1 | Rust PASS：415 passed / 2 ignored；前端 840+1 复测通过 | PASS：Windows 普通 NTFS 文件/目录；其他环境 NOT RUN | PASS：debug Workbench；前端修正版 build PASS | 改名/刷新/重入/不覆盖 PASS；冲突提示初测 FAIL，修后复测 NOT RUN | NOT RUN | 用户取消 CU，已停止输入；尚无 b1 PR/CI |
| b2 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施 |
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

## 每次实测记录模板

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
