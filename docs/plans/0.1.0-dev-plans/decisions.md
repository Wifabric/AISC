# 0.1.0 决策记录

> 状态标记：【已裁决】=2026-09-16 开池审问用户拍板，不可再议；【拟裁】=计划内推荐，随对应批次开工请用户确认；【待裁决】=开放问题，不阻塞开池。

## D-1 · 版本时序：0.1.0 一版收敛 + 开池即 dev0【已裁决，R2】

- **裁决**：2.1.11 final 跳过不发（v2.1.11-dev Preview 即其最终产物）；周期末出 0.1.0 final（dot tag `v0.1.0`）+ PyPI 首发同 tag；开池即四件套 bump `0.1.0.dev0`，TestPyPI dev 迭代从 dev0 起逐次 +1。final 发布执行链细化（tag 后 dispatch artifact.yml 出全量资产 Release、NSIS 补附、再 dispatch pypi-publish）见 A9；dev 迭代的 tag 前置链见 D-26——均为裁决的落地路径，不改变裁决本身。
- **证据**：仓库根 VERSION=2.1.11.dev0；docs/devlog.md:138-146（四件套封版先例）；docs/archive/2.1.11-dev-plans/README.md:4（上周期「开发期保持 2.1.10.dev0」惯例）；pypi-release-guide.md:179（同目录）（TestPyPI 同 dev 版二次上传被拒，须逐次 bump .devN）；git tag 列表（v2.1.4 后全 dash 格式 -dev prerelease）。
- **理由**：final-only PyPI 门（指南 3.4.1）使 2.1.11 final 无用户价值，跳过省一次裁切；dev 元数据是 TestPyPI 迭代硬前置，惯例让位于工程需要。
- **回滚/边界**：周期中应急发版以当时 VERSION 出 dot tag 即可，不破坏本裁决；四件套不同步会被 A6 版本一致性检查（指南 3.4.2）挡下。

## D-2 · 分发名 `aisc-cli` 与尽早占名【已裁决，R3；落实指南 D-1】

- **裁决**：分发名 aisc-cli，import 包与 console script 保持 `aisc`；四处脚本字面量同步（pyproject.toml:6、src/aisc/__init__.py:35、scripts/verify-cli-install.py:86,137、scripts/verify-sbom.py:31,76）；A6 前尽早注册 TestPyPI/PyPI pending publisher 占名。
- **证据/理由/回滚**：见指南 §2 D-1（aisc 已被 2019 年休眠包占用为实测事实；决策到首发之间有抢注窗口；PyPI 项目名不可原地改名，首发前可改、首发后不可）。

## D-3 · 资源模型路线 C：瘦 wheel + `aisc bundle fetch`【已裁决，R3；指南 D-2】

- **裁决**：PyPI 发纯 Python 瘦 wheel；fetch 从 GitHub Releases 取同版本 bundle 到 data root `bundles/<ver>/`；路线 B（载荷入 wheel）否决，理由进 ADR 002（指南 3.5.2）。
- **证据**：src/aisc/application/resources.py:115-204（site-packages 安装按设计返回 None，今天发布即坏包）。
- **回滚/边界**：fetch fail-closed + 三条手动逃生路（--from-file / 手动 URL / --aisc-root），降级模式文档化（指南 3.3.3/3.3.4）。fetch 的数据源 = Release 上的 `AISC-<ver>-<plat>-<arch>` 资产——这使「Release 必须先有全量档案资产」成为 A9 收口的硬前置（见 A9/D-25）。

## D-4 · 版本号策略：改 0.x，起始 0.1.0【已裁决，2026-09-16 A1 开工审问——推翻指南 D-3 推荐】

- **裁决**：放弃 2.x，改用 **0.x 表达 Alpha**（semver 下 0.x 即「一切可变，minor 也可能破坏」，无需额外承诺页）；起始号 **`0.1.0`**（全新起号，不取 0.2.12 对应式）。落地：本周期四件套已切 `0.1.0.dev0`，TestPyPI 迭代 `0.1.0.devN`，final tag `v0.1.0`，周期/计划目录更名 `0.1.0-dev-plans`（历史分支名保留不改）。
- **裁决理由**（用户）：0.x 是比「2.x + 契约页」更强的 Alpha 信号——公开 PyPI 首发期不该向用户暗示稳定。
- **与指南的出入**：pypi-release-guide.md §2 D-3 推荐「维持 2.x + 契约页」，其论据（四渠道存量用户跨 major 代价）经验证不成立于 pip 渠道（aisc-cli 全新分发名，无 pip 存量）；NSIS/便携为覆盖安装不比版本号；tauri.conf 版本随四件套同动无兼容负担。指南原文不改（分析快照），以本条为准。
- **连带**：`compatible_cli_versions` 首版精确匹配维持（指南 D-3 中与版本号无关的部分仍有效）；A8 的「semver 承诺页」改为「0.x Alpha 声明 + 升 1.x 的门槛说明」。


