# 进度

- 2026-10-31：登记用户十项手测反馈，拆分六个顺序批次；b1 分支从最新 develop `7cc5a25` 建立。
- b1：确认旧宿主 CLI pin 0.1.9.dev0 不支持 updates-check，空 envelope 稳定复现；补全 extensions argparse JSON 上下文，Workbench 仅在准确旧版本证据下尝试随附新 CLI，成功才写 pin。
- 本地门禁：Python 1699 passed / 53 skipped / 195 subtests；Rust 407 passed / 2 ignored；前端 822 passed；vue-tsc 通过。真实恢复测试另显式执行 1 passed / 9.29秒，含显式覆盖守卫。
- 冻结 CLI、生产 Tauri 静态 UI、匹配镜像完成；Windows CU T1–T4 通过：旧 pin 恢复、三市场/详情、重复/Services/双工作区隔离、适配器真实失败后不重启重试。
- 校验式启动器已备，HANDTEST 有准确路径和字段级结果；原始窗口树和日志位置、限制见 PRETEST。
- 产品提交 `7c01bac16a4d5fc619cb34cc570f72d04f5e2d55` 已推送；draft [PR #53](https://github.com/Wifabric/AISC/pull/53)。[Workbench CI](https://github.com/Wifabric/AISC/actions/runs/41113073318) 三个 job 与 [CLI sidecar build](https://github.com/Wifabric/AISC/actions/runs/41113143095) 三平台全部 SUCCESS；证据对应该产品 SHA。
- 当前：b1、b2、b3 已用户验收；PR #55 已合入 develop `bf886f2`，远端 CI 三项 SUCCESS。b4 下一个开工，b5–b6 顺序等待。

- 2026-10-31 用户批次验收：用户明确回复「b1 通过，进入 b2」。b1 关闭；PR #53 已合入 develop `cb60cd4`，最新提交 Workbench CI SUCCESS。b2 开始，尚未交付。
- 2026-10-31：b2 实施完成。补齐 adapter 的已安装 MCP/插件描述与只读 `skill-describe`，修正精确仓库简介，市场详情改为卡片内联展开，组/子技能简介、窄栏换行和键盘焦点已覆盖。Python 1705 passed / 53 skipped / 201 subtests，Rust 407 passed / 2 ignored，Vitest 98 files / 831 passed，vue-tsc 与生产构建通过；候选与镜像标识见 PRETEST。Windows CU 预测试完成。
- 2026-10-31 用户批次验收：用户明确回复「b2 通过，进入 b3」。B2-T1–T3 关闭，PR #54 可合并；b3 从合并后的最新 develop 开始。
- 2026-10-31：b3 从 develop `66d9549` 开工。官方 hosted MCP、Claude/Codex 指南与本机 cc-switch HTTP sync 行为已核实；规格落档，开始 RED 回归。
- 2026-11-01：b3 实现完成。官方 hosted GitHub MCP 默认进入 cc-switch SSOT 与双引擎 live 配置；AISC marker 保证用户启停与自定义同名配置不被覆盖，未内置 PAT。最终门禁 Python 1718 / Rust 407 / Vitest 833 / vue-tsc 通过，vendor 1534 校验通过；真实容器、生产候选与镜像标识见 PRETEST。
- 2026-11-01 用户批次验收：用户明确回复「b3测试通过，进入下一个批次开发」。b3 关闭；PR #55 远端 Workbench CI 三项 SUCCESS，已合入 develop `bf886f2`；进入 b4。
- 2026-11-01：b4 从 develop `b9f1dcf` 开工。初步归因确认 preview.1 安装包 698,809,734 字节比 2.1.16 增 405,685,606 字节，双架构离线 payload 是主要来源；显式更新清理与目标架构打包规格落档。
- 2026-11-01：b4 实现完成。下载校验后写入 receipt，新版本启动时复验 size/hash 并仅清理自有安装包；取消/失败/字节变化保留。三个打包 workflow 改为目标架构 staging，yazi 官方双架构 digest/size 入 pin 并由 bundle verify 强校验。全门禁 Python 1722 / Rust 410 / Vitest 833 / vue-tsc 通过，vendor 1533、x64 bundle/NSIS 与真实启动清理 PASS；实测安装包 384,516,079 字节，比 preview.1 减少 314,293,655 字节。
- 2026-11-01：修复 yazi staging 对 GitHub API 的依赖，改为消费版本 pin 直接下载固定 release asset；PR #56 最终 head `8960587` 的四条远端流水线全部 SUCCESS，已合入 develop `7c154cd`。
