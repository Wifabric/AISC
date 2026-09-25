# Docker 资源管理（容器/镜像操作）

> 状态：计划待用户验收（2026-09-20 立项，D-12）
> 来源：批 4 手测反馈——「想在 workbench 内对 docker 容器/镜像做简单查询和管理」
> 边界裁决（2026-09-20 用户三条）：①操作清单=镜像删除/重命名 + 容器启动/停止/删除，无其它；
> ②只允许操作 **aisc 相关**资源，其余只读；③**与检测同构**——跟随驱动机器
> （本机 target 管本机 docker，远程 target 管远程 docker）

## 1. Scope

在设置页「Docker 资源」组（B3 scan 所有权分类的宿主）为 **owned / legacy_owned**
资源行增加操作按钮：

| 资源 | 操作 | docker 命令 | 前置条件 |
| --- | --- | --- | --- |
| 容器（运行中） | 停止 | `stop` | owned/legacy_owned |
| 容器（已停止） | 启动 | `start` | owned/legacy_owned |
| 容器（已停止） | 删除 | `rm -f`（stop 已含） | owned/legacy_owned |
| 镜像（未被容器引用） | 删除 | `rmi <id>` | owned/legacy_owned 且 Containers==0 |
| 镜像 | 重命名（retag） | `tag <id> <新repo:tag>`（旧 tag 保留，可选删除旧 tag） | owned/legacy_owned |

## 2. Out of Scope

- **unverified 资源只读**——「只报告，永不操作」铁律延伸到管理功能；
- 日志查看、网络/卷操作、prune 类批量动作（用户裁定：清单外不做）；
- Workbench 运行中容器的强制删除——lease 活跃时按钮禁用（沿用 forget 的
  blocked 语义），防止 GUI 自己踩自己的运行时。

## 3. 安全不变量（沿用 02 §5 + 新增）

1. **执行时重扫判权**：每个操作命令在锁内**重新分类**，目标此刻必须是
   owned/legacy_owned——UI 快照过期不构成放行理由（「删前必重扫」的别名版）；
   unverified/未知 → `AISC_ERR_OWNERSHIP_REFUSED` 拒绝。
2. **容器先于镜像**；镜像删除前重查 Containers==0。
3. **卷/网络永不操作**。
4. 每个 CLI 动作独立子命令 + 稳定错误码，argv 无 secret；D-9b 路径：动作
   跟随驱动机器（run_control_target 解析当前 target，远程即 SSH 执行远程 CLI）。
5. 前端每个动作过 `confirm()` 对话框（文案含资源名 + 不可逆提示），沿用
   cleanup/rebuild 的确认流。

## 4. Interfaces

**CLI（src/aisc，maintenance 组新增四个子命令，全部 --format json envelope）：**
- `container-action --name <n> --action start|stop|rm`
- `image-rm --id <id>`
- `image-tag --id <id> --repository <r> --tag <t>`
- 退出码：0 成功 · 2 用法错 · 3 docker 不可用 · 6 `AISC_ERR_OWNERSHIP_REFUSED`
  （新码：目标非 AISC 资源或状态前置不满足）· 7 资源不存在

**Rust（workbench/src-tauri/cache.rs 同款薄封装）：**
- `container_action(name, action)` / `image_rm(id)` / `image_tag(id, repository, tag)`
  ——resolve_target_for → run_control_target(argv, 120s) → envelope 校验。

**前端（SettingsForm Docker 资源组改造）：**
- B3 scan 后每行（owned/legacy_owned）尾部渲染操作按钮；lease 活跃/当前窗口
  打开中 → 容器删除禁用（forget 同款守门）；动作完成自动重扫刷新列表。

## 5. Acceptance

- [ ] 运行中 owned 容器：停止 ✓ → 启动 ✓ → 删除 ✓（confirm 弹窗含名称）
- [ ] 删除动作作用于 unverified 容器 → 拒绝（exit 6 + 指引），docker 无变化
- [ ] 未被引用的 owned 镜像删除 ✓；被引用镜像 → 拒绝；unverified → 拒绝
- [ ] 镜像 retag 后 `docker images` 出现新 ref；旧 tag 保留
- [ ] 远程 target（NAS）：同套操作作用于 NAS 的 docker
- [ ] Workbench 正在运行的 runtime：容器删除按钮禁用（lease 守门）
- [ ] argv 契约测试：仅 start/stop/rm/tag/rmi，永不 prune/system/卷网络
- [ ] pytest + cargo + vitest + vue-tsc 四门绿；手测本地 + NAS 各一轮

## 6. 实施计划

1. CLI：ownership 重判辅助（锁内重扫 + 分类断言）→ 四个子命令 + 错误码
   ——验证：FakeExecutor 单测（重判拒绝/成功/状态前置/argv 无禁词）。
2. Rust：三命令薄封装 + argv pin + lib.rs 注册——验证：cargo 单测。
3. 前端：store 动作（confirm 路由）+ Docker 资源组行内按钮 + i18n——验证：vitest。
4. 门禁全绿 → 手测（本地 + NAS 双 target）→ todo 勾选。

## 7. 开放问题

| 决定 | 状态 | 默认 | 说明 |
|---|---|---|---|
| 镜像重命名后旧 tag 去留 | assumed | 保留旧 tag（retag 语义），UI 提示可再手动删 | 删旧 tag = 一次额外 rmi，风险面更大 |
| 容器删除 = stop+rm 组合 | assumed | 是（单按钮组合动作，文案「停止并删除」） | 与 docker_cleanup 既有顺序一致 |
| 操作记录 | assumed | 沿用 warnings/envelope 记录，不新增持久化日志 | 轻量优先 |
