# v2.1.15 b16：preview.7 字段反馈修复

## 用户反馈（2026-10-15，preview.7 实测后）

1. 新创建的 Work Record 应默认折叠。
2. 帮助菜单中原「关于 AISC Workbench」实为诊断入口，应改名「运行诊断」；
   「文档」应改名「帮助文档」；另增真正的「关于 AISC Workbench」弹窗展示核心版本。
3. 取消终端里的「fit 诊断（网格 5s 内 ≥6 次变化）— 截图反馈」探针弹层。
4. 关于与更新仍报 `app.update/network: releases HTTP 403 Forbidden`。
5. 设置 → 磁盘与缓存中，Docker 资源扫描基本准确，但其上方的 df 摘要 / cache inspect
   旧界面数值混乱；应合并到 Docker 资源中，保证数值正确，一键清理可成功执行。

## 根因取证（2026-10-15）

- GitHub API 当前本机出口已被限流：响应头显示
  `X-RateLimit-Limit=60`、`Remaining=0`，因此 403 是 unauthenticated API rate limit，
  不是更新资产不存在。`https://github.com/Wifabric/AISC/releases.atom` 可正常访问，
  且包含最新 release tag / release notes；`raw.githubusercontent.com` 与 GitHub release
  资产下载 URL 均可访问。更新器可以改用 Atom 作为主通道、API 作为 fallback。
- Work Record UI 当前默认所有 Collection 展开；`createCollection()` 没有把新 id 加入
  collapsed set。
- 帮助菜单当前 `openAbout()` 直接 `doctor.openDialog()`，语义确实混用。
  Runtime capability 已含 CLI / bundle / image / Claude / Python 版本，可配合 Tauri
  app version 构建真正 About 弹窗。
- Terminal 内 `fitDiagOpen` 会在 5 秒 6 次网格变化时自动弹出截图反馈层；这是用户要求移除的探针。
- 磁盘页存在三套数据面：
  1. `maintenance cache-usage`：Docker df 摘要；
  2. `maintenance cache-inspect`：按资源明细；
  3. `maintenance docker-scan`：AISC ownership 分类。
  前两者与 Docker 资源分开展示且口径不同，用户看到的是三张表。b15 已修复 Docker
  string-boolean 和同 ID tag 聚合，明细层数据源可保留为 build cache/volume/network
  统计，但应并入 Docker 资源扫描结果，不再独立展示。
- 一键清理目前分两条：Docker cleanup 只清 AISC owned/legacy 资源；cache cleanup 只清
  builder cache 与 dangling image。需要组合为一个明确按钮并刷新统一结果。

## 方案 / 任务

### Task 1：Work Record 新建默认折叠

- `createCollection()` 成功后将新 collection id 加入 collapsed set。
- 组件测试断言：创建后标题可见、成员区隐藏，手动展开后可见。

### Task 2：Help 菜单语义与 About 弹窗

- 菜单项改名：
  - 「运行诊断」→ doctor dialog；
  - 「帮助文档」→ opener；
  - 新「关于 AISC Workbench」→ About dialog。
- About 弹窗展示：
  - Workbench app version；
  - CLI / bundle / image / Claude Code / Python 版本；
  - 平台信息；
  - serve protocol 如可从现有状态获得。
- 测试覆盖三个入口语义和核心版本渲染。

### Task 3：移除 fit 诊断弹层

- 删除 `fitDiagOpen`、`fitDiag`、5s/6次变化检测和 overlay 模板/CSS。
- 保留正常 fit / resize 逻辑，不再向用户弹出截图反馈探针。

### Task 4：更新检查改用 Atom 主通道

- 新增 Atom release feed parser：
  - 提取 release tags；
  - 用现有 semver 规则选择最新 final/preview；
  - 资产 URL 按 GitHub release download 稳定规则构造。
- 检查顺序：`releases.atom` 主通道 → GitHub API fallback。
- 403 rate limit 不再表现为失败；下载 / sha256 继续走 GitHub release URL。
- bundled CLI 版本继续从 raw GitHub `src/aisc/VERSION` 读取。
- Rust 单测覆盖 Atom preview/final 排序与资产 URL 构造。

### Task 5：磁盘与缓存合并为统一 Docker 资源面板

- 移除 Docker 资源上方的旧 df 摘要和独立 cache inspect UI。
- 一个「扫描 Docker 资源」动作并行执行：
  - `docker-scan`：AISC ownership / 可管理资源；
  - `cache-inspect`：build cache、volume、network 与唯一 image 统计。
- 统一概览展示：
  - 可管理容器（unique）；
  - 可管理镜像（unique image ID）；
  - 悬空归属镜像；
  - Build Cache 总数 / 可回收；
  - Volumes / Networks（报告only）。
- 明细仅保留在统一 Docker 资源区域，不再出现多套标题。
- 「一键清理」组合执行：
  1. AISC Docker cleanup（owned/legacy containers + images）；
  2. cache cleanup（builder cache + dangling images，24h 过滤）；
  3. 重新扫描统一结果。
- 测试覆盖统一扫描、数值映射、一键清理调用顺序与最终刷新。

## 验收

- 新建 Work Record 默认折叠。
- Help 菜单三个语义清晰；About 弹窗展示核心版本。
- 终端不再出现 fit 诊断弹层。
- 在 GitHub API 403 / rate limit 环境下仍可发现 preview 更新。
- 设置 → 磁盘与缓存只呈现一套 Docker 资源口径；一键清理成功后数值刷新。
- 本地门禁与 CI 全绿。

## 执行状态（2026-10-15）

- `d3fcdeb` 计划落盘；`a80a8d8` 新建 Work Record 默认折叠；
  `4e56f39` Help 菜单语义拆分 / About 弹窗 / 移除 fit 探针弹层；
  `9444409` 更新检查改用 releases.atom 主通道并保留 API fallback；
  `df91326` 磁盘与缓存合并为统一 Docker 资源面板与组合清理。
- 本地门禁：Python 1412 passed / 53 skipped；Rust lib 362 passed / 1 ignored；
  Vitest 76 files / 599 tests；vue-tsc 通过，`LOCAL GATES: ALL GREEN`。
- 下一步：push → PR CI → ff-only merge develop → develop 全路径 CI →
  Workbench `v2.1.15-preview.8` → 用户复测。
