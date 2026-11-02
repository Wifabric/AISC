# b1 文件与目录大小写重命名

状态：PLANNED。来源 F1；验收 R-1/H1。进入条件：用户确认实施方案。

## 判断与方案

`workspace.rs::rename_entry` 构造目标后调用 canonicalize_lenient；在 Windows 已有条目上，规范化可能返回磁盘旧大小写，导致请求名称丢失。这是代码推断，实施先用真实 NTFS 场景证实。

保留规范化父目录用于 containment，最终目标保留用户输入 basename。先校验名称、来源身份、目标是否同一条目及冲突；能直接改名时直接执行。若文件系统对仅大小写改名需要中间跳转，只对此情形使用同目录唯一暂名，并在第二步失败时尝试恢复。恢复也失败必须返回实际留存路径和错误，不能吞掉失败或误覆盖别的文件。

不把“路径 casefold 相同”当作跨平台同一文件身份的充分证据；大小写敏感盘上 `Area`/`AREA` 可能是真实两个条目。目录缓存、选中项与刷新结果使用后端最终路径。

## 涉及文件

- `workbench/src-tauri/src/workspace.rs`：rename_entry、canonicalize_lenient、path_eq 与现有 Windows rename 测试。
- `workbench/src/stores/workspaceExplorer.ts`、`features/workspace-explorer/WorkspaceExplorer.vue`：renameEntry、缓存/选中路径刷新。
- `workbench/src/lib/ipc.ts`、`src/aisc/cli/commands/serve_fs.py`：核对 Remote fs.rename 与不覆盖/路径规则，只有必要差异才改。

## 验证与交付

- 真文件/真目录 `Area → AREA → area`，枚举父目录验证精确大小写及文件内容/子文件；仅 `.exists()` 不能证明成功。
- 同名完全不变、独立条目冲突、非法 basename、越界/链接、第二步失败与恢复失败，验证不丢失且错误可诊断。
- store/UI 保留多选、刷新和 2.1.17 复制/粘贴/拖入能力；Local/Remote 受影响路径分别核对。
- CU 按 H1；自动化、真实文件系统、CU、用户验收当前全部 NOT RUN。未增加全局文件移动/覆盖能力。
