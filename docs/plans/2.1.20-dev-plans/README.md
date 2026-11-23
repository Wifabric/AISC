# Workbench 2.1.20 开发计划

2026-11-23 用户确认本轮 11 条新反馈全部入版，按下表顺序推进。开发基线是 `develop@eb3fcc4a`，稳定线是 `main@3fa1a1b5`。正式 Workbench 为 2.1.19，正式 CLI 为 0.3.0，开发线 CLI 为 0.3.1.dev0。CLI 定版依据实际改动。

## 范围与验收

本轮执行和自查由主开发负责。每项均有独立的反馈记录和验收结果，共用入口的项目在同一批验证。用户在统一 Preview 上验收。

| 批次 | 原反馈 | 可观察的验收结果 |
| --- | --- | --- |
| B1 供应商 | [升级后不可见](https://feedback.alanevergarden.xyz/issue/20261119-旧版升级后Provider不见了-用户代录) | 在旧版保存的第三方配置，在同一工作区升级后仍可看到、选用。对比配置和激活状态，区分显示问题与实际数据丢失。 |
| B1 供应商 | [两张官方直连卡](https://feedback.alanevergarden.xyz/issue/20261119-官方直连卡片重复-用户代录) | Claude、Codex 列表分别展示可识别的配置。等价的直连入口合并显示，用户自建项保留名称与操作。 |
| B2 代理 | [节点刷新错误](https://feedback.alanevergarden.xyz/issue/20261119-刷新代理节点返回错误-用户代录) | 当前容器已应用代理订阅时可列出并切换节点，待重启或不具备控制条件时能看到具体原因和下一步。 |
| B3 技能 | [搜索后安装报错](https://feedback.alanevergarden.xyz/issue/20261123-扩展市场技能搜索后安装报错-Thomas) | 搜索 office-hours、安装、重开引擎后可调用其所需辅助程序。验证下载不可达、安装成功却缺依赖两条路径。 |
| B4 终端 | [选中即复制间歇失效](https://feedback.alanevergarden.xyz/issue/20261123-bash标签鼠标选中即复制完全没问题-但-Thomas) | Claude/Codex 交互和滚动后连续框选，每次剪贴板均为选区内容。对照 Bash，检查既有右键复制行为。 |
| B5 布局 | [设置与网络用量](https://feedback.alanevergarden.xyz/issue/20261119-设置与网络用量布局不合理-用户代录) | 设置内可找到网络与用量，订阅、节点、供应商和模型用量分区可辨；短窗口可滚动，各刷新按钮指向明确。复用 B2 的实际状态。 |
| B6 记录 | [结构化预览](https://feedback.alanevergarden.xyz/issue/20261123-工作记录预览不够结构化-Thomas) | 技能和工具详情默认折叠，展开后以可读格式显示。可用的路径和链接能打开，失效目标保留文本。 |
| B6 记录 | [导出 Markdown](https://feedback.alanevergarden.xyz/issue/20261123-工作记录缺少导出文件按钮-变为md文件-Thomas) | 右键、预览右下角均可导出当前记录，默认工作目录、可改保存位置，取消时无文件写入。 |
| B6 记录 | [删除确认](https://feedback.alanevergarden.xyz/issue/20261123-工作记录和工作记录集合右键删除等操作应该-Thomas) | 右键删除记录或集合时在弹窗显示实际影响，取消后内容保留，确认后仅处理提示中的对象。 |
| B7 会话 | [可输入工作目录](https://feedback.alanevergarden.xyz/issue/20261123-顶层标签栏下角标拉出的工作目录默认-ap-Thomas) | 保留默认工作目录，键入下级路径时只提示匹配文件夹，最终会话使用所选目录。 |
| B7 会话 | [集合新建会话](https://feedback.alanevergarden.xyz/issue/20261123-工作记录集合的-新建会话应该弹出和-标签-Thomas) | 集合内与标签栏共用工作目录和 Claude、Codex、Bash、个人能力与主题入口，保持正确集合归属。 |

## 开工核对及进展

- GitHub 全仓 open PR 与 open Issue 各查一页（每页 100），均为 0，含草稿及任意目标分支。当前 7 批均自行开发，合入前刷新 PR 状态。
- 已逐项查看 11 条[反馈原文](https://feedback.alanevergarden.xyz/)。上版暂缓的偶发卡死保留原决定；历史实时终端富文本另行排期，本轮结构化只涉及工作记录预览。
- 尚无统一候选。按 [WIKI §1.4.2](../../../DEVELOP_WIKI.md) 分批开发、自测及集成，再提供同源 Preview、操作清单和未测事项。
- 收尾覆盖 README、双轨版本与发布说明、WIKI、交接与开发 Skill、devlog、TODO、验收记录。发布前提交 Release 正文、渠道、资产、验证与遗留供用户确认。公开下载、CLI 渠道、反馈回写和阶段归档各自留证。
