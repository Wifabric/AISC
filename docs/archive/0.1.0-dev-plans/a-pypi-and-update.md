# A 链——pip 首发 × 自更新（aisc update / 工具更新入口 / Workbench 自更新）

> 状态：待做。P0。骨架 = pypi-release-guide.md（同目录） 五批次（§3.1-3.5），本文不复抄其清单，按小节号引用，并在其上叠加 cli update、工具更新合一入口、Workbench 自更新三块与收口发布。A1→A9 即依赖序（B 链可与 A1-A3 并行；A4 起依赖 A3；A5 内含 D-27 拍板点；A6 内含 D-26/D-25 拍板点；A7 复用 A4 的检查基建；A6 依赖 A1-A3；A9 收口）。

## 范围（scope）

- **in**：指南批次一~五全部；`aisc bundle fetch` 底座（A3）；`aisc update` sidecar 热换编排（A4）；工具更新合一入口 + versions.env 事实源（A5）；pypi-publish 流水线 + TestPyPI dev 迭代（含 devN tag 链，A6）；Workbench 自更新（A7）；文档与渠道治理（A8）；0.1.0 final + PyPI 收口发布（Release 全量资产，A9）。
- **out**（显式排除）：远程机器自动同步（D-18）；prerelease 通道/--pre（D-17）；CN 镜像 fetch（指南附录 B 留 v2）；rc 上 PyPI；路线 B 载荷入 wheel（D-3 否决）。

## 契约（contracts）

- 分发名 aisc-cli / import 包与 script 名保持 `aisc`（D-2；指南 D-1 注意不要改过头：python -m aisc 与 aisc.exe 不动）。
- VERSION 唯一版本事实源；A2 后位于 `src/aisc/VERSION`（指南 3.2）。
- 资源解析链六级：data-root 层级插在 cwd-repo 之后、包祖先之前；frozen/_MEIPASS 分支原样保留（指南 3.3.1）。
- bundle fetch 信任模型：GitHub API digest 校验 + fail-closed + 三条手动逃生路 + --from-file（指南 3.3.3）；aisc update 对齐同一标准（D-7）；fetch/update 的数据源 = Release 上 `AISC-<ver>-<plat>-<arch>` 档案资产——**Release 必须先有全量档案**，这是 A9 收口顺序的硬约束（tag→dispatch artifact.yml→pypi-publish）。
- PyPI 纪律：正式 PyPI 只发 final X.Y.Z（regex 门）；dev 只上 TestPyPI 且逐次 bump .devN，**每次上传前先推 dot tag `v0.1.0.devN`**（pypi-publish 的 dispatch 输入即已存在 tag，guard 要求 `v$(cat VERSION)`==tag，D-26）；publish 仅 workflow_dispatch 不挂 tag 自动触发（CLI-D08）（指南 3.4.1/3.4.2）。
- 工具 pin 权威位置 = 数据根用户层 `<data-root>/config/versions.env`，解析 root 内 versions.env 为出厂默认只读、消费时按键覆盖（D-27，A5 开工前拍板）。
- 新增 CLI 命令规约：main.py 注册 + commands/ 编排 + application 业务 + text/JSON envelope/exit code 同步 + unittest + README CLI 表（DEVELOP_WIKI §6.1）；--events 仅属 build/run——update 不做事件流。
- 降级契约分档（28 动词：不可用/降级/完全可用）固化契约测试，不改代码（指南 3.3.4）。

## 实施顺序（每步附验收）

### A1 包元数据（指南 3.1 + D-2 改名）
内容：name=aisc-cli；license 改 SPDX 字符串 + license-files + 删 MIT classifier + setuptools>=77；deps 加 requests>=2.26、docker>=7.1,<8；删 3.14 classifier；`__init__.py:35` metadata.version 改查 aisc-cli 及四处脚本字面量（verify-cli-install.py:86,137；verify-sbom.py:31,76）。README 对外语口径延后 A8。
验收：`python -m build` 零 license 弃用告警；`python scripts/verify-cli-install.py` 全腿（wheel+sdist+pipx）；local-gates 第一门。

