# 2.1.14 统一手测清单（HANDTEST）

> 按 DEVELOP_WIKI §1.3 四要素书写：前置准备 / 操作（命令级或 UI 位置级）/
> 理想结果（字段级）/ 异常判定。范本：docs/archive/2.1.13-dev-plans/HANDTEST.md
> 批 8（T1-T4）。
> 变量定义（示例值）：
> `$ai = E:\Windows\Users\alan\Documents\AISC\workbench\src-tauri\target\debug\aisc.exe`
> （或安装版 `& "C:\Users\<你>\AppData\Local\AISC Workbench\aisc.exe"`）；
> `<WS>` = 常用测试工作区绝对路径；`<容器>` = `docker ps --format {{.Names}}`
> 里的 aisc runtime 容器名。
> 「记下来告诉 Claude」= 打开新会话贴出现场（截图/命令输出/字段值）。

## 结果总览与分工（D-21：CLI 可测项全由 Claude 执行；用户只做交互式 UI）

> **2026-09-24 收口**：功能测试全部通过（用户确认）。表内✅为已验证终态；
> ⏸/挂起为观察项：T1-1/T1-2 应用内流随 preview.2→下一跳、T6-4/5/6 需断网
> 窗口、T5/T2-A/T4-1·3·4·5 随日常使用回归。

| 项 | 执行方 | 状态（2026-09-24） |
| --- | --- | --- |
| T1 出包（发布链） | **Claude** | ✅ 2026-09-24：v2.1.14-preview.1 发布（四轮构建：vendor checksums 补账→stage-npm bash3.2+NSIS 伴生包→PathRead 值不存在真缺陷修复→绿；292.7MB 含离线伴生包，prerelease ✓）
| T1-3 装后取证 | **Claude** | ✅ 2026-09-24：DisplayVersion=2.1.14-preview.1；PATH=ExpandString（存量自愈实证）；INSTDIR 恰 1 条；CLI 0.1.2 同批；dry-run 过且 source=manifest（F11 生效）；镜像 upgrade 链自动重建；数据保留 ✓
| T1-1/T1-2 应用内更新流 | 用户+Claude | ⏸ 顺延下一跳：本次 30s 整体超时腰斩 292MB 下载（b12 已修 connect/read 双超时）；/R 拉起链由 CI smoke 覆盖；staging 目标版本命名+清场在 2.1.14→下一跳验证 |
| T2-0 adapter 判别 | **Claude** | ✅ 2026-09-24：镜像内 adapter mtime=2026-09-24 05:09（b7 已入） |
| T2-B 保存保真（docker exec 容器实跑） | **Claude** | ✅ 2026-09-24 ×3：preset claude env 覆盖落库+模板基线保留（OPUS/SONNET 扇出跟随、HAIKU/SUBAGENT 基线）；preset codex model+catalog 落库；custom codex model 首存非空（H2 闭环） |
| T2 6 模板回归矩阵（保存路径） | **Claude** | ✅ 等价覆盖：adapter 单测 97 例含 preset/custom × claude/codex 矩阵 |
| T2 拉取日志核验（/tmp/aisc-fetch-models.log） | **Claude** | 待用户拉取实测后核（无 key 无法触发真实候选链） |
| T2 A 路径（baseUrl 静默改写，冷启动竞态观察）/ 3-5（拉取，需有效 key） | 用户 | 待测 |
| T3-1 高级槽位间距 / T3-2 徽标对齐 | 用户（视觉） | ✅ 2026-09-24 复测基本通过（用户反馈 #8）；后续 provider 页 cc-switch 复刻（b9）会再动该区域，收口前终验 |
| T3-3 关于弹窗 | 用户 | ✅ 通过（2026-09-24） |
| T3-1 回归线 vitest（ccSwitchUiTab 351-353） | **Claude** | ✅ 509+ 例绿（2026-09-24） |
| T3 picker 窄窗 | 用户（视觉） | 待测 |
| T4-1/3/4/5（按键回归，真实手感） | 用户 | 待测 |
| T4-2 Ctrl+/ codex 实测 | 用户 | ✅ 通过（2026-09-24，legacy 0x1F 臂生效，定案） |
| T4-6 单测 | **Claude** | ✅ 3/3 绿（2026-09-23） |
| T5 关闭工作区全项 | 用户（UI 交互） | 待测（T5-4 teardown 核验由 Claude 顺带 docker ps 复核） |
| T6-1 版本一致性 | **Claude** | ✅ 2026-09-24 实证：resolver(api) v5.10.5 == manifest == downloads == Dockerfile ARG == 镜像 label（build.complete argv 全链可见）；独立脚本（F6）留观察 |
| T6-2 被墙条件 | **Claude** | ✅ 等价实证 2026-09-24：真机构建 5 段预置全命中（mihomo1+geodata3+npm1+cc-switch1[sha 校验行]+yazi1）、零 GitHub 出站、apt CACHED；真防火墙模拟未做（不动用户网络） |
| T6-3 预置清单 | **Claude** | ✅ 9 条 tracked（含 .gitkeep）、yazi 7,944,048B 精确 |
| T6-7 镜像完整性 | **Claude** | ✅ claude-hud dist/index.js 在镜像（F9 反例外生效）；上下文差集由 git ls-files 对 downloads 抽查 ✓ |
| T6-8 保守分支 | **Claude** | ✅ 无 resolver 手动 docker build 命中预置 v5.10.5（glob 兜底生效），19s 完成，零在线 |
| T6-9 GH_PROXY 通道 | **Claude** | ✅（半）空值零注入已实证（build argv 无 GH_PROXY）；注入正向用例留待需要时（改 versions.env 即可验） |
| T6-4 慢速 / T6-5 断网负样本 / T6-6 失败诊断卡片 | 需断网窗口或防火墙授权 | 挂起（netsh 动用户网络未授权不做；T6-6 需真实失败构建） |

