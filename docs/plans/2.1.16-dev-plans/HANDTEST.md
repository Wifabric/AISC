# v2.1.16 手测方案

> 按《DEVELOP_WIKI》§1.3 书写规范：每条手测项必须包含操作、期望结果（可观察
> 的具体值/状态）、前置准备、异常判定口径。「正确 / 可用」这类结论词不达标。

## 前置准备（每组测试前）

- T1/T2 需要：v2.1.16 预览版安装包（含 b1 之后的镜像）或 `aisc build` 本地重建；
  Docker Desktop 已启动；一个测试工作区（如 `E:\Projects\aisc-b1test`）。
- T3 需要：容器内无预置离线 tgz 的镜像形态（即走在线 npm 安装的构建），
  或直接使用 b1 构建产物。

## T1 CLI 内 codex 自更新（反馈 #10 主链路）

1. **操作**：
   1. Workbench → 选择工作区 → 打开「codex」页签。
   2. 等 codex TUI 出现更新提示（或 Bash 页签内运行 `npm view @openai/codex version`
      确认存在比出厂 0.154.0 新的版本后，在 codex TUI 接受更新）。
   3. 更新完成后 `exit` 退出，重新打开 codex 页签，输入 `/status`（或首屏版本行）。
2. **期望结果**：
   - 步骤 2 不再出现 `npm error code EEXIST` / `File exists: /usr/local/bin/codex`，
     更新命令以成功状态结束。
   - 步骤 3 的版本号显示为更新后的版本（高于出厂 0.154.0），且 provider 路由
     正常（模型可对话；`aisc provider current` 显示的 route 与更新前一致）。
   - `which codex` 仍返回 `/usr/local/bin/codex`（wrapper 未被更新替换）。
3. **异常判定口径**：更新报任何 npm error、更新后 codex 无法启动、或 provider
   切换失效（对话报 provider/auth 错误），记下完整报错文本告诉 Claude。

## T2 CLI 内 claude 自更新（同链路）

1. **操作**：同 T1，把目标换成「claude」页签与 `@anthropic-ai/claude-code`。
2. **期望结果**：更新成功无 EEXIST；重开页签后 `claude --version` 显示新版本；
   settings.json 注入仍生效（对话正常、模型映射不变）。
3. **异常判定口径**：同 T1。

## T3 更新落点与 wrapper 完整性（docker exec 视角）

1. **操作**：宿主终端执行
   `docker exec <容器名> bash -lc "npm config get prefix && ls /tmp/aisc-toolchain/npm-global/bin && head -1 /usr/local/bin/codex"`
   （容器名用 `aisc ps` 查询）。
2. **期望结果**：
   - prefix 输出 `/tmp/aisc-toolchain/npm-global`（temporary/未挂载 toolchain 时）
     或 `/opt/aisc/toolchain/npm-global`（project 模式 entrypoint 树）。
   - `/tmp/aisc-toolchain/npm-global/bin/` 下出现更新后的 `codex`/`claude`。
   - `/usr/local/bin/codex` 首行仍是 `#!/bin/bash`（wrapper 完整）。
3. **异常判定口径**：prefix 为 `/usr/local`、wrapper 被替换为 JS/ELF 内容、或
   toolchain bin 下无更新产物，都记为异常并附命令输出。

## T4 project 模式持久性（可选，挂载 toolchain 的工作区）

1. **操作**：project 模式工作区内完成 T1 更新 → `exit` → Workbench 关闭工作区
   → 重新打开同一工作区 → 查 codex 版本。
2. **期望结果**：重开后仍是更新后版本（`/opt/aisc/toolchain` 跨容器保留）。
3. **异常判定口径**：重开后退回出厂版本，且 `docker exec <容器> ls /opt/aisc/toolchain/npm-global/bin`
   为空——记为异常（说明 toolchain 挂载或解析链有问题）。

> 说明：temporary 模式（无 toolchain 挂载）更新随容器销毁而回退属预期，
> 不算异常；正式升级路径仍是 `aisc update --pin-tool` + 重建镜像（§8.5）。

## T5 左键只读预览（b2 · 反馈 #11-1）

1. **前置准备**：打开有历史会话的工作区，Explorer → 工作记录；确认某记录含至少一条成员会话。
2. **操作**：左键单击任一成员行 / 未归档会话行（不点 ▶ 恢复、✎、✕ 按钮）。
3. **期望结果**：弹出只读会话查看器（与历史页相同的 viewer），标题为该会话名，
   内容为富文本渲染的 transcript；点击关闭后不产生任何新页签、不 resume、
   Work Records 列表不变化。
4. **异常判定口径**：单击后打开新 agent 页签、会话列表刷新、或 viewer 空白报错。

## T6 拖动父节点带动子节点（b2 · 反馈 #11-2）

1. **前置准备**：一个 Work Record 含父-子会话树（子会话默认折叠）；展开父节点；另有一个目标 Work Record。
2. **操作**：拖动父会话行到目标 Work Record 的成员区（先记录拖动前两边的成员列表截图/数目）。
3. **期望结果**：目标记录成员列表按原顺序出现父会话 + 其全部子孙会话；源记录中这些行全部消失；
   再次刷新后顺序保持一致。同区内拖动父节点到新位置同样整树移动。
4. **异常判定口径**：父节点移动但子节点留在原处 / 目标区顺序丢失 / 刷新后回退。

## T7 创建会话与分支会话（b2 · 反馈 #11-3）

1. **前置准备**：Work Records 可见一条 codex 与一条 claude 会话；终端区无同名运行中页签。
2. **操作**：右键 codex 会话 → 「新建会话」；等页签出现后回到工作记录右键同会话 → 「分支会话」；对 claude 会话重复两项。
3. **期望结果**：「新建会话」打开对应 agent 的空会话页签（等价 /new）；「分支会话」以该会话为源打开 fork 页签（等价 /fork，preflight 失败会在行内报错而不是无反应）；两个动作完成后工作记录列表立即刷新——新会话出现在未归档区（若 CLI 已落盘）。
4. **异常判定口径**：菜单项缺失、点击无反应、fork 打开的是原会话 resume 而非新 fork、刷新后新会话未出现。

## T8 引用缺失不闪现（b2 · 反馈 #11-4）

1. **前置准备**：关闭再重新打开工作区（或点 ⟳ 刷新），让会话列表重新加载。
2. **操作**：观察 Work Records 成员行标题在网络/磁盘加载期间的表现，等待加载完成。
3. **期望结果**：加载期间标题显示「加载中…」类占位而不是「引用缺失」；加载完成后直接显示真实会话标题；只有会话确实已被删除/不可解析时才显示「引用缺失」。
4. **异常判定口径**：打开瞬间出现「引用缺失」随后变为真实标题；或加载完成后真实会话仍显示加载占位。

## T9 删除级联同名会话（b2 · 反馈 #11-5）

1. **前置准备**：同一 agent 下准备两条同名会话（一条在 Work Record 中折叠/未显示，一条可见；可用 fork 后重命名同名构造）。
2. **操作**：右键可见会话 → 删除；阅读确认弹窗文案后确认。
3. **期望结果**：弹窗显示「将永久删除 2 个同名会话（含未显示会话）」；确认后两条会话都从未归档/记录中消失（刷新后不回来）；claude/codex 另一 agent 的同名会话不受影响。
4. **异常判定口径**：隐藏同名会话仍存在、弹窗数量为 1、跨 agent 同名被误删。
