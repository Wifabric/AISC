# AISC 项目地图

> 本文件描述仓库**现在**的样子，不描述计划。每条路径用反引号包裹；check-map.sh 逐条核验路径与命令。

## 开发流程

- 流程：Matt 流程（推荐默认）

## 1. 项目与产物线

| 产物线 | 源码 | 构建入口 | 分发 |
|---|---|---|---|
| Workbench（桌面端，主线） | `workbench/`（Tauri 2 + Vue 3 + Rust） | `workbench/src-tauri/`（beforeBuildCommand `npm run build`） | Windows x64 NSIS 安装器 → GitHub Release |
| CLI | `src/aisc/` | `pyproject.toml`（setuptools，动态版本） | PyPI `aisc-cli` |

## 2. 基线与发布角色

| 引用 | 角色 | 自动化 | 核验 |
|---|---|---|---|
| main | 正式发布线，PR 合入后打正式 tag | Release / Latest | `git rev-parse --verify main` |
| develop | 开发基线，下一版起点 | — | `git rev-parse --verify develop` |
| v2.1.20（Workbench）/ cli-v0.3.1（CLI） | 上一版正式 tag | Release / PyPI | `git rev-parse --verify v2.1.20` |

## 3. 开发环境

| 组件 | 版本 | 安装·配置 | 核验方式 |
|---|---|---|---|
| Python | 3.11.2（`pyproject.toml` 要求 >=3.11，CI 到 3.13） | `python3 -m venv .venv` 后 `.venv/bin/pip install -e '.[dev]'`（pytest / PyYAML / PyInstaller / build + 运行时 docker、requests、watchdog、argcomplete） | `.venv/bin/python --version` → `Python 3.11.2`；`.venv/bin/python -m pytest --version` → `pytest 9.2.0` |
| Node | 22.23.5（`.nvmrc` = 22） | UNVERIFIED（仓库外 ~/.nvm）：nvm v0.40.1 装到 `~/.nvm`，Node 22.23.5 解压到 `~/.nvm/versions/node/` 并建 `v22` 软链（供 `scripts/local-gates.sh` 识别）；`workbench/` 内 `npm ci` | `~/.nvm/versions/node/v22.23.5/bin/node --version` → `v22.23.5`（PATH 默认仍为 v26.13.0）；`npx vitest --version` → `vitest/4.1.10 linux-x64 node-v22.23.5`；`npx vue-tsc --version` → `Version 5.6.3` |
| Rust | 1.100.1 stable（`workbench/src-tauri`；目标版本） | `rustup-init -y --profile minimal --default-toolchain stable`；apt 装 `build-essential pkg-config libwebkit2gtk-4.1-dev libgtk-3-dev libsoup-3.0-dev librsvg2-dev libayatana-appindicator3-dev libssl-dev libxdo-dev`；按 CI 建 gitignore 占位 `workbench/src-tauri/binaries/aisc-x86_64-unknown-linux-gnu` 与 `workbench/src-tauri/nsis/bundle/aisc-bundle/` | NOT RUN：PATH 含 `/opt/aisc/toolchain/cargo/bin` 但目录缺失，`cargo` 未装；CI 为 Rust 权威，本地 gate 自动跳过 cargo |
| Docker | NOT RUN（未装） | 容器内无法安装/运行：存在 `/.dockerenv`，无 `/var/run/docker.sock` 与 `dockerd`，CapEff 不含 `cap_sys_admin`（DinD 需特权）；`scripts/local-gates.sh` 自动跳过依赖 daemon 的 `diag_engine_reachable` 测试 | `docker --version` → `command not found` |

## 4. 日常循环（改哪层怎么生效）

| 改动面 | 生效方式 |
|---|---|
| 前端 `workbench/src/` | `npm run dev`（vite 热更）/ `npm run build` |
| Tauri 壳 `workbench/src-tauri/` | `cargo build` / `cargo test` |
| CLI `src/aisc/` | `python3 -m pytest tests/` |
| 容器 `container/` | 重建镜像（`container/Dockerfile`） |

## 5. 门禁与快速验证

```bash
# 本地全门禁：Python 全测 + cargo test --lib + vitest + vue-tsc（需完整工具链）
bash scripts/local-gates.sh

# 快速验证：单测
python3 -m pytest tests/
```

> 门禁以 CI（`.github/workflows/`）为权威。本容器基线（2026-11-28，2.2.0 已修 2 个基线失败）：Python 全测全绿；vitest / vue-tsc 绿；cargo NOT RUN（容器未装 cargo）；Docker NOT RUN（未装）。

## 6. 架构与调用链

