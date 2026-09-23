# 2.1.14 阶段裁决记录

> 本文件是 v2.1.14 阶段的裁决日志（沿用 2.1.12/2.1.13 惯例）。每条裁决记：
> 问题、裁定、影响面。编号 D-N 阶段内连续；U-N 为待用户裁决项（裁定后转 D-N）。

## 用户裁定

- **D-1（2026-09-23 用户指示，开题范围）**：用户原话「阅读todo中给2.1.14版本
  target，以及E:\...\aisc-issues-feedback下搜集的问题，重新整理一下2.1.14版本
  的todo，并按照规约制定开发计划」。⇒ 阶段范围 = todo 8 条既有项 + 反馈站 4 条
  （构建镜像网络异常 / codex ctrl+/ 切换 / 历史页徽标对齐 / 关闭工作区）。
  4 条反馈项据此获得 §1.2.2「计划外项入版」的用户确认；实施仍按 §1.2.1 分支
  先行。悬账三条（README「悬账清单」）不在 D-1 范围内，逐条待裁（U-3）。

- **D-10（2026-09-23 用户裁定，U-2）**：分屏键盘导航悬账（todo:81，
  Ctrl+Shift+hjkl / Ctrl+方向键，WebView2 加速器层拦截）**入批 4 同批处理**。
  批 4 范围扩展为「终端键盘域」：Ctrl+/ 直发修复 + 分屏导航（须在 WebView2
  无公共钩子的既定事实下找路：xterm 层自定义绑定/菜单降级/或再次评估
  AreBrowserAcceleratorKeysEnabled 的可行开关——实施时先探针后定案）。
- **D-11（2026-09-23 用户裁定，U-1）**：npm 四包（claude-code/codex 相关
  tgz）**连带预置**进仓库；并要求**彻底调研构建工作流，使其无论什么网络
  条件都保底完成一次构建**——已立「构建保底」专项（ultracode workflow
  进行中：Dockerfile 全网络触点盘点 / resolver 离线 manifest / npm·apt·pip
  离线机制 / 条件矩阵降级链 / 体积与 CI 约束核算），结论落
  build-network.md 升级版后实施。批 6 范围由「修复反馈 #1」扩展为
  「网络保底构建」。
- **D-12（2026-09-23 用户裁定，悬账全部收编）**：三条悬账全部入版——
  todo:81 分屏导航 → 批 4（D-10）；todo:150 picker 窄窗持续挤压
  （width-clamp 进 zoom）→ 批 3（ui-align-fixes.md D 节）；todo:191 docker
  管理破坏性操作边界 → 本版立边界裁决（D-13）。
- **D-13（2026-09-23 Claude 代定草案，随批 7 归档的 docker-management
  语义正式化，用户可否决）**：破坏性操作边界 = ①清单制：镜像删除/重命名
  (retag)、容器启动/停止/删除五项之外的新破坏性操作（prune、rmi -f 批量、
  卷/网络删除）**永不自动**，逐项须用户裁决入清单才可实施；②owned/
  legacy_owned 之外只读不变；③执行时锁内重扫判权 + 前端 confirm + lease
  守门三重不变量沿用；④Workbench 永不触碰 aisc 资产以外的 docker 资产。
- **D-14（2026-09-23 用户裁定）**：「工作记录」概念**撤销，不做了**——从
  todo / 计划 / 待办全部移除，worklog-questionnaire.md 删除；2.1.13 批 8 已
  交付的 worklog 账本与开关钩子**维持现状不动**（已交付已手测能力不回滚，
  撤销的是聚合层概念立项）。D-9 随之作废。
