# R4：Work Record 阅读与中断恢复

2026-10-30 用户明确要求本批实施；追加 Docker 意外断连 / bash 会话中止后的恢复修复。
按 DEVELOP_WIKI §1.2 先入 target、分支先行，再实现与逐批验收。用户本轮转向 R4；
R3 保留待验收，不视为已通过。R4 完成后等待用户验收，不继续堆积新批次。

## 规格

- 终端实时交互继续字节穿透；阅读器只读取持久化记录，不串流、不打字输出、不显示输出阶段。
- 阅读器重新排版为宽阅读弹窗：标题、提供商、问答正文、历史分页、返回/关闭；适配明暗主题、窄窗、键盘关闭与焦点回归。
- 每一轮问答之间的思考、命令、工具结果与过程说明合成一个默认折叠的“思考与执行”项；展开后逐项查看，正文答案保持可读。
- Markdown 支持标题、列表、任务、表格、引用、代码高亮、脚注、链接和图片；支持 LaTeX 行内及独立公式。错误公式保留可读文本。
- Codex 与 Claude 的多模态块保留：图片（内嵌、网址、工作区文件）可见；音频、文档等不支持内嵌的对象有可读附件名称和可用链接，不静默丢弃。未知块有可展开文本兜底。
- 网址经系统浏览器打开；文件链接通过工作区已有 containment 边界打开，支持容器 /app、/root/app 与宿主工作区路径；越界路径不交给系统执行。记录 HTML 不执行脚本。
- 长回答提高预算并显式报告截断；历史超过边界需明确提示，不能显示伪造的完整尾部。切换会话/工作区后旧请求不得覆盖新正文。
- 恢复时保留 provider-native 会话 ID；配置引导、失败重试和重新打开不得退化成新会话。恢复前观察 runtime；Docker 尚未恢复时显示可重试错误，不创建无效页签；容器已停止时恢复既有 runtime，禁止删除用户容器/记录。

## 设计记录

对象：用户问题、助手答案、执行证据、附件、持久化会话 ID。常见单次 10–100 条，长记录分页。
主要问题：“上次问了什么、答案是什么，如何继续同一段工作？”
保留 Vue/Pinia/Tauri 与现有主题/字体。采用 framed-sheet 的平面阅读纸张，标题与正文共轴；
单列正文最大 920px、16px 阅读字号、1.75 行高，问题用浅底，答案直接排版。
产品特征：每轮单一证据折叠，保持问答主线；不引入聊天输入框。

## 实施与验证

- [x] RED：记录解析多模态/phase/长回答/损坏尾部；聚合、富文本和链接；中断恢复与引导重试。
- [x] GREEN：后端投影与 wire 类型；安全 Markdown/数学/附件阅读；恢复路径。
- [x] targeted Python / Vitest / Rust、vue-tsc；本地完整门禁和生产构建。
- [ ] Computer Use：本地真实阅读/折叠/链接及两提供商认证后进程/容器恢复主链通过；完整引擎断连/真实大历史/Remote 未测，见 PRETEST，待验收或明确延后。
- [x] 更新 HANDTEST / PRETEST / todo / devlog；本批精确复核步骤及两提供商已认证恢复证据已回写。
- [x] 用户验收：2026-10-30 用户明确确认“R3、R4 已手测通过，未测项留统一回归”；按 D-6 进入收尾，不把未测项目标成 PASS。

## 已识别风险

现有读取会丢弃图片、8k 截断正文、4000 条后仍继续读文件但保留头部。现有 resume
只校验记录文件；provider 探测失败跳转 guide 后 openTab 不再携带原 resume ID。
这些必须用回归测试固定。Docker 全局重启会影响其它工作区；预测试只中止本批隔离容器。

自审补充：新建会话与记录自动关联时，也必须把原生 ID 绑定到唯一匹配的 pane；
分屏中恢复已有会话须激活对应 pane，不能误激活旁边的 Bash。多个同类 pane 时不猜测关联。
旧 openSession 的失败响应不得把已重开的新会话改为失败。
视觉复核补充：深色阅读链接与代码关键字采用专用高对比语义色；保留产品现有系统字体栈，
数学字体为 KaTeX 公式结构所需，不受普通界面“两种字体”检查限制。

