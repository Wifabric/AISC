# 远程机器 CLI 版本配对与更新：「需更新」提示

> 状态：计划待用户验收（2026-09-19 立项）
> 方法：ultracode workflow（研究员 + 独立证据核验；核验 verdict=sound，两处行号修正已并入）
> 对应 target：docs/todo.md「远程机器 CLI 版本配对与更新」（v2.1.11 遗留，deb7117 入库）

## 1. 现状（file:line 在案）

- **banner cli_version 链路全通、零消费**：Python 端 emit `cli_version=__version__`（src/aisc/cli/commands/serve.py:484-491）→ Rust handshake 收进 `ReadyBanner`（workbench/src-tauri/src/serve.rs:365-388）。全库唯一读者 workspace.rs:861 只取 `home`。⇒ 加提示层**无需任何协议/服务端改动**。
- **协议硬门独立且不动**：`serve_protocol != 3` = 硬错（serve.rs:371-378，文案已含 upgrade 指引；serve.rs:29-33 用户裁定「never a silent fallback」）。本项是纯软提示层，与硬门不耦合。
- **远程池条目无版本配对驱逐**：本地条目有 mtime 驱逐（serve.rs:619-647），远程条目 `spawned_exe_mtime: None`（serve.rs:520-529、:574，注释「their CLI updates via its own channel」）。⇒ 远程 pip 升级后池内驻留 serve 仍跑旧代码，必须重连才生效——比提示更隐蔽的坑，须随本项修。
- **本机版本参照现成**：`negotiate()` 跑 `aisc version --format json`（cli.rs:245-254，核验修正：原引 242-253）；`negotiate_capabilities` 已注册（lib.rs:139）。双轨下参照只能是**本机 pin 的 CLI 版本**（src/aisc/VERSION=0.1.2.dev0），严禁拿 Workbench 版本（2.1.13）比较。
- **远程更新通道唯一 = pip**：D-8 后 `aisc update` 在线热换退役，pip form 拒绝执行并提示 `pipx upgrade aisc-cli` / `pip install -U aisc-cli`（src/aisc/application/update.py:196-218）；`update --check` 不在 serve deny 表（serve.py:221-263），可经 cli op 远程只读探测 install form——是一键升级（二期）的关键拼图。
- **ssh 传输可执行远端 argv**（BatchMode=yes 密钥-only，cli.rs:565-568，核验修正：原引 559-564）——「帮远程机跑 pip 升级」技术上只是新 ssh 命令路径，无新依赖。
- **UI 挂点全现成**：WorkspacePicker target-row（WorkspacePicker.vue:321-338）、设置页 machines 组（SettingsForm.vue:488-515，无版本列）、全局 toast（支持 action 按钮）、Rust→前端事件模式（stores/update.ts:31 + update.rs:309）。
- **价值实锤**：远程两次故障（r6 provider 全不可用 / step2 命令透传）都因手工 rsync 忘同步 NAS（devlog:345-352、419-420）。

## 2. 方案（研究推荐，Claude 代定采纳）

1. **比对源与时机**：池内驻留会话的 banner 为本体（零协议改动、零额外 RTT）+ 双时机——a) pooled_session 远程条目新建成功后被动 emit `remote://cli-version`（每 machine+版本进程内去重）；b) 设置页 machines 组「检测」按钮主动触发（已池化机器免费回填，未连接机器不主动 ssh）。
2. **UI 三落点**：设置页 machines 组加「CLI 版本」状态行（远程版本/本机参照/判定/检测时间 + 检测按钮 + 需更新指引与复制命令）为主；WorkspacePicker target-badge 旁「需更新」角标为辅；每窗口首次建池后 toast 一次（含「查看」action 跳设置页）。
3. **升级形态**：本期「提示 + 一键复制命令」（pip/pipx 按远程 form 显示），由用户在远程自行执行；「确认后一键远程执行」列二期 Open Decision。全自动静默升级不做。
4. **四层兼容模型（硬门不动）**：L1 serve_protocol≠3 硬错（现状）→ L2 required caps 中门（现状）→ L3 可选 caps 静默降级（现状）→ **L4 cli_version 落后 = 新增软提示**，永不阻断、永不自动驱逐会话。
5. **版本比较器**：新写 Rust 比较——strip `.dev0`/`.devN` 归一后按前 3 段数字比较（对齐 update.py:56-58 `_version_key` 语义）；**不复用** update.rs parse_tag（四段拒收）。判定：remote<local→「需更新」；remote>local→弱 info「远程较新」；相等/解析失败→静默。
6. **一致性修复（随本项）**：检测到远程版本与池内 banner 不一致（或 target 切换）时 evict 旧驻留 serve 重建，防「升级完还跑旧代码」。

