# v2.1.17 b4 — 统一扩展推荐执行计划

> 执行 agent：使用 superpowers:executing-plans 逐项执行；沿用已授权的连续批次流程，不逐批请求审批或用户手测。

**目标：** Skills / MCP / Plugins 均有本地精选推荐与搜索发现入口，并复用同一详情、安装、更新和恢复管线。
**架构：** 本地小型精选表 → 类型化推荐模型 → 既有 extensions store 搜索/安装动作；推荐卡不维护第二套 installed/version 状态。
**技术栈：** Vue 3、TypeScript、Pinia、Vitest；沿用现有市场 adapter。

## 范围与源码

- 依据：`README.md` b4、`feedback-intake.md` N3、`decisions.md` D-0/D-1、`DEVELOP_WIKI.md` §1.2–1.4；前置 b2 元数据与 b3 恢复已集成。从 `develop` 建 `2.1.17-b4-unified-extension-recommendations`，核对 target 与账本。
- 修改 `workbench/src/features/workspace-explorer/ExtensionsView.vue`、`workbench/src/stores/extensions.ts`；复用同目录 `skillGroups.ts`、`workbench/src/lib/ipc.ts` 的 `ExtensionsItem`。
- 新增 `workbench/src/features/workspace-explorer/extensionRecommendations.ts`：仅存 kind、canonical identity、source、搜索关键词、精选理由、可核验中文摘要来源和静态排序；三类至少各一项经实际市场 identity 核实的条目。
- 搜索/安装事实来自 `container/aisc-extensions-adapter` 的 `skill_search_result` / `mcp_search_result` / `plugin_search_result`、`skill_install` / `mcp_market_install` / `plugin_install`；无必要不改 adapter。
- 更新 `workbench/src/i18n/zh-CN.ts` / `en-US.ts`。不引入账号、遥测、重型远程推荐服务、LLM 在线翻译或第二套下载器。

## 任务与 TDD 验收

- [ ] **RED：** 新增 `workbench/src/features/workspace-explorer/__tests__/extensionRecommendations.test.ts` 与 `workbench/src/stores/__tests__/extensionsRecommendations.test.ts`；扩展现有 `extensionsView.test.ts`。先运行 targeted，验证缺少推荐映射/入口导致失败。
- [ ] **本地精选：** 固定表覆盖三类，identity 去重；精选理由与来源可见、排序确定。安装量/更新时间仅在市场真实提供时参与同类排序，缺值显示未知，不构造跨市场假热度；无可靠中文摘要时沿用 b2“市场原文”。
- [ ] **统一发现：** 推荐关键词点击调用现有 `searchSkills/searchMcp/searchPlugins`；推荐 identity 与搜索命中对齐后走相同详情与安装动作，Skills 多子项仍按 b1 组契约。测试三类的搜索参数、安装参数、已安装态和更新入口一致，无第二个安装 IPC。
- [ ] **离线与失败：** 无 runtime 仍能看本地精选，安装按钮禁用并说明原因；离线显示精选，不伪装成已刷新市场。实际搜索仍暴露 b2 缓存/网络诊断；安装失败进入 b3 同一操作记录和单项重试。推荐中已失效的远端条目显示错误，不跳转安装其他 identity。
- [ ] **异步竞态：** deferred 测同类型 query1→query2 倒序返回、清空搜索后旧请求返回、Skills→MCP 切页、工作区 A→B→A、卸载组件；只有当前 generation/query 能改 results/cache/error/busy，旧 finally 不清新 busy，旧推荐安装不改新工作区已安装列表。
- [ ] **GREEN/UI：** 实现推荐区、理由、搜索跳转与禁用态；已安装项继续复用 b2 可更新/unsupported 信号，不把 Skills/MCP 缺少可比版本源显示为“最新”。补 zh-CN/en-US 和空结果断言，小提交闭环。

## 门禁与预测试

```powershell
Push-Location workbench
npx vitest run src/features/workspace-explorer/__tests__/extensionRecommendations.test.ts src/stores/__tests__/extensionsRecommendations.test.ts src/features/workspace-explorer/__tests__/extensionsView.test.ts src/stores/__tests__/extensionsMarketUpdates.test.ts
npx vue-tsc --noEmit
Pop-Location
powershell -File scripts/local-gates.ps1
git diff --check
```

- [ ] targeted/类型/全门禁 exit 0；必要远端 CI 通过后并回 `develop`。若改 CLI/container，重建 sidecar/bundle/镜像并 vendor verify；用隔离 runtime 核实三类精选 identity 与真实安装结果。
- [ ] **CU 前置：** Windows/CU、当前构建、隔离 ready runtime。**操作：** ①扩展→Skills 推荐→搜索→安装；②MCP、Plugins 重复；③断网重开推荐并搜索。**理想：** 三类均展示理由/来源，推荐和搜索详情指向同 identity，安装进入同一操作状态；离线精选仍可见、市场明确缓存/失败。**异常：** 某一类型缺席、推荐绕过诊断管线、离线标为已刷新均 FAIL。
- [ ] 在 `PRETEST.md` 记时间、构建/sidecar/镜像标识、逐步理想/实际、截图/窗口树和 PASS/FAIL。不可用时写 `NOT RUN — b4 三类推荐→搜索→安装 UI：当前 agent 无 Computer Use`，或明确缺少的窗口/runtime/网络；可执行的其余验证继续。b4 不单独请求用户手测，完成后继续 b5。