```text
AISC Workbench（Tauri/Vue 桌面壳）→ 引擎适配（Claude / Codex，container/ 内 wrapper）→ Docker 容器（container/Dockerfile）→ 外部模型 API
CLI（src/aisc/）→ Docker SDK（exec pty）→ 容器
```

## 7. 仓库地图

```text
<repo>/
  workbench/          桌面端（Vue 前端 + Tauri/Rust 壳）
  src/                CLI Python 包（src/aisc）
  container/          容器镜像与引擎 wrapper
  packaging/          打包与安装器（PyInstaller / NSIS）
  config/             运行时配置（cc-switch、版本 env）
  scripts/            构建 / 门禁 / 校验脚本
  tests/              Python 测试（含 integration / packaging / features）
  docs/               计划、归档、发布说明、待办、devlog、adr
  tools/              工具脚本
  vendor/             第三方依赖与许可
  .github/workflows/  CI（tests / workbench-ci / pypi-publish / nsis-installer …）
```

## 8. 常见修改流程

| 需求 | 首要入口 | 关联文件 | 验证 |
|---|---|---|---|
| 改前端交互 | `workbench/src/` | `workbench/src-tauri/`（IPC） | `npx vitest run` + `npm run build` |
| 改工作记录预览 | `workbench/src/features/history/RecordContent.vue`、`ConversationViewer.vue`、`conversationReading.ts` | `workbench/src/stores/workspaceExplorer.ts`（missingRecordPaths / WORKSPACE_ERRORS）、`src/aisc/application/conversation.py`（kind 归一） | `npx vitest run` + `python3 -m pytest tests/test_conversation.py` |
| 改终端渲染/可观测 | `workbench/src/features/terminal/Terminal.vue`、`MarkdownOutputView.vue`、`markdownOutput.ts`、`markdownRender.ts` | `workbench/src/stores/workspaceRuntime.ts`（paneStreams / 探针）、`stuckProbe.ts` | `npx vitest run` |
| 改 CLI 行为 | `src/aisc/` | `src/aisc/schemas/` | `python3 -m pytest tests/` |
| 改容器/引擎适配 | `container/` | `container/Dockerfile` | 重建镜像 + 对应集成测试 |

## 9. 契约与状态

| 契约 | 位置 | 变更影响 |
|---|---|---|
| 版本事实源（Workbench / CLI） | `workbench/src-tauri/tauri.conf.json` / `src/aisc/VERSION` | 两条线独立定版，由 `scripts/check-version-sync.py` 校验同步 |
| Agent / Artifact 契约 | `tests/test_agent_contract.py`、`tests/test_artifact_contract.py` | 契约测试约束 CLI 对外行为 |

> 注：`workbench/package.json` 的 version 字段停留在 2.1.13，Workbench 版本事实源以 `workbench/src-tauri/tauri.conf.json` 为准。

## 10. 测试范围

| 路径 | 覆盖重点 | 命令 |
|---|---|---|
| `tests/` | CLI：契约、数据根、docker 网关、打包 | `python3 -m pytest tests/` |
| `tests/integration/` | 集成（本地门禁默认跳过） | `python3 -m pytest tests/integration/` |
| `workbench/src-tauri/` | Rust 后端 | `cargo test --lib` |
| `workbench/` | 前端（组件/逻辑） | `npx vitest run` |

## 11. 打包、CI 与发布

| 项 | 位置 | 说明 |
|---|---|---|
| CI 工作流 | `.github/workflows/` | tests / workbench-ci / pypi-publish / nsis-installer / artifact / bundle-linux-macos / cli-sidecar |
| CLI 打包 | `pyproject.toml` + `packaging/pyinstaller/` | wheel/sdist 发布 PyPI |
| 桌面打包 | `packaging/windows/`、`packaging/aisc.spec` | NSIS 安装器发布 GitHub Release |
| 容器 | `container/Dockerfile` | 工作区镜像 |

## 12. 提交前检查

```bash
bash scripts/local-gates.sh
```

## 13. 关键索引

| 需求 | 首要入口 | 关联文件 |
|---|---|---|
| 项目说明 | `README.md` | `DEVELOP_WIKI.md` |
| 开发流程交接 | `AISC-开发流程交接.md` | `DEVELOP_WIKI.md` |
| 当前待办/悬账 | `docs/todo.md` | `docs/devlog.md` |
| 计划与交付 | `docs/plans/` | `docs/archive/` |
| 发布说明 | `docs/releases/` | — |
| 反馈站（输入源） | Wifabric/aisc-issues-feedback（文件式：索引.md + issues/，非 GitHub Issues） | 开题输入 |