## 3. 规格

- **Scope**：Rust 比较器 + `remote_cli_info(machine)` command + `remote://cli-version` 事件 + 设置页/picker/toast 三落点 + evict 一致性修复 + zh/en i18n + cargo/vitest 测试。
- **Out of Scope**：远程一键执行 pip 升级（二期 open）；serve 协议改动；本地 mtime 驱逐逻辑改动。
- **Interfaces**：新 Tauri command `remote_cli_info(machine) → {remote_version, local_version, verdict, serve_protocol}`；事件 `remote://cli-version`；前端 settings store 扩 `remoteVersions: Record<machine, {remote, local, verdict, checkedAt}>`。
- **Constraints**：见 §2.4/2.5 + 版本串容错（`0.1.2.dev0`/`0.1.1`/空串；解析失败不提示，宁缺勿误报）+ 远程命令失败必须显式暴露 stderr + 不新增依赖。
- **Acceptance**：
  - [ ] NAS 真机（CLI 落后一版）→ 建池后 toast 一次 + 设置页显示「需更新」+ 复制命令正确
  - [ ] 版本一致 → 无提示；本机 dev 构建 → 无提示噪音
  - [ ] 远程手动升级后重新检测 → 提示消失且池已驱逐重建（新代码生效）
  - [ ] 未连接机器 → 主动「检测」前零 ssh 流量
  - [ ] cargo/vitest/pytest 四门全绿；zh/en 键奇偶通过

## 4. 实施计划

1. Rust 比较器 `compare_cli_version(a,b)`（.dev 归一 + 前 3 段数字）——验证：cargo 单测（0.1.1 vs 0.1.2.dev0、双向、解析失败、空串）。
2. `remote_cli_info(machine)` command（settings 找机器 → to_ssh_target → pooled_session 读/建 banner）+ lib.rs 注册——验证：cargo test（serve.rs:760+ duplex mock 模式）。
3. 建池被动 emit `remote://cli-version`（machine+版本去重）——验证：cargo test + dev 手测事件到达。
4. settings store 扩 remoteVersions + 事件回填（沿 stores/update.ts:31 模式）——验证：vitest。
5. UI 三落点 + i18n（zh-CN.ts/en-US.ts machines 组 496-510 区域新键）——验证：vitest 组件测试 + 双语截图。
6. evict 一致性修复——验证：cargo test + 手测（升级远程后重连提示消失）。
7. （Open）二期一键升级：serve cli op 跑远程 `update --check` → 确认框 → SshTarget 执行 + progress 回显 → evict + 复检。
8. devlog 入档 + todo 勾选 + local-gates 全绿；手测含 NAS 真机双通道场景。

## 5. 开放问题

| 决定 | 状态 | 默认 | 说明 |
|---|---|---|---|
| 比较方向与提示粒度 | assumed | 仅落后强提示；领先弱 info；.dev0 归一 | dev 构建恒最新，默认静默防噪音 |
| 「自动同步」做到哪档 | **open（用户裁）** | 一期纯提示+复制命令 | 二期一键执行工作量约两倍，且 NAS 失败率有先例 |
| 提示频率 | assumed | 每 machine+版本进程内一次 toast；badge 常显 | 防多窗口/驱逐重试轰炸 |
| 升级后自动驱逐重建池 | assumed | 是（无脑 evict，成本低） | 否则「已最新」提示与旧行为矛盾 |
| 设置页打开时自动检测全部机器 | assumed | 只回填已池化机器 + 手动「检测」按钮 | 未连接机器主动 ssh 有秒级延迟与失败噪音 |
