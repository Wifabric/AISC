# 20260625

1. [X] 仅保留docker_version使用即可

* [X] 没有挂VPN的时候node:20-slim无法安装
* [X] 挂VPN之后可以安装，配置提示`.claude/`缺少报错，不再继续进行

1. [x] ssh配置，windows端配置，检查是否打开ssh，如果没打开运行配置脚本

* [X] skill增加一个[github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md)（尽可能模拟/使用**Claude Code Plugin**安装）
* [X] 模型配置统一交由 cc-switch 管理

# 20260627

* [X] karpathy-skills安装后并没有被claude调用，需要主要启用；全局CLAUDE.md使用这个技能的CLAUDE.md文件（不是项目文件夹那个）
* [X] README.md使用引导统一，分为Windows，Linux，MacOS使用，各自有一键运行脚本
* [X] EADME.md中 直接运行super-claude:v1.1.2h 空白 和 bash的区别，两者使用上似乎没有区别，前者配置好之后再次登录不会调用claude
* [X] Windows一键运行脚本.bat，没有版本更新更改名称，改为“docker run -it --rm -v "%cd%:/app" super-claude:v1.1.2”
* [X] 保留之前的单次运行的使用方法，交互式+运行单个命令
* [X] 产生的Container如果用户直接关闭Terminal，不会关闭Container，需要docker手动删除（进入虚拟机之后，exit推出回windows，如果这个时候不输入exit，关闭windows的命令行，docker不关闭）
* [X] gstack没有成功安装: gstack的安装略微不同于其它的（/slash运行模式下没有/gstack./office-hour）
* [X] Caveman安装了，但是需要默认激活（默认是不激活的）
* [X] CMD运行有中文乱码问题，跨平台使用的终端方案（目前我用的是Wrap和Termius）

# 20260701