- **D-15（2026-09-23 用户澄清，D-8 强化为铁律）**：**构建与宿主网络完全
  解耦**——不论启动摘要页选什么网络模式，都不应影响宿主机网络环境，也
  **不得影响镜像构建**（网络模式仅作用于运行期容器 TUN 等）。保底目标 =
  **无论宿主网络环境如何（断网/GFW/TUN 代理/慢速），镜像构建都有兜底措施
  保证成功**——兜底 = 全预置离线路径（本地命中零网络），GH_PROXY 等显式
  通道仅定位为可选加速，不是兜底依赖。初步核实与现状一致：`--network
  direct|proxy` 为 run 期旗标（main.py:167/657/675），build 链路不消费；
  保底专项 workflow 结论落地时按此铁律校验全链。

## 立项规划裁定（2026-09-23，Claude 代定，用户可逐条否决）

> 依据当日立项研究（ultracode workflow：研究员 + 独立证据核验，verdict 全部
> confirmed/corrected；两处 429 阵亡核验已从首轮 journal 回灌）作出，细节见各
> 计划文档。

- **D-2（批次划分）**：六批 + 一个需求问询项（README 阶段表）。取舍：自更新
  三项合一批（同链路同验收形态，但保持**三条独立验收线**——/R 拉起链 / 下载
  参数穿透 / 注册表类型与自愈，回归点互不相同）；provider 两项合批（同页同
  链路，分批会两次触碰同一批文件）；UI 三小项合批（互不依赖、验收形态相同）；
  「工作记录」不占批次（需求未定，D-9）。
- **D-3（自更新三项技术路线，selfupdate-polish.md）**：①静默拉起 = 给
  update.rs 安装器参数追加 `/R`，激活 installer.nsi 既有模板机制
  （`.onInstSuccess` + `nsis_tauri_utils::RunAsUser`），不自研 Exec/降权；
  接受「整条升级链（含 30min 预算镜像重建）完成后才自动拉起」（改 Section
  顺序偏离模板，不做）；zh/en 更新卡片文案随之改「退出并更新（完成后自动
  重启）」。②staging 文件名 = `appDownloadUpdate` 增第三参 targetVersion
  （取 `info.latest`），staging 命名 `workbench-setup-{目标版本}.exe`；顺带
  清理 staging 目录旧 exe。③PATH = `PathWrite` 恒 `WriteRegExpandStr` +
  already-present 早退分支补类型规整自愈写（存量 REG_SZ 装机升级即愈）；
  CI smoke 补「首装新建 PATH 值类型」断言。
- **D-4（provider 合批改法基线，provider-add-fidelity.md）**：以**核验员修正版**
  为基线，否决研究员原案两处——①「模板未就绪禁用保存」与 FALLBACK 降级设计
  冲突（旧镜像用户将永久锁死），改「未就绪仅提示不阻断」；②「仅当 baseUrl
  为空才预填」与 D-6（2.1.12 阶段）端点跟随格式裁决冲突，改 **lastAutoPrefilled
  守卫**（仅当当前值===上次自动预填值才允许自动覆盖）。容器侧先行单行数据修复
  （codesome-v3 native 端点补 `/v1`）+ FALLBACK↔manifest 快照一致性单测。
  buildRequest 新建路径补发 env/model/model_catalog（键名对齐 adapter 契约）。
  模型拉取：add 内联探测纳入模板声明 OpenAI 侧 base 候选（照抄 codex 行路径
  既有做法）+ 单请求 15s→6s、总预算 <25s + 候选请求诊断日志（新增行为，
  仿 /tmp/aisc-live-catalog.log 先例）。
- **D-5（UI 三小项，ui-align-fixes.md）**：合批交付；间距/圆角一律走设计令牌，
  新增 `--radius-pill: 999px` 令牌（现 `--radius-full: 50%` 不适用胶囊）；
  计划文档中历史归属一律以 **commit 哈希**引用（仓库批号体系存在自称冲突，
  核验已证）；关于弹窗按 FloatingPane 惯例改造（Teleport + 自挂 zoom + 定高
  内部滚动）。
