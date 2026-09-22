# docker 资源检测精细化（扫描更细、项目更准）

> 状态：计划待用户验收（2026-09-19 立项）——D-2 改裁后的重新立项
> 方法：ultracode workflow（研究员 + 独立证据核验；verdict=corrected——核验员用本机 Docker 29.8.0 实测推翻两条采集矩阵前提，方案已按实测重写）
> 对应 target：docs/todo.md「docker 资源检测精细化（2026-09-19 改裁：不做自动清理；扫描更细、项目更准）」；裁决 D-2

## 0. 约束（D-2 铁律）

- **绝不加自动触发**：无定时、无事件、无 scan 后自动接 cleanup；所有删除仍需用户显式点击。
- **不动现有 cleanup 语义**：_cache_cleanup_argv / docker_cache_cleanup / docker_cleanup / docker_rebuild 的命令、until 过滤、锁序、确认流保持不变——本项只动**检测/呈现**。
- **检测为只读**：新增采集仅限 ls/df/du/ps 类命令，禁 prune/rmi/rm 副作用；02 §5 八条安全不变量全适用（永不 system prune、volumes/networks 不碰、unverified 永不删、Docker 不可用不下结论）。
- **数据一律机器格式**（--format json / 结构化），禁人读表格解析（模块既有 invariant）。

## 1. 现状（file:line 在案）

- **「缓存扫描」现状只有 4 行汇总**：`system df --format {{json .}}` → {Type:{total_count,active,size,reclaimable}}（docker_lifecycle.py `_system_df`/`cache_usage`）；UI=「磁盘与缓存」卡 4 行数字（SettingsForm.vue disk 组）+「Docker 资源」组的所有权三桶（B3：owned/legacy/unverified 预览前 6 个名字截断）——**无逐项、无尺寸、无卷/网络/cache 明细**。
- **cleanup 现状**：builder prune + dangling image prune（均 `--filter until=`，无 -a，<1h 拒绝；24h 硬编码在 SettingsForm onCacheCleanup）。
- **全链 subprocess docker CLI**（RealDockerExecutor.run_captured 永不 shell=True）；docker SDK（>=7.1）已是依赖，gateway 有 SdkGateway/AutoGateway。
- **超时预算骨架**：单命令 15-30s、prune 300s、Rust SCAN 120s/CACHE 300s。

## 2. 采集矩阵（核验实测修正后）

| 资源类 | 采集源（能力探测降级链） | 可回收口径 |
|---|---|---|
| 镜像 | **主源：`docker system df -v --format json`**（⚠️ Docker 29.x 实测可用，官方文档未记载——核验员本机 29.8.0 实测返回 {Images,Containers,Volumes,BuildCache} 结构化 JSON，Images[] 含真实 UniqueSize）；`image ls --format json` 供 id/repo/tag/created（⚠️ 29.x 其 SharedSize/UniqueSize 是 "N/A" 占位，仅旧版语义相反） | 未用镜像 Σ **UniqueSize**(Containers==0)；dangling 为其子集；区分「未用但不会被现有清理删除」（现 cleanup 只吃 dangling） |
| 容器 | `ps -a --size --format json` | 非 running 的可写层 size（解析 "35.6 kB (virtual 109 MB)" 双数字） |
| 卷 | `volume ls --format json` + dangling 过滤 + ps Mounts 交叉 → 四象限（named/anonymous × 在用/未用） | 大小默认 unknown（逐卷 du 可能分钟级）；02 §5 永不删卷，展示+「不会被清理」标注 |
| Build Cache | **主源：df -v json 的 BuildCache[]**（含 InUse/Shared/Size/LastUsedAt/UsageCount，无 Reclaimable 布尔——由 InUse 推导）；辅助：`buildx du --format json`（⚠️ Docker Desktop 现行 CLI 已把 `docker builder` 别名到 buildx，`builder du` 实测可用——能力探测针对插件/试跑，不按命令名断定）；多 builder（default+desktop-linux 常态）全扫串行、按记录 ID 去重 | Σ Size(可回收)，带 Type/Mutable/Shared/LastUsedAt |
| 网络 | `network ls --format json` + 容器引用计数（df -v json 无 Networks 节） | 0 字节，只报数量 |

- **能力探测兜底**：df -v --format json 失败（旧 CLI 可能忽略组合）→ 回退逐资源命令组合；UniqueSize 拿不到 → unknown；buildx 缺失 → cache 类降级 df 摘要行。失败类别标 unknown 不阻塞其他类别。
- **「项目更准确」的两个呈现要件**：①每行打 `will_be_cleaned_by_current_cleanup` 徽标（dangling && age≥until；cache LastUsedAt≥until；until 值从组件常量提为可显示配置）；②UI 明示「估算值，实际释放可能低于此值」免责（Docker RECLAIMABLE 共享层满额计入是著名高估口径）。

