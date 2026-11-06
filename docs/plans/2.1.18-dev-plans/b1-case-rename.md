# b1 文件与目录大小写重命名

状态：已实现，改名/刷新/重入及磁盘不覆盖 CU PASS；冲突提示初测 FAIL 后已修复，用户取消 CU，修后界面复测 NOT RUN。PR/CI/用户验收未完成。来源 F1；验收 R-1/H1。D-5 已授权启动。

## 判断与方案

`workspace.rs::rename_entry` 构造目标后调用 canonicalize_lenient；在 Windows 已有条目上，规范化返回磁盘旧大小写，导致请求名称丢失。真实 NTFS 回归已复现：返回 README.md，但枚举仍是 readme.md；修复后精确名称断言通过。

保留规范化路径用于 containment，最终 rename 目标保留用户输入 basename。先校验名称、来源、实际规范路径相等且 basename 仅大小写不同、目标冲突，再直接执行 fs::rename。Windows 实测直接改名可行，因此不引入中间暂名、两阶段操作或恢复分支；失败沿用现有可读错误映射。

不把“路径 casefold 相同”当作跨平台同一文件身份的充分证据；大小写敏感盘上 `Area`/`AREA` 可能是真实两个条目。目录缓存、选中项与刷新结果使用后端最终路径。

## 涉及文件

2026-11-02 H1 实测补充：文件/目录改名、刷新重入和磁盘内容均通过，但冲突时 alert 存在而文案不可见。重命名行没有定位上下文，绝对定位错误提示落到可见区域之外。此项属于既定 H1“冲突显示错误”的验收修复：仅给正在重命名的行复用 `name-input-row` 定位样式，随后重跑现有前端回归/构建与实际 CU 冲突检查。

- `workbench/src-tauri/src/workspace.rs`：rename_entry、canonicalize_lenient、path_eq 与现有 Windows rename 测试。
- `workbench/src/stores/workspaceExplorer.ts`、`features/workspace-explorer/WorkspaceExplorer.vue`：renameEntry、缓存/选中路径刷新。
- `workbench/src/lib/ipc.ts`、`src/aisc/cli/commands/serve_fs.py`：核对 Remote fs.rename 与不覆盖/路径规则，只有必要差异才改。

## 验证与交付

- 真文件/真目录 `Area → AREA → area`，枚举父目录验证精确大小写及文件内容/子文件；仅 `.exists()` 不能证明成功。
- 同名完全不变、独立条目冲突、非法 basename、越界/链接沿用现有保护；没有第二步及恢复分支，不把它们记录为已测。
- store/UI 保留多选、刷新和 2.1.17 复制/粘贴/拖入能力；Local/Remote 受影响路径分别核对。
- 自动化：Rust 415 passed / 2 ignored；Windows 文件和目录精确大小写、往返改名、内容保留、原名不变 PASS。普通 NTFS 未执行大小写敏感目录中独立 Area/AREA 的断言分支，Linux/macOS/真实 SSH NOT RUN。
- 前端 store 与 Python Remote fs.rename 路径无需修改；UI 根据 H1 实测补错误提示定位，见本节补充规格。用户验收尚未执行。未增加全局文件移动/覆盖能力。
- 构建、候选哈希、原始日志与 UI 证据见 [PRETEST](PRETEST.md)。新增回归留本机，遵守此前用户不上传新增测试用例的要求。

## PR #63 复审补充（2026-11-06）

#62 已合入 develop，#63 改投 develop；历史实测记录保留。本轮补验 H1 冲突反馈：行定位修复仍会让列表底部的提示落在滚动视口外。保留现有样式，在错误节点渲染、重命名输入恢复焦点后，将提示以 nearest 方式滚入可见区域；即时名称校验使用同一处理。原有键盘选择、取消和不覆盖契约不变。新增测试仍仅留本机。

本轮自动化、布局与 CI 结论见 PRETEST 新增条目；浏览器布局测试不代表真实 Workbench CU 或用户验收通过。