### A2 VERSION 迁移为 package-data（指南 3.2，约 14 触点）
内容：`git mv VERSION src/aisc/VERSION` + pyproject 改 package-data；触点表照指南 3.2 逐项（packaging/aisc.spec:22；artifact.yml:48,51,54,97,136；packaging/artifact.py:41-42,771,776；resources.py:27 _STRUCTURE_MARKERS；__init__.py:20-21；tests/test_version_source.py:20,31,34-36 必红改断言；verify-cli-install.py:192；build-cli.ps1:71；tests/packaging/test_release_notes.py:21；DEVELOP_WIKI §8.4 版本契约段）。
验收：`python -m pytest tests/packaging/ tests/test_version_source.py -q`；`python scripts/verify-cli-install.py`；手测 `python -m build --sdist` 后 `tar -tzf dist/*.tar.gz | grep 'src/aisc/VERSION'` 命中；local-gates；重建 sidecar 后 `aisc version` 正常。

### A3 `aisc bundle` fetch 底座（指南 3.3）
内容：safe-extract/verify 迁 `src/aisc/application/bundle_fetch.py`（packaging/artifact.py 改 thin wrapper 保留原符号 _write_manifest/verify_staged_bundle/safe_extract_archive）；解析链六级 + `bundle_compatible` 运行时校验（3.3.1/3.3.2）；`aisc bundle fetch/list/remove/path`（3.3.3：流式下载、原子安装 tmp+rename、幂等 no-op、.tmp-* 清扫、--from-file、--version/--allow-mismatch 逃生门）；降级文案（build root=None 分流 + doctor 独立 aisc-bundle CheckResult，3.3.4）。
验收：fake-transport 单测矩阵（离线/限流/损坏档案/digest 不符/manifest 不含本版本）；off-checkout 手测：临时目录内 `unset AISC_ROOT && aisc version --format json` exit 0 且 bundle_version=null；`aisc build` exit 1 且文案含 `aisc bundle fetch`；用 `python packaging/artifact.py` stage+archive 现场生成档案后 `aisc bundle fetch --from-file <archive>` 成功且 `aisc build --dry-run` 通过；local-gates。

### A4 `aisc update`（D-7）
内容：`aisc update [--check] [--from-file <archive>] [--version <ver>] [--rebuild]`。--check 报 CLI 当前/最新（Releases，final-only D-17）；执行 = 拉档案→校验→按安装形态替换：①Workbench bundle/sidecar 目录：Rust 侧编排 drain_pool（serve.rs:584-598）→ rename dance（aisc.exe→aisc.exe.old-<ts>）→ 写入新 exe/bundle → 池 mtime 驱逐自动 respawn（serve.rs:610-647）；②便携/frozen 根：staged replacement（同 install.sh:278-321 语义）后提示 `maintenance docker-rebuild`，--rebuild 直接执行；③pip 形态：输出 pipx upgrade 指引（D-18）。替换面均不含数据根用户层——工具 pin 不随 update 重置（D-27）。text/JSON envelope/exit code + README CLI 表 + unittest（DEVELOP_WIKI §6.1）。
验收：单测（版本比较、形态探测、替换计划 dry-run、防降级门）；手测三条：(a) tauri dev 下旧 sidecar → update → 不重启 Workbench，下一条命令 `aisc version` 已是新版本；(b) 便携目录 update 后 bundle 完整性校验通过、旧 exe 以 .old 保留可回退；(c) --from-file 离线路径全通。

