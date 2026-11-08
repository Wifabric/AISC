# 2.1.18 夜间交付与次日验收

2026-11-08：b1–b10 的产品实现均已合入 develop；协作流程/Skill PR #75、整合修正 #76、真实 GUI 复测修正 #78/#79/#83/#85/#87/#91 已合入。当前产品集成提交 `3b26609e7f0aef9f5eec449a91638c11eadb048e`。F4 默认成员仍待 U-4 批准，完整 GUI/用户验收、真实 GitHub 授权和正式发布未完成，不能把本版或反馈记为全部关闭。

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
| Windows 安装包 | `D:\AISC\p18\AISC Workbench_2.1.18-preview.7_x64-setup.exe` |
| 源码、哈希与状态清单 | `D:\AISC\p18\candidate-manifest.json` |
| 详细测试日志 | `D:\AISC\output\preview-2.1.18-20261108\output\verification` |

PowerShell 执行 `& 'D:\AISC\p18\start-candidate.ps1'` 启动独立配置候选。数据根为 `D:\AISC\p18\qa-data`，WebView 数据也独立；原平台安装和原工作区未替换。每轮检查后正常退出独立候选，原平台进程保留。QA 工作区与证据保留；QA-A 科研模块、QA-C 混合定义及历史保留供继续复测，QA-B 已验证删除定义不删资产。选择隔离工作区完成 HANDTEST，避免把原工作区当测试数据。

本地 Workbench 版本覆盖为 `2.1.18-preview.7`，源码仍保留现有正式版本标识；CLI/Bundle 为 `0.1.10`，用本版源码重新冻结/打包。此处是可审查的本地候选，不是已发布 Preview。U-4 批准和阶段收尾决定后，再统一更新正式候选的双轨版本及 Release Notes、重建并执行发布流程。

候选产品源码为 PR #91 head `5414a099192da1372380426fa2006b0f58c28016`，与其合并提交产品内容一致；后续交付文档不改变二进制。SHA256：

| 文件 | SHA256 |
| --- | --- |
| workbench.exe | `d70df77794d583a66e35b7b89007bc5d6ac57362ccd2439f1eb033c30d67a1d5` |
| aisc.exe | `e000a775ae16a446330b45cf22373f24b63c00088e228021701435920a84daf1` |
| setup.exe | `31a6615e153803083d9dde6d7fc95d3afe5039c41b1a17df1d201ca67b86dda5` |

## 验证结果

- 最近完整本地 Python（S6 时）：1796 passed、54 skipped、207 subtests；基础镜像/重建定向 52 passed，既有适配器定向 87 passed。前端最后一次完整本地门禁 882 passed，最终受影响定向 48 passed，类型/生产构建通过；Rust 最近产品批次 420 passed、2 ignored。
- 整合 PR #76 精确 head 的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/42411011239) frontend/rust/cli 全部 success。b3–b10 的 PR/CI/merge 逐项见 [PR_INTAKE](PR_INTAKE.md)。纯文档 PR #75 未触发产品 CI，Skill 格式和 105 个本地链接校验通过。
- 完整 bundle 初次校验发现过期/遗漏 checksum，修正后 1534 项覆盖及完整校验通过。NSIS 初次因长路径失败，使用本地短路径引用同一资源后，含最终修正的 Windows 安装包构建通过。
- 候选冻结 CLI + 实际打包资源：模块应用/卸载、合成双引擎认证配置及真实客户端读取、grill-me 详情通过。补充科研详情实际读取和四项提案成员 installed→removed 通过。该轮自建 QA 容器均已清理；后续 H4 的专用停止容器和镜像保留供继续复测。
- Windows 真实候选启动与“帮助 → 关于”基础检查通过：工作区选择页正常，显示 Workbench `2.1.18-preview.3`、CLI/Bundle `0.1.10`。真实 GUI 的本机 H1/H3、H5/H6/H9/H10 子集与发现的三项整合修正见 [统一候选复测](preview-gui.md)；**完整 H1–H10、安装/升级手测、SSH、真实 GitHub 凭据与工具权限仍未完成**。合成令牌和 DOM 测试不替代这些项目。

- GUI 发现并修复：模块预检独立通道避免拖慢后台同步，成功终态去掉旧预检原因，冻结 CLI 明确按 UTF-8 读取中文模块请求。Rust 定向 35、前端模块定向 12、Python 模块/分发 22 + 18 subtests 通过；冻结 CLI 多语言真实预检 48.38 秒通过。#78 [CI](https://github.com/Wifabric/AISC/actions/runs/42412882668) 和 #79 [CI](https://github.com/Wifabric/AISC/actions/runs/42413674608) 三项全部 success。Preview.3 完整 NSIS 构建通过；旧 Preview.1/.2/.3 仅保留作历史产物，不再用作当前验收入口。

