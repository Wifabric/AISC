# Preview 修复预测试账本

## b1（2026-10-31）

结论：本地门禁、真实旧/新 CLI 恢复、Windows CU T1–T4 **PASS**。
用户单批验收 **PENDING**；不能把 agent 结果当用户验收。
产品 SHA `7c01bac16a4d5fc619cb34cc570f72d04f5e2d55` 的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/41113073318)
与 [CLI 三平台构建](https://github.com/Wifabric/AISC/actions/runs/41113143095) 均 SUCCESS，draft PR #53。

### 产物与环境

- 工作分支 `codex/2.1.17-preview-b1-market-envelope`，develop 基线 `7cc5a25`。
- 候选目录 `release-staging/2.1.17-preview-b1/`，Tauri build --no-bundle 正式静态构建。
  Workbench SHA256 `8846df53c59de18065fdc245948901ce68a99ea78233972c3dc9f9dba3fdecc1`。
- 新冻结 CLI `0.1.10.dev0`，SHA256 `765592ae3df28cec8f0516d79cea563f5f58ff37448764bb94d813b7c2ac4225`；
  旧安装 CLI `%LOCALAPPDATA%/AISC Workbench/aisc.exe` 为 `0.1.9.dev0`。
- 镜像 `super-claude:2.1.17-preview-b1`，ID
  `sha256:9831ce1d36dfc0b874e97a97420118393a105726943e41c0f0cbd88bce61444d`。
  用原 closeout 完整 bundle/receipt 重建，source-version 为 `0.1.10.dev0`，不改 latest。
- 独立数据根 `C:/pt/aisc217pfb1-data`，主工作区 `C:/pt/aisc217pfb1-workspace`。
  真实进程测试 runtime `741bd054-b971-4a1a-8df7-47aa9b819044`；GUI 正常回收无 lease
  测试 runtime 后新建 `f8b0d568-e2ff-45fa-b643-789623f36907`，容器 `aisc-wb-f8b0d568` / `77493241c310`。
- 第二工作区 `C:/pt/aisc217pfb1-workspace-other`，同镜像独立容器 `dee22d3f73b8`。
  未复制用户凭据或历史，未改正常数据根配置。完整本机路径与校验见 [b1-artifacts.json](b1-artifacts.json)。

### 自动化与真实数据面

| 验证 | 实际结果 | 结论 |
| --- | --- | --- |
| 新回归先 RED 后修复 | extensions 未知 op/缺参等4组中3组先复现空 envelope；修复后 AISC_ERR_USAGE / exit 2 | PASS |
| Python 定向 / 全门禁 | 19 passed / 15 subtests；全测 1699 passed、53 skipped、195 subtests | PASS |
| Rust lib / 前端 / 类型 | 407 passed、2 ignored；97 files / 822 tests passed；vue-tsc 通过 | PASS |
| 显式执行真实恢复测试 | 旧冻结 serve 复现→direct stderr 确认不支持→新冻结 CLI 同工作区成功→显式覆盖不切换；9.29秒，1 passed | PASS |
| 冻结 CLI / 生产 UI | PyInstaller 成功；Tauri custom-protocol 正式静态构建成功 | PASS |
| 含真实插件的更新数据 | 14 skills + frontend-design@claude-plugins-official 1.1.1，共15项；exit_code=0，errors=[]；unsupported/update_available=false 且保留原因 | PASS |
| 文档与 diff | check-docs 39 passed / 0 warnings / 0 failures；diff --check 通过 | PASS |

日志均在 `C:/pt/`：`aisc-217-pf-b1-python.log`、`aisc-217-pf-b1-rust-final.log`、
`aisc-217-pf-b1-vitest-2.log`、`aisc-217-pf-b1-real-recovery-2.log`、
`aisc-217-pf-b1-production.log`、`aisc-217-pf-b1-final-updates.json`。
Rust 的两条 ignored 中，本轮真实进程项已独立执行通过，另一条是既有环境测试。

### Computer Use（约 02:33–02:53，Asia/Shanghai）

使用 computer-use 技能的 node_repl + @oai/sky；直接操作真实 Workbench，未在 Bash/
Codex/Claude 终端 UI 输入命令。依赖故障通过工具命令在自有隔离容器中可逆设置。
主窗口 `26086558`、第二工作区窗口 `1117150`，均按返回对象选择、逐次刷新。

| 项 | 操作与实际窗口树/字段证据 | 结论 |
| --- | --- | --- |
| T1 旧 pin 恢复 | 初始设置确指向旧安装 CLI；启动本批镜像，扩展→检查更新，忙碌结束无原错误；caveman 13项、mattpocock/skills 1项保留，pin 实际变为本批目录 aisc.exe | PASS |
| T2 三市场查询 | 独立市场技能 research：出现 research（742211）等，点击有中文详情；MCP github：10条，GitHub（6059）详情/原文可读；插件 frontend：12条，frontend-design（1266133）详情可读；各页“已刷新/上次成功” | PASS |
| T3 重复/服务/隔离 | 重复检查结束；真实安装的 frontend-design 仍在，卡片“暂无可靠版本源 / claude-plugins-official · 1.1.1”；服务页宿主工具及“暂无已注册服务”正常。操作→从文件夹打开 workspace-other，启动同镜像，插件为空、检查后仍空；回主窗口插件1.1.1保留 | PASS |
| T4 失败后重试 | 暂时 mv 主容器适配器到同目录 .pfb1-backup，点击检查：警报含“extensions updates-check failed: aisc-scope: line 21: /usr/local/bin/aisc-extensions-adapter: No such file or directory”，列表保留；恢复后直接再检查，警报消失、忙碌结束，未重启 | PASS |

窗口树证据 `C:/pt/aisc-217-pf-b1-other-window.txt`、`C:/pt/aisc-217-pf-b1-main-window.txt`；
失败警报原文如 T4。截图在本次工具调用结果，未另导出截图文件。

### 限制与后续

- Remote/无 sidecar 只有策略单测，显式覆盖另有真实进程验证；未运行真实 SSH。
- 上游未给可靠版本字段时仍明确 unsupported；真实插件为 metadata unavailable，未伪称最新版或执行更新。
- 模板简介、详情蓝框、错误长文挤压按钮在 CU 复现，属于已登记 b2，本批未改这些 UI。
- 初次普通 cargo release 候选访问 localhost:9000，已换为上列正确生产产物后完成 CU。
  初次真实测试未 drain pool 导致不退出，补清理后通过。初次 Vitest cwd 错误已正确重跑全绿。
- 用户验收尚未进行，b2–b6 未实施；原阶段免补测不适用于本轮。