- **D-6（Ctrl+/ 修复形态，ctrl-slash-key.md）**：前端 `onTermCustomKey` 拦截
  + `writeSession` 直发字节，仅修 Ctrl+/ 不做泛化层（泛化列后续可扩展项）；
  对所有终端会话生效（与 kitty 终端行为一致，不按 agent gating）；载荷
  **双臂手测定案**：`ESC[47;5u`（kitty CSI-u）与 `\x1F`（legacy，与上游
  xterm 7.0 PR #5515 选定编码一致，codex 解析器对仅存 Ctrl+/ 绑定时自动追加
  legacy 别名）——Windows conhost ConPTY 输入引擎翻译层为最大未验证风险，
  手测以「codex 实际切换」为唯一裁决，`cat -v` 回显降为参考项。
- **D-7（关闭工作区，close-workspace.md）**：完全复用既有 `closeWorkspace`
  链，零生命周期代码改动；三入口（「操作」菜单末尾项 + 顶栏右端按钮 + 命令
  面板 `app.closeWorkspace`），门控 status∈{ready,error}（starting 态不显示，
  避免 cancelRuntimeStart 缺失导致后台物化容器竞态）；confirm 误触保护（容器
  删除不可撤销）；「重开秒回」不纳入（与 runtime-lifecycle-ux ephemeral 裁决
  相抵，记观察项）。
- **D-8（构建网络交付形态，build-network.md）**：P0 yazi 预置进
  `container/downloads/`（+约 8MB，恢复 v1.2.3 自包含惯例；与 2.1.12「镜像
  零预置」裁决不冲突——那条指 provider 预配置模板）；P0b 保守分支 glob 去
  版本号；P0c yazi/cc-switch curl `--max-time` 60→180-300s；P1 构建失败诊断
  归因（exit 4 + curl (6)/(28)/(35)/(52) 模式 → build.failed 附结构化提示）；
  P1b Workbench 构建界面暴露既有 `GH_PROXY` build-arg（显式同意通道，符合
  2.1.13 阶段 D-12「不未经同意改写网络」与 network.ts 契约）；P2 宿主代理自动探测注入
  **降为 opt-in 不默认做**；P4 构建期容器 TUN sidecar **不立项**（写入不做
  清单）。对外口径：环境性根因 + 预置/参数级修复 + 引导，**非根治宿主 TUN
  覆盖**（反馈站回复据此校准）。
- **D-9（工作记录需求问询先行）**：六组歧义（粒度/父子/开关时机/UI 落点/
  归档/恢复语义）问询材料已备（worklog-questionnaire.md），用户作答后才排期
  （本版 b7+ 或转期）；**严禁按 assumed 默认推进**（2.1.13 批 3 前车之鉴）；
  裁决前不动 worklog.py 数据层与 resume 冻结契约。

## 待用户裁决（U-N）

- ~~U-1~~ → 已裁定（D-11：npm 连带预置 + 保底构建专项）。
- ~~U-2~~ → 已裁定（D-10：入批 4 同批）。
- ~~U-3~~ → 已裁定（D-12：悬账全部收编）。
- ~~U-5~~ → 已回访关闭（2026-09-23 用户回忆：新建走**模板 + 高级模式**，
  claude 与 codex 侧似乎都有发生、无明确记录）。⇒ 假设权重更新：**H2
  （preset+高级层 roles/catalog 字段不随保存生效）升为最可能**——与「模板
  模式 + 展开高级层」的现场完全吻合，且双侧发生与前端 buildRequest 共因
  一致；H1（端点竞态）仍待路径 A 复现确认。修复方案不变（全覆盖）。
- ~~U-7~~ → 已执行（2026-09-23 按反馈站 README 工作流回执 4 条，status →
  in-progress；构建网络条追加研究结论与追问）。
- **U-4（b5，仍开放）**：入口形态确认（推荐菜单项+顶栏按钮两者都做）；
  「停止 Runtime」与新入口是否统一文案/动作。未否决前按推荐执行。
- **U-6（b6，仍开放）**：是否向反馈 #1 用户追问成功前置操作（回复中已
  顺带追问，看用户是否答复，不阻塞 P0 落地）。
