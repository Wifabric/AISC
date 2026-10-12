# v2.1.15 b2：Windows 工作区路径大小写归一与历史去重

> For agentic workers: 本文件是 b2 批次实施记录。执行须遵守分支先行、根因先行、
> TDD、本地门禁与远程 CI 全绿后并回 develop。

## 目标

修复 Windows 下同一路径仅大小写不同（如 `E:\projects` 与 `e:\projects`）在
Workbench 历史中显示为两个工作区的问题。统一身份键匹配语义，保留用户原始
大小写作为显示形态；POSIX 大小写敏感语义不变。b2 不改 sha256-v1 hash 算法、
不做数据迁移。

## 反馈与证据

- 反馈：F4「工作区本来是一个文件夹却作为两个文件夹显示」，severity `low`。
- 公开回复承诺：统一路径身份键并清理历史显示中的重复项，保留原始大小写显示。

## 根因调查（已完成）

### 身份链路现状

1. **前端** `tabLayout.ts::sameWorkspace`：Windows 下已做 `toLowerCase()` 折叠
   （POSIX 精确比较）——该层已正确；
2. **data-root hash**（Python `domain/data_root.py` + Rust 镜像）：hash 输入经
   `resolve()` / `canonicalize()`，Windows 上对**已存在**路径返回磁盘真实大小写，
   大小写变体天然收敛——不需要改算法（改算法会使所有现有 `sha256-v1-<hex>`
   数据目录失效，需全量迁移，与 low 严重度不成比例）；
3. **Python `workspace_key_for`**（容器 label / 锁文件名）：同样 `resolve()`，
   已存在路径同样收敛；
4. **Rust `history.rs`（缺陷所在）**：
   - `save_locked` upsert 按原样字符串 `w.path == ws.path` 精确匹配 →
     大小写变体各自成条（用户可见的重复项）；
   - `remove_workspace` 按原样字符串 `w.path != path` → 删除只命中精确变体，
     留下孪生记录；
   - `load` 不去重 → 历史文件里已存在的重复项永久保留。

### 结论

重复项的产生与残留都在 history 层；身份统一通过「Windows 大小写折叠匹配 +
已存在路径真实大小写收敛」实现，无需触碰 hash 契约与迁移机制。

## 修复范围

1. `history.rs` 新增 `path_identity_key(path)`：
   - Windows：分隔符归一（`/` → `\`）+ ASCII 小写折叠；
   - POSIX：恒等（大小写敏感语义保留）；
2. `save_locked` upsert 按 identity key 匹配；命中时**保留旧记录的 path 作为
   显示形态**（承诺：保留用户原始大小写），其余字段取 patch；
3. `remove_workspace` 按 identity key 匹配；
4. `load` 按 identity key 去重（保留 `last_used_at` 最新一条及其显示 path），
   去重发生时置 `migrated=true` 让调用方在锁内持久化（沿用 v1→v2 迁移模式）；
5. Python 回归测试：Windows 上已存在目录经 `workspace_key_for` /
   `canonical_workspace_path` 大小写变体同 key（非 Windows skip）；
6. 不改前端（`sameWorkspace` 已正确）、不改 hash 契约向量、不做迁移。

## 实施步骤

1. 新增失败测试（Rust，双平台可跑）：
   - `path_identity_key` Windows 折叠 / POSIX 恒等（`#[cfg]` 双侧断言）；
   - upsert 大小写变体合并为一条、显示 path 保留旧形态（Windows 侧语义，
     POSIX 侧断言仍为两条——防误伤大小写敏感语义）；
   - remove 按 key 命中变体；
   - load 去重已存在重复项且 migrated=true；
2. 实现 `path_identity_key` + 三处匹配点 + load 去重；
3. Python 测试 `workspace_key_for` / `canonical_workspace_path` Windows
   大小写回归（win32 skipif）；
4. 全量门禁：`cargo test --lib`、pytest、vitest、vue-tsc、local-gates；
5. 手测（Windows 实机）：以不同大小写打开同一目录两次 → 最近列表单条；
   forget 后无孪生残留；
6. 提交推送，等远程 CI 全绿后并回 develop。

## 测试计划

自动化：

- Rust `history` 模块测试（POSIX CI 验证恒等分支；Windows 本地验证折叠分支）；
- Python `tests/`（win32 skipif）；
- `cargo test --lib` + `scripts/local-gates.ps1` 全绿。

手测：见上方实施步骤 5（Windows 实机验证）。

## 风险与回滚

- 风险：误伤 POSIX 大小写敏感工作区（`/ws/A` 与 `/ws/a` 是不同目录）。
  缓解：折叠仅在 `#[cfg(windows)]`；POSIX 测试断言变体仍为两条。
- 风险：去重改写历史文件丢数据。缓解：仅合并 identity key 相同的记录、
  保留字段最多的最新一条；复用既有锁内持久化与 corrupt 隔离机制。
- 回滚：revert 本批单个 commit，历史文件格式不变（仍是 schema v2）。

## 执行状态（2026-10-13）

- 分支 `2.1.15-b2-workspace-path-identity`（自 develop 切出）。
- TDD red→green：
  - red：`path_identity_key` 不存在，4 项新测试编译失败；
  - green：实现后 history 模块 21 项全过（4 新增：identity key 折叠/恒等、
    upsert 变体合并保显示形态、remove 变体命中、load 去重 latest-wins）。
- 实现：`path_identity_key`（Windows 分隔符归一+小写折叠 / POSIX 恒等）、
  `save_locked` upsert 按 key 匹配且保留旧显示 path、`remove_workspace` 按
  key 匹配、`load` 按 key 去重并置 migrated 让调用方持久化。
- Python 回归：`tests/test_workspace_path_identity.py` 3 项（win32 skipif）
  验证 `canonical_workspace_path` / `workspace_hash_v1` / `workspace_key_for`
  大小写变体同 key。
- 自动化门禁（fresh run）：
  - `cargo test --lib`：341 passed，0 failed，1 ignored；
  - pytest：新增 3 项通过；
  - `scripts/local-gates.ps1`：`LOCAL GATES: ALL GREEN`。
- 剩余门：Windows 实机手测（双大小写打开同目录 → 最近列表单条；forget 无
  孪生残留）；远程 CI 全绿；并回 develop。

### 手测记录（2026-10-13 00:11 实机，Windows debug 构建）

环境：真实 Workbench 二进制 + 真实 history.json（基线 rev=16，2 条工作区）。

| 步骤 | 结果 |
| --- | --- |
| save `C:\Users\wangyu\aisc-b1-t3`（canonical） | ✅ rev 16→17 |
| save `c:/USERS/wangyu/AISC-B1-T3`（大小写变体，F4 复现路径） | ✅ rev 17→18 |
| load：该目录记录数 | ✅ **1 条**（修复前为 2 条） |
| 显示形态 | ✅ 保留原 `C:\Users\wangyu\aisc-b1-t3` |
| `last_used_at` | ✅ 取较新 `00:11:00Z` |
| layout/tabs 合并 | ✅ 旧记录 layout 完整保留 |
| `workspace_history_remove` 用变体大小写 | ✅ 命中，rev 18→19 |
| 删除后该目录记录 | ✅ 0 条，history 无孪生残留 |

手测通过。T1（b1 lease）与前端 `sameWorkspace` 不受影响（未触碰）。
