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