## T1 批 1：自更新三项（三条独立验收线）

**前置**：装 2.1.13 的实机（Windows + Docker Desktop）；develop 已含批 1
并发布 `v2.1.14-preview.1`（或按 selfupdate-e2e.md 流程临时出包）；预置
`%TESTVAR%` 对照——若用户 PATH 亲手加过 `%变量%` 条目则以真实条目为对照，
否则本组跳过 (c)-2。

1. **staging 命名**：设置页「关于与更新」→「检查更新」→ 检出 2.1.14 → 下载。
   下载中另开 PowerShell：`dir $env:TEMP\aisc-workbench-update\`。
   理想：下载中出现 `workbench-setup-2.1.14-preview.1.part`；完成后存在
   `workbench-setup-2.1.14-preview.1.exe`（**文件名含目标版本，非 2.1.13**）；
   staging 目录内无旧版本 `workbench-setup-*.exe` 残留；ready 行显示 sha256
   前 16 位。
2. **静默拉起**：点「退出并安装」确认 → 应用窗口消失、无安装器窗口 →
   Docker 升级链完成（安装日志时间戳）后数秒内 Workbench **自动打开**。
   理想：设置页「当前版本」= 2.1.14-preview.1；任务管理器 aisc-workbench
   进程「账户名」=当前用户、无「已提升」标记；Docker Desktop 原为停止则
   被先拉起；zh 文案显示「退出并更新（完成后自动重启）」。
3. **PATH 类型**：
   `(Get-Item HKCU:\Environment).GetValueKind('Path')` → 升级前后均
   `ExpandString`；`$env:Path -split ';' | Select-String AISC` → INSTDIR
   条目恰一条；预置场景：`[Microsoft.Win32.Registry]::GetValue('HKCU:\Environment','Path',$null,'DoNotExpandEnvironmentNames')`
   → `%TESTVAR%\bin` 保持字面。存量自愈：一台历史装机（Path 曾为
   `String`）升级后 `GetValueKind` 变 `ExpandString`。
   回归：新 PowerShell `Get-Command aisc` 指向 `$INSTDIR\aisc.exe`。

**异常判定**：拉起后进程带「已提升」标记；文件名仍是 2.1.13；`GetValueKind`
仍 String（存量机升级后）；`%TESTVAR%` 被展开成绝对路径——任一出现即记下
告诉 Claude。

## T2 批 2：provider 新建保真

**前置**：Docker 已启动、runtime 就绪；**第 0 步 adapter 判别（必做）**：
`docker exec <容器> stat -c %y /usr/local/bin/aisc-cc-provider` → 日期须晚于
2026-09-19（commit 5f168f4）。早于该日期 = 旧镜像，本批手测全部作废，先
重建镜像（否则「拉取失败」是旧 adapter 的 requires --id，测了个寂寞）。
准备一个有效 GLM key（步骤 3-6 用）。

1. **复现路径 A（baseUrl 静默改写）**：冷启动 Workbench → 打开工作区 →
   立刻切 Provider 页点「添加」（抢在 loadTemplates 往返前）→ codex →
   模板 Codesome V3 → 高级 → 上游格式改 openai_responses → 记录预填
   baseUrl（应带 `/v1`）→ 填测试 key → 原地等 5s → **不再看 baseUrl** →
   保存 → 重开编辑页查 baseUrl。
   理想（修复后）= 第 2 步所见值（带 /v1）或保存前有可见变更提示；
   现状（bug 标志）= 被静默改为无 `/v1`。
   **对照臂 ×2**：①第 2 步手敲一遍 baseUrl 再等 5s（touched）→ 两版都应
   保持；②切格式后手填 baseUrl 再等 5s → 修复后仍保持（onApiFormatChange
   重臂不覆盖手填值）。
2. **复现路径 B（新建丢字段）**：添加 → 自定义 claude → 填 id/baseUrl/key →
   高级映射 Sonnet/Opus 槽填 `glm-5.3` → 保存 → 重开编辑页。
   理想：两槽回显 `glm-5.3`；现状：为空。codex 变体：自定义 codex 填
   「模型」→ 重开编辑页 model 非空。
3. **拉取·claude 侧**：添加 → 模板 Zhipu GLM（预填
   `https://open.bigmodel.cn/api/anthropic`）→ 填有效 key →「拉取模型列表」。
   理想：按钮数秒内回弹，fetched.ok=true、n≥1，下拉含 `glm-5.3`。