## 3. 规格

- **Scope**：新只读 CLI 子命令 `maintenance cache-inspect`（新 envelope `aisc.docker-cache-inspect/v1`）+ Rust 薄封装 + 前端「详细检测」手风琴详情 + i18n + fixtures 值一致性测试。首屏保留现 df 4 行快照与 B3/O7 全部按钮原样。
- **Out of Scope**：自动触发（D-2）；cleanup/rebuild 语义改动；逐项勾选删除（研究推荐默认不做——改动面数倍，列下阶段候选，见开放问题 1）；docker-rebuild --pull 等顺手项。
- **Interfaces**：envelope {categories: images/containers/volumes/build_cache/networks，每行 {id,name,kind,state,size?,unique_size?,shared?,dangling?,in_use?,reclaimable?,will_be_cleaned?,last_used_at?} + 每类 summary + totals + capabilities + disclaimer}；Rust `cache_inspect` command（≤120s）；TS cacheInspect()。
- **Acceptance**：
  - [ ] 真机（Docker Desktop）扫描 <120s，五类齐全，唯一尺寸与 df -v 人工对照一致
  - [ ] 无 docker → 现状降级文案；buildx 缺失 → cache 类降级不阻塞
  - [ ] argv 只读 pin 测试通过（断言永无 prune/rmi/rm/-a/system prune）
  - [ ] will_be_cleaned 徽标与实际 cleanup 影响集一致（抽对手测）
  - [ ] cleanup/rebuild 链路 git diff 为零；cargo/vitest/pytest 全绿；i18n 双语

## 4. 实施计划

0. 本地钉版：把本文件符号锚点换成精确行号（研究员经 raw 读 origin/main，无行号；develop 与 main 有漂移）——验证：锚点清单入规格。
1. 契约先行：envelope schema + Rust/TS 共享 fixture 值一致性测试先行（红→绿）。
2. Python 采集器 `docker_lifecycle.cache_inspect()`：§2 矩阵 + 能力探测 + 超时降级——验证：FakeExecutor fixture 单测（解析/去重/兜底）+ argv 只读 pin。
3. 可回收口径纯函数 + will_be_cleaned 徽标计算（until 参数化默认 24）——验证：纯函数单测。
4. CLI 注册 maintenance cache-inspect（--format json；部分类别失败以 capabilities/warnings 表达不 exit 1）——验证：CLI 集成测试 + 现有 8 个 cache 测试回归。
5. Rust 薄封装（cache.rs 扩展，transport-only 惯例）+ lib.rs 注册——验证：cargo 单测（argv pin/envelope 解析/null 容忍）。
6. TS 层：ipc.ts + settings store 新状态（loadDockerInspect，保留 loadCacheUsage 不动）——验证：vitest 三态（成功/部分失败/超时）。
7. UI：disk 组「详细检测」按钮 → 分组手风琴（行级大小+徽标+每组合计+总可回收+免责）——验证：手测清单。
8. i18n zh/en 全套 key；**顺带清偿** settings.ts/SettingsForm.vue 存量硬编码中文（store 日志改 message key+params 结构）——验证：缺 key lint + 双语截图。
9. 回归与发布件：全门绿 + cleanup 链路 diff 审查为零 + devlog 入档 + todo 勾选。

## 5. 开放问题

| 决定 | 状态 | 默认 | 说明 |
|---|---|---|---|
| 手动逐项删除纳入本阶段？ | **open（用户裁）** | 不做；扫描只读+徽标，保留现有全量手动 cleanup | 用户裁了「不自动清理」，但「手动逐项删」未裁；逐项删除=新命令+确认流+unverified 排除，改动面数倍 |
| 深扫挂载点 | assumed | 新增只读 cache-inspect 子命令；cache-usage 4 行保留为首屏快照 | 改 cache-usage shape 有兼容风险 |
| named 未用卷展示（现有清理永不删） | assumed | 展示+「不会被清理」徽标 | 信息完整优先 |
| 卷大小默认算不算 | assumed | 默认 unknown，显式「计算卷大小」动作按需触发 | 逐卷 du 可能分钟级 |
| buildx 多 builder 全扫/只扫当前 | assumed | 全扫（串行，每 builder ≤30s，失败标 unknown） | 只扫当前会漏 cache |
| 可回收展示口径 | assumed | 准确口径（UniqueSize 去重）+ 免责声明；首屏 df 摘要保持原样 | 深扫比现在「更小」需解释 |
| 老版本 docker 兜底 | assumed | 能力探测→类别降级 unknown | df -v json 是 29.x 实测、官方未记载 |
| until 阈值可见化 | assumed | 做（徽标+阈值展示，不做修改入口） | 「项目更准确」核心 |
| i18n 债务顺带清偿 | assumed | 做（新增代码触碰同一片） | settings.ts 硬编码中文 |
