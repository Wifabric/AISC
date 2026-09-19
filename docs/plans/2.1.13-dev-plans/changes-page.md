# 变更页：vscode git 插件体验 + 变化文件用文件树

> 状态：计划待用户验收（2026-09-19 立项）
> 方法：ultracode workflow（研究员 + 独立证据核验；核验员缺本地工具判 BLOCKED，四条 load-bearing 断言由主线抽查证实——unattributed 无清除机制、FLAT/tree-only 注释、serve fs.* 无 exec、docker_api 无写通道）
> 对应 target：docs/todo.md「变更页：vscode git 插件的体验 + 变化文件用文件树」

## 0. 边界声明（不回退既有裁定）

- **v2.1.9 D-6 朴素化裁定继续有效**：变更信息唯一出口=变更页；归因分类（kind 分组/chips/归因徽章）**不复活**——树形分组是呈现层重构，不是分类复活。
- **文件树行「只显示名字」（7169909）继续有效**：变更徽标只出现在变更树，不得加回 explorer 文件树行。

## 1. 现状（file:line 在案，关键断言经主线抽查）

- **扁平列表现状**：变更 tab（activeKind `artifacts`，WorkspaceView.vue:69-87）渲染 `changesFiltered` 扁平列表（WorkspaceExplorer.vue:147-155 注释「FLAT list」、:1225-1245）；唯一过滤器=共享搜索。
- **数据源三合一**：Rust watcher 批事件 `workspace://changed`（stores/workspaceExplorer.ts:339-355、:375-406）+ loadDir 快照对比（:455-475）+ 1.5s 兜底轮询（:541-555）——全写同一个 `unattributed` 映射（:196）。
- **只增不减（方案核心前提，已抽查证实）**：unattributed 无「已读/过期」清除——唯一变动点是 rename 换键（:803-811）与切工作区重建（:274-328）。⇒ 变更页语义是「**本会话累计事件日志**」，不是「当前未提交状态」；与 vscode git 体验的本体差距在此。
- **watcher**：本地 notify + 远程 fs.watch 投影同一 debounce 循环（300ms 防抖、批 200、溢出→stale，watcher.rs:401-452、:489-606）；TempRenameTracker 根治原子写误报（49dc539）；WATCH_IGNORE 含 .git（:132-148）。
- **git 可得性**：容器有 git 且工作区 `-v` 挂 /root/app 共享 .git（Dockerfile:75、:400-406；runtime.py:1188）——但 **Workbench→容器无 exec 通道**（docker_api.rs 仅 HTTP GET，已抽查）；**远程 serve 协议仅 fs.\* 8 个 op，无 exec**（serve_fs.py:359-368，已抽查）；宿主 git 可跑（host_mcp.rs git-ro 先例 :42-49）但**非 repo 是常态**（devlog T-F2e：git status exit 128 实测）。
- **预览 pane 是 diff 落点**：512KB 有界读取、text/image/不支持三态（workspace.rs:50、:1040-1081）；前端零 diff 依赖。

## 2. 方案裁决（研究推荐 B，Claude 代定采纳）

**双源：本地工作区 + 宿主 git 存在 + 是 repo → git 为权威源；否则回退现有 watcher 源。**

- git 源：`git status --porcelain=v1` 为列表权威（当前未提交态、自净），`git diff --no-color -U3` 为 diff 数据；watcher 事件继续复用为**实时触发器**（事件→节流重跑 status，≥2s 间隔，不造新轮询）。
- 回退源：现状 watcher 逻辑原样（远程工作区恒回退；非 repo 无感降级）。
- git **严格只读**：仅 status/diff/cat-file 级；stage/commit/discard/checkout 写操作本期禁止（作用于宿主用户 repo，需独立裁定）。
- UI 结构：共享搜索保留；源指示行（git=「分支 · N 变更（M2 A1 D1）」/回退=「会话变更 · N」）；**变更树**（从变更路径集合构建投影树，目录行=twisty+聚合徽标计数）；底部 diff pane（扩展现有 preview pane：unified ± 着色、created 全绿/deleted 全红、二进制占位、图片走现有 preview、512KB 截断）。

被否决：A 纯 watcher 升级（无当前态语义）；C 全 git 化（非 repo 工作区直接失去变更页，违反普适性）。

## 3. 规格

