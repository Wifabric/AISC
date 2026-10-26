# v2.1.17 Computer Use 预测试记录

> 执行环境：Windows 11，Computer Use 可用。按 DEVELOP_WIKI §1.4，本文件先于用户
> 统一手测记录 agent 预测试；`PASS` 不替代用户最终手测。

## 状态总览

| 批次 | 实现状态 | 预测试 | 说明 |
| --- | --- | --- | --- |
| b1 | 已实现 | UI 关键路径 PASS | H1 安装、H4 更新状态保留已用真实 Workbench UI 执行 |
| b2 | 待开工 | PENDING | 尚无可测实现 |
| b3 | 待开工 | PENDING | 尚无可测实现 |
| b4 | 待开工 | PENDING | 尚无可测实现 |
| b5 | 待开工 | PENDING | 尚无可测实现 |
| b6 | 待开工 | PENDING | 尚无可测实现 |
| b7 | 待开工 | PENDING | 尚无可测实现 |

## b1 预测试（2026-10-26）

### 运行标识

- Workbench：分支 `2.1.17-b1-proxyless-extension-reliability` 的
  `workbench/src-tauri/target/debug/workbench.exe`
- Explicit CLI：同分支 `workbench/src-tauri/target/debug/aisc.exe`
  （避免 worktree `.venv` editable 指回主 checkout）
- 镜像：`super-claude:latest @ sha256:c2a0790a297b214c360158ac957683b43c8bc571f97e7adb6d0a61087f6bc352`
- 工作区：`C:\Users\wangyu\AppData\Local\Temp\AISC-217-B1-CU-45b44292155c44c0b6424306cd3452e8`

### 发现并修复

1. **Explicit CLI 优先级破坏**
   - 现象：即使 `workbench.exe --aisc-cli <branch-cli>` 启动，本地 target/serve 仍
     复用已安装版 `C:\Users\wangyu\AppData\Local\AISC Workbench\aisc.exe`，
     导致 `skill-install-group` 以空 stdout 被 serve 报
     `cli op got non-envelope output: ''`。
   - 根因：`session::resolve_cli()` 只读 saved pin，未优先读取 `CliArg`。
   - 修复：`resolve_cli_choice(explicit, pin)` 让 explicit path 先于 saved pin；
     新增 Rust 回归 `explicit_cli_path_outranks_saved_pin`。
2. **Market repo 大小写漂移**
   - 现象：skills.sh 返回 `juliusbrussee/caveman`，SSOT 已登记
     `JuliusBrussee/caveman`；cc-switch 对同目录报
     `SKILL_DIRECTORY_CONFLICT`。
   - 根因：组安装未按 directory 对齐已注册 repo 的 owner/name 大小写。
   - 修复：`_canonical_skill_spec()` 在 group dedup 前按 SSOT directory 匹配
     casefold 相同的已注册 repo，并用已登记大小写执行官方 install；新增
     `test_skill_group_reuses_registered_repo_casing`。
   - 注意：adapter 位于容器镜像内，修复后必须重建 Docker 镜像；仅重建 sidecar
     不够。本轮已重建镜像并用新 runtime 复测。

### H1 UI 安装路径 — PASS

Computer Use 实际操作：

1. 通过最近工作区打开预测试 workspace。
2. 等待预检结果：Docker / 工作区 / 镜像 / 网络 / 运行时冲突均显示“通过”。
3. 点击“启动”，等待状态“就绪”。
4. 点击左侧“扩展”。
5. 在“搜索技能商城（skills.sh）”输入 `caveman` 并点击“搜索”。
6. 观察市场结果：`juliusbrussee/caveman · 13 个技能`。
7. 点击该行“安装全部”。
8. 操作期间窗口树出现状态：`安装中 / 0/13 / juliusbrussee/caveman`，
   全部操作按钮禁用；当前组级 IPC 非流式，0/13 保持到完成符合已文档化行为。
9. 约 6.5 分钟后操作状态消失，按钮恢复可用，未出现错误 alert。
10. 数据面复核：13 个 `JuliusBrussee/caveman` 子技能均存在，且
    `enabled_claude=true, enabled_codex=true`。

### H4 UI 更新状态保留 — PASS

Computer Use 实际操作：

1. 展开 `JuliusBrussee/caveman` 已安装组。
2. 点击子技能 `caveman` 的 `X`（Codex 启用/停用）。
3. 观察 toast/status：`切换完成：caveman`。
4. 点击父组“更新全部”。
5. 操作期间窗口树出现 `更新中 / 0/13 / JuliusBrussee/caveman`；
   当前组级 IPC 非流式，0/13 保持到完成符合已文档化行为。
6. 约 6.5 分钟后操作状态消失，按钮恢复可用，未出现错误 alert。
7. 数据面复核：
   - `caveman`: Claude=true，Codex=false；
   - 其余 12 个 caveman 子技能：Claude=true，Codex=true。
   - 用户显式关闭状态未被更新覆盖。

### 未执行的 H2/H3 UI

- H2 UI 的“direct 失败 + mirror 可用”未在本轮 UI 重构后重复执行；此前的当前
  数据面 H2 证明已记录于 HANDTEST。若统一用户手测前需要完整 UI H2，可在容器
  `/etc/hosts` 屏蔽 `github.com` 后重复 H1。
- H3 前置条件仍不满足：ghfast 与 gh-proxy 均可访问；不得伪充实网全失败结果。

## 后续批次

b2–b7 完成实现与自动化验证后，逐批追加 Computer Use 预测试记录。全部批次均达到
PASS 或记录具体阻塞后，才发起用户统一手测窗口。

### 修复后验证

- Targeted：adapter / bridge / dispatch Python `57 passed + 10 subtests`，extensions
  Vitest `21 passed`，vue-tsc 通过，Rust `367 passed`。
- Vendor：`1532` checksums 全部通过。
- Sidecar / bundle / Workbench debug exe 已重建。
- Full local gates：Python `1487 passed`、Rust `367 passed`、Vitest `644 passed`、
  vue-tsc 通过，输出 `LOCAL GATES: ALL GREEN`。
