# 批 6：网络保底构建（反馈 #1 履约 + D-11 升级 + D-15 铁律）

> 状态：计划待用户验收（2026-09-23 立项；同日 D-11/D-15 升级为保底专项，
> 专项调研当日完成）
> 来源：反馈站 20260922-构建镜像时网络异常-匿名（D-1）+ 用户 D-11/D-15 裁决
> 方法：两轮 ultracode workflow——批 6 原始研究（研究员读两份构建日志 + 截图
> + 代码，双镜头核验）+ 保底专项（5 研究员：触点盘点 / 管线 bundle / 离线
> 机制 / 条件矩阵 / 体积核算，各配 evidence+feasibility 双核验 + 完备性批评；
> 16 agent 零阵亡，1.09M subagent token）。核验修正已全部并入（体积三处
> 纠错、GitHub 100MB 硬限、A/C 方案价值重估等）
> 对应 target：docs/todo.md「v2.1.14-target」网络保底构建条目

## 0. 设计铁律与保底语义（D-15，2026-09-23 用户裁定）

**构建与宿主网络完全解耦**：启动摘要页网络模式仅作用于运行期（容器 TUN
等），不影响宿主网络、也不得影响镜像构建。保底 = 构建自带全部所需物料，
不依赖宿主代理/TUN/网络模式。已核实 `--network direct|proxy` 为 run 期
旗标（main.py:167/657/675），build 链路不消费——现状已解耦。

**保底地板语义待用户终裁（U-9）**：专项研究证明「物理断网（air-gap）零
网络构建」存在两个结构性缺口（apt×2 无预置机制、新机基底镜像拉取），
按字面铁律不可达。二选一：
① **弱化地板 = 「GitHub 全阻/被墙 + 国内源（清华 apt、npmmirror、docker
镜像站）任一可达」可保底构建**——覆盖本项目全部实机死亡场景，零额外
体积（推荐，本版落地）；
② 真·零网：apt 闭包（.deb 全预置 +300-400MB）或 aisc-base 分层基底镜像
（烧进 apt 闭包，同时关掉 FROM 残余）——量级 L，另立项。

## 1. 构建期网络触点全矩阵（12 处，按断网死亡顺序链）

| # | 触点 | 位置 | 当前预置状态 | 断网/被墙形态 |
| --- | --- | --- | --- | --- |
| 1 | 基底镜像 FROM ${NODE_IMAGE} | Dockerfile:10（node:22-slim，无 digest 锁定，NODE_IMAGE_DIGEST 空键不消费） | 本地 store 命中即零网络 | 宿主预拉链三镜像（docker.1ms.run→daocloud→dockerproxy，versions.env:9-12）全灭 exit 4（build.py:303-345）；镜像 ~80MB，30KB/s 下需 44min，_PULL_TIMEOUT_S=600 必死 |
| 2 | apt 第一段（14 包） | Dockerfile:72-87（git/curl/tmux/iptables/neovim/ripgrep/zsh 三件套…） | **无任何预置机制** | 清华/官方源，3 次重试后 exit 1——容器内第一个死点 |
| 3 | mihomo 二进制 | Dockerfile:102-125 | ✅ 已预置（v1.19.27，glob 命中） | 未命中走 GitHub 5 镜像链+直连，max-time 120 |
| 4 | geodata 三件 | Dockerfile:128-146 | ✅ 已预置（逐名精确匹配） | 软失败仅警告不致死 |
| 5 | npm 四包（claude-code/codex） | Dockerfile:164-208 | ⚠️ **离线分支已存在**（四 glob + file: 清单 + npm install --offline，实测可用）但 downloads/ 无 tgz → 实际 100% 走在线 registry（npmmirror/npmjs，重试 ×2 + fetch-retries=5） | 硬失败 exit 1——死点② |
| 6 | claude 软触点 ×2 | Dockerfile:221（claude -p init，\|\| true）、274（plugin install 本地 marketplace） | 本地 | 软失败不致死 |
| 7 | apt 第二段（python3 四件） | Dockerfile:372-386 | **无预置机制**（刻意放 npm 层后保缓存） | 同 #2，exit 1 |
| 8 | pip 升级 | Dockerfile:413-421（清华/官方 pypi） | — | 软失败（\|\| echo 沿用内置）不致死 |
| 9 | cc-switch-cli | Dockerfile:433-491 三分支 | pinned 分支 ✅ 已预置 v5.10.5+sha256 强校验；**手动/降级分支 ❌ 漏配**——Dockerfile:440 字面拼 `cc-switch-cli-${CC_SWITCH_VERSION}-…`，ARG 默认 v5.10.4 vs 实存 v5.10.5 → 预置 miss → 静默转在线无校验下载 | 硬失败 exit 1 |
| 10 | **yazi**（两次实机死亡点） | Dockerfile:492-516 | ❌ **唯一无预置口的下载段**（恒在线：3 镜像+直连，max-time 60 全 Dockerfile 最短） | 硬失败 exit 1——实机 a1/a2 均死于此 |
| 11 | 宿主侧 resolver | cc_switch_resolver.py:50（api.github.com，15s） | cache→receipt→unpinned 三级降级（S8b）；config/cc-switch-manifest.json 离线 manifest **存在但不随 NSIS bundle 分发、默认链路不消费** | 降级为无 pin 构建（不致死，但触发 #9 漏配链） |
| 12 | GH_PROXY/镜像链 | Dockerfile:112/130/456/470（mihomo/geodata/cc-switch 有）/503（yazi **无**） | 镜像链四处漂移（5/4/3 站不统一）；GH_PROXY 仅手动 docker build 专用（src/ 与 workbench/ 零引用） | 加速通道，非兜底（D-15 定位） |

