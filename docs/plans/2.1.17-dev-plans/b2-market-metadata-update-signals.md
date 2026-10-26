# v2.1.17 b2 — 市场元数据、更新标识与详情中文化

## 来源

- 反馈 N2：已安装 Skills / MCP / Plugins 需要新版本标识，有更新时加粗显示。
- 反馈 N4：市场详情中的单项简介需要中文化。
- 原 v2.1.17 开题范围中的市场元数据与更新信号；在 b1 修复无代理可靠性后实施。

## 问题

当前已安装快照与市场搜索结果缺少统一 identity/version 对齐，UI 无法可靠判断
“已有新版本”；详情文案直接沿用市场原文，界面中英文混杂且字段没有统一中文说明。

## 方案

1. 建立本地 metadata 快照：
   - 搜索、详情、安装共享 normalized identity 与 source/version/updated_at；
   - Skills 以 repo + directory + content hash/update time 对齐；
   - MCP 以 qualified name 与 server version/updated_at 对齐；
   - Plugins 以 marketplace version/lastUpdated 对齐。
2. 已安装列表加载后可触发更新检查：
   - 单项显示“可更新”徽标，组标题显示数量；
   - 有更新的名称加粗，操作仍支持单项更新；
   - 检查失败显示网络诊断，不把“无法检查”误报为“已是最新”。
3. 详情中文化：
   - 字段名、状态、来源、安装量、更新时间与操作说明全部中文；
   - 单项简介优先使用可靠中文摘要来源；
   - 无可靠中文来源时保留原文并标明“市场原文”，不用猜测翻译。
4. 搜索缓存只作为远端刷新失败后的显式兜底，不得掩盖 b1 修复的网络错误。

## 任务

- [ ] 先写失败测试：三资产 installed/market identity 对齐与 update available。
- [ ] 实现市场 metadata snapshot 与更新检查 API。
- [ ] Workbench 单项 UI 显示“可更新”徽标、名称加粗和单项更新入口；组标题
      显示可更新数量；检查失败显示具体网络诊断。
- [ ] Vitest 断言 zh-CN/en-US 均包含上述状态文案。
- [ ] 详情区中文化与“市场原文”兜底。
- [ ] 补搜索缓存兜底测试，确保远端失败时返回 cached 元数据。
- [ ] targeted Python / Vitest / vue-tsc，全门禁后并回 develop。
- [ ] 真实容器手测三市场搜索、详情、安装、更新标识与无代理失败诊断。
