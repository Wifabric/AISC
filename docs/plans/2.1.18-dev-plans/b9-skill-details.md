# b9 技能搜索结果与详情读取

状态：已实现并完成本地/真实容器验证，准备 PR。D-11；F7 / R-9 / H9。自行开发，排在 b8 后；可复用 b7 网络取证，独立验收。

## 方案与范围

保留精确查询 `grill`、`mattpocock/skills:grill-me` 及相关结果。分开检查搜索元数据与详情请求，核对真实上游路径、分支、响应/编码和代理通路；不得将反馈中的报错直接推断为固定网络或路径故障。

按定位结果修复路径解析/访问与恢复。详情区分别显示加载、有效简介、无简介和读取失败；失败提供可用的重试与来源入口，保留有用缓存并隔离查询/工作区。只接受合法仓库/目录和受控读取大小；不执行上游 SKILL.md 指令，不因简介失败改动安装资产。

## 阅读与验证入口

- `ExtensionMarketDialog.vue`、`ExtensionItemDetail.vue`、`ExtensionDetailPanel.vue`、`extensions.ts`、`container/aisc-extensions-adapter::skill_describe`。
- `extensionsDescriptions.test.ts`、`extensionDetailPanel.test.ts`、`tests/test_extensions_adapter.py`：多层目录、有效简介/空简介、404/超时/断网、重试、缓存及迟到响应。
- 使用实际上游来源核对 grill/grill-me；记录版本/URL/读取时间，避免上游漂移。无网只覆盖失败路径，不记成功加载。
- 门禁、更新后的真实 runtime、CI、H9 CU 与用户验收逐项记账。


## 2026-11-08 实现与验证

上游 `mattpocock/skills:grill-me` 位于多层目录 `skills/productivity/grill-me/SKILL.md`，原三个浅层路径均无法覆盖。保留浅层快速读取，未匹配时读取受大小限制的 GitHub tree，唯一目录匹配后按 blob SHA 读取；拒绝歧义、截断 tree、超大内容和身份不符，五分钟有界缓存避免重复 tree 请求。仅解析简介，不执行文档指令。真实来源固定为 [4ae2317d](https://github.com/mattpocock/skills/blob/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/productivity/grill-me/SKILL.md)。

搜索后后台串行补充至多三条缺失摘要，其余按需读取；上下文和查询代数隔离。详情区区分有效空简介、加载和失败，显式重试保留已有摘要并显示来源。监听稳定身份，避免摘要回写引发自动无限重试；非技能条目不继承技能缓存。Rust 详情读取预算 60 秒且使用独立通路。

- Python 全套 1789 passed / 54 skipped / 207 subtests；适配器定向 85 passed / 11 subtests。
- 前端全套 876 passed（新增组件用例前）；最终描述与真实组件回归 7 passed，最终类型与生产构建 PASS。Rust 420 passed / 2 ignored。
- 真实隔离 Docker 搜索 `grill` 包含准确 `grill-me`；读取 4.00 秒，重复 2.14 秒，返回准确简介及固定提交来源。QA 容器已清理。证据在本机 `output/verification/real-details.json` 及测试日志。
- 自查完成，无独立评审；GUI/H9、SSH 尚 NOT RUN，按 D-15 留到统一 Preview。真实上游成功不代表人为断网 GUI 已验证。