## D-5 · PyPI 长描述【拟裁，R3 范围内；指南 D-4——随 A8 文档批请用户确认】
readme 面向 PyPI 去掉「推荐服务」返佣小节（README.md:330-363）；相对链接 :10/:328 改绝对 URL；description 语言一致性首发时确认。详见指南 §2 D-4。

## D-6 · sdist 不含 tests【已裁决，2026-09-16 A1 开工确认；指南 D-5】
v1 维持最小 sdist；下游验证走 GitHub Release SBOM 与源码 tag；若将来要含，配 MANIFEST.in 并记新 ADR。

## D-7 · `aisc update` = sidecar 热换编排【已裁决，R4】

- **裁决**：新增 `aisc update`（含 `--check`）：按版本从 Releases 拉 release archive → API digest + sha256 校验 → 按安装形态原子替换 exe/bundle。Workbench 侧编排 = drain_pool → Windows rename dance（aisc.exe 改名 aisc.exe.old-时间戳，运行中 exe 可改名不可覆盖删除）→ 写入新文件 → 下一条命令由既有 mtime 驱逐自动 respawn（免重启 Workbench）。standalone（便携/bundle）形态替换后提示 `maintenance docker-rebuild`，`--rebuild` 直接执行（对齐 install.sh 升级链语义）。
- **证据**：workbench/src-tauri/src/serve.rs:584-598（drain_pool 关停全部池会话）、:610-647（pooled_local_session 注释：rebuilt sidecar evicts + respawns automatically）；DEVELOP_WIKI.md:90 + devlog r8（运行中 aisc.exe 锁文件、build-cli 检测拒绝构建）；packaging/install.sh:18-21,278-321（升级生命周期先例 scan→cleanup→替换→rebuild）；installer.nsi:1636-1638（安装器同链）。
- **理由**：「热」的本质上限=免重启换 CLI（本地池 mtime 驱逐机制已就绪）；与 A3 fetch 共用同一「下载+校验+原子安装」底座（指南 3.3.3 要求 safe-extract/verify 迁入 src/aisc，两任务共享此前置）；信任模型对齐 fetch（API digest、fail-closed、--from-file 离线注入）。
- **回滚/边界**：新命令独立可 revert；.old 残留由下次 update 或启动清扫；远程机器自动同步显式出周期（D-18）。注意：bundle 属全量替换面（连带其内 config/versions.env）——工具 pin 的存续语义由 D-27 定义（pin 落数据根用户层，不在替换面内）。

## D-8 · Workbench 自更新选型：自研轻量，不用 Tauri updater【拟裁（推荐），R4——A7 开工前请用户确认】

- **裁决（推荐）**：不引 tauri-plugin-updater。自研：Rust 侧查 GitHub Releases 最新 final（reqwest+系统代理，复用 subscription.rs:5-22,127-133 模式）→ 对比四件套版本 → 下载 NSIS setup.exe + sha256 校验 → 用户确认后退出应用并静默执行安装器，安装器自带完整升级链（PATH 接管 installer.nsi:801-811、maintenance docker-scan/cleanup/rebuild --context upgrade installer.nsi:1542-1638、S4.2 升级冒烟）。标准体验=「检查更新→下载→重启完成」；真热替换（不重启换 Workbench 本体）明确不做。
- **证据**：零 updater 底座（workbench/src-tauri/Cargo.toml:21、tauri.conf.json:25-57、capabilities/default.json:9-22、artifact.yml 无 updater 痕迹）；现行发布资产仅 NSIS+sha256 两件（gh release view v2.1.11-dev）；installer.nsi:767-780 唯一 updater 字样是 WebView2 修复，与自更新无关。
- **理由**：Tauri updater 需新建 minisign 密钥对（谁持有/存哪是新问题）+ CI 签名链 + latest.json 产物，且它直接换文件会**绕过 NSIS 安装器内嵌的 Docker 生命周期**——与两条既有安装渠道行为分叉（侦察约束：任何 Workbench 内更新若不走同一 Docker 生命周期即分叉）。自研复用安装器既有升级语义与 aisc update 的 Releases 检查/校验代码，零新信任根（sha256 sidecar 已在产）。
- **回滚/边界**：首版仅 Windows NSIS 渠道（对外产物本就仅 Windows 安装器，docs/releases/v2.1.11.dev0.md:3）；日后需要 macOS/Linux 自更新再评估 Tauri updater。回滚=移除菜单项与 Rust 命令，安装器执行链本就存在零风险。注意 A9 起 final Release 的资产底座由 artifact.yml 自动产出（三平台档案+setup），NSIS setup 仍为补附资产——A7 下载源按补附后的资产名单核对，不依赖「Release 仅 NSIS 两件」的旧现状。

