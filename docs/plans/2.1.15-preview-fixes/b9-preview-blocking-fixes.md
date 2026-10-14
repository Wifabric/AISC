# v2.1.15 b9：preview.1 阻断修复

## 用户反馈（2026-10-14，v2.1.15-preview.1）

1. WSL 远端 AISC 可进入 bash；Windows 远端 AISC 仍停留在无 `/root/app#`
   prompt 的旧问题。
2. 当前打开 bash 直接失败：`open_session() got an unexpected keyword argument
   'fork_session'`。
3. Work Records UI：
   - 长会话标题使恢复/删除按钮溢出所属卡片；
   - collection 内子代理会话重复平铺，与 All Sessions 树状行为不一致；
   - 从 Work Records 恢复会话不可用；
   - 未归档会话看不出树状结构。
4. 需要让 Work Records 内的会话树 visually obvious。

## 根因结论

- **P0 session open 崩溃**：`aisc.cli.commands.session.cmd_session_open` 已向
  `open_session()` 传递 `fork_session`，但 `application.session.open_session`
  的签名没有该参数，也没有继续传给 `build_session_exec()`。此前测试 mock 了
  `open_session`，没有覆盖真实调用链。
- **P0 Windows 远端旧 CLI 配对缺口**：b5 修复远端 PTY pump，b8 给
  `session.open` 增加 `fork_session` 语义，但 serve wire 仍停在 protocol 3，
  旧 0.1.3 Windows 远端可被接受。用户可见的 WSL/Windows 差异与“WSL 使用当前
  开发 CLI、Windows 使用旧 0.1.3 CLI”的形态吻合；本批把 serve 协议升到 4，
  使旧远端在握手阶段明确报“升级远端 AISC”，不再落入半可用 PTY。
- **P1 Work Records child 重复**：`memberTree()` 能从 provider conversation
  构建树，但 `memberVisible()` 错误地从 `WorkRecordMember` 读取不存在的
  `parent_thread_id`，导致所有 child 被认为无父并平铺显示。既有测试把该字段
  动态塞进 fixture member，掩盖了 wire 类型不匹配。
- **P1 树状不明显 / 溢出**：缩进通过 `li.style.paddingLeft` 施加，深层 child
  会把整行（包括右侧按钮）推出卡片；未归档列表仍是 flat `v-for`。

## 实施与验收

1. Python red test：真实 `cmd_session_open(..., fork_session=True)` 调用链必须
   生成 `--fork-session --resume-id`，不得 TypeError；默认 bash open 必须成功。
2. Serve protocol red tests：Python/Rust 均钉 protocol 4；旧 banner 3 必须
   在握手阶段失败并提示升级远端 CLI。
3. Work Records red tests：
   - fixture member 不携带 `parent_thread_id`，仅 provider conversation 携带；
     child 默认隐藏、展开后单次出现；
   - 深层缩进由专用 leading indent 承担，行和右侧按钮不随 padding 整体右推；
   - unfiled provider conversations 使用同一 tree builder，child 默认折叠。
4. 会话恢复链路由 P0 session open 修复恢复；不新增“整工作区一键恢复”语义
   （D-3 已裁定 Collection 只保存成员关系，不绑定/恢复 workspace）。
5. 门禁：目标 Python/Vitest/Rust red→green，随后 full local gates；PR CI
   全绿后 ff-only 回 develop，再打下一跳 preview。

## 手测边界

- Windows 远端需在远端安装同协议的下一跳 AISC/CLI 后复测；
  当前从本机探测 `10.147.20.90:22` 超时，暂无法只读取样远端版本。
- Claude fork 仍需有 Claude transcript 的环境做实机回归。

## 执行状态（2026-10-14）

- P0 session open：已补真实 command→application 调用链测试；红灯精确复现
  `TypeError: open_session() got an unexpected keyword argument 'fork_session'`。
  `open_session` 接收并转发 `fork_session` 后目标测试转绿。
- P0 远端配对：Python/Rust 均新增 protocol 4 契约测试，红灯复现 `3 != 4`；
  双端 `SERVE_PROTOCOL` 已升至 4，CLI 开发版本升至 `0.1.4.dev0` 并补 release notes。
- P1 Work Records：修正 member tree 的 parent 判定来源；缩进改为专用 leading
  indent，不再把整行右推；unfiled 列表复用 conversation tree builder。
- 目标测试：session/serve 93 passed；WorkRecordsView 15 passed；Rust protocol
  契约测试 passed；vue-tsc passed。
- 全量门禁：Python 1394 passed / 53 skipped；Rust lib 349 passed / 1 ignored；
  Vitest 74 files / 568 tests；vue-tsc passed；`cargo test --no-run` 与前端 build
  均通过。
- 待办：PR CI 全绿后合并，发布下一跳 preview，再按 `HANDTEST.md` 完成
  b9-T1–T3 实机验证。远端 `10.147.20.90:22` 当前从本机连接超时，Windows
  远端版本采样待机器可达后补充。