### A5 工具更新合一入口（D-9/D-10/D-27；D-27 开工前拍板）
内容：BuildPlan/_BuildEnv 转发 CLAUDE_CODE_VERSION/CODEX_VERSION/NODE_IMAGE（build.py:44-59、models.py:346-360），versions.env 消费解析序 = 解析 root 出厂默认为底、数据根用户层 `<data-root>/config/versions.env` 按键覆盖（D-27）；`aisc update --check` 扩展报 claude/codex（npm registry 元数据）+ cc-switch（resolver 复用）可用版本，并标注工具 pin 现值来源（user/default）；工具更新动作 = pin 写数据根用户层（所有安装形态统一；解析 root 含安装目录 aisc-bundle 副本与 pip `bundles/<ver>/` 一律只读）+ 重建引导/执行；cc-switch 三处漂移修齐（versions.env:32 / Dockerfile:34 / cc-switch-manifest.json:4 以 live resolver 结果统一）——**Dockerfile 改动属 vendor 校验面（vendor/checksums.txt:1 即 container/Dockerfile），提交前必跑 `bash tools/vendor-refresh.sh && bash tools/vendor-verify.sh`（DEVELOP_WIKI §6.4；local-gates 对 container/ 仅提示不阻断，scripts/local-gates.ps1:77-80，勿依赖其兜底）**；node:22 评估（D-10）出结论文档段落。
验收：单测 build args 转发（text/json 双格式）+ 用户层覆盖解析（按键覆盖出厂默认、用户层缺失时回退现状）；手测：`aisc update --check` 一次输出 CLI+三工具版本对照（含 pin 来源标注）；改 pin（写用户层）后 `aisc build --dry-run` 的 argv 含新 build args；`aisc maintenance docker-rebuild` 用覆盖后 pin 构建成功；A4 到位后 `aisc update` 执行 → 数据根用户层 pin 原样保留且 `--check` 报告未重置（D-27 交互）；pip 形态（pipx 安装 + `aisc bundle fetch`）下 pin 写用户层、fetch 新版本 bundle 后 pin 不丢；cc-switch 修齐提交含刷新后 vendor/checksums.txt——`bash tools/vendor-refresh.sh && bash tools/vendor-verify.sh` 为**无条件必跑项**（不挂 node:22 条件）；若 node:22 升级：另做三条 NODE_IMAGE_MIRRORS 前缀手测拉取 + 完整构建冒烟（vendor 门禁上条已含）。

### A6 发布流水线（指南 3.4）+ TestPyPI dev 迭代（D-26；D-26/D-25 开工前拍板）
内容：新增 `.github/workflows/pypi-publish.yml`（workflow_dispatch + OIDC Trusted Publishing + testpypi/pypi 两 environment（后者 Required reviewers）+ 版本门 regex + attestations 显式 true + gitleaks 制品终扫 + pip-audit + concurrency 串行，3.4.1）；两道 guard + check-version-sync（3.4.2，与修 README/tauri 版本字面量同一 PR）；off-checkout 冒烟固化 + verify-pypi-install.py + twine check 内建（3.4.3）；制品正负向断言（3.4.4）；TestPyPI dev 迭代纪律（D-26）：每次上传 = 四件套 bump `0.1.0.devN`（VERSION / tauri `0.1.0-devN` / envelope fixture / `v0.1.0.devN.md` 占位）→ 提交 → 推送 dot tag `v0.1.0.devN`（打当时 develop HEAD）→ dispatch pypi-publish 选该 tag（dev 被 final regex 门限在 testpypi 段）；首个 dev0 复用 P0 bump、tag 随首次上传推送；develop→main 同步一次 + TestPyPI/PyPI pending publisher 注册（D-19；指南 5 阶段 0：维护者开 2FA、repo+workflow 文件名+environment 名逐字匹配）。
验收：dispatch 前置核对：`v0.1.0.devN` tag 已推送且指向 VERSION==该 devN 的提交（guard `v$(cat VERSION)`==tag，指南 3.4.2）；TestPyPI 页面出现 aisc-cli 0.1.0.devN；`python scripts/verify-pypi-install.py --index-url https://test.pypi.org/simple ...` 通过（含 index 传播重试）；`python -m pytest tests/test_workflow_contract.py -q`；手测 dispatch 一次全链（build+guard→publish-testpypi→verify-testpypi）。

### A7 Workbench 自更新（D-8）
内容：Rust 侧 check_for_update（reqwest+系统代理，复用 subscription.rs:5-22 模式）对比 Releases 最新 final vs 四件套版本；UI：帮助菜单「检查更新」+ 设置页「关于」区（i18n zh-CN/en-US 同步）；下载进度 + sha256 校验 + 失败不落地；用户确认后退出应用并静默执行 NSIS 安装器（安装器自带 docker 生命周期与 PATH 接管）；sidecar 单独热更新入口 = A4 `aisc update`（不重启 Workbench）。
验收：`cargo test --lib` + `pnpm vitest run` + `pnpm vue-tsc --noEmit`；手测：以 D-25 中段 dev 预览 Release（dispatch artifact.yml 于某 devN tag 自动产出）或本地假 Release 走通 检查→下载→校验→确认→安装→重启 后版本变更、工作区数据与 Docker 资源无损、安装器升级链（scan/cleanup/rebuild）被执行。