## D-9 · 工具更新合一入口 + versions.env 单事实源【已裁决，R5】

- **裁决**：`aisc update --check` 一次报 CLI + claude/codex/cc-switch 可用版本（npm registry 元数据 + GitHub resolver 复用）；工具更新 = pin 写入**数据根用户层** `<data-root>/config/versions.env`（覆盖语义与 update/fetch 交互见 D-27；解析 root 内 versions.env 一律降为出厂默认、只读）+ 镜像重建引导/执行；BuildPlan 转发 CLAUDE_CODE_VERSION/CODEX_VERSION 等 build args，versions.env 从「声明」升为「被消费」（消费解析序 = 出厂默认为底、用户层按键覆盖，D-27）；cc-switch 三处漂移本周期修齐。**不做**容器内原地 npm 更新（镜像唯一事实源，wrapper 拦截结构会被踩踏）；**不做**自动停运行中容器（重建提示制）。
- **证据**：src/aisc/cli/commands/build.py:44-59 与 src/aisc/domain/models.py:346-360（BuildPlan 只转发 USE_CN_MIRROR/NODE_IMAGE*/CC_SWITCH_*，CLAUDE/CODEX 版本声明零消费方）；config/versions.env:16,19（latest+TODO）、:32（v5.9.0）vs container/Dockerfile:34（v5.10.4）vs config/cc-switch-manifest.json:4（v5.10.1）三处漂移；container/Dockerfile:303-310（wrapper 拦截：/usr/local/bin/claude 是 wrapper 真身 claude-real）；docs/devlog.md:2256-2272（r4 事故：漂移致静默降级、db 不可读、provider 行丢失）；src/aisc/application/cc_switch_resolver.py:114-185（解析链复用底座）；installer.nsi:1636-1638（已安装用户重建发生在安装目录 aisc-bundle 副本上——副本属可替换面，pin 不能写它，见 D-27）。
- **理由**：NSIS 升级链已是「CLI 更新+镜像重建」耦合先例；合一入口即 todo:183 自带问号的答案（能合并，合并为一个检查入口、两类执行动作）。
- **回滚/边界**：版本更新单向门禁（防降级，r4 教训）；docker-rebuild 的 cc-switch 钉版偏缓存（可复现导向）语义保持不变；匿名 GitHub API 60 req/h + TTL 600s（cc_switch_resolver.py:52）——「定期」首版为手动触发，自动轮询归 D-22。Dockerfile:34 改动属 vendor 校验面（vendor/checksums.txt:1），修齐提交必过 vendor-refresh/vendor-verify（DEVELOP_WIKI §6.4）。

## D-10 · node:20→22 基底升级处置【拟裁，R5 顺带】

- **裁决（推荐）**：评估门制——仅当 claude-code 新版实际触发 EBADENGINE 或 `--check` 报告的新版本要求 node>=22 时，才把 NODE_IMAGE 升 node:22-slim；升级前必须验证三条 NODE_IMAGE_MIRRORS 前缀对 node:22 可达；升级走一次完整镜像构建冒烟 + vendor 门禁。结论写入 A5 交付文档。
- **证据**：config/versions.env:7,13（node:20-slim、DIGEST 空）；docs/archive/2.1.9-dev-plans/decisions.md:241-243（claude-code 2.1.251 要求 node>=22，EBADENGINE 已现）。
- **理由**：基底升级是独立变更，捆绑进 A5 会扩大爆炸半径；评估先行可控。回滚：NODE_IMAGE 单变量回退 + 重建。