Preview.4 补充：#83 [CI](https://github.com/Wifabric/AISC/actions/runs/42417635698) frontend/rust/cli 全部 success。真实完整镜像重建验证了基础镜像回退、固定 digest、本机 builder 和无缓存参数，选中标签更新、其他标签及停止容器引用保持；新镜像适配器哈希与 Node/Claude/Codex 版本探针通过，Codex 另有旧临时目录跨设备清理警告，未据此宣称所有工具运行场景通过。Preview.4 的真实 GUI 两入口缓存重建成功、无缓存取消与镜像保护、About 版本核验通过；缓存取消尝试时构建已先完成，未记取消通过。修正后的冻结 CLI、Workbench 和 384431133 字节 NSIS 安装包已重新生成并替换当前候选；旧 Preview.3 仅留作历史。具体 GUI 覆盖及未测项目继续见 [统一候选复测](preview-gui.md)。

Preview.5 补充：#85 [CI](https://github.com/Wifabric/AISC/actions/runs/42420724178) 三项 success 后合入。修正四个科研推荐的真实安装目录，前端 28 项/类型/构建及冻结 CLI 四项 installed→removed 通过；384419837 字节 NSIS 与独立 Workbench 已生成。CLI 与 bundle 相对 Preview.4 未变化，旧 Preview.4 保留作历史。H7 正常插件安装已在 Preview.4 实机通过。Preview.5 GUI 已实际安装 arXiv/OpenAlex，验证预装 research 保留、当前项完成后停止、重新预检仅补缺项，以及关闭市场/切换视图后执行终态保留；共享卸载等后续结果见 preview-gui。H2 追加键盘 Home/上下键、底部菜单、窄短窗口左展与内部滚动，以及实际改名/移动后磁盘逐项比对通过，未扩写为完整手测通过。

Preview.6 补充：#87 [CI](https://github.com/Wifabric/AISC/actions/runs/42425026074) 三项 success 后合入。修正短窗口编辑器底部保存时看不到上方错误的问题，模块相关 13 项、类型/生产构建通过；384429548 字节 NSIS 与独立 Workbench 已生成。CLI/bundle 未变，Preview.5 留作历史。双窗口冲突保护、明确重新读取后保存和目标容器离线保存已在 Preview.5 通过；Preview.6 实机重复空名称提示、冲突自动可见、草稿保留与显式恢复保存通过，磁盘核对外部修改没有被覆盖。H2 追加侧栏滚动和实际缩窄后菜单关闭、数据不变通过；About 显示 Preview.6 / CLI/Bundle 0.1.10。完整覆盖与未测边界见 [统一候选复测](preview-gui.md)。

H9 后续实机补测：隔离目标断网时返回带说明的搜索缓存，技能详情明确失败并提供来源/重试。恢复网络后首次重试仍失败，确认实际连通后再次重试成功；固定提交来源、普通查询切换和摘要缓存通过，1,545 个技能文件哈希保持不变。网络恢复完毕。跨工作区和真实迟到响应 GUI 仍未完成；精确结果见 [统一候选复测](preview-gui.md)。本轮只有验证文档变化，Preview.6 二进制与哈希不变。

Preview.7 补充：#91 [CI](https://github.com/Wifabric/AISC/actions/runs/42429010839) 三项 success 后合入，修复 Windows 取消重建遗留临时 tag。关联 Python 103 / 19 subtests、Rust 协议 2 通过；CLI 与 Workbench 重新构建，384428294 字节 NSIS 完成，bundle 不变。真实 GUI 缓存取消 9.5 秒、无缓存构建受控残留取消 27.5 秒通过：临时 tag 回收，selected/其他 tag/停止容器保持不变。冻结 CLI 精确回收/幂等、About 版本与四项哈希核验通过；原候选已备份。Preview.6 的完整无缓存 GUI 123.8 秒成功仍按其版本记录，原取消泄漏不改写为 PASS；自然导出竞态未在修后重复撞中，完整边界见 [统一候选复测](preview-gui.md)。

## 次日集中处理

1. **U-4 默认成员**：批准或调整 [四项具体提案](default-modules-proposal.md)。科研基础为 arXiv/OpenAlex，开发基础为 systematic-debugging/test-driven-development；四项安装/卸载已验证。批准后落默认清单并重建候选，未批准前保持空清单。
2. **统一 Preview 验收**：按 [HANDTEST](HANDTEST.md) 执行；用户本人完成真实 GitHub 认证。记录实际 PASS/FAIL/NOT RUN，再决定修复或收尾，不预记验收通过。
3. **反馈站写权限**：当前凭据对反馈数据仓库只有读取权限。回复草稿见 [反馈进度文案](feedback-replies-draft.md)，尚未发布；有权限后先刷新原文/新回复，再按实际阶段更新，验收发布前不置 resolved。
4. **发布与归档**：当前未合入 main、未发布公开 Preview/final、未归档本版或关闭反馈。待用户宣布收尾并满足验收/版本条件后执行；已有授权沿用，正式发布批准不由本地构建代替。
