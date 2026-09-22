# 自更新端到端实测（含发布链版本戳修正）

> 状态：计划待用户验收（2026-09-19 立项）——**实测前有一个必须修的语义坑**
> 方法：ultracode workflow（研究员 + 独立证据核验；verdict=corrected，三处行号/措辞修正已并入）
> 对应 target：docs/todo.md「自更新端到端实测」

## 1. 现状与关键发现

- **端到端此前从未成立**：旧 release 挂的是 Inno CLI 安装器，Workbench NSIS 从未上过 release（devlog:20-23，核验修正：原引 14-16）；v2.1.12-preview.1 是首个真载荷（在架实查：prerelease，恰 `AISC-Workbench-2.1.12-preview.1-setup.exe`(+.sha256) 两资产）。
- **核心语义坑：tag 版本 ≠ 嵌入版本**。`git show v2.1.12-preview.1:workbench/src-tauri/tauri.conf.json` → `"version": "2.1.12"`（final 形态，无 preview 后缀）；工作流构建步无版本覆盖，update.rs:81-83 直接用 package_info。后果链：
  - 比较语义本身没坑：`(2,1,13,false,1) > (2,1,12,true,0)` 成立（update.rs:160-162 + :448 单测）→ **preview.1 装机能正确检出 v2.1.13-preview.1**。
  - 真正的坑是**同 base 不可达**：已装 2.1.12 永远检不出 v2.1.12-preview.N；将来装了「报 2.1.13」的 v2.1.13-preview.1，也永远检不出 v2.1.13-preview.2 和 final v2.1.13（相等不大于）。阶段内迭代链全断。
  - ⇒ **实测目标版本必须是 v2.1.13-preview.1**（develop conf 已是 2.1.13，无需改仓库）；todo 原文「preview.2」措辞按此理解。