## D-11 ·「docker 管理的简易映射」= Docker 资源管理简化 UI【已裁决，R1】

- **裁决**：释义=**C（docker 资源管理的简易管理界面）**——把 maintenance docker-scan/docker-cleanup/cache-usage/cache-cleanup 产品化为 Workbench 用户可见界面（并入设置页「磁盘与缓存」卡片扩展，O7 先例）。释义 A（用户自助端口映射）/B（远程转发简化）/D（「镜像」笔误）否决：svc 网关体系、冻结契约与回环安全边界全部不动。maintenance CLI 组契约**零改动**（installer-facing 边界），UI 走同一 application 层实现避免行为分叉。P0。
- **证据**：docs/todo.md:174（词条全仓唯一出现、零展开）；src/aisc/cli/main.py:484-525（maintenance 组 help=Installer-facing Docker lifecycle ops）；docs/devlog.md:590-595（O7 设置页磁盘与缓存组先例）；src/aisc/application/docker_lifecycle.py:302-358,428-513（scan/cleanup/rebuild 应用层）；src/aisc/domain/web_services.py:50（回环 only 安全契约，本链不触碰）。
- **理由**：用户裁决 R1；maintenance 既有 CLI 契约被两条安装渠道依赖（installer.nsi:1542-1638、install.sh:278-321），产品化只能加用户面不能改既有面。
- **回滚/边界**：UI 卡片整组可 revert；不动 web_services 三语言冻结契约与 runtimeServices 能力协商。

## D-12 · 重建按钮范围与 BUILD_TIMEOUT 顺带修【拟裁（形态按用户裁决框架细化），B 链】

- **裁决**：BuildProgress failed + cancelled 终态加「重新构建」按钮，复用 store.startBuild 不另起 IPC；摘要页 imageNotFound「构建镜像」按钮即既有快捷重试入口，维持现状；重试 tag=store.buildTag（本次失败的 tag）；按钮自持 disabled=building（组件级守卫）；BUILD_TIMEOUT 600s→1800s 并校正「初次构建 10-20 分钟」文案矛盾。v1 **不做**失败结构化错误码（网络拉镜像失败 vs Dockerfile 错同码维持，避免动 docs/rfc/aisc-cli-v1.md 三模式测试），**不做** docker 恢复自动重试（仅手动按钮）。
- **证据**：workbench/src/features/startup/BuildProgress.vue:133-141（终态按钮现状仅「启动 Docker」/「返回摘要」）；workspaceRuntime.ts:356-414（startBuild 契约 A-G14：终态只能 Promise settle 写入）+:279-281（buildOpId supersede）；workbench/src-tauri/src/runtime.rs:35（BUILD_TIMEOUT=600s）vs workbench/src/i18n/zh-CN.ts:167（durationHint「通常需要 10-20 分钟」）+ cli.rs:1060-1070（超时 sigint_or_kill 后呈已取消）；error.rs:20-27,271-282（action=BuildImage 枚举可复用）。
- **理由**：零协议成本路径；600s < 文案下限 10min 是硬矛盾（超时初建被杀呈已取消，用户会反复点重试）。
- **回滚**：纯前端 + 一个 Rust 常量，revert 零风险。

## D-13 · provider 模板化：先调研后定【已裁决，R6】

- **裁决**：调研先行（验证清单见 c-research.md C1），出结论文档后用户单独裁实施；结论文档出来前不写实施代码。P1。
- **证据**：上游非交互 CLI ProviderAddTemplate 枚举 14 值（上游 provider_input.rs）vs container/lib/cc_switch_preset_providers.py:199-297（AISC 自有 5 preset 与上游清单几乎不相交）；container/entrypoint.sh:480-509,511-532,581-584（preset 模块三调用点，reconcile/official-seeding/proxy 对账等 must-keep 职责与预配置耦合同文件，不能一刀切删除）。
- **边界**：调研不附带实施承诺；cc-switch 三处版本漂移修齐不等调研（归 D-9/A5）。

## D-14 · codex computer use 调研形态【已裁决，R7】