4. **拉取·codex 侧**：同 3（同模板同 key）→ 结果与 3 完全一致。
5. **降级路径**：故意填错 key 拉取 → fetched.ok=false、message 为上游 401
   摘要（非超时、非空串），下拉仍列已知模型可手输——不得整页报错。
6. **日志**：`docker exec <容器> cat /tmp/aisc-fetch-models.log` → 能看到
   本轮候选请求行（base/status/ids 形如 `base=.../api/paas/v4/models
   status=200 ids=8`）。
7. **回归矩阵**：其余 5 家模板各做一次步骤 3（deepseek/ark/kimi 需对应
   有效 key；codesome 需 sk-/cr-）；通用验收：新建（preset/custom ×
   claude/codex）→ 保存 → 重开编辑页逐字段比对（baseUrl、model、映射槽、
   compact 阈值、key 掩码）与保存前一致；再编辑保存一次仍一致。

**异常判定**：第 0 步日期旧于 2026-09-19；任一模板拉取超 25s 才回弹
（预算失效）；保存后重开比对任一字段不一致——记下「哪个模板/哪步/差哪个
字段」三要素告诉 Claude（U-5 回访同口径）。

## T3 批 3：UI 对齐四项（含 picker 窄窗——验证：设置字号 1.0，窗口缩至 700×500/600×500，picker 整页不再随窗口缩小、元素完整可读）

**前置**：dev 态 `cd workbench; npm run tauri dev`（或装批 3 后的包）；
历史面板须有 claude 与 codex 各 ≥1 条历史（不足先各跑一条对话）。

1. **高级槽位间距**：Provider 页 → 添加 → 任一 claude 模板 → 保存进编辑页        不行，为什么claude添加provider的页，变成codex页的样子了？模型映射区域都没有opus这些框了
   → 高级 → 模型映射 →「展开高级槽位（默认模型/子代理）」。
   理想：MODEL 与 SUBAGENT 两行出现垂直间距（computed `gap: var(--space-2)`
   =8px，与 SONNET/OPUS/HAIKU 同节奏，边框不再贴合）；收起再展开正常。
   回归：codex 高级页签目录表行距不变；简易页签不变；
   `npx vitest run src/features/ccswitch/__tests__/ccSwitchUiTab.test.ts`
   全绿（351-353 用例仍找到 5 个 mapping 输入框）。
2. **历史页徽标**：活动栏「历史」tab → 出现 CODEX N / CLAUDE N 分组 →    不行，当前依旧是在历史名过长时，出现错位
   逐行检查：徽标与标题/「N 条消息」中心对齐、不整体偏高、✳ 与 claude
   文字等高不上凸；悬停：「查看对话」chip 淡入、行高无跳变、chip 与徽标
   等高平齐；组头位置不变。
   字段级（F12）：`.cv-view-chip` 与 `.agent-glyph` 的
   `getBoundingClientRect().height` 相等（目标 20px）、top 差 ≤1px；悬停
   前后 `.conversation-row` 高度不变（恒 24px）；侧栏拉窄至 240px：标题
   省略号、条数/chip/徽标单行完整不换行；dark/light 往返配色完整
   （transparent 边框等高方案不露馅）。
