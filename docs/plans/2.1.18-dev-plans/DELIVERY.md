# 2.1.18 夜间交付与次日验收

2026-11-08：b1–b10 的产品实现均已合入 develop；协作流程/Skill PR #75 和整合修正 PR #76 已合入。当前产品集成提交 `41d046d95e94f58ad7b6e7b129c9daacb92ae54d`。F4 默认成员仍待 U-4 批准，完整 GUI/用户验收、真实 GitHub 授权和正式发布未完成，不能把本版或反馈记为全部关闭。

## 变更说明

- F1/F2：仅大小写改名保留目标名称；工作记录菜单/子菜单按边界避让并避免误移。
- F3：完整镜像名称编辑与随机默认名；本机镜像重建预检和进度，运行容器阻止重建，不自动停删，远程重建入口明确禁用。
- F4：用户模块定义、编辑、持久化、缺项安装、逐项恢复，以及共享/预装/用户修改保护；默认模块提案已验证但未启用。
- F5：插件安装独立等待预算、容器进程锁和超时后实际状态核对；未知结果不盲目重试。
- F6：GitHub MCP 按引擎配置认证、取消/失败保护与显式连接检查；凭据不进入诊断或重试历史。
- F7：多层技能目录、固定来源、简介缓存/空简介/重试，合法连字符名称与下划线目录匹配，歧义继续拒绝。
- F8：关闭失败卡片与同次重复错误文案，保留日志/诊断，新失败仍提示，焦点恢复和目标隔离。
- 协作：贡献者必要测试后提 PR，主开发者处理小修正、集成和统一 Preview；WIKI、职责、贡献者、PR intake 与 [开发 Skill](../../../skills/aisc-development/SKILL.md) 一致。单代理兼任只记自查。

## 本机可运行候选

本机输出，不作为仓库文件上传，也尚未创建公开 Release/tag：

| 产物 | 位置 |
| --- | --- |
| 隔离候选启动脚本 | `D:\AISC\p18\start-candidate.ps1` |
| 完整可运行目录 | `D:\AISC\p18\candidate` |
| Windows 安装包 | `D:\AISC\p18\AISC Workbench_2.1.18-preview.1_x64-setup.exe` |
| 源码、哈希与状态清单 | `D:\AISC\p18\candidate-manifest.json` |
| 详细测试日志 | `D:\AISC\output\preview-2.1.18-20261108\output\verification` |

PowerShell 执行 `& 'D:\AISC\p18\start-candidate.ps1'` 启动独立配置候选。数据根为 `D:\AISC\p18\qa-data`，WebView 数据也独立；原平台安装和原工作区未替换。基础检查后候选已关闭，原平台进程保留。选择隔离工作区完成 HANDTEST，避免把原工作区当测试数据。

本地 Workbench 版本覆盖为 `2.1.18-preview.1`，源码仍保留现有正式版本标识；CLI/Bundle 为 `0.1.10`，用本版源码重新冻结/打包。此处是可审查的本地候选，不是已发布 Preview。U-4 批准和阶段收尾决定后，再统一更新正式候选的双轨版本及 Release Notes、重建并执行发布流程。

候选产品源码为 PR #76 head `be39b2a97d3ef292cf630a8adb53d761f5937f12`，与其合并提交产品内容一致；后续交付文档不改变二进制。SHA256：

| 文件 | SHA256 |
| --- | --- |
| workbench.exe | `da0ddbb6900c31434d40a79bd4a3a58cff2c8e93b20dde31bdaead5e6ba936dc` |
| aisc.exe | `165b5ff38fc555eed02b551a5c90fa54ee2b315e06b111bdf5c3857c7c1f9f44` |
| setup.exe | `38890ecc14ff05c6c4220deee56d85d4172f8fc23ad418eace39308f5ed8bf82` |

## 验证结果

- 最终 Python：1791 passed、54 skipped、207 subtests；适配器定向 87 passed。前端最后一次完整本地门禁 882 passed，最终受影响定向 48 passed，类型/生产构建通过；Rust 最近产品批次 420 passed、2 ignored。
- 整合 PR #76 精确 head 的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/42411011239) frontend/rust/cli 全部 success。b3–b10 的 PR/CI/merge 逐项见 [PR_INTAKE](PR_INTAKE.md)。纯文档 PR #75 未触发产品 CI，Skill 格式和 105 个本地链接校验通过。
- 完整 bundle 初次校验发现过期/遗漏 checksum，修正后 1534 项覆盖及完整校验通过。NSIS 初次因长路径失败，使用本地短路径引用同一资源后，含最终修正的 Windows 安装包构建通过。
- 候选冻结 CLI + 实际打包资源：模块应用/卸载、合成双引擎认证配置及真实客户端读取、grill-me 详情通过。补充科研详情实际读取和四项提案成员 installed→removed 通过。自建 QA 容器均已清理。
- Windows 真实候选启动与“帮助 → 关于”基础检查通过：工作区选择页正常，显示 Workbench `2.1.18-preview.1`、CLI/Bundle `0.1.10`。仅此基础检查为 CU PASS；**完整 H1–H10、安装/升级手测、SSH、真实 GitHub 凭据与工具权限仍 NOT RUN**。合成令牌和 DOM 测试不替代这些项目。

## 次日集中处理

1. **U-4 默认成员**：批准或调整 [四项具体提案](default-modules-proposal.md)。科研基础为 arXiv/OpenAlex，开发基础为 systematic-debugging/test-driven-development；四项安装/卸载已验证。批准后落默认清单并重建候选，未批准前保持空清单。
2. **统一 Preview 验收**：按 [HANDTEST](HANDTEST.md) 执行；用户本人完成真实 GitHub 认证。记录实际 PASS/FAIL/NOT RUN，再决定修复或收尾，不预记验收通过。
3. **反馈站写权限**：当前凭据对反馈数据仓库只有读取权限。回复草稿见 [反馈进度文案](feedback-replies-draft.md)，尚未发布；有权限后先刷新原文/新回复，再按实际阶段更新，验收发布前不置 resolved。
4. **发布与归档**：当前未合入 main、未发布公开 Preview/final、未归档本版或关闭反馈。待用户宣布收尾并满足验收/版本条件后执行；已有授权沿用，正式发布批准不由本地构建代替。