- **裁决**：r0 表单单文件调研文档（状态头/编号调研问题/对比表/工程要点提炼/AISC 对照，先例 docs/archive/2.1.10-dev-plans/r0-vscode-remote-and-hpc.md:1-6）；内容=原理 + 容器落地三路线对比（容器加显示栈 X11/Xvfb/VNC vs headless 浏览器 vs 宿主侧截图/视觉通道）+ 必含安全影响章节（对齐 DEVELOP_WIKI §12.1：容器 root + codex 默认 --dangerously-bypass-approvals-and-sandbox 红线，container/codex-wrapper:33-52）。允许联网检索官方文档/开源实现；结论标注 codex 版本基线（latest 未钉，config/versions.env:19）。以 codex 为主，Anthropic 侧仅引 vendored claude-api skill 的 computer use 章节作对照（tool-use-concepts.md:278-284）。不附带实施承诺。P1。

## D-15 · 优先级与排期【已裁决，R8】

P0 = A 链全部 + B 链全部（cli update+自更新、pip 首发链、Docker 资源管理 UI、重建按钮）；P1（视余力）= C 链两条调研。执行序：P0 先行；B 链与 A1-A3 无耦合可交错；A4 起依赖 A3；C 链任何时点可插入（纯文档）。

## D-16 · 工作树存量处置与 todo [x] 回填【拟裁，P0 执行】

- **裁决（推荐）**：约 10 个未提交文件分四批提交（docs / scripts+gitignore / workbench UI / tests），每批过对应 local-gates 门；仓库根游离 containers.json（空 registry）判定为运行时 CWD 泄漏——删除并加入 .gitignore；todo.md 四条 [x] 翻改逐条核对：已交付者（doctor aisc-root 限定、picker 窄窗、热切换显示层——均在 2.1.11 P2/P3 轮内交付）保留 [x] 并补交付指针；「远程 CLI 版本配对与更新」实际只交付协议硬门+banner 记录（src/aisc/cli/commands/serve.py:48-53；serve.rs:12-13「cli_version recorded for display, serve_protocol is the hard gate」），主动提示/自动同步未交付——回退 [ ] 并注「由 V0.1.0-target A 链承接」。
- **证据**：git status（约 10 文件）；git diff docs/todo.md:163-183（四条 [x] 翻转与 V0.1.0-target 段均为未提交新增）；v2.1.11-dev tag 后 develop 仅 4 个 docs 提交。
- **回滚**：纯 git/docs 操作，分批可逐一 revert。

## D-17 · 更新通道策略：final-only【拟裁】

检查更新默认只跟 final（dot tag Release）；无 final 可更时报「已是最新」；prerelease 通道开关（--pre）留 v2；TestPyPI 只服务 dev 迭代不进检查入口。证据：git tag（v2.1.4 后无 final）+ 指南 4.2（无 final 时裸 pip 装上 prerelease 的风险）。理由：R2 后 0.1.0 final 即存在，final-only 上线即有物可更。

## D-18 · `aisc update` 渠道边界与远程拆批【拟裁】

首版面向 frozen/bundle 形态（便携包、Workbench sidecar、安装器安装的 aisc-bundle）；pip 渠道输出 `pipx upgrade aisc-cli` 指引不自替换（其工具 pin 落数据根用户层、与 fetch/pipx 生命周期解耦，D-27）；install.sh 渠道输出重跑 install.sh 指引（其对 pipx shim 的归属判定修补在 A8，指南 3.5.5）。远程机器自动同步**显式出周期**：需 SSH 文件传输+远端重装编排，是独立大块（2.1.11 只交付协议门+banner，远程池无 mtime 守卫 serve.rs:560-577；更新靠手工 rsync 已两次踩坑）——记 backlog 不排期。

## D-19 · 发版分支流与 main 同步【拟裁】

v0.1.0 final tag 打 develop 封版提交（沿 2026-08 以来惯例）；A6 落地 pypi-publish.yml 时做一次 develop→main 同步合并（pending publisher 要求 workflow 先存在于默认分支，指南 5 阶段 0）；DEVELOP_WIKI §11.1/§11.2/§1 的过期描述随 A8 改写：认可 develop-tag 惯例 + 补 PyPI 步骤 + 六 workflow 清单。证据：git log -1 main = 81f1940（2026-08-06 起冻结）；git branch --contains（v2.1.5-dev 后 dev tag 全仅在 develop）；DEVELOP_WIKI.md:715-742 vs 实际。回滚：main 同步是快进性质合并，可重做。devN tag（D-26）同打 develop 提交，不改变本裁决。

## D-20 · 收口卫生三件【拟裁，P0/A8 执行】