* [x] 每日skill/claude学习模块
* [X] clash翻墙配置（docker内部翻墙）— v1.2.3 完成：容器内建 Mihomo TUN 透明代理 + 多格式订阅转换（yaml/base64订阅/URI/JSON，ss/vmess/trojan/vless/hysteria2），详见 devlog
* [X] 一键启动脚本规范化配置 — v1.3.0(模块化流水线)+ v1.3.1(目录重构)完成：scripts/ 下 4 模块 + 薄入口，跨平台对等，状态解耦
* [X] claude code CLI外配置 cc-switch-cli：[github.com/saladday/cc-switch-cli](https://github.com/saladday/cc-switch-cli)；v2.1.1-dev 起作为唯一 Provider/skills 管理入口
* [X] 配置docker容器系统的python — v1.3.2 完成：apt 装 python3/pip/venv + 默认 venv /home/AISC/.venv（挂 PATH 头，绕过 PEP 668，pip install 直达），详见 devlog
* [x] 用户自定义模型
* [x] 自定义接入服务商
* [x] 兼容openai请求格式

* [x] 文件结构
* [x] 安装后的文件结构
* [x] cc-switch使用
* [x] user版本调整
* [x] 剪枝
* [x] readme_dev调整
* [x] 进程保活
* [x] docker操作
* [x] 使用流程捋清楚、aisc使用引导、tool
  * [x] 初次使用cli环境配置
  * [x] config环境配置
  * [x] docker管理
  * [x] claude

# 20260730

1. [X] 更新 README.md 的 `aisc run` 前台运行容器说明，补充 `--workspace`（使用指定目录作为工作区）的用法
2. [X] 更新 README.md 的「Codesome｜Codex 与 Claude Code 二合一服务」部分：说明下单入口变更为 <https://meta.codesome.cn/?aff=FAP2ASVX>、注册后可自助创建 AFF 并查看邀请情况、满 100 可提现，并参考 `doc.codesome.ai` 介绍 Claude、Codex 及二合一服务
3. [X] 检查 `aisc switch --quick` 是否可用及其实现逻辑，并为 cc-switch 常见供应商提供除 API Key 外的一键配置：DeepSeek、Claude 使用 Codex 订阅、火山引擎 Ark、智谱 Z.ai、Kimi
4. [X] 检查容器内代理/翻墙设置，重点排查与 cc-switch 的冲突，并验证 Docker 容器内可通过官方渠道访问 Codex
5. [X] 移除 README.md 开头的版本要点内容
6. [X] 完善 Docker 直接引导安装流程，实现开箱即用
9. [x] 调研适合 AI 稳定访问和读取网页的方案
10. [x] 准备一套使用演示材料，PPT+解说词+实机演示。


# 20260806
- [x] Workbench S4.1.b：Windows NSIS 定制安装器（依赖检测 + winget 引导装 Docker/Python/WebView2）— CI 构建验证通过（产物 setup.exe），实机手测进行中（docs/问题.txt 4 个问题已修：Docker 引导启动/引擎检测/console 闪现/构建失败，待复测）
- [x] 修复安装版 Workbench「打开目录 → 构建镜像」失败（2026-08-08）：NSIS 安装器随附 aisc-bundle（CI staging + 静默安装冒烟）+ build --events 流式捕获跨平台化（_drain_threads + _kill_child）+ vendor/checksums.txt 刷新，见 devlog S4.1.b 修复
- [x] 安装向导增加语言选择（英/简中），全中文安装（2026-08-08）：languages + displayLanguageSelector + LangString DEP_* 本地化，见 devlog S4.1.b
- [x] 安装器依赖检测修复 + winget 隐藏终端（2026-08-09）：Docker 查真实路径/卸载键、Python 枚举 PythonCore 版本键（32/64 视图）、ExecWait→nsExec::ExecToLog（进度进安装日志）+ 非 0 退出重检测，见 devlog S4.1.b
- [x] 临时模式下，cc-switch不可用
- [x] aisc run命令解耦，引导混乱，用户感到费解（2026-09-18 用户标记完成）
- [x] aisc cli的更新命令优化（2026-09-16 关闭：无实施记录、语义不可考，由 V0.1.0-target cli update 吸收，D-21）
- [x] 预配置的deepseek配置项错误，修复
- [x] 预配置的codesome配置项错误，修复
- [x] runtime内，cc-switch显示异常（表现为终端显示不及时，能正常使用TUI，但是选择的位置不到对应区域时，对应区域显示的是乱七八糟的TUI结构，应该是旧的。且在windows下，TUI不会随窗口变化自适应）
- [x] 界面字体太小，增加设置页，可以设置软件各类属性 — 2026-08-10 Step 3/7 完成：typed settings + 设置对话框 + UI 字号缩放（自适应窗口）+ 终端字号/行高/回滚/渲染器
- [x] 通过winget安装docker desktop并启动，从引导界面勾选打开workbench，打开的workbench，无法内启动摘要界面无法正常检测，且点击启动docker也无效。而关闭该workbench，重新打开，就可以成功识别docker。— A+C 已实现（自动重试 preflight + CLI 绝对路径兜底）；复测发现 2 新问题已修（空目录误报冲突：resolve_conflict 仅限真冲突；构建失败：docker-credential-desktop PATH 兜底），2026-08-09 待最终复测
# 20260810

- [x] codex 打开即进默认配置（login_required 直接开会话，终端内登录）——用户决定保留数据驱动行为（A-G08-2 只拦 not_configured）；若日后想更保守（login_required 也先进 guide 配置页），改 `runtime.ts` maybeOpenCreated 条件为 `["not_configured", "login_required"].includes(...)`（代码内已有 TODO 注释 + 2026-08-10 决策记录）
- [x] **未来路线探讨：容器内 GUI 版 cc-switch**。当前 cc-switch-cli 是 TUI 应用，经终端管道渲染到 xterm.js（Step 9 管道方案已解决编码/对齐/性能/刷新问题，体验基本可用）。但 TUI 仍有固有局限：图标/emoji 需终端字体支持、布局受终端网格约束、无鼠标交互（部分 TUI 框架支持但受限）。若在容器内增加 GUI 版 cc-switch（如 Web 前端 + 后端 API），Workbench 可通过 webview 直接打开 GUI 版，绕过终端层。优势：完整 Unicode/emoji、自由布局、鼠标交互、更接近原生应用体验。需评估：cc-switch 是否有或可加 Web UI 模式、容器内端口暴露方式、Workbench webview 集成路径。保留 cc-switch-cli 作为终端备选。
- [x] 工作区，aisc配置文件集中在一个文件夹下，不要像现在这样太零散是否可行？
- [x] 退出前询问用户是否想要保留runtime，若选择不想则直接删除该runtime及对应的container
- [x] 分屏键盘导航无效（Step 16 遗留）：`Ctrl+Shift+W` 关 pane 可用，但 `Ctrl+Shift+hjkl` / `Ctrl+方向键` 移动 pane 焦点在实机 WebView2 无反应。已修到：window capture handler 生效、scope `.xterm`→`.pane`（覆盖 guide/dormant）、导航成功后 focusTabTerminal 移交键盘焦点（f409b3f），实测光标仍不动。结论：监听器/guard/`navigatePane`/焦点移交代码均已验证正常（`Ctrl+Shift+W` 同一路径可用），最可能是 WebView2 在浏览器加速器层拦截 Ctrl+Shift+字母 / Ctrl+方向键组合（`AreBrowserAcceleratorKeysEnabled` 默认开启；Tauri 2 未暴露禁用该行为的公共钩子，COM 方案已尝试并放弃）。留待之后解决，见 devlog。
- [x] Step 16（G-17 分屏）暂时通过、小问题之后再改（2026-08-10）：用户验收"暂时算通过"。已修的：恢复布局黑屏/闪烁/布局错误、stop 丢布局、tab 标题陈旧、空状态居中、bash 卡"启动中"。遗留待改的小问题未逐一枚举，用户之后再反馈；键盘导航（上一条）为已知遗留。


# 用户体验
- [x] 资源管理器；单击，系统默认方式打开；双击，插入到对话。
- [x] 生成文件快速打开
- [x] 简易模式，不显示工作区冲突，发现冲突直接帮用户处理
  - [x] “工作区已有runtime”当前只能删e，除旧的runtim有什么存在的意义？  
- [x] 生成大量文件时，产物页爆炸（疯狂转圈）
- [x] 第一次启动工作区，bash下的文字教学
- [x] 产物区/文件区文件改动属性优化
- [x] 对话历史记录整理页
- [x] zsh下help命令
- [x] 提升dockerfile构建的稳定性
- [x] provider页切换provider响应超时
  - [x] codesome适配（2.1.12 codesome 专项闭环：双模板+S9a 端点分离+模板化 UI，2026-09-18 手测通过）
- [x] 分屏的×点不了
- [x] cc-switch挂掉
- [x] 屏蔽ctrl+c，让ctrl+c，ctrl+v由复制、粘贴覆盖
- [x] 全局禁用非我们提供的右键表单
- [x] 资源管理器、bash tab行大小可拖动


# 手测异常/问题
- [x] 欢迎使用 AISC Workbench的初次运行环境失败，没有找到aisc cli（多次出现，从之前的版本里就有出现，但是当时没有重视）
- [x] 初次进入选择工作区页面时，显示没有aisc cli能力，点击重新检测后恢复正常（同上，多次出现，之前没有重视）
- [x] aisc卸载、升级，要同步删除、重建docker的镜像、数据文件等配套资源，如果能同步更新container就更好了。
- [x] aisc卸载时，清空相关images，升级时，重构images


# 调研
- [x] 容器调用宿主工具*(MCP->白名单（）)



# UI美术动效
- 当前情况：
  - 纯 CSS，无框架无预处理器：
    - 每组件 \<style scoped\>：样式随 SFC 就地管理（App.vue / TabBar / WorkspaceBar 等都是）
    - 设计令牌 = CSS 自定义属性（Stage 6 UX-01 落的）：间距/字号/圆角/阴影/层级/时长统一为 --surface、--text-2、--radius-md、--space-2 这类变量，组件只消费变量不写死值
    - 主题：src/theme.ts 按 settings 的 ui.theme 在根元素打 data-theme（system/dark/light），变量在全局样式表里按主题重定义
    - 字号缩放：ui.font_scale 用 CSS zoom 实现（App 的 uiZoom + 终端区 1/scale 反向补偿）
- [x] 首页'bash'类字样
- [x] provider 表头
- [x] bash引导头
  - [x] agent引导头
  - [x] 命令补全提示
- [x] 生命周期、
- [X] 资源管理器功能
  - [x] 图标
  - [x] 功能对标windows资源管理器
  - [x] 拖动引用
- [x] 设置页组织优化
- [x] 初次引导砍掉


# v2.1.10-target
- new feature
  - [x] aisc-cli能力：类似vscode codeserver，一台机器上的cli可以和其它机器上的workbench沟通，workbench可以选择和哪台机器上的cli进行通信？先调研vscode ssh remote的实现方式
- fix
  - [x] 历史页的claude、codex图标区别度提升
  - [x] aisc-cli命令优化
  - [x] 资源管理器、bash tab行等非终端区域的拖动，且提供类似vscode的可隐藏折叠设计


# v2.1.11-target（已收口，余项转下周期）
- fix（本周期已交付：P1 key 显隐/spool 空白/生命周期治理导出/recent 守门、S2 传输统一、Shell W1-W3+P2-1..5、P3 模型热切换 r1-r10）
  - [x] doctor 的 aisc-root 检查在生产容器恒警告（无 repo 根）——repo 根检查宜限定 dev 检出场景，远程/容器工作区不该出现「not found」级联（2026-09-11 远程诊断截图裁决入库）
  - [x] picker 界面窄窗持续挤压时整 UI 随 effectiveScale 同步缩小（App.vue `Math.min(scale, 1.5, w/800, h/600)` 把 <800px 拉进 zoom）——无害但不美观；下阶段让 picker 场景脱离 width-clamp 或改响应式布局（2026-09-11 P2-2 手测反馈，用户裁决下阶段处理）
  - [x] 热切换显示层边界：CLI 界面模型名仍停在启动值（两 CLI 显示层死结，功能已随切换实时变化；工作台侧以「实际模型」toast/卡片补真值）


# V2.1.12-target（已收口 2026-09-17：v0.1.0 final 全渠道发布——GitHub Release 三平台+NSIS+SBOM、PyPI aisc-cli 0.1.0；plan 归档 docs/archive/0.1.0-dev-plans/，余项转 0.1.1）
- new features
  - [x] docker管理的简易映射（R1 裁决 = Docker 资源管理简化 UI：maintenance scan/cleanup/rebuild 产品化入设置页 Docker 资源组，扫描前置门+悬浮提示；手测 PASS 2026-09-16）
  - [x] cli update; workbench 热更新（R4：aisc update 热换 sidecar + Workbench 标准自更新，A4/A7 交付；pytest 1255/1297+ vitest 488/500）
  - [x] cli作为pip包发布准备（R3：A1-A3/A6/A8-A9 全链交付；PyPI aisc-cli 0.1.0 live，pypi.org/project/aisc-cli）
- fix
  - [x] provider行为优化调研（R6：r1 结论文档已交付 docs/plans/2.1.12-dev-plans/r1-provider-templates.md——已裁决 2026-09-18 D-1/D-2/D-3：纯静态 AISC 自有模板路线、赞助商模板完全排除（codesome 例外）、存量一次性迁移；实施转 2.1.12 阶段）
    - [x] 不再提供预配置，但是提供添加模板（2.1.12 已实施：镜像零预置 + 模板清单，2026-09-18）
    - [x] 模板先完全映射cc-switch内置的（2026-09-18 D-1 裁决推翻：改 AISC 自有 5 家模板清单，不映射上游）
  - [x] 调研codex computer use 实现原理（R7：r2 结论文档已交付——CLI 侧能力依赖上游捆绑 MCP 插件；已裁决 2026-09-18 D-4：暂不原生实施，闭环转观察，路线三永久否决）
  - [x] 初次启动构建失败时，提供重新构建按钮（B1：BuildProgress failed/cancelled 态「重新构建」按钮，同 tag 复用 startBuild 链；B2 顺带 BUILD_TIMEOUT 600→1800s；手测 PASS 2026-09-16）
  - [x] claude、codex、cc-switch等内置工具，定期更新（R5 裁决 = 与 cli update 合一入口；A5 交付：--pin-tool 用户层+build args 消费+cc-switch 三处漂移修齐+node:22 基底）
  - [x] v2.1.11 bug：切换颜色主题后，历史会话视图的消息/终端输出块残留深色样式（深底+淡化字不随主题重绘，2026-09-16 用户截图报障，B0 修复——addon-webgl 图集不随 options.theme 重绘，切主题时重建 addon；手测 PASS 2026-09-16）
  - [x] 上下文后面加个自动compact阈值；
  - [x] codex只选模型，无法选择思考深度





# v2.1.13-target （已收口 2026-09-22：十二批次全交付手测，v2.1.13-preview.1 发布，自更新 E2E 通过，plans 归档 docs/archive/2.1.13-dev-plans/）

**发布与更新**
- [x] 自更新端到端实测（2026-09-21 实测通过：2.1.12-preview.1 → v2.1.13-preview.1 全链，含 Docker 升级链与数据保留；devlog 有取证。观察项随下批：静默装后自动拉起/staging 文件名/PATH REG_SZ）
- [x] 远程机器 CLI 版本配对与更新：「需更新」主动提示 UI 与自动同步（协议硬门已交付，v2.1.11 遗留）

**会话 / 工作区**
- [x] 长对话无法恢复（bug）
- [x] 历史会话重构·聊天式只读对话查看器（2026-09-21 已交付：`conversation read` + 查看对话面板，HANDTEST 批 11）
- [x] 变更页：vscode git 插件的体验 + 变化文件用文件树（批 5 交付，2026-09-22 用户确认基本没有问题）
- [x] 导出的工作区 zip 恢复为工作区，且指向新路径
- [x] 资源管理器没有滚动能力，文件太多的时候看不到下面的内容（2026-09-21 用户指派入版，立刻解决）

**运行质量**
- [x] docker 缓存自动清理
- [x] 设备性能受限情况下，如何保证稳定运行
- [x] cli run在存在容器的情况下禁止使用
- [x] workbench 内 docker 容器/镜像的简单查询与管理（镜像删除、容器删除/停止等常用操作；2026-09-20 手测反馈，破坏性操作边界待立计划裁决）

# v2.1.14-target（2026-09-23 开题：范围 = 转期/预置项 + 反馈站 4 条〔D-1〕+ 悬账收编〔D-12〕；计划 docs/plans/2.1.14-dev-plans/；「工作记录」概念已撤销〔D-14〕；开放项 U-4/U-6）

> **2026-09-24 收口**：六批（b1-b12，含四轮 provider 修复与三轮发布修复）全部交付。手测 T3-3/T4-2/T1-3/装机取证 PASS；provider 域用户确认收口；剩余观察项：T1-1/T1-2 应用内更新流随 v2.1.14-preview.2→下一跳验证（b12 下载超时已本地实证 61.2s/292MB）、T6-4/5/6 断网模拟挂起（需断网窗口）、T5/T2-A/T4-1·3·4·5 随日常使用验证。

> **2026-09-25 销账（用户裁定维持 2.1.14，不开新版本）**：观察项全部关闭——T1-1/T1-2 已于 preview.2→3 实测 PASS；T6-4/5/6 与 T5/T2-A/T4-1·3·4·5 经用户确认日常使用无异常，销账；D-13 docker 破坏性操作边界用户追认定稿（archive decisions.md D-23）。已知状态：装机 sidecar CLI 停留 0.1.2（无独立升级通道，随下一版 Workbench 安装器按「先 bump CLI 再构建」规则携带更新）。

**发布与更新（批 1）**
- [x] 开池版本 bump 2.1.13 → 2.1.14 + 自更新三项：静默升级完成后自动拉起新版（update.rs 加 /R 激活 installer.nsi 既有 RunAsUser 机制；接受升级链全程后拉起，文案/发布说明写明）／ staging 文件名改目标版本（appDownloadUpdate 穿透 targetVersion，顺带清理 staging 旧 exe）／ NSIS PATH 写 REG_EXPAND_SZ（PathWrite 恒 ExpandStr + 存量自愈写 + CI smoke 补首装新建值断言）
**Provider 新建保真（批 2，合批）**
- [x] 新建的 provider 第一次保存的结果和用户填写的不同（偶发，未复现；三假设已定位：模板清单竞态 + 切格式确定性覆盖 baseUrl〔lastAutoPrefilled 守卫修〕／ buildRequest 新建路径丢 env/model/model_catalog／容器侧 codesome-v3 native 端点缺 /v1 数据修复 + FALLBACK↔manifest 一致性单测）
- [x] 添加 provider 模型拉取失败，claude 和 codex 侧都是这样（add 内联探测纳入模板声明 OpenAI 侧 base 候选 + 超时 15s→6s 总预算 <25s 对齐 30s 杀线 + 候选请求诊断日志；手测第 0 步先判 adapter 版本——旧镜像 requires --id 同症状）
**UI 对齐四项（批 3，合批；2026-09-23 D-12 收编 picker 窄窗）**
- [x] provider claude 添加时展开高级槽位两个输入框挨太近（ModelMappingEditor.vue:103 裸 div 吃掉 .mapping 的 flex gap——加 class 补 gap 令牌，一处修全部 claude 模板）
- [x] 历史记录页徽标按钮未对齐（反馈 #3；胶囊规格统一 + ✳◈ 字形度量隔离 + 散值令牌化，新增 --radius-pill；非批 9 回归）
- [x] 关于 aisc workbench 结果弹窗异常，太长超出显示范围无滚动条（DoctorDialog 未 Teleport 逃逸 zoom + max-height:84vh 被放大——k>约1.19 越界，字号 ≥1.20 必现；照 FloatingPane 惯例改造；内容推高来自 2.1.12 新增 doctor 检查项）
**终端键盘域（批 4）**
- [x] codex 用 /btw 后 ctrl+/ 无法切回 main（反馈 #2；xterm 6.0 键盘映射无 Ctrl+/ 条目静默丢弃——onTermCustomKey 拦截 + writeSession 直发，载荷 CSI-u/ 双臂手测定案，conhost 翻译层为主要实测风险；D-10 用户裁定同批收编分屏 Ctrl+Shift+hjkl 导航悬账〔todo:81〕：替代键绑定/加速键开关复查/菜单兜底三路探针定案）
**工作区（批 5）**
- [x] 顶栏增加「关闭工作区」：关闭当前工作区回 picker、窗口不关（反馈 #4；复用既有 closeWorkspace 链零生命周期改动，操作菜单项 + 顶栏按钮 + 命令面板三入口，confirm 误触保护，ready/error 门控）
- [x] picker 窄窗持续挤压（2.1.11 遗留，D-12 收编批 3）：App.vue width-clamp 把 <800px 窗拉进 zoom——picker 场景脱离 width-clamp 或改响应式
- [x] docker 管理破坏性操作边界裁决立账（2.1.13 尾巴，D-12 收编；D-13 代定草案：清单制 + owned-only + 三重不变量 + 永不触碰 aisc 外资产，随验收定稿）
**网络保底构建（批 6，反馈 #1 履约 + D-11 升级）**
- [x] 宿主 TUN 代理模式下构建镜像失败（根因：TUN 不覆盖 buildkit 容器出口，GitHub 全阻而国内源全通；两次构建实死在 yazi 下载——无预置 + curl max-time 60 必死；保守分支 glob 硬编码 v5.10.4 是隐藏第二雷。修复：yazi + npm 四包预置 downloads/〔D-11〕+ glob 去版本号 + max-time 180-300s + 失败诊断归因 + GH_PROXY 显式通道 + resolver 离线 manifest + 条件矩阵降级链——「保底完成构建」专项调研已完成（12 触点矩阵+修复层 F1-F11），**发现硬墙**：npm 伴生包 codex tgz 123.7MiB 超 GitHub 单文件 100MiB 上限，「全进仓库」push 必拒——落地形态待 U-8 终裁（推荐 C-混合 +7.6MiB）；保底地板语义待 U-9 终裁（推荐 GitHub 全阻+国内源可达））

# 待解决

# v2.1.15-target（2026-10-12 开题；2026-10-15 b1–b16 收口，v2.1.15 final 发布；计划已归档）
- P0 fix
  - [x] SSH 远程电脑后卡在 CLI bash 光标，或打开会话报错；先分析诊断包并复现，修复远端 shell/PTY/会话开启链路（反馈 F5；b1 已闭环）
- fix
  - [x] Windows 下仅大小写不同的工作区路径应归一为同一身份，历史不重复显示，同时保留用户原始显示形态（反馈 F4；b2 已闭环）
  - [x] CLI 输出运行/结束后终端滚动不应把用户视口拉到顶部；明确自动跟随与手动回看边界（反馈 F2；b3 已闭环）
- UX
  - [x] 顶部 bash/codex/claude 状态栏不应参与上下拖动，只保留侧边栏与分屏边界拖拽（反馈 F1；b4 已闭环）
- design
  - [x] 实施 Work Record / Collection 完整语义：会话记录 + 轻量集合层、active 自动收容、归档、级联删除与失败提示（反馈 F3；b6 已闭环）
- 追加（b1 手测发现）
  - [x] PTY 输出流在初始输出后停止而输入仍可达；修复 pump 误判 timeout/EINTR 为 EOF（b5 已闭环）
- 追加（收尾前修复，2026-10-14 用户裁定）
  - [x] bash/codex/claude 会话退出后直接关闭标签，不保留 exited 横幅（b7 已闭环）
  - [x] Work Records UI 树状重构：动作符号化、右键菜单（重命名/fork）、子代理会话折叠、树状展示、历史并入全部会话（b8 已闭环）
  - [x] preview.4 实测追加 b13：远程全盘导航、Recent 机器身份、远端数据面取证、Help 文档/更新反馈（preview.5 已发布，待实机）
  - [x] preview.5 实测追加 b14：协议错误 detail、远程 Explorer 首载、Recent 配置机器名迁移、同 ID image tag 聚合（preview.6 已发布，待实机）
  - [x] preview.6 实测追加 b15：更新链路、中文标题、Claude parent、Work Records 折叠/去 Active、Docker 统计与 alias（preview.7 已发布，待实机）
  - [x] preview.7 实测追加 b16：新建 Work Record 默认折叠、Help/About 语义、fit 弹层移除、更新 Atom fallback、统一 Docker 资源面板（v2.1.15 final 收口）

# v2.1.16-target（2026-10-17 开题；2026-10-25 b1–b13 与 preview-fixes b1–b3 收口，v2.1.16 final 发布；计划已归档）
- fix
  - [x] 容器内 codex 自动更新报 npm EEXIST；codex/claude 更新落持久 toolchain（b1）
  - [x] project bind mount 上 Codex 自更新 EACCES rename；shadow 运行 + 持久安装链路修复（b13）
- UX
  - [x] Work Records 五项：只读预览、父子拖拽、新建/分支、加载占位、同名级联删除（b2）
  - [x] Docker 资源卡片、中文语义、扫描/清理/重建布局与数据刷新（b3/b8/b9/b13）
- 扩展
  - [x] 供应商/扩展迁入左侧 rail，TabBar 仅 bash/codex/claude（b5/b6）
  - [x] Skills/MCP/Plugins 查看与生命周期管理、三市场检索安装、进度动画、来源冲突提示（b5–b13）
  - [x] Skill 按仓库聚合，支持子项单独操作与仓库级批量操作（b13）
  - [x] 出厂 Skills/Plugins 清空，官方插件市场保留（b10/b12）
- 终端
  - [x] bash/claude/codex 普通拖选自动进宿主剪贴板；Codex mouse tracking 下无需 Shift（b9–b12）
- 稳定性
  - [x] 关闭工作区后租约释放，重进不被阻断（b6）
  - [x] factory npm 与 runtime toolchain 分离，claude/codex wrappers 不再 not found（b8）
  - [x] Docker 冷启动基础镜像按源轮转；每源 120 秒，无需手工 tag（b12）
  - [x] builder cache 全量 `--all` 清理并移除 Node 基础标签（b9/b13）
  - [x] tests.yml 收敛 pytest，九组矩阵全绿（方案 B）
- 发布
  - [x] b1–b13 本地门禁与 develop CI 全绿；关键链路 Computer Use/真实容器/真实 Docker 预复测通过
  - [x] Workbench `v2.1.16-preview.1` 发布准备；CLI `0.1.9.dev0` TestPyPI 配对验证
- 追加（v2.1.16 preview.1 反馈，2026-10-25；preview-fixes b1；v2.1.16-preview.2 发布准备）
  - [x] 磁盘清理输出一行化并移除估算 disclaimer
  - [x] 扩展侧栏随宽度收缩；顶层文件搜索在 Provider/Extensions 隐藏
  - [x] Skills/MCP/Plugins 状态与操作互相隔离；搜索清空即清结果
  - [x] 子技能介绍与父组展开分离；安装进度稳定显示 `x/y`
  - [x] 出厂技能改为仅 grill-me + caveman（覆盖 b10 全清裁定）
- 追加（v2.1.16 preview.2 反馈，2026-10-25；preview-fixes b2；v2.1.16-preview.3 发布准备）
  - [x] 子技能动作右置、说明独立换行并再次点击收起
  - [x] 磁盘页删除第一层重复资源名列表
  - [x] 宿主工具 F2 合并到 Services 视图
  - [x] Smithery MCP 改用 HTTP deploymentUrl 安装
  - [x] 操作完成 / 失败 toast 与重复 spinner 收敛
  - [x] skills.sh / Smithery / GitHub 操作镜像兜底
- 追加（v2.1.16 preview.3 反馈，2026-10-25；preview-fixes b3；v2.1.16 final 收口）
  - [x] 出厂 caveman 改为 13 个 `caveman-*` + grill-me
  - [x] 无宿主代理 skill 安装 / 更新使用 archive 探测 + 镜像 Git 暂存
  - [x] 更新 / 卸载按钮动画按 action + target 区分
  - [x] Workbench 自更新 API / asset / raw 镜像兜底
  - [x] cc-switch resolver 与构建网络静态契约补齐
  - [x] v2.1.16-preview.4 实机冒烟与远程 CI 全绿
- 发布
  - [x] Workbench `v2.1.16` final；CLI `0.1.9` final
  - [x] `2.1.16-dev-plans` 与 `2.1.16-preview-fixes` 均归档

# v2.1.17（preview 收尾完成，2026-10-31）
> D-7（2026-10-31）：用户取消剩余批次/统一手测与环境补测并放行收尾；NOT RUN 不改为 PASS。preview/TestPyPI 已发布并归档，正式 final/main 另走批准门。
（2026-10-26 反馈驱动重启；方案 A = 生态与可靠性；计划 docs/archive/2.1.17-dev-plans/）
- 反馈站 2026-10-26
  - [x] N1 / b1：无代理 skill 安装/更新完整性与逐项诊断（CU H4/安装进度与终态通过；H1 toast、H2/H3 故障网络D-7 用户免补测放行）
  - [x] N2 + N4 / b2：市场元数据、已安装项更新标识与详情中文化（CU 三类市场搜索/详情通过；断网缓存与隔离D-7 用户免补测放行）
  - [x] N3 / b4：Skills / MCP / Plugins 统一推荐与发现（CU 中英文推荐与搜索路由通过；离线禁用态D-7 用户免补测放行）
  - [x] N5 / R4：Work Record 友好阅读、每轮思考/命令合并折叠、Markdown/LaTeX/图片附件/可点击文件与网址；实时终端继续字节穿透（2026-10-30 用户明确纳入 R4；实现/门禁/真实阅读 CU 已通过，公式滚动修复/最终构建通过，D-6 用户手测通过）
- 可靠性
  - [x] R4：Docker 意外断连 / bash 中止后从 Work Record 恢复原 Codex/Claude 会话；配置引导与重试保留会话身份（2026-10-30 用户追加；已认证 Codex/Claude 进程/容器中断 CU 恢复同 native ID、CLI 追加召回及真实阅读器完整两轮问答 PASS；D-6 用户手测通过；全局 Docker 引擎断连/真实大历史/Remote 等未测项按 D-7 免补测放行）
  - [x] b3：扩展安装 / 更新 / 卸载失败恢复、单项重试与操作日志（CU 超时日志/复制诊断通过；第二次可重试失败D-7 用户免补测放行）
  - [x] b5：网络 / 显式自更新 / CLI 与 bundle 版本配对健康报告（实现/自动化/CI/CU 显式更新主路径与健康报告通过；诊断竞态D-7 用户免补测放行）
- 默认体验
  - [x] b6：Services 注册服务标签补齐；caveman 安装即默认开启（实现/自动化/真实容器/CI/CU Services 与默认态通过；A→B→A D-7 用户免补测放行）
- 发布
  - [x] b7：镜像内置 cc-switch / Codex / Claude / Node 稳定最新版刷新（b7 Node 24.22.1 依 D-5；收尾依 D-4 刷新至 Active LTS Node 26.13.0、Codex 0.166.0、Claude 2.1.314、geodata 20261030，PR #52 与精确集成 CI/最终镜像验证通过）
  - [x] R1：CU 预手测修复轮——长扩展组操作改为独立 direct 传输，避免占用 serial serve 导致 Services 控制面 30 秒超时（代码/TDD/审查复审通过/Rust 门禁/生产构建通过；Local CU 组安装期间 Services PASS；Remote 真实 SSH UI NOT RUN；PR #48 已合并且远端 CI 最终全绿；D-7 用户免补测放行）
  - [x] R2：扩展 UI 重设计——删除主视图操作日志、分类扩展市场（六类各 10 条）、中文详情、整体布局优化与技能仓库/插件市场维护（PR #49 已合入 develop `6133eef`；审查/增量复审、803 前端测试、既有完整门禁、最终 PR/develop CI、三平台 sidecar/deb/dmg/NSIS 通过；来源维护与跨市场保留真容器通过，已修正插件市场级联卸载双语警告；早期 CU 工具阻塞，收尾关键 CU 已通过；来源最终删除与窄屏等 UI 仍 NOT RUN，D-7 用户免补测放行）
  - [x] R3：扩展市场批次修复——旧 runtime 来源维护稳定提示、已安装空态移除“打开扩展市场”按钮、推荐卡片内联展开详情（TDD/完整门禁/最终生产构建/真实数据面通过；独立审查最终 Critical=0/Important=0；PR #50 已合入 develop `c3b297b`，合入后 Workbench/三平台 sidecar/deb/dmg/NSIS 全绿；早期 CU 阻塞记录保留；D-6 用户已确认本批手测通过）
  - [x] 高频链路自动化冒烟与 v2.1.17 preview 准备（10-31 发布依赖刷新 PR #52 合入 `bc189a3`；最终干净镜像三轮数据面 9/9、12 phases 全 PASS，完整门禁/clean-room/三平台出包与分支及精确集成四条 CI 全 SUCCESS，CU 市场/Services/阅读关键路径通过；剩余手测依 D-7 免除；Workbench 2.1.17-preview.1 / CLI 0.1.10.dev0 GitHub preview 与 TestPyPI 已发布，计划归档）
  - [x] CLI `0.1.10.dev0` GitHub preview / TestPyPI 已发布并通过真实 index 安装验证；正式 PyPI job skipped。
  - 正式 final/main 发布与最终反馈、Release、临时分支清理不属于本次 preview 收尾，按独立批准门处理。

# v2.1.17-preview-fixes-target（2026-10-31 用户手测追加）

用户本轮明确授权以下十项反馈进入 preview 修复，计划见 `docs/plans/2.1.17-preview-fixes/`。
按 DEVELOP_WIKI §1.4 逐批实现、验证、CU 预测试及用户验收，再进入下一批；原阶段 D-7 不冒充本轮验收。

- [x] b1 / 反馈 1：修复扩展/技能市场检查更新 `cli op got non-envelope output: ''`，覆盖真实常驻 CLI 与失败后重试。
  - PR #53 实现、本地门禁、远端 Workbench/三平台 CLI 与 Windows CU T1–T4 已通过；用户已确认 b1 通过并合入 develop。
- [x] b2 / 反馈 2、5、6：已安装/市场/子技能功能简介、内联详情与布局修复。
  - 实现、本地门禁、真实数据面、生产候选、Windows CU B2-T1–T3 与用户验收已通过；PR #54 待合并。
- [x] b3 / 反馈 3：默认安装 GitHub MCP，接入既有双引擎默认配置，认证状态如实展示，不内置凭据。（实现、门禁、真实数据面、生产候选、远端 CI 与用户验收通过；PR #55 已合入）
- [ ] b4 / 反馈 4、9：退出更新启动交互式 setup.exe，安装成功后清理此次下载包；实测对比旧/新安装包组成并减少冗余体积。（实现、门禁、NSIS 优化、远端 CI 与真实启动清理通过；完整安装 CU/用户验收待执行，PR #56 已合入）
- [ ] b5 / 反馈 7、8：修复 Work Record 分支会话失败及失败标签回收；移除单会话右键新建，记录/未归档分组“重命名”左侧增加新建加号，新会话归属对应工作记录（实现、门禁、生产构建、PR #57 CI 与合入通过；待全部批次 preview 整体实测）。
- [ ] b6 / 反馈 10.1–10.3：文件管理 Ctrl+C/V 与右键粘贴、Delete/右键删除、Ctrl/Shift 多选、文件/目录及多选路径拖入 Bash/CLI。（规格落档，实施中）

验收：2026-11-01 用户确认 b1、b2、b3 通过；PR #53/#54 已合入，b3 PR #55 已合入，随后进入 b4。

- 追加（v2.1.17 preview 反馈 #10；preview-fixes b6）
  - [ ] 文件/目录真实 CF_HDROP 复制粘贴、多选删除与目录/多路径终端拖入已实现；待 preview.N 统一实机验收后关闭