3. **关于弹窗**：设置 → UI 字号缩放设 **1.25** → 帮助 →「关于 AISC            关于页当前行为正常，通过
   Workbench」→ 等诊断 done。
   理想：弹窗底缘在视口内；检查列表容器有竖向滚动条；滚动可达最后一条
   （channel-confusion）与底部「导出诊断包」按钮；Esc/背景/× 三路关闭且
   焦点归还。字号 1.0 复验：内容不满屏无滚动条无多余空白；**1.5 档 +
   800×600 小窗**复验不越界。

**异常判定**：任一档字号下弹窗仍越界/无滚动（若 1.0 档也越界，说明 zoom
机制判断有误——务必告诉 Claude 实际 font_scale 值）；chip 与徽标 rect 高度
差 >1px；vitest 基线（480+）下降。

## T4 批 4：终端键盘域（Ctrl+/ + 分屏导航）

**前置**：dev 态起 Workbench；工作区内开一个 codex 会话终端 pane；知道
本批载荷定案臂（A=`ESC[47;5u`、B=`\x1F`，实现按定案，两臂都试时逐臂记录）。

1. **字节链路（参考项，不作裁决）**：pane 跑 `cat -v` → 按 Ctrl+/。                 
   修复前基线：无任何输出（静默丢弃证明）；修复后：可能回显 `^[[47;5u`
   或 `^_`——**ConPTY 下 cat -v 不可靠，回显与否不判成败**。
2. **codex 实测（唯一裁决）**：pane 跑 `codex` → 输入 `/btw` 回车 → 进入               快捷键生效，通过
   旁路线程（出现 side/btw 标识）→ 按 Ctrl+/。
   理想：焦点切回 main（标题/输入上下文变回、不新建线程、不杀进程）；
   再按可往返；全程不需要 Ctrl+C。若臂 A 无效臂 B 有效（或反之），
   记下有效臂告诉 Claude 定稿。
3. **回归-SIGINT**：`cat -v` 下 Ctrl+C → 回显 ^C 且进程中断（\x03 不受
   影响）；终端有选区时 Ctrl+C 仍为复制。
4. **回归-既有快捷键**：Ctrl+F 搜索浮层、Shift+Esc 回 tab 栏、Ctrl+B 侧栏
   ——均与 2.1.13 行为一致。
5. **干扰面**：bash 空提示符 Ctrl+/ → 无字符插入、无报错、无补全触发。
6. **单测**：`npx vitest run src/features/terminal/__tests__/terminalCtrlSlash.test.ts`
   全绿（ctrl+'/' → writeSession 字节 + preventDefault + return false；
   keyup 不发；Ctrl+Shift+/ 不发）。

**异常判定**：步骤 2 切不动（两臂都无效）——记下臂别与 codex 版本
（`codex --version`）；步骤 3/4 任一回归。

## T5 批 5：关闭工作区回 picker

**前置**：dev 态或装包；一个 ready 工作区 + 2 个运行中 bash 会话。

1. 入口可见性：顶栏右端出现「关闭工作区」按钮、「操作」菜单出现「关闭
   当前工作区」项且可用；picker 态两者隐藏/禁用；starting 态不显示。
2. confirm（有会话）：点按钮 → 弹「将结束 2 个活动会话，并删除此工作区的
   临时运行环境。继续？」→「取消」→ 状态仍 ready、会话数不变。
3. 执行：<1s 回 picker。字段级：顶栏状态标签=「选择工作区」、窗口标题=
   「AISC Workbench」、路径输入框空、最近列表**含**刚关工作区（注意：
   last_used_at 保持**打开时刻**不因关闭刷新；若该区恰是最近打开的则居
   首行——这是预期，不是 bug）。
4. teardown 落实：稍等后 `docker ps -a --format {{.Names}}` 过滤该 runtime
   名 → 无残留容器；lease 已释放（维护命令/注册表查询）。
5. confirm（无会话）：文案=「将删除此工作区的临时运行环境（工作区文件
   不受影响）。继续？」。
6. 重开同一工作区：reconcile→preflight→summary→starting→ready 全链正常
   （**不要求秒回**）；工作区文件、~/.aisc 历史、explorer 树完整。
