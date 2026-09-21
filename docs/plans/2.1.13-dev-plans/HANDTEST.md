# v2.1.13 批 1–6 手测清单（2026-09-19 自动化交付后统一手测）

> 覆盖批 1（发布链）/批 2（zip 恢复）/批 3（远程 CLI 配对）/批 4（docker 检测）/
> 批 5（变更页 + D-11）/批 6（拖图/粘贴图）。全部已过 local-gates + 远程 CI；
> 以下为实机确认项。每项通过后在行尾记 ✅ + 日期，失败项贴报错截图并回填 devlog。

## 批 1：发布链准备

- [x] `aisc run` 在已有运行中容器的工作区 → exit 6 + 中文指引（进入/生命周期/多实例）
- [x] 停止容器后 `aisc run` 正常激活；`--label` 多开不受影响
- [ ] （首发 tag 时）装机 preview.1 → 检查更新能检出 v2.1.13-preview.1 → 下载/校验/
      退出安装/手动重启后 About 显示 2.1.13-preview.1，数据与 PATH 保留（详见
      selfupdate-e2e.md §3）
- [x] 设置页「关于与更新」文案为新表述（preview 范围说明 / 最新版本 / 退出并安装）

## 批 2：zip 恢复工作区

- [x] 对工作区 A「彻底忘记」前先导出 zip → 恢复到新路径 B（目录预先不存在）→
      preflight/启动成功
- [x] B 的会话选择器列出 A 的历史会话，claude 与 codex 各 resume 一条可正常收发
- [x] provider 配置与 CLAUDE.md 记忆在位；toolchain 由启动自动重建
- [ ] 恢复对话框：目标 hash 已存在 → 明确拒绝；含 `../` 的 zip → 拒绝；
      旧版无 manifest 的 zip → 可恢复（来源信息为空）
- [x] 首次成功启动前，B 不出现在最近列表（R4）
- [x] 远程 target 下「从 zip 恢复…」按钮不显示

## 批 3：远程 CLI 版本配对

- [x] NAS（CLI 落后一版）设置页 machines 组「检测」→ 显示远程版本/本机版本 +
      「需更新」+ 升级命令复制按钮
- [ ] 切换到该远程机器 → toast 一次（同机器同版本不重复弹）
- [ ] 远程手动 `pip install -U aisc-cli` 后重新检测 → 提示消失，且后续操作走新代码
- [ ] 版本一致 → 无提示；本机 dev 构建（0.1.2.dev0）→ 无提示噪音
- [ ] WorkspacePicker 远程 target 行「CLI 需更新」角标与设置页判定一致

## 批 4：docker 资源检测精细化

- [x] 启动 Docker Desktop → 设置页磁盘组「详细检测」→ 五类分组逐项可见(只显示了数据卷、网络、容器、构建缓存4项)
      （镜像/容器/卷/构建缓存/网络），大小与 `docker system df -v` 人工对照一致
- [ ] 悬空镜像行「现有一键清理会命中」徽标准确（跑一次一键清理后复查徽标消失）
- [x] 扫描期间无任何删除发生；「一键清理 / Docker 资源」原有按钮行为不变
- [x] Docker 未运行 → 优雅降级文案（不崩溃）详细检查在docker没有运行时的报错是纯英文，与原先两项不统一。显示内容为“Reclaimable figures are estimates (UNIQUE-size based, deduped); actual freed space can be lower. will_be_cleaned approximates the current manual cleanup (dangling images / not-in-use build cache) without its age filter.”
- [x] 卷行标注「AISC 永不删除」；网络只计数

这些功能都还行，但是实际上我想实现的是能在workbench内对docker的容器、镜像进行简单的查询和管理，比如镜像删除、容器删除、停止之类的常用操作


## 批 5：变更页 + D-11

- [x] repo 工作区：agent 改/增/删/重命名文件 → 变更树实时更新、徽标正确、（正确）
      点文件出 diff（±着色、二进制占位、大文件截断） 点文件出diff不需要
- [x] 源指示行：repo=「git · 分支 · N」；非 repo/远程/宿主无 git →「会话变更 · N」
      且无报错