**ARG 登记表**：USE_CN_MIRROR（总开关，aisc build 从 versions.env 注入）、
NODE_IMAGE、MIHOMO_VERSION、GH_PROXY、CLAUDE_CODE_VERSION/CODEX_VERSION、
CC_SWITCH_VERSION（漂移源）+ resolver 六件套（models.py:345-379：aisc build
只注入这几类 + resolver 成功时的 CC_SWITCH_*；CC_SWITCH_* 六参仅 resolve
成功才注入，降级路径全不传）。

## 2. 专项研究三个关键发现（改变实施前提）

1. **npm 四包真实体积 ≈ 231.3MB（x64）**，非立项时估计的 ~60MB（该数字
   沿用了 stage-npm.sh:96 过时注释「~100MB 级」）。实测（npmmirror CDN
   2026-09-23）：两主包合计仅 33KB；claude-code-linux-x64 tgz 101,647,074B
   （96.9MiB）；codex-linux-x64 tgz 129,654,638B（123.7MiB）。arm64 伴生包
   另 +221.1MiB。yazi zip 实测 7,944,048B（7.6MiB）。
2. **GitHub 单文件 100MiB 硬限（GH001）直接否决「npm 四包全进 git」的字面
   落地**：codex 伴生包 123.7MiB > 104,857,600B，push 必被拒；claude 伴生
   包 96.9MiB 距红线 3%，一两个版本内也会越限。仓库未用 LFS
   （.gitattributes 仅 eol、git lfs ls-files 空）。
3. **A/C 方案价值重估（feasibility 核验）**：即便全进 git（假设可行），
   「物理断网保底」仍不成立（apt×2 + 基底结构性缺口）；A 相对 C 的唯一
   增量场景收窄为「GitHub 全阻 且 npmmirror 也断 但 apt 镜像仍活」的极窄
   窗口——而 GitHub 被墙的典型网络里 npmmirror（阿里 CDN）恰是最稳一环。
   **C（混合）用 +7.6MiB 覆盖全部实机死亡触点**；A（若可行）要多付
   .git 53→291MB、每版本 +220MiB 永久死历史。

## 3. 方案（分两层：修复层无争议即做；预置层按 U-8/U-9 终裁）

### 3.1 修复层（纯 bug fix，与裁决无关，全部本批交付）

| 项 | 改法 | 位置 |
| --- | --- | --- |
| F1 .gitignore 拦截 | 删 :87-88 两行（*.tgz / yazi-*.zip 被 git 静默吞；cc-switch .tar.gz 是扩展名巧合豁免），改写 :84-86 D-9 政策注释 | .gitignore |
| F2 cc-switch 漏配 | Dockerfile:440 glob 去版本号（`cc-switch-cli-*-linux-${cs_arch}-musl.tar.gz \| sort -V \| tail -1`，对齐 mihomo 模式）；三处 v5.10.4（ARG:34/versions.env/config manifest）一次性顺手对齐 v5.10.5（manifest 用 resolver 产物重写） | Dockerfile/versions.env/config |
| F3 yazi 段对齐 | :503 补 GH_PROXY 分支（对齐 mihomo/geodata/cc-switch）；max-time 60→**300-420s 档**（7.6MB@30KB/s 需 265s，300s 档仅 35s 余量，必须高档）；错误文案同步 | Dockerfile |
| F4 超时分级 | curl 家族统一 --connect-timeout 8 / --retry 2；max-time 分档（≤10MB: 180s；>10MB: 300s；cc-switch 下载段 60→同档）；_PULL_TIMEOUT_S 参数化（AISC_PULL_TIMEOUT_S 环境变量，默认 900） | Dockerfile/build.py |
| F5 镜像链统一 | GH_MIRRORS 单一 ARG 一处定义四段同源消费（消 5/4/3 站漂移）；错误文案统一指向 stage 脚本 + GH_PROXY 用法 | Dockerfile |
| F6 版本一致性门 | check-version-sync.py 增查五处同源：Dockerfile ARG == versions.env == downloads 实存 == config manifest == vendor/manifest.json；npm 预置分支文件名版本 vs CLAUDE_CODE_VERSION/CODEX_VERSION 不符至少警告 | tools/CI |
| F7 stage 脚本钉版 | stage-npm.sh 默认从 versions.env 读 pin（现拉 registry latest，:94），--latest 显式覆盖；下载后断言主包 dependencies 为空/仅平台 alias（闭包守卫：上游加真依赖时 stage 期显式报错，而非构建期 ENOTFOUND） | scripts/stage-npm.sh |
| F8 预置完整性校验 | COPY vendor/checksums.txt 进镜像，各预置分支 sha256sum -c --ignore-missing（与 cc-switch pinned 分支同构；checksums.txt:1501-1506 已覆盖 downloads 现存件但**无任何消费方**）；vendor-refresh 补录新预置件 license 条目 | Dockerfile/vendor |
| F9 .dockerignore 剥离 | `**/dist/`+`**/node_modules/` 已静默剥掉 **226 个 tracked 文件**（claude-hud dist ×120 等），Dockerfile:242 COPY 的是残缺集、statusLine（claude-settings.json:19 实引 dist/index.js）静默坏——加反例外 `!container/_bundle/**` + 镜像内断言 test -f dist/index.js；新增通用不变量：构建上下文与 git tracked 差集必须为空 | .dockerignore/CI |
| F10 失败诊断（原 P1） | docker exit 4 / curl (6)(28)(35)(52) 模式 → build.failed 附结构化 diagnostics + 三出路（预置/GH_PROXY/文档），Workbench 失败卡片动作化 | main.py/build.py/前端 |
| F11 manifest 随 bundle（保守版） | stage_bundle 增拷 config/cc-switch-manifest.json（artifact.py:184-190 后一行）；装机用户可 `--cc-switch-manifest <INSTDIR>/…` 离线保钉版。**不做**「第四级自动 fallback」（改 S8b 语义，留观察） | packaging/artifact.py |

