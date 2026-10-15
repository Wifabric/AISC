# v2.1.15 b15：preview.6 字段反馈修复

## 用户反馈（2026-10-15，preview.6 实测后）

1. 设置 → 关于与更新出现 `app.update/network: error sending request ... api.github.com ...`，需要保证 Workbench 可更新；GUI 与 CLI 是不同版本线，但更新要一并处理。
2. Work Records 会话重命名含中文不成功；Collection 重命名中文出现乱码。
3. Work Records 本身也应可折叠，不只折叠会话。
4. Claude 也会出现同名会话，需要像 Codex 一样识别 parent-child。
5. 磁盘与缓存除 build cache / images / containers 外，也要管理 AISC 安装引入的 node 等基础镜像；标注与可回收统计不一致。
6. Docker 构建后 Docker Desktop images 中出现 `docker.1ms.run/library/node` 与 `node` 两行；同 ID mirror alias 应视为单一资源，尽量避免保留双 tag。
7. 删除 Work Records 的 Activate 状态；新建会话直接进入未归档会话。
8. Work Records 的会话删除与 Collection 删除确认弹窗不应发声。

## 根因取证（2026-10-15）

- 更新器当前只用一个 reqwest client：显式 system proxy 存在时绑定该 proxy，失败无 direct fallback；请求也无重试。用户网络中 GitHub TLS/代理瞬断时直接显示 `app.update/network`。
- 当前 `UpdateInfo` 只报告 Workbench 版本，没有报告本地 sidecar CLI 与目标安装包内 CLI 的独立版本；无法表达「GUI 与 CLI 分开比较、同一个 installer 一并升级」。
- 远端 Windows serve 复现中文请求：通过 JSON frame 发送 `work-record create --title 中文记录`，远端返回 `UnicodeEncodeError: '\udcad' surrogates not allowed`。b12 注释声称从 `stdin.buffer` 按 UTF-8 解码，但 `_serve_loop()` 实际仍调用 text `stdin.readline()`；Windows SSH 下 TextIO 用本地代码页/surrogateescape 解码，中文在进入 JSON parser 前已被破坏。会话与 Collection 重命名同走该通道。
- Claude JSONL 复盘发现 resumed/forked 文件中同时存在当前 `sessionId` 与历史 `session_id`（不同 UUID）。当前 scanner 只为 Codex 提取 parent，Claude parent 恒为 null，因此同名 Claude 会话无法树状折叠。
- Work Records UI 只有 member/unfiled child 的 expanded set，Collection 自身无折叠状态；且 UI/后台 reconcile 维持 `active_collection_id` 与自动收容。
- 删除确认使用 Tauri native `confirm()`，Windows 系统对话框会播放提示音；项目内已有大量自绘 dialog 模式，可改为无系统音的自绘确认。
- Docker `system df -v --format json` 的 `InUse`/`Shared` 是字符串 `"false"`/`"true"`；Python `bool("false") == True`，导致 1254 条未用 build cache 全被判成 in-use，inspect 可回收为 0，与 df summary 的 17.58GB 不对应。
- `docker.1ms.run/library/node:22-slim` 与 `node:22-slim` 是同一 image ID 的两个 tag。构建预拉 mirror 后 `docker tag` 成 bare name，但没有移除 mirror alias；Docker Desktop 按两个 repo tag 显示两行。
- Cache inspect images 也按 tag 展开，同一 ID 双 tag 被计两次；b14 仅 Settings 管理列表聚合，inspect 明细尚未聚合。
- AISC 构建的最终镜像带 `org.aisc.managed=true` label，但基础 node 镜像没有该 label。可安全管理的基础镜像需要通过 layer provenance / 构建记录证明，不能把用户手动 node 镜像全局认定归 AISC。

## 方案 / 任务

### Task 1：更新链路可靠 + GUI/CLI 双版本报告

- Rust update 模块：
  - 构建多个 HTTP strategy：system proxy → no-proxy direct，各带短重试；
  - 输出 reqwest error cause chain，区分 proxy/TLS/read；
  - `UpdateInfo` 增加 `cliCurrent` / `cliLatest` / `cliUpdateAvailable`；
  - 从当前安装目录 sidecar 读取 CLI current；
  - 从目标 Workbench release tag 的 `src/aisc/VERSION` 读取 bundled CLI target；
  - GUI newer 或 CLI older 任一成立即显示可更新，下载仍使用同一个 Workbench installer，一并替换 GUI + CLI。
