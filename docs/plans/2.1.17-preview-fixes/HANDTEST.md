# Preview 修复逐批验收

## b1 市场更新检查

前置：Docker Desktop 运行。当前已打开隔离候选，主窗口标题为
`aisc217pfb1-workspace · Bash · AISC Workbench`，另有 `workspace-other` 窗口。
主工作区有 caveman 13 个技能、grill-me 1 个技能、frontend-design 插件 1.1.1；无需 Provider。
若已关闭，PowerShell 运行校验式启动器：

```powershell
$repo = 'C:\Users\wangyu\.codex\worktrees\217-b1-proxyless-extension-reliability\AISC'
& "$repo\release-staging\2.1.17-preview-b1\start-handtest.ps1"
```

若出现选择工作区，输入 `C:\pt\aisc217pfb1-workspace`→下一步；启动摘要→更改设置，
镜像选 `super-claude:2.1.17-preview-b1`→启动。不要启动旧安装目录的 Workbench。
预测试细节见 [PRETEST.md](PRETEST.md)，用户验收当前待确认。

1. **T1 检查更新**：左侧扩展→技能→检查更新，等待按钮恢复，再检查一次。
   理想：无 `cli op got non-envelope output: ''`；caveman 13项及另一技能组1项保留，
   C/X 状态不变。插件页仍有 frontend-design / 1.1.1，“暂无可靠版本源”表示上游
   没有可靠比较字段，不应伪称“已是最新”。
2. **T2 独立市场**：扩展市场→技能，输入 research→搜索→点击 research；MCP 搜
   github→点击 GitHub；插件搜 frontend→点击 frontend-design。
   理想：查询结束出现“已刷新/上次成功”，都有结果和详情，无原空输出错误；安装量
   是实时值可变化。模板简介与蓝框属 b2，本批只确认数据链路。
3. **T3 服务和隔离**：关闭市场再检查；切左侧服务，应有“宿主工具”和“注册服务”，
   无协议报错；切回扩展。到另一个 workspace-other 窗口→扩展→插件→检查更新，
   理想：第二工作区保持“暂无内容”；回主窗口 frontend-design / 1.1.1仍在。
   第二窗口若关闭，通过操作→从文件夹打开工作区选择
   `C:\pt\aisc217pfb1-workspace-other`，用同批镜像启动。
4. **T4 失败重试（agent 已预测试，用户可按需复核）**：仅主测试容器仍存在时，
   PowerShell 执行第一条命令→UI 扩展→检查更新→观察错误→执行第二条恢复→UI再检查。

   ```powershell
   docker exec aisc-wb-f8b0d568 mv /usr/local/bin/aisc-extensions-adapter /usr/local/bin/aisc-extensions-adapter.pfb1-backup
   # 观察失败后立即恢复，即使不继续测试也要执行下一条
   docker exec aisc-wb-f8b0d568 mv /usr/local/bin/aisc-extensions-adapter.pfb1-backup /usr/local/bin/aisc-extensions-adapter
   ```

   理想：失败含 `No such file or directory`，列表保留；恢复后再检查无错误且按钮恢复，
   无需重启。重开工作区使容器名变化时跳过固定命令，告知 agent 重新准备，不猜容器名。

异常：原错误复现、按钮卡住、隐藏真实错误、列表丢失/串工作区或后续调用失败均不通过。
请反馈“b1 通过”或 T 编号与实际文案。依 DEVELOP_WIKI §1.4，单批验收/明确放行后才进入 b2。
其它批次精确步骤在对应批实施前补齐。

- 2026-10-31 用户批次验收：用户明确回复「b1 通过，进入 b2」。b1 关闭；PR #53 已合入 develop `cb60cd4`，最新提交 Workbench CI SUCCESS。
- 2026-10-31 用户批次验收：用户明确回复「b2 通过，进入 b3」。B2-T1–T3 关闭；PR #54 的实现、门禁、CU 与用户验收均通过。

## b2：功能简介与内联详情

### 前置准备

Docker Desktop 已运行。候选 `release-staging/2.1.17-preview-b2/`，独立数据根
`C:/pt/aisc217pfb2-data`，测试工作区 `C:/pt/aisc217pfb2-workspace`；镜像
`super-claude:2.1.17-preview-b2`（精确标识见本批 artifacts.json）。只使用本批
候选，不在旧 b1 或普通安装窗口复核。校验并打开候选：

```powershell
$repo = 'C:/Users/wangyu/.codex/worktrees/217-b1-proxyless-extension-reliability/AISC'
& "$repo/release-staging/2.1.17-preview-b2/start-handtest.ps1"
```

首次打开从首页点击置顶测试工作区，再按「启动」；镜像选择 b2。预测试完成后
候选保持打开，可直接复核。隔离环境无用户凭据，skills 为默认 caveman/grill-me，
另准备只用于查看的 MCP 与真实 frontend-design 插件；不要求执行安装/删除。

### B2-T1：已安装简介与折叠

1. 左侧视图栏「扩展」→「技能」，点击 JuliusBrussee/caveman 组标题。
2. 观察组简介，然后点击 caveman-evidence-review、caveman-compress 子技能。
3. 再点同一子技能收起；点组标题收起，再展开。
4. 切「MCP」→点测试文件服务，切「插件」→点 frontend-design。

