# v2.1.17 收尾统一预测试（2026-10-30 至 10-31）

本文件是收尾候选的权威增量记录；历史批次记录保留。用户已确认 R3/R4 手测通过，
未测项留统一回归。结论为**已执行项 PASS，环境项仍 NOT RUN，等待用户统一回归**，
不宣称所有批次完整 CU、Remote 或发布验收通过。

## 固定产物与环境

- 产品提交 `cf2567127d25dd14e2e25817db4667ab5be0d44c`；PR #52 合入 develop
  `bc189a3cd5dd598ef3e0e28c72b82a13634622fd`。本轮没有修改 GUI/Rust，GUI 字节沿用
  R4 产品提交 `df332967201ab6338c4efe8f240288605131240a` 的最终生产构建。
- 本地目录 `release-staging/2.1.17-closeout`（忽略产物），启动器 `start-handtest.ps1`；
  `-VerifyOnly` 校验 GUI/CLI/adapter SHA256 和镜像 ID，通过后才允许启动。
- GUI `AISC-Workbench-2.1.17-CLOSEOUT.exe` SHA256
  `1ef06065f9f399516a47f344e52e734ffb0b400f8d6ccf3931985d32e6ed72b4`。
- CLI `aisc-closeout.exe` SHA256
  `b9ac5b84d3da39afa023553d07fe7a0cc36c8e5836ade75da9a353340bb52f47`；adapter SHA256
  `97464109c7aec00d1721fb06716b9ce513b61c5fe97e669637a60f969a7e2c5f`。
- frozen CLI 从干净 stage bundle 无缓存构建镜像 `super-claude:2.1.17-closeout-final`，
  ID `sha256:7f82194edeeda7a2668a071c73ba63c92f99485ebb95aafb06807c03b7377e64`。
- Node 26.13.0、Codex 0.166.0、Claude 2.1.314、cc-switch 5.11.3、Mihomo 1.19.33、
  Yazi 26.9.1 实测版本和 geodata 三份 SHA256 均与锁版一致。
- Windows 11，Computer Use `node_repl + @oai/sky`，窗口 ID `48236006`；截图 1365×672。
  工作区 `C:/pt/aisc-closeout-workspace`，隔离数据根 `C:/pt/aisc-217-r4-handtest-data`；
  GUI runtime `b290f18e-da74-4ab0-9159-16c03ee0e21f`，容器 `2242e9954846`。
- 只复制四份明确的 R4 测试 transcript 和 reports 测试附件，未复制 provider/凭据；
  原文件不改。hash 清单 `C:/pt/aisc-closeout-reading-import.json`。

## 已执行结果

| 范围 | 操作与字段级理想结果 | 实际与结论 |
| --- | --- | --- |
| 门禁 | pytest/Rust/Vitest/vue-tsc 无失败 | Python 1697 passed/53 skipped/191 subtests；Rust 405 passed/1 ignored；Vitest 97 files/822 tests；vue-tsc PASS |
| 供应链/构建 | payload 校验、vendor、干净 bundle、无缓存镜像与安装形态均成功 | vendor 1533 项、refresh 9 verified/0 missing、bundle stage/verify、版本同步、文档 39 检查 PASS；最终镜像 ID 如上 |
| CLI 安装 | wheel/sdist 在新 venv 重装、卸载重装，pipx 与 off-checkout 均可运行 | clean-room 全部 PASS；twine 检查通过，日志 `C:/pt/aisc-closeout-install-check-2.log` |
| 真实扩展三轮 | 每轮 Skills/MCP/Plugins 搜索、安装、更新、卸载达到成功终态 | full-three-rounds 12 phases 全 PASS，分类轮次 9/9，exit 0，532.736 秒；含 bootstrap、部分失败/仅失败项重试、caveman 首装双开和升级保留 off |
| 启动 CU | 选隔离工作区、通过五项预检、指定最终镜像并启动 | 显示就绪、Bash 与相同 runtime；扩展默认 caveman 13 项、mattpocock 1 项，PASS |
| 市场 CU | 扩展→扩展市场→推荐→科学研究→任一卡片 | 独立弹窗、六分类、科学研究 10 个 article；整宽卡片内展开中文简介/类型/来源/安装量/来源链接，不出现右侧空栏，PASS |
| 来源 CU | 市场→来源管理，分别切技能/插件/MCP | 技能 4 仓库且已启用，插件 2 市场，均有删除入口；MCP 内置来源说明；无 skill-repos-list argparse 报错，PASS；本轮未点击最终删除 |
| 技能搜索 CU | 市场→技能→搜索 caveman→点击子技能 | 已刷新、父组 13 子技能；子技能右详情显示中文简介，PASS |
| 已安装空态 CU | 关闭市场→扩展→MCP | 仅“暂无内容。”，空态无第二个市场按钮；顶部市场入口保留，无操作日记，PASS |
| Services CU | 服务视图查看宿主/注册分组与两端口 | “宿主工具（F2）”“注册服务”；3000 closeout docs 在前、5173 端口回退名在后，HTTP/已注册/网关就绪和复制/打开入口，PASS |
| 服务数据面 | frozen CLI 注册真实 3000/5173 HTTP 服务，经网关逐一 GET | 两者均响应 `closeout gateway ok`，gateway ready/host_port=47001；`C:/pt/aisc-closeout-services.json`，PASS |
| 阅读 CU | 工作记录→点击合成 Codex 记录正文，展开“思考与执行”，向下滚动 | 默认单折叠“思考与执行 3 项”；展开显示思考过程/过程说明/exec_command；表格/任务列表/高亮代码/复制入口/脚注/行内和独立公式可见，无公式内部多余竖滚动条，页脚“第 1–5 条 / 共 5 条”“会话阅读 · 只读快照”，PASS |
| 图片降级与加载 CU | 先不复制 reports 打开记录，再复制既有测试附件后关闭重开 | 缺文件显示“图片不可用: 本地图片”；补齐 reports 后 UIA 为“图形 本地图片”，不再不可用，PASS（该样例是小尺寸测试图） |
| 真实问答 CU | Escape 后分别点真实 Codex/Claude 记录正文 | 两者各显示两轮问题和回答，页脚“第 1–4 条 / 共 4 条”；第二问不含标记，回答分别为 R4-RESUME-1030-CODEX/CLAUDE，PASS；是旧恢复证据的静态阅读，本轮未重新发模型请求 |
| 恢复既有证据 | 沿用 R4 已认证两提供商的进程/隔离容器中断恢复 | 同 native ID 与原生上下文召回 PASS；用户已验收。本轮新工作区未复制凭据，不冒称新锁版两提供商认证恢复已重跑 |

