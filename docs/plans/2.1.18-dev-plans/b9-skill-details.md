# b9 技能搜索结果与详情读取

状态：PLANNED，未实施。D-11；F7 / R-9 / H9。自行开发，排在 b8 后；可复用 b7 网络取证，独立验收。

## 方案与范围

保留精确查询 `grill`、`mattpocock/skills:grill-me` 及相关结果。分开检查搜索元数据与详情请求，核对真实上游路径、分支、响应/编码和代理通路；不得将反馈中的报错直接推断为固定网络或路径故障。

按定位结果修复路径解析/访问与恢复。详情区分别显示加载、有效简介、无简介和读取失败；失败提供可用的重试与来源入口，保留有用缓存并隔离查询/工作区。只接受合法仓库/目录和受控读取大小；不执行上游 SKILL.md 指令，不因简介失败改动安装资产。

## 阅读与验证入口

- `ExtensionMarketDialog.vue`、`ExtensionItemDetail.vue`、`ExtensionDetailPanel.vue`、`extensions.ts`、`container/aisc-extensions-adapter::skill_describe`。
- `extensionsDescriptions.test.ts`、`extensionDetailPanel.test.ts`、`tests/test_extensions_adapter.py`：多层目录、有效简介/空简介、404/超时/断网、重试、缓存及迟到响应。
- 使用实际上游来源核对 grill/grill-me；记录版本/URL/读取时间，避免上游漂移。无网只覆盖失败路径，不记成功加载。
- 门禁、更新后的真实 runtime、CI、H9 CU 与用户验收逐项记账。