理想结果：组下同时有功能简介和13条子技能；证据审查介绍 Caveman Cloud 费用、
调用链/延迟/节省，压缩技能介绍记忆文件/CLAUDE.md/待办压缩。每次仅所选子技能
行下出现介绍，折叠后详情消失；MCP/插件介绍实际文件访问/前端设计能力，均在自身
卡片内，后续条目顺排，不被底部浮层遮住。来源独立可见，不出现“这是一个来自…；
安装前请核对…”套话。

### B2-T2：市场功能与按需描述

1. 「扩展市场」→「推荐」→点击科学研究分类首个推荐，再点第二个。
2. 切「技能」，搜索 `research`，点击一个有中文推荐简介的技能，再点击另一个
   不在本地推荐目录的技能（预测试会记录具体名字）。
3. 切「MCP」搜索 `github` 并打开结果；切「插件」搜索 `frontend` 并打开结果。
4. 点击当前条目再次收起，再打开另一条；关闭弹窗。

理想结果：详情跟随对应卡片展开，无固定右侧窄栏；推荐显示具体任务和场景。
目录之外的技能先显示“正在读取上游功能介绍…”，成功后显示实际 SKILL.md 介绍；
无中文校订时保留上游原文。MCP/插件正文是实际市场功能描述。请求失败只影响当前
详情，有原因和「重新读取」，不清空搜索结果、不卡住安装按钮、不串到其它条目。
只有真正缺失描述才显示“暂无功能介绍，可查看来源说明”。

### B2-T3：窄栏、长文与焦点

1. 关闭弹窗，拖动侧栏右边界缩到约280px；展开技能组、子技能和MCP/插件详情。
2. 滚动到末尾再回顶部；点「扩展市场」打开推荐及三类搜索详情。
3. 鼠标点击条目，随后按 Tab/Shift+Tab 遍历按钮，按 Enter 展开；在详情内
   源链接/按钮获得焦点时按 Escape 收起，再按 Escape 关闭市场。
4. 检查更新（正常应无 b1 旧错误）。CU 另外通过可逆适配器故障制造长错误，
   验证错误换行且两个工具栏按钮仍完整，再恢复并重试。

理想结果：介绍自动换行、来源不撑宽，按钮完整可见，滚动可以读完正文与操作区；
鼠标点击无蓝色大框，键盘仍有清晰内收焦点框；焦点框不越过卡片边缘。详情 Escape
收起后焦点回所选条目；关闭市场回「扩展市场」按钮；长错误显示于按钮下方。

异常判定：详情缺失/被盖住、按钮或焦点框裁切、同名技能套用别人的简介、点击其它
条目仍出现上一个介绍、失败清空列表，均反馈具体页签/条目名与操作步骤，b2不通过。

- 2026-11-01 用户批次验收：用户明确回复「b3测试通过，进入下一个批次开发」。B3-T1–T3 关闭；生产候选、真实容器数据面与用户实机验收通过。

## b3：默认 GitHub MCP

### 前置准备

Docker Desktop 已运行。候选 `release-staging/2.1.17-preview-b3/`，独立数据根
`C:/pt/aisc217pfb3-data`，测试工作区 `C:/pt/aisc217pfb3-workspace`；镜像
`super-claude:2.1.17-preview-b3`（精确标识见 b3-artifacts.json）。校验并打开：

```powershell
$repo = 'C:/Users/wangyu/.codex/worktrees/217-b1-proxyless-extension-reliability/AISC'
& "$repo/release-staging/2.1.17-preview-b3/start-handtest.ps1"
```

若启动摘要仍选默认 `super-claude:latest`，先点「更改设置」把镜像改为
`super-claude:2.1.17-preview-b3`；不要用旧镜像复核。隔离环境不提供 GitHub PAT。

### B3-T1：默认安装与认证状态

1. 新工作区启动 ready 后，左侧「扩展」→「MCP」。
2. 展开 `GitHub` 条目并等待详情读取完成。
3. 理想结果：列表默认有 GitHub，Claude/Codex 均开启；详情显示官方功能介绍、
   HTTP URL `https://api.githubcopilot.com/mcp/`，认证为
   “未配置（需要 GitHub PAT：GITHUB_PAT_TOKEN）”。不显示任何 token/Authorization 值，
   也不把未认证写成可调用成功。

### B3-T2：用户开关与重启保留

1. 关闭 GitHub 的 Claude 开关，等待列表刷新。
2. 重启工作区/runtime，再进入「扩展」→「MCP」。
3. 理想结果：GitHub 仍在；Claude 保持关闭、Codex 保持开启。容器内 Claude 项目
   MCP 配置不再包含 AISC 默认 `github` 键，Codex `[mcp_servers.github]` 仍为官方
   URL 与 `bearer_token_env_var = "GITHUB_PAT_TOKEN"`。其它 MCP 配置不变。

### B3-T3：自定义同名不被覆盖