数据面主证据 `C:/pt/aisc-closeout-smoke-1030/run/summary.json`，同目录保留 events、
逐阶段 stdout/stderr；父目录有镜像/容器 inspect 和实际 harness 快照。
数据面三轮不等价于三轮完整 CU，也不等价于 MCP 握手/认证成功。

## 远程构建与安装形态

产品 SHA `cf25671` 四条 workflow 全 SUCCESS，产物列表与步骤摘要保存在
[closeout-ci-evidence.json](closeout-ci-evidence.json)：

- Workbench CI [41083807037](https://github.com/Wifabric/AISC/actions/runs/41083807037)。
- 三平台 sidecar [41083821623](https://github.com/Wifabric/AISC/actions/runs/41083821623)：
  Verify artifact、parity、clean-room、SBOM/integrity 各平台均成功。
- Linux/macOS [41083807638](https://github.com/Wifabric/AISC/actions/runs/41083807638)：
  deb/dmg 实际上传成功，非 checkout 目录解包/挂载后运行 sidecar 与 bundle discovery 均成功。
- Windows NSIS [41083815402](https://github.com/Wifabric/AISC/actions/runs/41083815402)：
  实际上传 698985810 字节资产，安装/PATH/升级/卸载保留数据 smoke 成功；publish skipped 符合无 tag 预期。
- 只核对 GitHub artifact 元数据/digest 与实际 CI smoke，没有把远端资产下载到本机安装。
  本机显式更新 Explorer/正常 NSIS 交互沿用 10-29 预测试；新包交互安装仍待用户统一回归。
- develop 集成 `bc189a3` 的四条 CI 独立复核结果见 CLOSEOUT.md，不能用分支成功代替。

## 保留 NOT RUN 与用户统一回归

按 HANDTEST 文首 C0–C5 复核高频交叉链路，余项按以下边界执行或明确延后：

- 全局 Docker 引擎意外断连、Remote SSH、真实大历史分页；不得为测试停止其它工作区。
- 新锁版 Codex/Claude 的已认证中断恢复；本轮仅旧 transcript 阅读兼容与 R4 已验收恢复证据。
- 故障网络 H2/H3、b2 断网缓存回退/清空竞态、b3 第二 attempt 的 UI 路径、b4 离线禁用、
  b5 诊断竞态、b6 A→B→A 隔离、完整三轮 UI 冒烟、来源最终删除/窄屏键盘细节。
- MCP 真实握手与需要第三方认证的流程、当前候选 NSIS 显式更新及交互安装。

本轮未发现新增产品 FAIL。历史失败（错误 editable 源、旧版本断言、CRLF 校验、
生成缓存、clean-room 命令误用）均保留在 CLOSEOUT.md 与原日志，修正后相关验证重跑通过。
