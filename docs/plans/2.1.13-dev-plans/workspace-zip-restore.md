# 导出的工作区 zip 恢复为工作区，且指向新路径

> 状态：计划待用户验收（2026-09-19 立项）
> 方法：ultracode workflow（研究员含实机取样核验 + 独立证据核验）
> 对应 target：docs/todo.md「导出的工作区 zip 恢复为工作区，且指向新路径」——导出半边已交付（2.1.11 P1-3，6034a53），本项补恢复半边

## 1. 现状（file:line 在案，含实机核验）

- **导出半边（已交付）**：`workspace_export_lifecycle(path,dest)`（workspace.rs:557-623）——遍历 `<data-root>/workspaces/<hash>/` 整棵子树写 zip；**zip 根目录名 = `sha256-v1-<旧路径64hex>`**（:583-584）；任意层级 `toolchain` 目录剔除（:600-605）；被锁文件 best-effort 跳过（:609-615）；**无任何 manifest/元数据**。入口：forget 对话框与 InvalidPathDialog 的「先导出（zip）」两处（WorkspacePicker.vue:90-97、270-281）。
- **哈希契约（恢复的落点铁律）**：目录名必须 == `workspace_dir_name(hash(canonical(目标路径)))`（data_root.rs:23/:107-138/:98-101；Rust/Python 双端 SSOT + hash-vectors.json 夹具锁定）。SHA256 单向 ⇒ **无法从 zip 反解原路径**，「原样解包保留旧目录名」方案对新路径天然不成立。
- **恢复即复活**：runtime start 自动 mkdir claude/codex/cc-switch/runtime 四子目录并挂到容器固定位置（runtime.py:1188、:1224-1233）——容器内路径与宿主路径无关，子树放回 `workspaces/<新hash>/` 下次启动自动接管。
- **会话/记忆可恢复性（关键核验）**：resume 扫描源就是状态子树本身（conversation.py:360-361、:376-398）；实机子树 grep **无任何 `C:\` 宿主路径残留**（claude/projects 目录名为 "-"，即容器 munge）⇒ 会话在新宿主路径下原样可用。唯一携带旧宿主绝对路径的是 `runtime/containers.json`（container_registry.py:277-285，有惰性 GC）。
- **应跳过的机器本地易腐产物**：runtime-lease.json、runtime/containers.json、runtime/workspace-locks/**、runtime/runtime/daemon.pid|sock、*.lock。
- **硬要求**：runtime start 要求工作区目录已存在（runtime.py:993-999 AISC_ERR_WORKSPACE_INVALID）⇒ 恢复流程需负责创建目标目录。Workbench 布局在 `config/history.json` 按 path 键控（不在 zip 内）；R4 保证恢复动作本身不产生 history 记录、首次成功启动才入 recent（workspaces.ts:401-412）。
- **零新增依赖**：zip="2" 已在（Cargo.toml:23）；open()/save() 对话框、store 路由（F-A01）、lib.rs 注册、picker 测试与 Rust dirs_override 注入缝（workspace.rs:2670-2701）全部现成。

## 2. 方案裁决（研究推荐，Claude 代定采纳）

- **核心语义 A：按新路径重算 hash 落新目录**。新后端命令 `workspace_import_lifecycle(zip_path, target_path)`：resolve_data_root 全套校验（env/overlap/reparse fail-closed）→ 算新 hash 得 `workspaces/<新hash>/` → 冲突检查（已存在拒绝）→ 解包：剥离 zip 单一根目录（旧 hash 名）映射进新目录，按跳过清单剔除易腐产物 → 目标工作区目录不存在则创建 → 返回 {workspace_key, files, skipped}。
  - 否决 B（原样解包保留旧 hash 目录名 + 只改注册路径）：与解析器契约不自洽，新路径场景不可行。
- **叠加增强 C：导出加 manifest.json，导入可选读取**。`workspace_export_lifecycle` 在 zip 根写 `{schema:"aisc.lifecycle-export/v1", source_path, workspace_key, exported_at, workbench_version, file_count}`；导入端 manifest 存在则展示来源/核对，缺失按 v0 旧 zip 处理不拒绝。向后兼容、改动小。
- **zip 安全**：单一根校验、zip-slip 路径消毒、跳过 symlink/特殊条目、总解压体积上限、拒绝多根。
- **本机限定**：远程机器的数据根恢复不在本期（export 本身也无 remote 参数）。

## 3. 规格

- **Scope**：Rust import 命令 + 纯核函数（dirs_override 注入缝）+（C）导出 manifest + ipc/store/UI「从 zip 恢复」入口 + i18n + cargo/vitest 测试 + 实机验收。
- **Out of Scope**：合并/替换已存在目录；远程数据根恢复；zip 完整性校验和（v1）；Workbench 布局迁移。
- **Interfaces**：`workspace_import_lifecycle(zip_path, target_path) → {workspace_key, files, skipped}`；manifest schema `aisc.lifecycle-export/v1`；UI 走 store 层路由（组件不经 lib/ipc 直连）。
- **Constraints**：用户文件红线（绝不读写目标目录既有用户文件内容）；日志只记 workspace_key + 计数，绝对路径不落日志；resolve_data_root 不得自拼；R4 不写 history；i18n zh/en。
- **Acceptance**（=手测脚本）：
  - [ ] 对工作区 A 导出 → forget（勾选清理）→ 恢复到新路径 B（目录不存在）→ preflight/启动成功
  - [ ] B 的会话选择器列出 A 的历史会话，claude 与 codex 各 resume 一条可正常收发
  - [ ] provider 配置与 CLAUDE.md 记忆在位；toolchain 由启动自动重建
  - [ ] 目标 hash 已存在 → 拒绝且提示明确；含 `../` 条目的 zip → 拒绝；旧版无 manifest zip → 可恢复
  - [ ] history/recent 在 B 首次成功启动前无新记录（R4）；门禁全绿（6034a53 同口径）

## 4. 实施计划

1. Rust 纯核函数 `import_lifecycle_core(zip_path, target_path, dirs_override)` + `workspace_import_lifecycle` 命令注册——验证：cargo test（内存 ZipWriter 构造夹具；用例：happy/无 manifest/zip-slip 拒绝/多根拒绝/hash 冲突拒绝/跳过清单生效/AISC_DATA_ROOT 生效/目标为文件拒绝）。
2. （C）导出写 manifest.json + 单测（file_count 正确、既有导出用例不回归）。
3. ipc.ts `workspaceImportLifecycle` 包装——验证：vue-tsc。
4. workspaces store `importLifecycle(zipPath, targetPath)`——验证：store 三态用例（成功/取消/失败）。
5. WorkspacePicker UI：路径行加「从 zip 恢复」次级按钮（remote target 隐藏）→ 恢复对话框（选 zip → 目标路径输入 + browse + 「目录不存在将创建」明示 + manifest 来源信息）→ 成功后预填 launcher 输入框 + 结果 toast——验证：workspacePicker.test.ts 扩展。
6. 门禁全跑（vitest + vue-tsc + cargo test workspace）→ devlog 入档 → todo 勾选。
7. 实机验收 §3 清单 a-h。

## 5. 开放问题

| 决定 | 状态 | 默认 | 说明 |
|---|---|---|---|
| UI 入口范围 | assumed | 仅 WorkspacePicker 加按钮（remote 隐藏）；InvalidPathDialog 保持三钮 | picker 按钮已可达恢复场景 |
| 目标 hash 已存在冲突策略 | **open（用户裁）** | v1 一律拒绝并提示换路径/先清理；不做替换 | 替换会静默抹现有生命周期数据，风险不对称，可后补 |
| 导出加 manifest（方案 C） | assumed | 做 | 恢复 UI 可展示来源；旧 zip 兼容零成本 |
| 恢复成功后自动 preflight | assumed | 自动填输入框并聚焦「下一步」，不自动跑 | 保持 single-flight 与启动时机控制 |
| docker_api.rs:149 registry 路径不一致顺带修 | assumed | 搭车修（一行+单测：应 join("runtime")，现轻量轮询永远读不到 registry，有全量兜底非功能损坏） | 研究顺带发现 |
| zip 炸弹体积上限 | assumed | v1 不强制（与导出对称）；需要则 2 GiB 可配置 | 导出已剔 toolchain，正常 zip 小 |