- **升级安装路径 CI 未覆盖**：静默升级走「卸载旧版再装」分支——installer.nsi **L241**（SemverCompare，核验修正：原引 267-272）+ **L340-345**（upgrading 默认选卸旧）+ **L355-373**（reinst_uninstall: ExecWait 旧卸载器）；nsis smoke S4.2 只测同版本重装（same→add/reinstall）。
- **安装后不自动重启**：`app.exit(0)` 后静默安装器跑完即结束（update.rs:353-354）；finish page 仅 GUI 生效。
- **升级链**：docker-scan → docker-cleanup --context upgrade（仅清容器，镜像存活，与 D-2 不冲突）→ docker-rebuild（30min 预算；installer.nsi:1542/1624/1636-1638）——实测机需预留时长。
- **文案三处与 D-8.8 脱节**：zh/en hint「仅正式版通道；开发预览版不在此列」（zh-CN.ts:552、en-US.ts:552）、note「no final release published yet」（update.rs:209）、「安装并重启」（实际不自动重启，zh-CN.ts:562）。
- **下载链 fail-closed**：sha 不符删 .part；staging 文件名用当前版本、装后残留 `%TEMP%\aisc-workbench-update\` 无清理（update.rs:225-326）。
- **无启动自动检查**：仅 help 菜单「检查更新」与设置页「关于与更新」两个手动入口。

## 2. 方案裁决（Claude 代定，用户可否决）

- **采纳 CI 版本戳（研究选项 B）**：nsis-installer.yml 构建步改为
  `npm run tauri build -- --bundles nsis --config "{\"version\":\"${GITHUB_REF_NAME#v}\"}"`
  （tauri CLI --config 支持 JSON merge 覆盖 conf.version）。嵌入版本与 tag 全等（如 `2.1.13-preview.1`）→ preview.1→preview.2→final 全链自更新可达，update.rs 零改动，仓库零改动（不动收官 bump 流程）。
  - 首刷观测点：tauri bundler 对 prerelease 版本的 NSIS 处理（VIProductVersion 四段、注册表 DisplayVersion 写 `2.1.13-preview.1`、SemverCompare 对 semver prerelease 的升级分支判定）——「首刷观察、发现问题再修」。
- **不采纳**：仓库侧双 bump（每次发 preview 改 conf，churn 大易漏）；纯流程实测（阶段内版本链永久断裂）。

## 3. 实测协议（E2E 步骤）

1. **文案修正批**（随首发批入库）：update.rs:209 note →「无可更新的已发布版本」；zh/en hint → preview 通道表述；「安装并重启」→「退出并安装」。
2. **CI 版本戳落地**（若采纳 B）：workflow_dispatch 手动触发一次（不打 tag），确认产物嵌入版本=指定值 + S4.2 smoke 全绿。
3. **凑首发批**：首个完成的 v2.1.13 实施批并入 develop，四门 CI 绿。
4. **写 `docs/releases/v2.1.13-preview.1.md`**（对照 preview.1 格式：Preview 声明/亮点/安装与更新/CLI 通道）。
5. **发布**：`git tag v2.1.13-preview.1 && git push origin v2.1.13-preview.1` → 盯 nsis + release-preview 两 job → `gh release view` 确认 prerelease、资产命名、notes。
6. **CI 侧断言**（人工跑一次脚本）：资产可下载、sha256 sidecar=64 hex 且与实文件一致、按 update.rs 同款 version_key 复核「2.1.12 装机视角应检出 2.1.13-preview.1」。
7. **用户实机 E2E**（唯一真实验证；有 Docker 走全升级链，预留 30min 级窗口）：
   - 基线：About 当前版本 = 2.1.12；发版前检查应「已是最新」（负基线）。
   - help「检查更新」→ 检出 2.1.13-preview.1 并跳设置页 → 下载进度字节推进 → ready 显示 sha 前 16 位 → confirm → 应用退出、无安装器窗口 → 等 docker 升级链 → **手动重启** → About = 2.1.13-preview.1（采纳 B 后）。
   - 保留验证（对照 S4.2）：会话历史/App data 存活、工作区完好、PATH 恰一条 INSTDIR 且 REG_EXPAND_SZ、卸载键 DisplayVersion 更新、`aisc version` 与 release 同批、`aisc build --dry-run` 通过、docker 镜像存活且已 rebuild。
   - 断点记录：About 错误行原文 + `%LOCALAPPDATA%\AISC\data\logs\aisc.log` 尾部 JSONL + `%TEMP%\aisc-workbench-update\` 清单；安装器阶段可手动重跑 staged exe 取退出码。
8. **归档**：实测结果入 devlog；todo 勾选（备注版本戳生效证据）。

## 4. 约束

- D-8 全套不动：preview 为默认渠道、final 仅经用户明确要求；发布节奏裁决权在用户（打 tag 前须用户点头）。
- GUI 安装→升级链必须用户 Windows 实机（已装 preview.1 + 有 Docker）；GitHub API 侧可 CI。
- 匿名 API 限速 60 req/h/IP（可设 AISC_GH_API_TOKEN 提额）；实测机需可达 api.github.com。

## 5. 开放问题

| 决定 | 状态 | 默认 | 说明 |
|---|---|---|---|
| 首发批凑哪些变更 | open（用户裁） | 首个完成的实施批 + 文案修正 + CI 版本戳 | 不塞过多目标 |
| 采纳 CI 版本戳（选项 B） | **open（用户裁）** | 采纳，随首发批落地 | 不落地则阶段内 preview.2/final 永不可自更新达 |
| 实测机与环境 | open（用户裁） | 用户日常机（有 Docker，接受 30min 升级链） | 无 Docker 备机可跑主链跳过 docker 断言 |
| CI 化跨版本升级 smoke | assumed | 本期不做，记 backlog | 双构建显著增加 CI 时长 |
| DisplayVersion 为 preview 全形的 SemverCompare 行为 | assumed | 首刷观察、发现问题再修 | nsis_tauri_utils 从未实测过 prerelease 形态 |
