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