7. 回归：ready 态直接点窗口 X → 仍走原 confirmExit/runExitFlow（行为不因
   新按钮改变）；命令面板出现 app.closeWorkspace 与 app.picker 成对。

**异常判定**：关闭后 `docker ps -a` 有该 runtime 残留容器；picker 字段
核对任一不符；X 退出路径行为改变。

## T6 批 6：网络保底构建（升级版）

**前置**：dev 或安装机均可；`$ai` 指向装好批 6 的 CLI；`$ev = events.jsonl`；
一台可断外网的测试环境（或防火墙/clumsy 模拟）。按 U-8 终裁后的预置形态
准备 downloads/（C-混合：yazi zip + npm 主包已入 git，伴生包在 bundle/本地
stage 补齐——本组 T6-2 前先跑 `bash scripts/stage-npm.sh`（不带 --latest，
按 versions.env 钉版拉取））。

1. **版本一致性预检（F6/F7）**：改动任一版本源（如 versions.env 的
   CLAUDE_CODE_VERSION）后跑 `python tools/check-version-sync.py`。
   理想：五处版本（Dockerfile ARG/versions.env/downloads 实存/config
   manifest/vendor manifest）不一致 → 非零退出 + 指明冲突处；一致 → 0。
2. **被墙条件（主死亡场景复现）**：防火墙封 github.com 与全部 gh* 镜像域
   （保留清华 apt / npmmirror / docker 镜像站）→ `& $ai build --tag ht141:1 --events 2>$ev`。
   理想：构建日志「📦 使用本地预置」恰 **7 行**（mihomo 1 + geodata 3 +
   npm 1 + cc-switch 1 + yazi 1）；末条 `type=build.succeeded`、
   `image_tag=ht141:1`；全程零 GitHub 出站（容器日志无 ghfast/gh-proxy/
   moeyy 连接尝试）。
3. **yazi 预置文件名与体积**：`git ls-files container/downloads/`（C-混合
   口径 = 现有 6 条 + yazi 1 条 + npm 主包 2 条 = 9 条，含 .gitkeep）；
   yazi 文件名 `yazi-x86_64-unknown-linux-musl-v25.2.26.zip`、体积
   7,944,048B（7.6MiB）。
4. **慢速条件**：clumsy 限速 30KB/s → 构建。理想：>10MB 档下载
   （cc-switch/yazi 伴生链）max-time ≥300s 不中途超时；基底预拉可配
   `$env:AISC_PULL_TIMEOUT_S=3600` 覆盖；全程不 exit 于 timeout。
5. **断网边界（U-9① 口径的负样本）**：全断网（含国内源）→ 构建。
   理想：失败于 apt 段（结构性边界，见 build-network.md §4），失败卡片
   （F10）diagnostics 给出明确归因与出路，**不是**裸 curl 报错。
6. **失败诊断（F10）**：仅封 GitHub 且移走伴生 tgz（模拟预置缺失）→
   `$ev` 末条 `type=build.failed`、error_code=`AISC_ERR_BUILD_FAILED`，
   附 `diagnostics={"network":"container-cannot-reach-github","matched":["curl:(28)"]}`
   形态 + suggestions 数组 3 项（stage/gh-proxy/doc）；Workbench 失败卡片
   三按钮（重试/预置下载包/文档）可点。
7. **镜像完整性（F9）**：T6-2 成品容器内
   `docker exec <容器> test -f <plugins/cache/claude-hud>/dist/index.js` →
   存在（.dockerignore 反例外生效）；构建上下文与 git tracked 差集为空
   （CI 不变量，本地可 `git ls-files | comm` 抽查）。
8. **保守分支（F2）**：CC_SWITCH_ASSET_URL 置空手动 `docker build` →
   日志「📦 使用本地预置 cc-switch」（glob 命中任意版本，sort -V 取最新）
   而非转在线；预置分支 sha256 校验行出现（F8）。
9. **GH_PROXY 通道（升格后）**：versions.env 填 GH_PROXY=… → `& $ai build` 日志
   可见代理前缀生效于四段镜像链；不填 → 零注入（D-12 口径）。

**异常判定**：被墙条件下任一段转在线；预置行数 ≠7；yazi 仍 60s 超时；
断网死于 apt 之外的段；镜像内 dist/index.js 缺失；未填 GH_PROXY 却出现注入。