## 当前验证证据（2026-10-30）

- 全门禁：Python 1697 passed / 53 skipped / 191 subtests；Rust 405 passed / 1 ignored；Vitest 97 files / 822 tests；vue-tsc 通过。日志 `C:/pt/aisc-r4-gates.log`。
- 自审新会话 pane 关联用例先 RED，再修复；最终前端全测 822、vue-tsc 及阅读/runtime targeted 29 通过。
- 冻结 CLI、最终 Tauri release 及独立阅读组件生产构建通过；版本仍为 Workbench 2.1.17 / CLI 0.1.10.dev0。
- 深浅两主题 × 1440/768/390 生产组件截图检查：0 FAIL；保留一项 hero-void 警告，窄表/公式旁留白属于阅读列，未增加无意义面板。数学结构需要 KaTeX 多字体，原有产品系统字体栈保持，font-count/font-fallback 为记录在案的例外。
- 浏览器组件交互 PASS：单折叠/逐项工具结果、代码复制参数、文件/网址路由参数、Escape 关闭。组件 harness 使用隔离数据与 store spy，不能代替真实 IPC。
- 真冻结 CLI：两条夹具均可 list/preflight/read，Claude 图片附件保留；Codex 损坏尾行仍允许 preflight，reader malformed_lines=1，前后原文件 SHA256 相同。
- 真 Workbench CU：Codex/Claude 阅读、单折叠/逐项执行证据、数学与图片节点均已观察；停止隔离容器后从记录恢复，重启同一个容器 c4da83e8aa5d / runtime df5c8f56-ea51-4ad2-9a77-14682db0e9e7 成功。
- 首轮隔离环境无 Codex/Claude Provider 认证，Codex 仅恢复到登录引导；用户随后自行配置两者并处理 Claude 首次工作区信任。本轮 FINAL 已分别通过 Codex/Claude 真实记录恢复、进程强制中止重开、隔离容器停止后同容器/runtime/native ID 恢复。关闭 TUI 并确认进程退出后，原生 CLI resume 追加不含标记值的问题，两者都回答原标记，确认上下文连续；CU 阅读器均显示两轮完整问答（第 1–4 条 / 共 4 条）。CU 只操作 Workbench 记录/窗口并观察，未在 Codex 终端自动输入；上下文召回为 CLI 补充证据。Claude 运行期间自行从 2.1.311 更新为 2.1.314，准确边界已记 PRETEST。
- 最终产物与 SHA256 见本机 `release-staging/2.1.17-r4/artifacts.json`；启动器 `start-handtest.ps1` 校验 Workbench/CLI/adapter，使用 R4 隔离数据根。当前旧 R3 用户验收状态保持待验收。
- 阅读增量修复：真实 WebView2 公式出现额外竖滚动条，补充垂直留白并禁止公式内部纵向滚动；FINAL SHA256 `1ef06065…`。生产组件公式 clientHeight/scrollHeight=61/61；FINAL 真阅读公式完整。最终三宽视觉检查 0 FAIL / 1 阅读留白 WARN，已看桌面/手机图；targeted 29、vue-tsc 与生产构建通过。
- 真 IPC 补充：代码复制显示“已复制”、文本报告启动 Notepad、Escape 关闭；FINAL 网站链接启动系统 Chrome 的 Wifabric/AISC 页面。本机 .md 没有默认关联，手册增加 .txt 成功路径。
- draft PR #51：https://github.com/Wifabric/AISC/pull/51；首轮提交 f1bd8ee 的 Workbench CI 41005979469、最终产品提交 df33296 的 41022607098 均 SUCCESS。完整证据/仍未执行项见 PRETEST；两提供商本地认证恢复主链通过，用户验收尚未完成，不进入下一批。