- **Scope**：Rust 三个本地限定命令（git_info/git_status/git_diff）+ store 双源改造 + 变更树组件 + diff pane + i18n + 测试。
- **Out of Scope**：git 写操作（stage/commit/discard）；远程工作区 git 源（协议无 exec）；语法高亮 diff 库（bundle 纪律，v2.1.12 有 bundle CI 拦截先例 37f8a3d）。
- **Interfaces**：`workspace_git_info → {available, branch, autocrlf}`、`workspace_git_status → [{path, X/Y, renameFrom?}]`、`workspace_git_diff(path) → {unified, binary?, truncated?}`；错误用新 `WB_ERR_GIT_*` 稳定码；remote target 直接返回不支持。
- **Constraints**：containment（前端只传 workspace 相对路径，D11-04）；非 repo 零报错零退化；性能纪律（git 子进程事件节流 ≥2s、复用 512KB 预算、无新依赖）；CRLF 陷阱（diff 调用带 `-c core.autocrlf=false`，验收覆盖 CRLF 用例）；工作区切换清理全部新状态。
- **Acceptance**：
  - [ ] repo 工作区：agent 改/增/删/重命名 → 树+徽标实时更新（watcher 触发），diff 正确，列表随回滚自净
  - [ ] 非 repo / 远程 / 宿主无 git → 回退源正常、无报错
  - [ ] CRLF 用例无全文件行尾噪音；大文件/二进制/图片正确降级
  - [ ] 会话中途 git init → 源热切换；切工作区状态清理干净
  - [ ] 1.5s poll 与 PERF P 系列行为不回退；cargo/vitest 全绿

## 4. 实施计划

1. 立项文档评审（本文件）+ 开放问题裁决入 decisions。
2. Rust：workspace.rs（或新 git_status.rs）三命令 + WB_ERR_GIT_* 码 + porcelain=v1 -z / numstat 二进制判定 / `-c core.autocrlf=false`——验证：cargo 单测（porcelain 解析、rename、二进制、非 repo 稳定码）。
3. ipc.ts 三封装 + types（GitInfo/GitStatusEntry/DiffResult）——验证：tsc。
4. store 双源：changesSource('git'|'watcher') + gitEntries + 检测/刷新 action（激活变更页/watcher 事件节流触发 ≥2s）+ 切工作区清理——验证：store 单测（源切换/跳变/清理）。
5. `changesTree.ts` 投影树（前缀嵌套、目录聚合徽标、deleted 孤儿目录、搜索过滤）——验证：vitest 全覆盖（深路径/根级文件/纯目录删除/重名基名）。
6. WorkspaceExplorer.vue artifacts 分支重构：变更树（复用 TypeIcon/ChangeBadge/APG 键盘 onTreeKeydown 模式 :852-905、右键加「查看变更」）+ 源指示行 + 三态文案——验证：组件测试。
7. diff pane 扩展（unified ± 解析着色、二进制占位、图片走现有 base64、512KB 截断；非 git 源点击回退 previewFile）——验证：组件测试 + fixture 手测。
8. i18n zh/en 全量键（源指示行/diff 头/二进制占位/WB_ERR_GIT_* 映射）——验证：键奇偶 + bundle CI。
9. 手测九项清单（repo 实时更新/非 repo 回退/远程回退/宿主无 git/CRLF/大文件二进制图片/中途 git init/切工作区清理/回归 poll 行能）→ devlog 入档 → todo 勾选。

## 5. 开放问题

| 决定 | 状态 | 默认 | 说明 |
|---|---|---|---|
| git 源切换时的列表语义跳变 | assumed | 接受收缩，首次切换不警报；源评估仅在激活/切工作区时进行 | vscode 体验=当前态；现状=日志 |
| git 写操作列入本期？ | **open（用户裁）** | 不做，Out of Scope 注明前提（用户批准 + git 身份检测） | 替用户写宿主 repo 历史，高危 |
| 非 repo 回退面板保留/引导 init | assumed | 保留现状文案，不做 init 引导 | 引导 init 又回到写操作问题 |
| 远程工作区是否显式说明不支持 git 视图 | assumed | 静默回退，源指示行已表达 | 不弹窗 |
| diff 引入高亮/组件库 | assumed | 不引入，纯 ± 行前缀着色 | bundle 供应链纪律 |
| diff 形态 unified/双栏 | assumed | unified；未来可升级中央 pane | 变更树在 240-320px 窄 dock |
| 目录行聚合徽标样式 | assumed | 计数为主（N + M/A/D 缩写） | 四色堆叠是 D-6 教训 |
| git 可用性检测缓存/失效 | assumed | 激活必查 + 事件节流重查（≥2s）；树操作不主动探测 | spawn 成本与 .git 中途出现的平衡 |