- Settings 更新卡片显示两行版本与更新说明。
- Rust 单测覆盖版本比较与「GUI 相同但 CLI 落后仍需更新」。

### Task 2：serve Windows UTF-8 stdin

- `_serve_loop()` 改为优先从 `stdin.buffer.readline()` 读取 raw line 并 UTF-8 解码；测试 StringIO 无 buffer 时保持兼容。
- Python 测试用本地代码页/surrogate 场景证明中文 title 不再破坏。
- CLI bump `0.1.8.dev0`。

### Task 3：Work Records 折叠 / 去 Activate / 静默确认

- UI 增加 `expandedCollections`，Collection header 显示 twisty 与成员计数，默认展开、可折叠；折叠时保留拖拽目标边界。
- 移除 Active badge、Activate/Deactivate 按钮、自动激活 watcher 与 `data-active` 呈现。
- 后台 reconcile 不再按 active collection 自动收容；刷新 observed baseline，新会话进入 unfiled。兼容旧 ledger 字段但不再使用。
- 新增自绘删除确认 overlay，会话删除与 Collection 删除不再调用 native `confirm()`，因此无系统提示音。
- 测试覆盖折叠、无自动 activate、新会话 unfiled、删除不调用 native confirm。

### Task 4：Claude parent-child

- Claude scanner 从 JSONL 中与当前文件 sessionId 不同的历史 `session_id` UUID 提取 `parent_thread_id`。
- 保留 Codex 既有 source.subagent / history_base 逻辑。
- 测试覆盖 Claude resumed/forked 同名会话 parent 关联与 parent 自身无 parent。

### Task 5：Docker 构建去重与管理

- `_ensure_base_image()`：
  - bare tag 已存在时，检查 mirror alias 是否同 ID，同 ID 则 `docker rmi <mirror>` 仅移除 alias；
  - 从 mirror 拉取并成功 `docker tag` bare 后，立即移除 mirror alias。
- `_cache_rows()` 用严格 Docker bool parser 解析 `"true"`/`"false"`，修复 build cache 可回收统计。
- Cache inspect images 按 image ID 聚合多个 repo tag，name 合并显示，unique/reclaimable 只计一次。
- Docker scan 增加安全的基础镜像归因：
  - 对 AISC managed 最终镜像与候选基础镜像比较 RootFS layers；
  - 基础 layer 是最终镜像前缀/子集时标记 `legacy_owned`，纳入 AISC 管理与 cleanup；
  - 不按 `node` 名称全局声明所有权。
- 测试覆盖 string bool、build cache summary、同 ID tag 聚合、mirror alias 清理、layer-provenance 基础镜像管理。

### Task 6：门禁 / 发布

- 目标测试 → full local gates。
- PR CI → ff-only merge develop → develop Workbench / CLI sidecar / Bundle / NSIS 全绿。
- Workbench `v2.1.15-preview.7`；CLI `0.1.8.dev0` / TestPyPI。

## 验收

- 更新检查在网络抖动时尝试 proxy/direct 多路，并在 UI 明确区分 GUI 与 CLI current/latest；一个 installer 一并升级。
- 远端 Work Record / 会话中文重命名保真，无乱码、无 surrogate 错误。
- Collection 与会话均可折叠；没有 Activate 状态；新会话默认 unfiled。
- Claude resumed/forked 同名会话按 parent-child 折叠。
- Docker Desktop 不再保留同 ID mirror alias 双行；AISC 安装引入且可安全证明的基础镜像纳入管理。
- 磁盘 df summary 与 inspect 的 build cache / image 可回收口径一致。
- 删除确认无系统音。
- 本地门禁与 CI 全绿。

## 执行状态（2026-10-15）

- `4556ec5` 计划落盘；`d561861` serve UTF-8 / 中文标题与 Claude parent 扫描测试；
  `543e5e2` Work Records 折叠、去 Active、静默删除；`8e96843` Docker alias、
  string-bool、layer provenance 与统计修复；`3bf7ead` + `fc9093b` 更新链路、
  GUI/CLI 双版本与 CLI envelope 解析修正。
- 本地门禁：Python 1412 passed / 53 skipped；Rust lib 361 passed / 1 ignored；
  Vitest 75 files / 594 tests；vue-tsc 通过，`LOCAL GATES: ALL GREEN`。
- 下一步：push → PR CI → ff-only merge develop → develop 全路径 CI →
  Workbench `v2.1.15-preview.7` + CLI `0.1.8.dev0` / TestPyPI → 用户复测。
