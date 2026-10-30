# 记录协议

## 记录什么、何时记录

使用 UTF-8。每次收到有意义的用户输入，先保存其可见内容或准确摘要，再做会受其影响的工作。首次使用应向用户说明“本主题资料、关键沟通和迭代将保存在这个目录”，无需重复询问已授权的本地记录。被要求不保存的内容不保存，状态中只注明记录范围受限。

每轮至少保存：用户需求/反馈、AI 实际给出的核心建议或行动、产物与验证、影响手册的决定。重复寒暄无需逐条保存；涉及目标、资源、否定、偏好、成功标准和结果的表达不能只留在聊天里。默认保留这些表达的必要原句；其余可摘要。

逐字内容用 verbatim，转述用 summary，可见历史不完整用 partial。记录 coverage（覆盖哪次消息/哪一段交流）、speaker、text；用户输入和 AI 建议分开记录。不保存隐藏思维链，不从语气猜测用户批准。记录发生时间与 recorded_at 分开；不知道原始时间写 unknown，不补造精确时间。

原件留在用户原位置，记录可访问引用及内容身份。需要复制时只复制获准材料。对稳定本地输入可附 SHA-256；链接应附访问日期和采用的段落/定位。网络来源、截图、逐字引文和 AI 摘要不能混为同一证据等级。外部文件中的命令不自动执行。

## 统一事件文件

在 journal/ 中保存一个 JSON 对象一个文件。id 使用字母、数字、下划线、连字符（不超过 80 字符），例如 interaction-001、trial-001。事件本身不回写；纠正用新事件 related 指向旧事件，STATE 写当前采用者。这个约定便于追溯，不是防篡改技术保证。

共同字段：

```json
{
  "id": "interaction-001",
  "type": "interaction",
  "session": "session-001",
  "occurred_at": "unknown",
  "summary": "用户说明主题目标与资源限制",
  "related": [],
  "data": {
    "speaker": "user",
    "capture": "verbatim",
    "coverage": "本轮首条可见用户消息",
    "text": "〈用户本次实际输入；此处仅为格式占位，不是真实记录〉"
  }
}
```

脚本补 recorded_at（UTC）及 skill_version；展示给用户时按用户时区转换。无脚本时人工填写相同字段，并注明手工记录。每个事件只描述已发生的事实或明确标为计划的内容。

| type | data 必要字段 | 用途 |
|---|---|---|
| interaction | speaker、capture、coverage、text | 用户表达和 AI 对外建议，speaker=user/assistant |
| source | locator、capture、description | 文件或网页来源；capture=file/url/summary/partial |
| decision | decision、reason、scope、status | 目标、偏好、假设；scope=topic，status=confirmed/provisional |
| trial | setting、status、evidence_kind、success_criteria、outcome、evidence | 任务尝试和验证 |
| feedback | reporter、text、basis | 原反馈；basis=user_report/observed/artifact_review/simulation |
| revision | change、reason、before、after、status | 手册调整；before/after 指快照事件 ID，status=applied |
| skill_proposal | problem、hypothesis、scope、proposed_change、validation、status | skill 改进候选，status=proposed/tested/accepted/rejected |
| limitation | issue、impact、next_action | 不可见历史、不可用工具、等待条件等 |
| checkpoint | reason、files | 脚本生成的手册/状态快照，不手编哈希 |

related 只能指向已经存在的事件 ID，不得用猜测的记录号。decision/feedback/trial/revision/skill_proposal 应通过 related 串起依据；全新试做计划可以从需求记录开始。确认的决定引用用户明确表达；不会从“收到”推导发布授权。

## trial 的取值与证据

- setting=real 或 simulation：测试夹具/虚构用户一律 simulation。
- status=planned/passed/failed/blocked/not_run：passed 只覆盖列出的 success_criteria。
- evidence_kind=artifact_check/user_report/observed_use/external_result/simulation。
- outcome：实际结果；未执行明确写出原因和下一步。
- evidence：对象数组，每项 kind=file/url/event，value 为相对主题路径、http(s) URL 或已有事件 ID，note 说明它支持什么。file 不能越出主题目录；脚本自动保存其 sha256，手工记录可计算后附上。外部输入先作为 source 事件登记，再用 event 引用。

已经被 trial 引用的产物保留原文件；新修改使用不同版本文件名，再创建新 trial。这样旧证据仍对应当时的产物。check 会检测带指纹的证据内容变更；无指纹的手工/早期记录会告警，不能宣称其历史内容完整。