①docs/archive/2.1.11-dev-plans/README.md:11,14 两行陈旧「待做」（P2 UI 批/收口）回填为已交付——证据 docs/devlog.md:109-117（P2-1..5 交付）与 :138-146（封版）；②docs/plans/README.md:10-12「Current active plan」改指 0.1.0-dev-plans（现仍指已搬走的 2.1.10）；③DEVELOP_WIKI §11 发版流程描述校正归 A8（指南 3.5.3）。另：devlog 补记 v2.1.11-dev tag/Release 发布条目（2.1.9 有专门发布条目先例 devlog:2349-2359，2.1.11 封版条目漏记 tag/Release）。

## D-21 · todo:72 旧项关闭【拟裁】

「aisc cli 的更新命令优化」（20260806 段，docs/todo.md:72）无任何 devlog 实施记录、语义不可考，由 V0.1.0 cli update 取代——勾掉并注「由 V0.1.0-target 吸收」。

## D-22 · 检查更新执行者与节流【待裁决】

v1 推荐=仅手动触发（命令/设置页按钮），复用 resolver TTL 缓存与离线 receipt 回退；Workbench 后台定期轮询（含启动时轻提示）要不要做、频率多少，待用户裁。约束：匿名 GitHub API 60 req/h（cc_switch_resolver.py:52）+ npm registry 元数据接口限额。不阻塞 A1-A5 开工，阻塞 A7 的「定期」语义定型。

## D-23 · 运行中容器镜像陈旧提示【待裁决】

devlog:563 backlog（启动时比对 image id 提示重建）是否并入本周期。不做它则「工具更新」闭环缺一环：镜像重建了但运行中/keep-alive 容器仍旧镜像（entrypoint .factory-version 增量同步仅启动时生效；2.1.9 有实际事故 devlog:560-562）。建议随 B3 Docker UI 或 A5 收尾时用户拍板。

## D-24 · 赞助商返佣模板处置【待裁决，随 C 链】

cc-switch 内置 8 个赞助商模板自带返佣注册链接与 promo code（上游 provider_templates.rs）；AISC 是否原样引入、与 README 推荐服务区（Codesome）的关系，随 C1 调研结论一起裁。

## D-25 · 中段 dev 预览 Release【拟裁（随 D-26 于 A6 开工前拍板）】

- **裁决（推荐）**：做，且机制不再是「额外打一次 tag」而是**复用 A6 迭代已存在的 `v0.1.0.devN` tag，dispatch artifact.yml 选该 tag ref**——aggregate/release job 仅在 tag ref 运行（artifact.yml:261,341），release job 自动建 prerelease Release 并附全量资产（`AISC-<devN>-<plat>-<arch>` 档案 + 各 .sha256 + SHA256SUMS + setup/pkg），body 取 `docs/releases/v0.1.0.devN.md`（devN 四件套 bump 已保证该文件存在，artifact.yml:359）。时点：A7 端到端真实验证需要时（或 A6 首轮全链验证时）执行一次；`--from-file` 离线注入保留为无 Release 时的冒烟路径。
- **理由**：D-26 使 devN tag 成为 TestPyPI 迭代例行副产物，预览 Release 只多一次 dispatch；update/fetch 的端到端真链路必须命中真实 Release 资产（指南 3.3.3：按精确版本匹配资产，dev 无资产即 fail-closed），构造假 Release 覆盖不了资产名/digest/Release 元数据面。
- **边界**：dev 预览 Release 是 prerelease，不进 D-17 final-only 检查入口；dispatch artifact.yml 有三平台 CI 成本，按需一次而非每个 devN 都跑。

## D-26 · TestPyPI dev 迭代的 tag 前置链【拟裁（A6 开工前拍板）】

