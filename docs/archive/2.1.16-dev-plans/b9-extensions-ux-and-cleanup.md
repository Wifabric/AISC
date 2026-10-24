# b9 — 扩展 UX 统一 + 缓存政策裁定 + 手测第四轮（2026-10-23）

> 来源：用户复测第四轮 8 项。分支 `2.1.16-b9-extensions-ux-and-cleanup`。

| # | 反馈 | 处置 |
| --- | --- | --- |
| 1 | 三页签 UI 统一：单行、右侧图标、安装改图标、左键展开 | ExtensionsView 重写：单行行（chevron+名称+徽标+spacer+右侧 C/X/⟳/✕），左键展开介绍；市场结果同布局，安装按钮＝＋图标 |
| 2 | 市场技能安装 SKILL_DIR_NOT_FOUND | 复现：`owner/name:dir` 在仓库未注册时直接失败；适配器 install 前 best-effort `repos add owner/name`（幂等）。MCP/插件无同类依赖（deeplink/marketplace 自含来源） |
| 3 | codex 里右键复制灰、不进剪贴板 | 根因：TUI 接管鼠标后拖选不产生 xterm 选区 → hasSelection 恒 false。`rightClickSelectsWord: true`：右键即选词建选区，菜单「复制」可用并写系统剪贴板 |
| 4 | 「移入 测试/移入 Test」扁平噪音 | 收敛为「移入工作记录 ▸」hover 子菜单 |
| 5 | **用户裁定：缓存清理应全量；悬空镜像/容器保持 ≥24h** | `_cache_cleanup_argv`：builder 去掉 until 过滤；dangling 保留；全部文案同步 |
| 6 | 镜像（aisc 相关）要包括 node | 归类 `node`/`node:*` 为 legacy_owned（reason=build-base-image），与其他 legacy 资产同等可管理 |
| 7 | 「容器/镜像（可清理）」与「（aisc 相关）」重复 | 卡片标签统一为「容器（aisc 相关）」「镜像（aisc 相关）」 |
| 8 | 1060 项/15GB 为何清不掉 | **非检测错误**：旧政策给 builder 也套 until=24h，新构建缓存全部 <24h → 回收恒 0B。#5 裁定后 builder 无过滤，一键即清 |

## 门禁
- pytest 1443（cache argv 契约更新）/ Vitest 611（work-records 子菜单断言更新）/ vue-tsc 0 / cargo 362 / vendor 1520/0。
- 适配器新测试 ×2（repos-add 前置 / 纯目录跳过）。