1. 仅在已有自定义 `github` MCP 的隔离测试环境中执行；不要改真实用户配置。
2. 重启工作区后展开 GitHub。
3. 理想结果：自定义 URL、名称、启停状态和 live 配置原样保留；AISC 不把其改回
   官方 URL，也不写入 token。若不存在该环境，此项以 PRETEST 的真实容器证据为准，
   不要求用户手工改数据库。

异常判定：默认 GitHub 缺失、双引擎未默认开启、重启后覆盖用户开关、自定义同名被
改写、认证状态误报“已配置”或泄露凭据，均判 b3 失败。

- 2026-11-01：b4 实现、全量门禁、x64 NSIS 构建与真实启动清理预测试完成，待用户验收。

## b4：显式更新清理与包体积

### 前置准备

候选与校验脚本位于 `release-staging/2.1.17-preview-b4/`（实施完成后生成）。
B4-T1 使用隔离 TEMP 和数据根，不触碰真实 Downloads 或用户手动下载。

### B4-T1：成功升级后的下载包清理

1. 关闭其它 AISC Workbench，运行候选目录的 `start-cleanup-pretest.ps1`。
2. 脚本会预置一个已验证 receipt、假的 `workbench-setup-2.1.16.exe` 和无关
   `user-download.exe`，然后启动候选。
3. 等待脚本返回。理想：旧目标安装包与 receipt 被删除；无关文件保留；脚本输出
   `PASS real Workbench startup cleanup`。取消安装/失败保留由自动化回归覆盖，
   不要求用户手工破坏安装流程。

### B4-T2：包体积与离线闭包

1. 打开 `package-size-intake.json` 与候选 NSIS 文件属性。
2. 理想：x64 安装包约 384,516,079 字节（本地构建允许因签名/时间戳小幅差异），
   相比 preview.1 的 698,809,734 字节减少约 314.3MB；7-Zip 列表只包含
   x64 Codex/Claude/yazi payload，不包含 arm64 payload；bundle verify PASS。

异常判定：清理无关文件、未复验 hash/size、取消或失败后删除、双架构 payload 再次
进入同一安装包、bundle verify 降级或 arm64 包缺失导致对应平台无法离线安装，均判失败。

## b5：工作记录分支与分组新建会话

前置：preview.N 发布后直接更新安装；准备至少一条可恢复的 Codex/Claude 会话和一个活动工作记录。

### B5-T1：分支原上下文与失败回收

1. 左侧“工作记录”→右键成员→“分支会话”。
2. 理想：只新增一个该引擎标签，进入原会话上下文的 fork；原会话标题、成员位置和原标签不变。
3. 若启动失败：只回收本次失败新标签，其他标签不关闭；错误可读且原 Work Record 成员保留。

### B5-T2：分组新建会话

1. 活动工作记录标题操作区点击“重命名”左侧“＋”。
2. 理想：按该记录既有 Claude/Codex 引擎打开新会话；首次输出可被唯一识别后自动加入该工作记录，不落入未归档。
3. 刷新/重启后成员归属保持。空记录默认使用 Codex。

异常：原会话被改写、失败标签残留、成功新标签误关、新会话掉入未归档、归属错到同名其他记录、多标签上限被绕过均判失败。

## b6：文件管理

前置：preview.N 发布后直接更新安装；准备一个本地工作区，含普通文件、中文名/空格
文件、子目录和目标同名冲突；另开一个 Bash 或 CLI 会话。

### B6-T1：多选复制/粘贴与 Explorer 兼容

1. Ctrl 点选 2–3 个文件/目录，Ctrl+C 后在 Windows 资源管理器粘贴。
2. 理想：资源管理器得到全部真实文件/目录；不写入命令文本。
3. 在资源管理器复制一个文件，回到 Explorer 选中目录或空白后 Ctrl+V/右键粘贴。
4. 理想：本地工作区能粘贴；同名自动生成不覆盖后缀；远端工作区不误走本机文件面。

### B6-T2：多选、删除与部分失败

1. Ctrl/Shift 选择多项，普通单击仍只选/打开当前项；目录单击仍展开。
2. Delete 或右键删除，确认一次。
3. 理想：全部成功显示数量；某项被占用时其它项继续删除，报告列出成功与失败路径、
   稳定错误，不覆盖越界路径，也不留下未确认删除。

### B6-T3：粘贴目标与边界

1. 选中目录粘贴 → 进入该目录；选中文件/空白粘贴 → 进入其父目录/根。
2. 多选混合粘贴 → 不猜测，不覆盖；失败/成功逐项可见。
3. 尝试删除 `..` 或工作区外路径无入口；Rust containment 拒绝。

### B6-T4：目录与多选拖入终端

1. 将目录、单文件、Ctrl 多个混合条目拖到 Bash/CLI 输入区。
2. 理想：输入区按稳定顺序出现全部 quoteForTerminal 路径；空格/中文/特殊字符安全；
   不自动执行；操作系统文件拖拽不被误当成 AISC 路径执行。

异常：剪贴板是文本却假成功、远端路径落到宿主 FS、同名被覆盖、单项失败阻断全部、
目录拖入不可用、多选乱序/漏项/重复、终端自动回车，均判 b6 失败。