- **问题**：指南 3.4.1 的 pypi-publish.yml 为 workflow_dispatch-only、输入是**已存在的 v\* tag**、job checkout 该 ref 构建，guard 要求 `v$(cat VERSION)`==tag（指南 3.4.2）——因此 TestPyPI 每次上传都必须先有指向「VERSION 已 bump 提交」的 dot tag。P0 的四件套 bump 只是必要条件之一，tag 才是 dispatch 的直接输入；无此安排，A6 按原排程会在 dispatch 第一步卡住（无 tag 可选）。
- **裁决（推荐，方案 a）**：每次 TestPyPI 迭代 = 四件套 bump `0.1.0.devN`（①VERSION ②tauri.conf.json `0.1.0-devN`——dash 语义保留，PEP 440 归一化后与 `0.1.0.devN` 相等，check-version-sync 兜底 ③envelope-version.json 三字段 ④`docs/releases/v0.1.0.devN.md` 占位——test_release_notes.py:20-27 既有门）→ 提交 → 推送 dot tag `v0.1.0.devN`（打在当时 develop HEAD）→ dispatch pypi-publish 选该 tag（dev 版被 publish-pypi 的 final regex 门挡住，只走 testpyi 段）。首个 dev0 直接复用 P0 bump，tag 随 A6 首次上传推送。D-25 的中段预览 Release 由此成为 A6 迭代的自然副产物。
- **备选（方案 b，不推荐）**：修订 workflow 设计——testpypi 段允许 dispatch 于 develop ref、guard 只查该 ref 的 VERSION 合法性，正式 PyPI 段维持 tag-input，并同步回写指南 3.4.1。代价：刚定稿的流水线设计二次改动 + develop 直发削弱「tag 即发布单元」的 provenance；除非用户嫌 devN tag 噪音，否则不取。
- **边界**：devN tag 推送不触发任何 workflow（artifact.yml dispatch-only；nsis-installer.yml 的 push 触发 branches 限 develop/main，tests.yml 同理），tag 本身零副作用；devN bump 与 A 链开发提交交错时四件套必须同步（不同步会被 check-version-sync 与 test_release_notes 拦）。

## D-27 · 工具 pin 权威位置与 update 覆盖语义【已裁决，2026-09-16 A5 开工审问——采纳推荐 A】

- **问题**：若把工具 pin 写进「解析 root」的 config/versions.env，则 D-7 的 `aisc update` 全量替换 bundle、NSIS 升级替换安装目录 aisc-bundle 副本（installer.nsi:1636-1638）、pip 形态 fetch 换 `bundles/<ver>/` 目录（同版本幂等 no-op、版本升级换新目录，指南 3.3.3）——用户手动 bump 的 pin 每次更新即被出厂默认**静默覆盖**，该交互是否预期此前未定义；且 pip 形态的 root 由 fetch 生命周期管理，「工具更新」动作实际无落地路径。recon2 开放问题（fetch 新 bundle→docker-rebuild 成为第三个更新锚点、避免双份 bundle 来源漂移）需一并吸收。
- **裁决（推荐）**：pin 权威位置 = **数据根用户层 `<data-root>/config/versions.env`**（`shared_root()` 解析，data_root.py:249-256；`AISC_DATA_ROOT` 旋钮沿用；与指南 3.3.1 的 `bundles/` 同根）。所有安装形态统一：解析 root（repo 检出 / 安装目录 aisc-bundle 副本 / pip `bundles/<ver>/`）内 config/versions.env 一律为出厂默认、只读；消费解析序 = 出厂默认为底、用户层**按键覆盖**（只覆盖用户 bump 过的键，保留 versions.env 注释可读性）。`aisc update` / NSIS 升级 / bundle fetch 的替换面均不含数据根用户层——pin 恒不丢；update 完成输出与 `--check` 联动报告工具 pin 现值与来源（user/default），用户层为空时行为=现状。
- **理由**：第三个更新锚点（fetch→rebuild）的漂移在结构上消除——出厂默认随新 bundle 走、用户 pin 恒在用户层；r4 事故教训（pin 被静默降级）不可再现；versions.env 消费链本周期才建立（D-9），day-one 定权威位置比事后回迁便宜。
- **裁决落地（2026-09-16）**：用户选 A（通俗版：偏好与软件本体分开存，更新不覆盖偏好）。实现为 `tool_versions.py`（effective_tool_versions 双层解析 + write_user_pins 注释保留原子写 + PINNABLE_TOOL_KEYS=CLAUDE_CODE_VERSION/CODEX_VERSION/CC_SWITCH_VERSION；NODE_IMAGE 留出厂层——CN 镜像链与其配对，裸覆盖会失配）。CLI 面：`aisc update --pin-tool KEY=VALUE`（可重复）与 `--check` 的 tools 区（现值+来源 user/default+最新版，registry 失败降级 null）。
- **备选（若用户否决用户层）**：v1 维持写解析 root + 显式定义「update 后 pin 重置为出厂默认」并在 `--check` 报告——代价：用户 pin 每次更新即丢、pip 形态无路径，不推荐。
- **回滚**：用户层纯增量（不存在即回退现状）；按键覆盖为纯函数可单测。