### A8 文档与渠道治理（指南 3.5）
内容：README pip 小节（pipx 首选政策）+ 升级/卸载 SOP + 安装陷阱 FAQ 三行 + 资源根链尾补支 + 版本字面量与相对链接修（3.5.1）；恢复 docs/adr/ + 新写 ADR 002（三轨分发/六级解析链/依赖立场修订/路线 B 否决理由/fetch 信任模型/semver，3.5.2）；DEVELOP_WIKI §11.2 加 PyPI 步骤 5b 与 pre-tag gate、§11.1 六 workflow 清单、§1、§4.5 run argv 校正（3.5.3；侦察：§4.5 现状无 --publish 仍写 --rm -it，DEVELOP_WIKI.md:325-335——无论做不做端口映射都欠校正）；release notes 模板「安装与获取」节（3.5.4）；渠道共存代码小改：install.sh/uninstall.sh pipx shim 归属判定修补、doctor channel/platform-support 检查、version 输出 channel 行（3.5.5）。
验收：`bash tools/check-docs.sh`；`twine check dist/*`；README 推荐服务审计区修改前后逐字比较（DEVELOP_WIKI §13）；手测多 PATH 命中 aisc 时 doctor channel 检查 WARN。

### A9 收口发布（指南 5 阶段 2-4 + D-1/D-26；Release 全量资产）
内容：pre-tag gate（full unittest + check-docs + vendor-verify + artifact stage+verify + `git diff --check` + verify-cli-install 含 off-checkout + twine check + 版本一致性）；发布提交（VERSION→0.1.0 + 新增 `docs/releases/v0.1.0.md` 含「安装与获取」节，四件套同动——**notes 文件必须随 tag 提交在内**：artifact.yml release job 的 body_path 按标签名取此文件，artifact.yml:359）；annotated dot tag `v0.1.0` → 推送 → **dispatch artifact.yml（ref 选 v0.1.0 tag）**——tag push 不自动出产物（artifact.yml 仅 workflow_dispatch，:3-4；aggregate/release 仅 tag ref 运行，:261/:341）：三平台 build → aggregate 校验 SHA256SUMS → release job 自动建正式 Release 并附全量资产（`AISC-0.1.0-{linux-x86_64.tar.gz, windows-x86_64.zip, macos-arm64.tar.gz}` + 各 .sha256 + SHA256SUMS + Windows setup.exe/.sha256 + macOS pkg/.sha256，指南 §5 阶段 3、§7.1 Release 先行）→ Workbench NSIS lane 产物（`AISC.Workbench_0.1.0_x64-setup.exe` + sha256，nsis-installer.yml lane）在自动 Release 建好后手工补附（附加动作沿 v2.1.9-dev/v2.1.11-dev 先例，但 Release 底座改由 artifact.yml 自动创建——final 不再走「人工从头建仅 NSIS 两件的 prerelease 式 Release」旧链）→ dispatch pypi-publish 选 tag（TestPyPI 复验→pypi environment 人工审批→publish→verify-pypi；SBOM `aisc-sbom.json` 由该 workflow 附到同一 Release，指南 3.4.1）→ 发布后紧跟提交 bump `2.1.13.dev0` + plans 归档 + devlog 收口条目。
验收：`gh release view v0.1.0` 资产齐：**三平台 AISC-0.1.0-* 档案 + 各 .sha256 + SHA256SUMS + NSIS setup + SBOM**（artifact lane 自带的 Windows setup/pkg 资产随 release job 自动在列）；全新环境临时目录 `pipx install aisc-cli==0.1.0` 后 `aisc version` / `aisc doctor` / `aisc bundle fetch`（数据源即上列档案资产——与资产验收互证，指南 3.3.3 精确版本匹配）/ `aisc build --dry-run` 全通过；PyPI 项目页目检（README 渲染/链接/版本号/attestation/maintainers）。

## 风险

