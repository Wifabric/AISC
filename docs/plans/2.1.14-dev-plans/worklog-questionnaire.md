# 「工作记录」概念——需求问询材料（用户作答后排期）

> 状态：待用户作答（2026-09-23 备妥）
> 来源：todo v2.1.14-target「历史会话重构·工作记录概念」（2026-09-21 用户
> 裁决移出 2.1.13：待捋清需求再立项）；概念 = 工作记录负责记录/保存打开过
> 的 bash（内含 codex）会话状态，与 codex 的 resume 记录非一一对应（惯用单
> codex 会话=1:1；一任务一干净会话=1:N）
> 方法：ultracode workflow（研究员 + evidence 核验 verdict=confirmed，25 条
> 证据全中）；前计划稿 docs/archive/2.1.13-dev-plans/history-worklog.md 批 3
> 铁律（D-9）：**裁决前不动 worklog.py 数据层与 resume 冻结契约；严禁按
> assumed 默认推进**（批 3 前车之鉴）

## 0. 现状地基（批 8 已交付，作答时请以已知能力为底）

- **账本**：`<ws>/runtime/worklogs.json`（schema `aisc.worklog/v1`；容器
  删除不丢）——worklog.py:5-38（record 结构含 sessions[]，**天然支持 1:N**，
  无需迁移）；CRUD ops 90-142；CLI 五命令（list/open/close/archive/reconcile
  等，cli/commands/worklog.py:206-258）。
- **开关钩子闭环**：build_session_exec 开账 + terminate 关账
  （session.py:112-124/168-176）；serve 事件流（serve.py:230-238/331/349）；
  fail-open（账本坏了不阻会话）。
- **查看链**：只读 transcript 查看器（conversation read）+ resume 链 +
  findLiveResumeTab 防重复开。
- **批 0 探针结论**：codex resume 续写原会话文件（会话状态可锚定）。
- **已知缺口**：conversation_id 回填（resume 后账本条目与历史面板会话的
  关联）；reconcile 的存量拆分语义。

## 1. 六组歧义（A-F 主裁 + G/H 附带），每项请勾选

### A. 工作记录的粒度（1:N 时的「一条」是什么）——最优先，决定规模量级

| 候选 | 利 | 弊 |
| --- | --- | --- |
| A1 一 bash 会话一条（现状 record_open 即此） | 零操作零遗漏、已实现 | 惯用单 codex/多任务者条目碎片化，「任务」被拆散 |
| A2 一任务一条，多会话挂靠+拖挂解挂（批 3 原案） | 贴合 1:N 心智；sessions[] 已兼容 | 要建 CRUD+归组 UI，交互成本高 |
| A3 自动建占位+用户合并/晋升 | 冷启动即有用、渐进整理 | 合并语义（时间交叠/resume 边/占位卡）最复杂 |

> A2 → 批 3 原案（分段切换+CRUD+拖挂）复活为实施蓝本，规模 **L**；
> A1 → 收缩为「账本可视化 + conversation_id 回填修复」，规模 **M**。

### B. bash 与 codex 会话的父子关系呈现

| 候选 | 利 | 弊 |
| --- | --- | --- |
| B1 平铺时间线（sessions[] 按 opened_at，现状 schema） | 实现就绪、免探测 | 看不出运行时嵌套 |
| B2 嵌套树/父子指针 | 直观表达「bash 包住 codex」 | bash 页签内**手敲** codex 探测不到（裸 docker exec 盲区，前计划稿明言） |
| B3 bash 仅占位卡（前计划稿默认） | 简单 | 与「bash 一等公民」心智相悖 |

### C. 记录开/关时机

C1 全自动（现状钩子）｜C2 全手动新建｜C3 自动入账 + 手动晋升命名（推荐倾向：
C3 兼顾零遗漏与整理）。

### D. UI 落点（另需裁决：历史页 flat「全部会话」视图去留）

D1 历史 tab 分段切换（工作记录/全部会话，批 3 原案 D1）｜D2 独立顶层页｜
D3 现有列表按 worklog 分组。

### E. 归档策略

E1 手动（CLI 已有、UI 未接）｜E2 closed_at 超时自动｜E3 混合（N 天未开自动
归档+可恢复）。

### F. 恢复语义

F1 仅查看（现状：查看器 + 单会话 resume）｜F2 「一键恢复工作记录」（该记录
下每个可 resume 的会话各开一个页签——需处理 provider 拒绝双开的行内错误）。

### G. reconcile 触发与存量拆分（技术性，可给默认）

G1 打开工作区时自动 reconcile（现状时机）+ 幂等（两次跑第二次补录 0 个）；
存量（批 8 之前的会话）是否拆分入账。

### H. 标题（技术性，可给默认）

H1 首条消息截断自动命名 ｜ H2 手动命名（晋升时）｜ H3 两者兼有。

## 2. 裁决顺序建议

**A + C 先**（定数据模型语义与 ops 面）→ **B + D**（定前端形态与 flat 视图
去留——flat 下线走用户裁决门）→ **E + F + G + H**（多为可后调默认值）。

## 3. 裁决后的手测

按 §1.3 四要素重写（研究员已备草案骨架：自动入账字段级断言 / reconcile
幂等与回填 / UI 落点并存 / 归档恢复 / 账本损坏 fail-open——见 workflow
产出，随实施批并入 HANDTEST）。