- [x] 变更列表随 git 回滚自净（vscode 当前态语义）；agent 回滚后旧条目消失
- [x] git 严格只读：任何位置都没有 stage/commit/discard 按钮
- [x] **D-11 底部预览零残留**：文件树单击不弹预览；变更面板单击不弹预览
      （git 源下弹出的是 diff 面板，不是原始文件预览）；⌫搜索已清
- [x] CRLF 仓库 diff 无全文件行尾噪音；会话中途 `git init` 源热切换；切工作区清理
- [x] 非 git 工作区：watcher 行为与之前一致（1.5s poll、重命名识别不回退）

## 批 6：拖图/粘贴图给 agent

- [x] Windows 资源管理器拖 png/jpg/gif/webp 进 claude/codex 会话 → 灰字提示
      「已上传 N 张」+ 终端出现 `'/root/app/.aisc/uploads/...'` token → agent 能读图(这里有问题，显示的插入成功提示会导致TUI错乱，不如把插入成功提示改成全局统一的消息弹窗提示样式，然后在agent的输入框中插入对应图片的路径,而且当前插入的路径有bug，当前效果为“上传 1 张图片并插入路径（.aisc/uploads/）'/root/app/.aisc/uploads/.aisc/uploads/图片名'”，而正确的路径是“/root/app/.aisc/uploads/图片名”)
- [x] 截图后 Ctrl+V → 落盘 + 插路径；纯文本粘贴不受影响
- [x] 拖非图片 → 「仅支持图片文件」拒绝；无会话/dead pane → 拒绝不写 PTY
- [x] explorer 内拖文件仍走纯路径引用链路（受控 MIME 优先）
- [x] 多张（≤10）框选拖入 → 逐个落盘、token 一次插入
- [x] 远程 target 拖图 → 上传到远程 `.aisc/uploads/` 成功
- [x] git 仓工作区：`.aisc/uploads` 未出现在 git status（info/exclude 或观察）
- [x] 超过 20MiB 的图片 → 明确失败提示

## 回归底线

- [x] claude/codex/bash/cc-switch 四类会话开/关/分屏正常
- [x] provider 页/cc-switch 切换正常（批 3-6 未触碰其数据面）
- [x] pytest / cargo / vitest / vue-tsc 四门绿（已在交付时验证）

## 批 8：history-worklog 批 1（worklog 账本，2026-09-21 交付）

> 准备：启动 Docker Desktop；启动 Workbench（`npm run tauri dev`）；打开你的常用
> 工作区（有 codex/claude 会话历史的那一个）。CLI 用 `$ai` = `E:\Windows\Users\alan\Documents\AISC\workbench\src-tauri\target\debug\aisc.exe`
> （sidecar 已重建含批 8），下文统一写 `$ai`。
> 你的工作区路径下文用 `<WS>` 代指（例如 `D:\proj\demo`）。

### T1 开两个会话（其一 resume）→ 关闭 → 账本正确记录

**操作：**

1. Workbench 里点 `+` 新建一个 **codex** 页签 → 随便问一句话（比如「你好」）→
   等 agent 回复完成 → 点页签的 `×` 关闭它
2. 左侧「历史」面板（文件区第 4 个视图）→ 找到刚才会话 → 右键 → **恢复**
   → 随便再问一句 → 回复完成后点 `×` 关闭（恢复时，codex提示：“This conversation is open in another app；Close it there and press R to continue here.”按下R后，显示To continue this session, run codex resume 01a0c237-9d32-75b1-ad6a-859b212d0035，无法直接使用）
3. 再新建一个 **bash** 页签 → 不用输命令，直接点 `×` 关闭
4. PowerShell 执行：（这个部分你替我测试）
   ```powershell
   & $ai worklog list --workspace <WS> --format json
   ```
   （想看人读格式就去掉 `--format json`）

**理想结果（JSON 里 `data.worklogs` 数组）：**

- **3 条** worklog（每个开过的页签一条：codex 新建、codex 恢复、bash）
- codex 恢复那条的 `sessions[0]` 里有非空的
  `"resume_of_conversation_id"`（= 你恢复的那个会话 ID）；新建那条该字段为
  `null`
- 三条的 `sessions[0].closed_at` 都是**非空时间戳**（`exit_code` 可为 null）
- `sessions[0].agent` 分别是 `codex / codex / bash`
- 数组顺序：**刚关闭的排最前**（按 last_opened_at 倒序）