| 风险 | 证据 | 缓解 |
| --- | --- | --- |
| pip 包 root=None 致 build 致命失败（blocker） | resources.py:115-204；main.py:1114-1127 | A3 路线 C + off-checkout 冒烟作为发布 gate（指南 4.1） |
| 收口漏 dispatch artifact.yml 致 Release 无档案资产、fetch fail-closed | artifact.yml dispatch-only（:3-4）且 aggregate/release 仅 tag ref（:261/:341）；v2.1.9-dev/v2.1.11-dev Release 实测仅 NSIS+sha256 两件（gh release view） | A9 顺序固化：tag→dispatch artifact.yml→NSIS 补附→dispatch pypi-publish；验收清单含三平台档案 + SHA256SUMS，与 pipx+fetch 验收互证 |
| TestPyPI 迭代无 tag 可 dispatch（卡在流水线第一步） | 指南 3.4.1：dispatch 输入=已存在 v* tag + guard v$(cat VERSION)==tag（3.4.2） | D-26 devN tag 链：每次上传前四件套 bump + 推 dot tag；P0 不提前推 dev0 tag |
| 工具 pin 被 update/fetch 静默重置（pip 形态无落地路径） | D-7 全量替换 bundle；指南 3.3.3 fetch 同版本 no-op/升级换目录；r4 事故 devlog:2256-2272 | D-27：pin 落数据根用户层，替换面不含用户层；A5 验收含「update 后 pin 状态」手测 |
| 名称抢注窗口 | 指南 §2 D-1（2026-09-14 实测 aisc-cli 空闲） | A6 前尽早注册 pending publisher |
| tag/版本漂移毒化自动化（dev 误上 PyPI 不可撤回） | artifact.yml:359 body_path 仅 dot 匹配；指南 4.2 | 3.4.2 两道 guard + final-only 正则门 |
| clean-room 假覆盖（repo 内碰巧通过） | verify-cli-install.py:74-75 | off-checkout pass 固化契约 |
| Windows 文件锁致替换半途失败 | DEVELOP_WIKI.md:90；devlog r8 事故 | drain_pool 先行 + rename dance + .old 清扫 |
| NSIS 静默升级与运行中 Workbench 冲突 | installer.nsi（S4.2 升级冒烟存在） | A7 手测覆盖「运行中触发更新」路径 |
| 发布供应链（token/OIDC 滥用/workflow 篡改） | 指南 4.2 | Trusted Publishing 零 token + environment 审批 + job 级最小权限 + workflow contract 断言 |
| cc-switch 版本降级事故复发 | devlog:2256-2272（r4） | D-9 单向门禁；docker-rebuild 钉版偏缓存语义保持 |
| 带过期 vendor checksums 提交（A5 改 Dockerfile） | Dockerfile 属被校验文件（vendor/checksums.txt:1）；local-gates 对 container/ 仅提示不阻断（local-gates.ps1:77-80） | A5 验收把 vendor-refresh/vendor-verify 定为无条件必跑项（DEVELOP_WIKI §6.4） |
| node:22 国内镜像不可达 | versions.env:7,13 + NODE_IMAGE_MIRRORS 三前缀 | D-10 评估门 + 升级前三前缀预验 |
| GitHub API 限额（60 req/h） | cc_switch_resolver.py:52 | TTL 缓存 + 手动触发（D-22 裁决前不做后台轮播） |

## 决策引用

D-1~D-10、D-17~D-19、D-25~D-27（见 decisions.md）。

## 回滚（rollback）

A1/A2 各为单一提交可整体 revert（改名/迁移不产生存量数据）；A3 为纯新增命令 + 解析链插层，fail-closed 失败不影响既有五级解析与两条安装渠道；A4/A5 新命令 revert 即消失，无状态迁移（D-27 用户层为纯增量，删除即回退现状）；A6 workflow 为 dispatch-only，停用=不触发，TestPyPI 污染可忽略（dev 永不上正式 index），devN tag 留存无副作用（无 workflow 挂 tag push）；A7 UI 可整体移除（菜单项+Rust 命令），安装器执行链本就存在；A9 发布后事故按指南 §6：坏包可升级则发 X.Y.Z+1 hotfix + 旧版 yank（yank 非 撤回、精确 pin 仍可装回）；半发布状态（Release 已出、PyPI 失败）修 workflow 后 re-run，不重打 tag 不改版本号（Release 资产不全同理：re-run artifact.yml，tag 不动）；版本号一经上传永久烧录。若周期末未达发布质量：唯一不可逆动作（PyPI 正式上传）不执行即无痕回退，final tag 推迟，四件套回 dev 基线继续迭代。
