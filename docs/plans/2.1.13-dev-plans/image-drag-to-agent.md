# 拖动图片给 agent（含剪贴板图片粘贴）

> 状态：计划待用户验收（2026-09-19 立项）
> 方法：ultracode workflow（研究员 + 独立证据核验；verdict=corrected——「远程 leg 首例破窗」前提被推翻，远程成本反而下降，已按修正改写）
> 对应 target：docs/todo.md「拖动图片给 agent」

## 1. 现状（file:line 在案，关键互斥关系经核验）

- **应用内拖拽链路（Stage 11d 已交付）**：explorer 文件节点 dragstart 只写受控 MIME `application/x-aisc-workspace-path`（workspaceDnd.ts:9，D11-10：只带相对路径不带 OS 绝对路径）→ Terminal.vue onDragOver 只认该 MIME（:723-740）→ onDrop 映射 `/root/app/<rel>`（dropPath.ts:15-21）→ quoteForTerminal 恒 POSIX（:67-69）→ writeSession 插入（无 Enter，D11-09）→ 失败只写终端灰字（:753）。
- **OS 文件拖拽当前全应用静默无效**：onDragOver 对无受控 MIME 的拖拽不 preventDefault → drop 不触发；无全局兜底、无 tauri onDragDrop 消费方（grep 证实）。
- **关键互斥（tauri 官方 schema 抓取）**：`dragDropEnabled` 必须保持 **false**（tauri.conf.json:18）——「Disabling it is required to use HTML5 drag and drop on the frontend on Windows」；改 true 会复发 a9198a5 修复的 explorer→终端 drop 失效。**false 下 OS 文件拖入走 WebView2 原生 HTML5 DnD，Terminal.vue 可捕获 File 对象（name+bytes），但拿不到宿主绝对路径**（Chromium 不暴露）——恰好与 D11-10 契约一致。
- **粘贴现状**：doPaste 仅 readText（Terminal.vue:765-776）；write_session 有 1MiB 输入上限（session.rs:33）⇒ 图片字节不能走既有写通道，需新 invoke。
- **落盘位置天然合适**：`.aisc` 在 DEFAULT_IGNORE（workspace.rs:28-47）⇒ `<workspace>/.aisc/uploads/` 对 explorer 树与变更投影不可见（但对 git 是 untracked，见开放问题 3）。
- **远程落盘通道现成（核验修正）**：所有 explorer 变更命令已带远程 leg——统一经 `remote_mutation` 助手（workspace.rs:1735-1736：workspace_create_file→fs.write base64 :1764、create_dir→fs.mkdir :1784、copy_entry、rename）；serve 协议 fs.write/fs.mkdir 已在（serve_fs.py:140-176）。⇒ 上传命令**不是首例破窗**，复用助手模式即可。
- **agent 图片接收通道**：claude code 官方 interactive-mode——`Ctrl+V/Alt+V` 粘贴剪贴板图片插 `[Image #N]`，但读的是**容器内系统剪贴板**（AISC 场景天然无）；prompt 给图片路径 → Read 工具读图（与现有 dropped-path 同契约）。codex：`--image/-i FILE` → `UserInput::LocalImage{path}`（codex-rs/cli/src/main.rs:306-308 源码实证）——**路径通道是唯一等效通路**。
- **直传二进制不可行（方案 C 否决）**：write_session 是 PTY 键盘字节流，裸 PNG 进 TUI stdin=乱码；`[Image #N]` chip 只能由 claude 自己读系统剪贴板产生，workbench 无法经 PTY 伪造。

## 2. 方案裁决（研究推荐，Claude 代定采纳）

- **方案 A（本 target 主体）**：OS 图片拖入 → 前端读 bytes → 新 Rust 命令落盘 `<workspace>/.aisc/uploads/<ts>-<name>`（本地 resolve_contained 包容校验 + no-clobber + .aisc-tmp 原子写；远程走 remote_mutation/fs.write）→ writeSession 插入带引号容器路径 token（无 Enter）。
- **方案 B（同批顺带）**：剪贴板图片粘贴——doPaste 先 readImage（capabilities 增 `clipboard-manager:allow-read-image`）→ 有图走与 A 相同的落盘+插路径 → 失败/无图回退既有 readText。**这是「把图片给 agent」的另一半**：容器内 agent 自己的剪贴板粘贴结构性失效，截图后 Ctrl+V 是比拖文件更高频的场景，边际成本极低。
- **否决**：C 直传二进制（见上）；D 改 dragDropEnabled=true（打破现有拖拽，a9198a5 实证）；落盘 data-root+额外 bind mount（动 runtime.py+容器重建，收益仅「git 无痕」）。