### 3.2 预置层（按 U-8 终裁，推荐 C-混合）

| 方案 | 内容 | .git 增量 | 伴生包去哪 | 保底语义 |
| --- | --- | --- | --- | --- |
| ~~A 全进 git~~ | 四包+yazi 全入 | 53→291MB，每版 +220MiB 死历史 | — | **不可行**：codex tgz 123.7MiB > GitHub 100MiB 硬限，push 必拒 |
| **C 混合（推荐）** | yazi zip + npm 两主包（33KB）+ 现有小件入 git；**两个 linux 伴生包（231MB）随 NSIS bundle 分发**（artifact.py 按文件系统扫描自动带上）+ 好网时 `stage-npm.sh` 本地补齐 + npmmirror 在线兜底 | **+7.6MiB（53→61MB）** | NSIS/deb/dmg 携带 + stage 引导 | GitHub 全阻/被墙可构建（U-9①地板） |
| LFS 变体 | 全量走 git-lfs | 配额 1GiB ≈ 4 个版本周期触顶 | 仓内 | 无 LFS 环境 clone 得指针文件，预置 glob 静默失效（需指针检测改造）——不推荐 |

配套：arch 边界声明（保底承诺 = **x64**；arm64 伴生包 +221.1MiB 不入库，
arm64 宿主走在线分支，文档明示）；GH_PROXY 升格为 aisc build 正式通道
（versions.env 有效键 + models.py 注入，空值不注入——versions.env 手工
编辑即显式同意，符合 2.1.13 D-12 口径，Workbench P1b 界面通道同批）。

### 3.3 不做清单（明示）

- P2 宿主代理自动探测注入（维持 opt-in 不做）；
- P4 构建期容器 TUN sidecar；
- apt 离线化（.deb 闭包 / aisc-base 基底）——U-9 若选②再立项；
- S8b 第四级自动 manifest fallback（语义变更，保守只做 F11 分发）；
- `--pull` 强制回源旗标：保底场景禁用/提示（build.py 已有通道，加守卫一行）。

## 4. 残余网络依赖清单（诚实边界，随 U-9 定稿写进文档）

基底镜像（本地命中零网络；新机断网且无 tar 时三镜像链全灭——docker
save/load 历史仅人工操作记载，无工具化）、apt×2（无预置机制）、
resolver 全新机器离线首建（S8b unpinned 降级，不致死）、npm 在线分支
（预置齐备后仅版本漂移场景触达）、第三方镜像站自身可用性、
aisc bundle fetch（pip 形态走 api.github.com；repo/bundle 形态不受影响）、
BuildKit 前端（当前无 # syntax= 零网络；约束=未来不得添加）、arm64。

## 5. 待用户（终裁）

- **U-8**：npm 预置落地形态——C-混合（推荐，+7.6MiB，伴生包随安装器）/
  LFS（不推荐）——A 字面已被 GitHub 100MiB 硬限否决，无法按原裁决执行。
- **U-9**：保底地板语义——① GitHub 全阻+国内源可达（推荐，零成本）/
  ② 真·零网（apt 闭包，+300-400MB，另立项）。
- 顺带确认：yazi 同批入 git（强烈建议，实机死因本体）；arm64 明示 x64-only
  保底边界；GH_PROXY versions.env 通道（显式同意口径）。

## 6. 验收

见 [HANDTEST.md](HANDTEST.md) T6（升级版：预置行计数 7 行、yazi 7.6MB、
超时分档、断网/被墙/慢速三条件模拟矩阵、镜像内 dist 断言、上下文差集
不变量）。