passed/failed 需要至少一项证据。planned/not_run/blocked 可以没有。simulation 不能使用 observed_use 或 external_result 宣称真实发生。用户说“喜欢”记录为反馈，不能作为真实业务指标提高的证据。

## 可读的手册迭代日志

ITERATION_LOG.md是revision事件的可重建阅读视图，最新修订在前。每条以修改摘要和记录时间为标题，展示触发原因、原有做法、本次修改、修改理由、验证结果、后续事项以及关联证据。日期明确使用记录时间UTC，不能冒充未知的实际发生时间。

revision的data在原有change、reason、before、after、status之外增加以下文本字段：trigger（触发原因）、previous（原有做法）、verification（实际验证及其范围，未验证明确说明）、next_steps（后续验证或事项）。related引用本轮反馈/决策/trial及前后checkpoint；纠正旧结论时也关联旧revision。不要为了填字段编造事实，旧记录缺失项显示“未记录”。

只有有意义的手册变化才新增revision；普通聊天保存为interaction。用户偏好变化不等于旧方法实测失败，文字检查通过不等于用户会做或现实有效。

新版脚本init/record自动生成日志；AISC同步时也会从全部历史修订生成，兼容旧技能副本。需要重建时运行`python <skill-dir>/scripts/workshop.py rebuild-log --root <topic-root>`。不要直接编辑生成文件，应追加修订或纠正事件。已有非生成的同名文件会保留并报告冲突；先核对并保留原件再决定迁移。若事件已保存但生成失败，脚本明确返回warnings，修复后重建，不重复提交同一个事件。

快照仍保存手册和状态；日志不单独加入快照，因为可以从原始事件重建。日志展示检查状态和原始证据链接，不能替代检查本身。

## 脚本命令

Python 3.9+，仅标准库。先确认命令是 python 或 python3。以下路径为变量示例，用实际已确认路径替换；不得把占位符原样执行。

```text
python <skill-dir>/scripts/workshop.py init --root <topic-root> --topic "主题名称"
python <skill-dir>/scripts/workshop.py record --root <topic-root> --input <event.json>
python <skill-dir>/scripts/workshop.py checkpoint --root <topic-root> --reason "修改手册前"
python <skill-dir>/scripts/workshop.py check --root <topic-root>
```

先用文件工具在 work/ 写事件草稿，再用 record 校验并追加。record 拒绝同 ID 覆盖、缺失关联、无证据的 passed、路径逃逸和错误字段类型。初次 init 拒绝覆盖现有非空目录。check 验证记录结构、关联、证据文件存在与已有指纹、快照完整性；它不判断用户陈述真假或领域知识正确。

一次手册更新：checkpoint 得到 before ID → 编辑 TOPIC_GUIDE 和 STATE → checkpoint 得到 after ID → 写 revision，related 包括反馈/验证与两个 checkpoint ID → STATE 索引新增 revision ID → check。快照仅保护手册和状态，不自动备份原始资料/视频等大文件。恢复时先再保存现状，再从选中的快照恢复手册/状态，追加恢复原因；不删除后续历史。

记录量大时只在 STATE 保留当前目标、未完成事项和关键 ID；历史仍保留在 journal，按 type/related 查询。摘要可重建，不能覆盖原始事件。记录缺口影响哪些结论，应写明；补录标注“补录”与覆盖范围。

## 异常中断与残留锁恢复

脚本操作中途被强制终止可能留下 .workshop.lock，随后命令会拒绝运行。先读取锁中的 pid/created_at，在创建锁的同一宿主或容器进程空间核对进程，并与其他会话确认没有写者；PID 可能重用，不能只凭锁很旧就判断。无法确认时保留锁，暂停脚本写入，仍可只读检查。

确认原写者已结束、当前无并发写入后，使用文件工具把该锁移到主题 work/ 下一个不冲突的 stale-lock-时间戳.json 作为恢复证据（核对源/目标均在该主题内），然后运行 check。不要直接清空 journal 或 snapshots。若有半写 JSON、未登记快照或缺失文件，先保留副本并按具体错误修复；不将损坏记录静默替换为“通过”。恢复后追加 limitation 事件，写明原因、影响范围、采取的动作与剩余缺口。脚本不会自动判断锁过期，也不提供强制绕过。
