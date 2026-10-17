# b1 — 容器内 codex/claude 自动更新 EEXIST 修复

> 反馈来源：`20261017-Codex自动更新存在问题-Thomas`（反馈 #10，bug/low）。
> 分支：`2.1.16-b1-container-tool-update`（从 `develop` 切出）。

## 1. 问题

用户在容器内 codex CLI 收到更新提示并确认后，codex 自更新执行
`npm install -g @openai/codex` 报错：

```text
npm error code EEXIST
npm error path /usr/local/bin/codex
npm error EEXIST: file already exists
Error: `npm install -g @openai/codex` failed with status exit status: 1
```

claude 走同一 npm 全局安装形态，存在同类风险。

## 2. 根因

- 出厂镜像把 `/usr/local/bin/{codex,claude}` 换成注入 wrapper
  （`COPY container/*-wrapper`），真实二进制在 `*-real`。
- `NPM_CONFIG_PREFIX` 只在 entrypoint 进程树里导出（D-RUNTIME-09：
  project=/opt/aisc/toolchain、temporary=/tmp/aisc-toolchain）；
  **docker exec 会话（Workbench 全部页签）不经过 entrypoint 的 export**，
  `aisc-session-wrapper` 从 runtime-context.json 重建的 env 也不含它。
- 因此 Workbench 会话内 npm 回落默认 prefix `/usr/local`，自更新要在
  `/usr/local/bin/codex` 建 bin link → 撞上 wrapper（npm bin-links 对已存在
  且非本包管理的落点直接 EEXIST）→ 更新失败。

## 3. 方案

1. **镜像层统一 npm -g 前缀重定向**（Dockerfile，npm 安装层之前）：
   - `ENV NPM_CONFIG_PREFIX="/tmp/aisc-toolchain/npm-global"` +
     `ENV PATH` 把 `/tmp/aisc-toolchain/bin` 放最前、`npm-global/bin`、
     `cargo/bin` 追加在系统路径**之后**（保证 wrapper 永远先被解析，注入不旁路）；
   - `mkdir -p` 该布局。docker exec 会话继承镜像 ENV，`npm install -g`
     不再触碰 `/usr/local`；entrypoint 树按 scope 覆盖（project 持久
     toolchain / temporary 同路径），行为不变。
2. **出厂二进制落点归一**（Dockerfile）：`mv /usr/local/bin/{codex,claude} → *-real`
   改为 `ln -sf "$(readlink -f "$(command -v codex)")" /usr/local/bin/codex-real` +
   `rm` 原名——离线直装（/opt/aisc/npm）与 npm -g（toolchain prefix）两种
   出厂形态都归一，且在线 fallback 路径不再因 `mv` 缺文件而断。
3. **wrapper 自更新感知解析**（codex-wrapper / claude-wrapper）：exec 真实
   二进制前按「会话 `$NPM_CONFIG_PREFIX` → 持久 toolchain → 临时 toolchain」
   顺序找新装二进制，命中即 exec；否则回退出厂 `*-real`。wrapper 自身永远
   留在 `/usr/local/bin` 解析链上，settings.json 注入不因更新旁路。
4. **entrypoint PATH 次序**：`$TC/npm-global/bin`、`$TC/cargo/bin` 从系统
   路径之前移到之后（`$TC/bin` 仍最前）。理由：npm -g 里的 codex/claude
   若排在 wrapper 之前，更新后会旁路注入；其余 npm -g 工具排在系统之后
   仅在同名冲突时让位系统包，属可接受权衡（记入 decisions）。

## 4. 明确不做

- 不改 `CODEX_VERSION` / `CLAUDE_CODE_VERSION` 出厂 pin 与 versions.env 语义。
- 不改 `_SCOPE_WRAPPER`（Python CLI exec 路径）——镜像 ENV 已覆盖。
- 不承诺跨容器持久更新：temporary/exec 会话的更新随容器消亡；project 模式
  entrypoint 树的更新仍落持久 toolchain。`aisc update --pin-tool` + 重建
  仍是正式升级路径（§8.5）。

## 5. 测试

- 单测（TDD，`tests/test_cc_switch_runtime.py` 新增契约组）：
  - codex/claude wrapper 含 toolchain 解析链与 `*-real` 回退；
  - Dockerfile 含 `ENV NPM_CONFIG_PREFIX`、toolchain PATH 追加、
    `readlink -f` 归一，且不再出现旧 `mv /usr/local/bin/codex` 形态；
  - entrypoint PATH 次序 npm-global/cargo 在 `$PATH` 之后。
- `bash -n` 全部 container 脚本；`compileall`；全量 unittest。

## 6. 手测（交付时补进 HANDTEST.md）

1. `aisc build`（有预置离线包）后进 Workbench bash 页签：
   `codex --version`、`which codex`（应为 `/usr/local/bin/codex`）。
2. 容器内 `npm install -g @openai/codex@latest` 模拟自更新 → 成功、无 EEXIST；
   新开 codex 页签 `codex --version` 变为新版；provider 路由（/model 或
   doctor）仍走 cc-switch 注入。
3. claude 同样验证 `npm install -g @anthropic-ai/claude-code@latest` 覆盖安装。
4. 临时模式（无 toolchain 挂载）重复 2，确认 `/tmp/aisc-toolchain` 落点可用。
