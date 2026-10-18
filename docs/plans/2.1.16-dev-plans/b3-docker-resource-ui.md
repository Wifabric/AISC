# b3 — Docker 资源面板信息层级与「清理构建缓存」

> 反馈来源：`20261017-磁盘与缓存UI需要优化-Thomas`（反馈 #9，UX/low）。
> 分支：`2.1.16-b3-docker-resource-ui`（从 `develop` 切出）。

## 1. 反馈映射

| # | 反馈 | 现状 | 方案 |
| --- | --- | --- | --- |
| 1 | 扫描结果 UI 不好看 | 摘要是普通 label/val 行列表 | 改成卡片网格（每类一张：计数 + 可回收量 + 说明角标） |
| 2 | 信息再多一点点 | 仅 count（Build Cache 另有 size） | 每类补 reclaimable；顶部补总条目/总可回收合计 |
| 3 | Build Cache 中文化 | `rowBuildCache: "Build Cache"` | → 「构建缓存（可清理）」 |
| 4 | 「重新构建镜像」右移，原位加「清理构建缓存」 | 按钮序：扫描 / 清理AISC / 重建 | → 扫描 / 清理AISC / **清理构建缓存** / 重建（最右） |
| 5 | 命令行能删构建缓存且前后数据正确 | `cacheCleanup(24)` 已存在（builder+dangling prune，CLI 测试钉死）但只捆绑在「一键清理」里 | 新增专用 store action：`cacheCleanup(24)` → 日志 → `refreshDockerResources()` |

## 2. 设计

### 专用清理构建缓存
- store 新增 `runCacheCleanup()`：`ipc.cacheCleanup(24)` → 逐条日志（builder/dangling
  回收量或错误）→ `refreshDockerResources()`（与 runDockerCleanup 相同的刷新契约）。
- **不调** `dockerCleanup`（不动容器/镜像）；确认文案明确「仅清理 24h 前的构建缓存
  与悬空镜像」。
- 后端零改动：`docker builder prune --force --filter until=24h` +
  `docker image prune --force --filter until=24h`（无 -a）已由
  `docker_lifecycle.py` 测试钉死（`_cache_cleanup_argv`）。

### 摘要卡片网格
- 每类卡片：图标行（类别名 + 角标说明）→ 主数值（count 或 owned/total）→
  次行（可回收字节，inspect 有数据的类别；仅报告类显示「仅报告」）。
- 顶部合计卡：总条目 / 总可回收（对齐 inspect.summary）。
- 保留 `data-testid="docker-resource-summary"` 兼容既有测试，卡片加
  `data-testid="docker-summary-card"`。

### i18n
- `settings.docker.rowBuildCache` → 「构建缓存（可清理）」。
- 新键：`settings.docker.cacheCleanup`（清理构建缓存）、`cacheCleanupTip`、
  `cacheCleanupConfirm`、`settings.docker.totalCard`（合计）、
  `reportOnly`（仅报告）。

## 3. 不做

- 不改 Rust / CLI 数据面（命令与安全过滤全部复用）。
- 不做逐条缓存选择删除（超出反馈范围）。
- 不动「清理 AISC 容器与镜像」的语义（仍捆绑 cacheCleanup，与现行为一致）。

## 4. 测试（TDD）

- `SettingsForm.test.ts` 追加：
  1. 摘要含「构建缓存（可清理）」且不再出现裸 "Build Cache"。
  2. 按钮顺序：扫描 → 清理AISC → 清理构建缓存 → 重建（重建最右）。
  3. 点「清理构建缓存」→ `cacheCleanup` 以 24 调用、`dockerCleanup` 不被调用、
     扫描/inspect 各再拉一次（删除前后数据正确）。
  4. 合计卡渲染总条目与总可回收。
- 门禁：Vitest + vue-tsc；全量见提交前。

## 5. 手测（并入 HANDTEST.md b3 节）

见 `HANDTEST.md` T10–T12。

## 6. 执行状态（2026-10-18）

已实施并验证。改动全部在 Workbench 前端（store + 组件 + i18n），零 Rust/CLI 变更；
顺带删除 b16 遗留的死代码 `runCacheCleanup(minAgeHours)`（vue-tsc 重复定义暴露）。

- **TDD**：`SettingsForm.test.ts` 新增 3 用例（卡片/中文化/合计、按钮顺序、专用
  清理只动 cache 且刷新扫描），先 RED 后 GREEN。
- **门禁**：全量 Vitest 76 files / 608 tests；`vue-tsc --noEmit` 通过。
- 既有「一键清理」测试（resources→cache→scan 顺序）不回归。
