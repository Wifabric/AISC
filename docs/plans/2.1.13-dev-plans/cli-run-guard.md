# cli run 防重入守卫（存在运行中容器即拒绝）

> 状态：实施中（2026-09-19，随批 1；分支 `2.1.13-b1-release-chain`）
> 来源：用户 2026-09-19 入 todo「# 待处理」，同日裁定随本版本批 1 实施并移入 target（运行质量组）
> 规格路径：Focused 合并规格（vibe-coding-skill）

## Scope

`aisc run` 在该工作区已存在**运行中**容器时禁止使用——硬拒绝并给出指引。取代此前的三组行为：同系列活容器静默复用（r1#2 revised）、改名意图围绕活容器重建（r2#C 的 live 半边）、workbench 属主活容器被绕过后堆叠一次性容器。

## 行为规格

| 场景（label-less、非 dry-run） | 旧行为 | 新行为 |
| --- | --- | --- |
| 同系列活容器（CLI 属主） | 复用不新建（`result.reused`） | **拒绝** |
| 不同系列活容器（CLI 属主） | 视为改名：清扫重建 | **拒绝** |
| workbench 属主活容器 | 跳过不动，照样新建（堆叠） | **拒绝** |
| 已停止/退出的 CLI 属主容器（任意系列） | 清扫（stop+rm+unregister）后新建 | 不变（改名意图 = dead 不同系列清扫重建） |
| workbench 属主死容器 | 跳过不动 | 不变（生命周期归 Workbench/reconcile） |
| `--label <槽位>` | 旁路激活，不检查不触碰 | 不变 |
| `--dry-run` | 零 docker 调用 | 不变（不做存在性检查） |

## 错误契约

- `error_code="AISC_ERR_CONTAINER_EXISTS"`，`exit_code=6`（新码，全仓无占用）
- 消息（中文，按属主区分措辞）：指明容器名 + 三行指引（进入 / 生命周期 / 多实例 `--label`）
- 拒绝发生在清扫判定之后：live 命中即拒，**不执行任何 stop/rm**
- 拒绝以 `CliError` 抛出，必须落在 `try/except Exception: pass` 清扫块**之外**（防吞错）

## 不变量

- runtime 路径（`aisc runtime start`）的 reused 语义不受影响（runtime.py 自有逻辑，未动）
- 注册表写入/清扫锁序不变；`--events` 事件流不变（拒绝路径走 CliError，无 `run.*` 事件）
- CLI 文本摘要（main.py）删除 reused 分支（原「复用现有容器，未新建」提示随语义退役）

## Acceptance

- [ ] tests/test_run_activation.py `ReactivationReplaceTests` 重写：live 同系列拒绝 / live 不同系列拒绝 / dead 不同系列清扫重建（改名路径保留）/ dead 同系列清扫不变 / `--label` 旁路不变 / workbench live 拒绝
- [ ] 全 pytest 门禁绿
- [ ] 手测：有活容器的工作区跑 `aisc run` → exit 6 + 中文指引；停止后可正常 run
