# 2.1.13 阶段裁决记录

> 本文件是 v2.1.13 阶段的裁决日志（沿用 2.1.12 惯例）。每条裁决记：问题、裁定、影响面。编号 D-N 阶段内连续。

- **D-1（Pi/opencode，2026-09-19 用户裁定 + 同日澄清）**：用户原话「Pi/opencode 不用安装」；立项时曾按「做，但免安装」理解并写入 pi-opencode.md，**用户同日澄清：本意是本阶段不做**。⇒ 最终裁定：**v2.1.13 不做 Pi/opencode**，条目退回后备池；pi-opencode.md 作废保留备查（重启时「免安装」路线可复议，外部事实需重新核验），D-9 随之作废。（原「免安装」理解存档：不做镜像内置安装，镜像/Dockerfile 不变。）
- **D-2（docker 检测精细化，2026-09-19 用户裁定）**：原 target「docker 缓存自动清理」改裁——**不要自动清理**，任何形式都不做；目标改为「**检测更细致、项目更准确**」（扫描分类更细、逐项可辨、可回收口径更实）。现有手动清理维持现状不动。
- **D-3（局域网通信增强暂缓，2026-09-19 用户裁定）**：移出 v2.1.13 阶段，退回后备池。重启先决：场景澄清 + serve TCP 传输安全裁定（2.1.12 前遗留的 D-7 议题，与本阶段编号无关）。

## 立项规划裁定（2026-09-19，Claude 代定，用户可逐条否决）

> 依据当日立项研究（ultracode workflow：研究员 + 独立证据核验）作出，细节见各计划文档。

- **D-4（自更新版本戳 + 实测目标，selfupdate-e2e.md）**：①采纳 **CI 版本戳**——nsis-installer.yml 构建步以 tag 覆盖 conf.version（`--config` JSON merge），嵌入版本与 tag 全等；否则 tag 版本≠嵌入版本（preview.1 实嵌 "2.1.12"），同 base 的 preview.2/final 对已装机**永远不可自更新达**。②端到端实测目标版本 = **v2.1.13-preview.1**（从 2.1.12 装机升级），非 todo 原文字面的 preview.2。③自更新文案三处修正随首发批。**用户确认（2026-09-19）：接受 CI 版本戳。**
- **D-5（远程 CLI 配对一期形态，remote-cli-pairing.md）**：banner（池内驻留会话）为比对本体 + 双时机（建池被动 emit + 设置页主动检测）；UI 三落点（设置页版本列主 / picker badge 辅 / 一次性 toast）；升级动作本期 = **提示 + 一键复制命令**（「确认后一键远程执行」列二期 open）；硬门四层模型不动；版本比较器 = .dev 归一 + 前 3 段数字（不复用 update.rs parse_tag）；随项修复「远程升级后旧驻留 serve 不换代」。
- **D-6（变更页双源，changes-page.md）**：本地 + 宿主 git + repo 三条件满足 → git status/diff 为权威源（**严格只读**，写操作出期）；否则回退现有 watcher 源（远程恒回退）。树形分组不复活 v2.1.9 D-6 已裁掉的归因分类。**用户确认（2026-09-19）并补充**：UI 直接模仿 vscode 的 git 页（源代码管理视图）形态；**只显示、不提供任何 git 操作**。
- **D-7（工作记录四批交付，history-worklog.md）**：数据层 `<ws_dir>/runtime/worklogs.json`（aisc.worklog/v1）+ CLI 会话开/关钩子（fail-open）+ 只读 transcript 渲染 pane + 历史 tab 并存过渡（flat 下线走用户裁决门）；批 0 = codex/claude resume 文件行为 T0 探针（仓库无证据，规格冻结前置）；与「长对话恢复」bug 禁止两处同时动 conversation 解析层。
- **D-8（拖图落盘通道，image-drag-to-agent.md）**：OS 图片拖入 → 落盘 `<ws>/.aisc/uploads/` → 插入容器路径 token（不直传二进制、不改 dragDropEnabled）；**剪贴板图片粘贴同批顺带**（容器内 agent 剪贴板结构性失效，这是「给图」的另一半）；远程复用 remote_mutation 既有模式。
- **D-9（Pi/opencode 混合形态）——已作废（2026-09-19）**：D-1 经用户澄清为「本阶段不做」，本条随之失效；pi-opencode.md 作废备查。原条目：基线 = 全链注册 + wrapper which 检测 + 未安装中文指引 + 一键复制安装命令（零网络代码）；增强 = 可关的按需获取提示。
- **D-10（docker 检测形态，docker-scan-fidelity.md）**：新增只读 `maintenance cache-inspect`（envelope aisc.docker-cache-inspect/v1），采集矩阵以 **`docker system df -v --format json`** 为主源（29.x 实测可用、官方未记载，能力探测兜底）+ buildx du / volume dangling / network ls 补齐；逐行「会被现有清理命中」徽标 + 可回收去重口径 + 高估免责；逐项删除、自动触发均不做。
- **D-11（底部预览彻底移除，2026-09-19 用户裁定，随变更页批实施）**：左键单击文件预览此前已在文件树侧移除（D11-01），但变更面板因 D11-16 例外保留单击预览——即用户所见「偶尔在侧边栏底部出现」的来源。裁定：**底部预览 pane 连同全部触发点彻底移除**（模板/样式/store 状态与动作/ipc 包装/Rust 死代码/i18n 键全清）；变更页的 diff 呈现不受影响且不再回退 previewFile。
