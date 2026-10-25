# v2.1.17 b1 — 市场元数据缓存与更新信号

## 问题

v2.1.16 已能检索并安装 Skills / MCP / Plugins，但市场结果每次依赖远端请求，已安装项缺少稳定的市场版本对照；网络抖动时搜索体验和更新判断仍不够可靠。

## 方案

1. 为 skills.sh、Smithery、Claude plugin market 增加本地 metadata cache：
   - 记录查询词、结果、来源、版本 /更新时间、fetch 时间；
   - 搜索失败时可显示上次成功结果，并明确标记缓存时间；
   - 手动刷新绕过缓存，自动刷新使用短 TTL。
2. 扩展列表快照补充可更新信号：
   - skill 使用 repo / directory / content hash 对齐；
   - MCP 使用 qualified name 与 server version / updated_at（字段可用时）；
   - plugin 使用 marketplace version / lastUpdated。
3. 搜索与安装共享同一份 metadata 解析结果，避免详情与安装输入漂移。
4. UI 显示“缓存结果 / 已刷新 / 刷新失败但展示缓存”，不掩盖网络错误。

## 任务

- [x] 设计并测试 metadata cache schema 与 TTL / 刷新语义。
- [x] Python adapter 增加市场元数据缓存与统一解析函数。
- [x] Workbench Extensions store 接入缓存状态与手动刷新。
- [ ] 已安装列表补充可更新信号，不自动触发破坏性操作。
- [ ] 增加无代理 / 远端失败时缓存兜底的组件与 adapter 测试。
- [x] 真实容器手测三个市场的搜索与远端失败缓存兜底（安装与更新信号仍待后续批内验证）。

## 验收

- 远端搜索失败时不清空上次成功结果，并明确显示缓存来源与时间。
- 手动刷新能绕过缓存并更新结果。
- 已安装项只在有可靠版本证据时显示可更新。
- Skills / MCP / Plugins 搜索与安装互不污染缓存。
- Targeted tests 与 local gates 全绿。

## 执行记录（2026-10-26 首片）

- 已完成本地 metadata cache、远端优先 / 失败回退、cache 元数据透传与三个市场的缓存状态展示。
- 更新信号仍保持保守未显示；待市场版本字段可靠对齐后实现。
- 2026-10-26 实容器冒烟：`caveman` skill 搜索返回 20 项；Smithery `reportflow` 返回 10 项；plugin `skill-creator` 返回 1 项。人为切断远端后三项均回退 cache，保留 20 / 10 / 1 项并返回 `cached=true`、原抓取时间与失败原因。
