# 批 1：自更新三项（静默拉起 / staging 目标版本命名 / PATH REG_EXPAND_SZ）

> 状态：计划待用户验收（2026-09-23 立项）
> 来源：v2.1.13 收口时用户裁决转期 v2.1.14 的三个观察项（devlog.md:3652-3663；
> 批 1 含开池版本 bump 2.1.13 → 2.1.14）
> 方法：ultracode workflow（研究员 + 独立证据核验；verdict=corrected，4 处
> 行号/措辞修正已并入，含 devlog 时间戳行修正 3658→3646-3647）
> 对应 target：docs/todo.md「v2.1.14-target」自更新三条

## 1. 现状与关键发现

### a) 静默升级完成后自动拉起新版

- **拉起机制已存在，从未被激活**：`app_install_update`（update.rs:332-356）
  以 `cmd /c start "" <setup> /S` detached 拉起安装器（342-345）、600ms 后
  `app.exit(0)`（353-354）——**不传 `/R`**。而 installer.nsi 的
  `.onInstSuccess`（1647-1672）在 silent/passive 下解析 `/R`（1658-1660）→
  CheckDocker/StartDockerDesktop → `nsis_tauri_utils::RunAsUser` 拉起新版
  （1669）；GUI 完成页 `RunFinishApp`（428-443）同款 RunAsUser。该机制是
  tauri-bundler 2.9.4 模板原生（nsis/README.md），非自研。
- **提权边界双保险**：`installMode: currentUser`（tauri.conf.json:45）+
  `RequestExecutionLevel user`（installer.nsi:117-119）——安装器本身不提权；
  RunAsUser 以发起安装的原始用户上下文拉起（对比：裸 Exec 继承安装器令牌、
  ShellExecute runas 是升权方向、Explorer 代理 trick 脆弱——均不取）。
- **拉起时点在升级链之后**：`.onInstSuccess` 位于 Section Install 尾部
  `UpgradeDockerLifecycle`（1607-1645，docker-cleanup + rebuild，
  nsExec TIMEOUT=1800000=30min 预算）之后。E2E 实测链约 2min（devlog:3646-3647：
  安装 21:43 落盘、镜像 21:44:54 重建），冷机可至 30min——文案与发布说明
  必须写明（zh/en 更新卡片 614-627 块「退出并安装」→「退出并更新（完成后
  自动重启）」类表述，双语同改）。

### b) staging 文件名改目标版本

- `staging_path`（update.rs:225-229）用 `current_version(app)`（81-83 取
  package_info）；下载落 `.part`（287-288）→ sha 校验 rename（323-325）。
  目标版本在调用方现成：`pick_latest` 返回去 `v` 前缀 tag（update.rs:156）
  = 前端 `info.latest`（stores/update.ts:22/41）——只是没穿透到下载参数
  （ipc.ts:824-825 只传 setupUrl/sha256Url；stores/update.ts:59 同）。

### c) NSIS PATH 写 REG_EXPAND_SZ

- `PathWrite`（installer.nsi:917-924）是「保型写回」：`PathRead`（887-914）
  只查类型（898）、值由 ReadRegStr 读字面文本（902，`%VAR%` 不展开——CI
  smoke nsis-installer.yml:181-182 断言字面 `%USERPROFILE%` 存活即证）；
  值缺失时 `$PathType` 强制 1（907）→ **首装机 user PATH 不存在则新建为
  REG_SZ**（正是 E2E 翻车点）。
- **存量无法自愈**：升级链 `/UPDATE` 卸载保留 owned entry（1811-1815）→
  新装 `AddInstDirToPath` already-present 早退（1030-1038）不写回。
- 实害机理（观察项措辞成立）：Windows 只对 REG_EXPAND_SZ 展开 `%VAR%`；
  NSIS `WriteRegStr` 写入时还会展开 `%VAR%` 冻结内容（devlog:1355 CI 实证）。

## 2. 方案（D-3）

| 项 | 改法 | 触达 |
| --- | --- | --- |
| (a) /R | `update.rs:343` 参数追加 `"R"`：`["/c","start","",&setup_path,"/S","/R"]`；installer.nsi 零改动 | update.rs 一行 |
| (a) 文案 | zh/en 614-627 块 ready/install/installConfirm 补「完成后自动重启」 | zh-CN.ts / en-US.ts |
| (b) staging | `appDownloadUpdate` 加第三参 targetVersion（ipc.ts:824-825；update.ts:59 传 `info.value.latest`）；Rust `app_download_update` 加 target_version 参数，`staging_path(app,&target)` → `workbench-setup-{目标版本}.exe`；顺带清理 staging 旧 `workbench-setup-*.exe` | update.rs / ipc.ts / update.ts / update.test.ts:63-68 mock |
| (c) PATH | `PathWrite` 917-921 删类型条件恒 `WriteRegExpandStr`；already-present 早退分支补「$PathType<>2 → Call PathWrite」类型规整自愈；CI smoke 补「全新 PATH 首装后 GetValueKind=ExpandString」断言（157-182 区域） | installer.nsi / nsis-installer.yml |

## 3. 风险

- (a) 拉起在 30min 预算升级链后——已按 D-3 接受并写入文案/发布说明；
- (a) `CheckIfAppIsRunning`（utils.nsh 构建时注入，仓库无源）与 app 退出的
  600ms 竞态为**既有**风险，E2E 已实测通过，加 `/R` 不改变；
- (b) latest 含 `-preview.N` 连字符，Windows 文件名合法；
- (c) 极旧第三方工具对 HKCU\Path 期待 REG_SZ（实际未见）；既有 CI 断言
  （保型/字面）不受影响。

## 4. 验收

见 [HANDTEST.md](HANDTEST.md) T1（三条独立验收线：/R 拉起链——进程账户名
无 Elevated、Docker 先拉起；下载参数穿透——`%TEMP%\aisc-workbench-update\`
文件名含 2.1.14；注册表类型——升级前后 GetValueKind 均 ExpandString、
`%TESTVAR%` 字面存活、新装机首装断言）。