> **2026-09-21 手测修复（重测前必读）**：你测出的「closed_at 全缺」与「codex resume
> 撞锁」是同一个根因——Workbench 关页签的 terminate 被 serve 的 session 整体
> deny 静默吞掉，容器内 agent 从未被杀（还顺带成了僵尸进程）。已修复并重建
> sidecar。**重测前请完全关闭并重启 `npm run tauri dev`**（serve 驻留进程要用
> 新二进制），然后从 T1 步骤 1 重来一遍。这次理想结果不变：closed_at 非空、
> resume 不再出现「open in another app」。

### T2 rename / archive / delete 三件套

**操作（接着 T1 的数据）：**（这个部分你替我测试）

1. 从 T1 输出里挑一条 `"worklog_id"` 复制（取前 8 位也行）：
   ```powershell
   # 改名（把 <ID> 换成复制到的值）
   & $ai worklog rename --workspace <WS> --id <ID> --title "调研笔记"
   # 再 list 看一眼
   & $ai worklog list --workspace <WS> --format json
   ```
2. 归档同一条：
   ```powershell
   & $ai worklog archive --workspace <WS> --id <ID>
   & $ai worklog list --workspace <WS> --format json   # state 变 "archived"
   & $ai worklog archive --workspace <WS> --id <ID> --restore   # 变回 active
   ```
3. 删掉 bash 那条：
   ```powershell
   & $ai worklog delete --workspace <WS> --id <bash那条ID>
   ```

**理想结果：**

- rename 后那条的 `title` = `"调研笔记"`（list 里可见）
- archive 后 `"state": "archived"`，`--restore` 后回到 `"active"`
- delete 后再 list，bash 那条消失、其余两条还在
- 对不存在的 id 操作：命令不崩溃，输出「未找到该 worklog」

### T3 reconcile 收容存量会话

**操作：**

1. 先看一眼账本当前条数（T2 之后应该是 2）
2. 执行：
   ```powershell
   & $ai worklog reconcile --workspace <WS>
   ```
3. 立刻**再跑一次**同命令
4. list 查看

**理想结果：**

- 第一次 reconcile：输出 `补录 N 个未归档会话`（N = 该工作区在账本上线前
  存在的 provider 会话总数——你平时的 claude + codex 历史会话数，可能不小）
- list 里出现一条 `title` 为**「未归档会话」**的 worklog，`sessions` 数量 = N，
  每个条目带 `"inferred": true`，`terminal_session_id` 为 null
- **第二次 reconcile：输出 `补录 0 个`**，list 不变（幂等，不重复收容）
- 注意：该工作区**打开中的 Workbench 会话**对应的 provider 会话不该被收容
  （它们会随开/关自然入账）——若发现正在用的会话被塞进「未归档」，记下来告诉我

### T4 账本持久性与 fail-open

**操作：**

1. 在 Workbench 里把该工作区停止（或删除 runtime）
2. `& $ai worklog list --workspace <WS> --format json` 再看一次
3. （可选，破坏性实验）把账本文件改坏：
   ```powershell
   # 账本实际路径 = <数据根>\workspaces\<hash>\runtime\worklogs.json
   # 数据根默认 %LOCALAPPDATA%\AISC\data；hash 目录可用下面命令找到：
   & $ai worklog list --workspace <WS> --format json   # 正常输出
   # 直接往该文件写入垃圾（路径手动定位后）：
   Set-Content "<账本路径>" "{broken"
   & $ai worklog list --workspace <WS> --format json
   ```

**理想结果：**

- 容器停止/删除后 list 内容**原样还在**（账本在 host，不随容器消失）
- 账本被写坏后：list **不报错**，返回空列表 `worklogs: []`；runtime 目录里
  出现一个 `worklogs.corrupt-<时间戳>.json`（坏文件被隔离保留）
- 此后 Workbench 里**仍能正常开关会话**（fail-open：账本坏了不挡会话），
  且新开的会话会重新开始记账

### 批 8 验收口径

四组全过 = 批 1 闭环；T3 的「未归档」数量如果大得离谱（比如把整个
`~/.codex` 全局会话算进来了）也告诉我——reconcile 只应扫当前工作区的
claude/codex 目录，不该碰全局。