## 3. 规格

- **Scope**：Rust 上传命令（本地+远程双 leg）+ Terminal.vue drop/paste 扩展 + UPLOADS_DIR 契约常量 + i18n + capabilities（仅方案 B 一条）+ 测试。**container/ 不动**（D-1 同精神，纯 Workbench 层）。
- **Out of Scope**：uploads 自动清理（与 D-2 同哲学——不自动动手；体积纳入 docker/磁盘检测项联动）；svg（默认排除）；非图片文件。
- **Interfaces**：新命令 `workspace_upload_image(workspace, relative_dir, name, bytes_base64) → {relative_path}`（命名对齐 workspace_create_file，核验修正：命令面无 workspace_create_entry）；错误稳定码；冲突加 `-2/-3` 后缀不覆盖（D11-05 no-clobber 传统）。
- **Constraints**：D11-09/10/14 契约全保持（不追加 Enter、不取宿主路径、恒 POSIX quoting）；图片判定 MIME+扩展名双兜底（**Windows WebView2 上 File.type 可能为空串**，否则整功能不可用）；大小上限 ≤20MB（自设，不走 writeSession 1MiB）；不覆盖；路径逃逸拒绝。
- **Acceptance**：
  - [ ] Windows 资源管理器拖 png/jpg/gif/webp 进 claude/codex 会话 → 插入 token、模型实读出图
  - [ ] 截图后 Ctrl+V → 落盘+插路径；纯文本粘贴回退不受影响
  - [ ] 拖非图片 → 醒目拒绝灰字；无会话/dead pane → 拒绝不写 PTY
  - [ ] explorer 内拖图仍走纯路径链路（受控 MIME 优先分派）
  - [ ] 多文件（≤10）逐个落盘、token 空格连接一次写入
  - [ ] 远程 target 落盘成功（fs.write 通道）；`tauri.conf.json` 未动（重启验证）
  - [ ] vitest/cargo 全绿；zh/en 键奇偶

## 4. 实施计划

1. 契约常量：UPLOADS_DIR=`.aisc/uploads` + containerUploadsPathFor()（dropPath.ts）——验证：vitest 路径/quoting 断言。
2. Rust 本地 leg：upload_workspace_file（resolve_contained + no-clobber 后缀 + .aisc-tmp 原子写，对齐 op_fs_write 模式）+ lib.rs 注册——验证：cargo 单测（逃逸拒绝/冲突后缀/空 bytes）。
3. Rust 远程 leg：resolve_target_for 分支 → remote_mutation（fs.mkdir + fs.write）——验证：cargo test + 远程手测。
4. 前端接线：ipc.ts 包装；Terminal.vue onDragOver 扩展（types 含 "Files" 或受控 MIME → preventDefault+dropActive）；onDrop 分派（受控 MIME 优先，否则按 kind==="file"+MIME/扩展名过滤图片 → arrayBuffer → upload → quote → writeSession）——验证：组件测试。
5. i18n+反馈：dropImageSaved/dropImageRejected/dropImageFailed（沿用终端灰字先例，terminal.drop* 族）——验证：键奇偶。
6. 方案 B：capabilities 加 clipboard-manager:allow-read-image；doPaste readImage→落盘→插路径，异常回退 readText——验证：terminalPasteKey 测试扩展。
7. 手测清单（§3 Acceptance 逐项 + git 仓 workspace 的 .aisc/uploads 观测）→ devlog 入档 → todo 勾选。

## 5. 开放问题

| 决定 | 状态 | 默认 | 说明 |
|---|---|---|---|
| 剪贴板粘贴（B）同批 | assumed | 同批顺带交付 | 另一半场景，复用落盘函数 |
| 远程 target v1 支持 | assumed | 支持（remote_mutation 现成，成本低） | 核验修正后成本进一步下降 |
| git 仓 .aisc/ untracked 泄露 | assumed | 自动追加进该 workspace `.git/info/exclude`（本地生效、不动用户 .gitignore、幂等） | 联动：变更页 git 源若落地，uploads 不进变更页 |
| 接受范围 | assumed | 仅 png/jpg/jpeg/gif/webp；svg 排除 | 需求出现再放宽 |
| 多文件 | assumed | ≤10，逐个落盘，一次 writeSession | 框选多图常见 |
| 上传命令命名 | assumed | workspace_upload_image | 对齐 workspace_create_file |
| uploads 生命周期 | assumed | 不自动清理；体积纳入 docker/磁盘检测展示项 | 与 D-2 哲学一致 |
