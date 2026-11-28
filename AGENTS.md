# AISC 项目常驻规则

> 本文件是任何实施者（含 /implement、/implement-spec、子代理）启动时都应遵守的不变量。
> 只写「忘了就出事」的规则；需要判断的细节进工单，能机器检查的下沉到脚本或 hook。

## 身份

- 主开发：wangyuncepu（收尾 = 收集贡献者 PR + 合并 + 推 preview/final 的 tag 与 Release）

## 分支与合并

- 从 develop 切分支；命名 `<version>-bN-<topic>` 或 `<version>-<owner>-integration`。
- 只有主开发可以合入 main。

## 门禁

- 提交前：`bash scripts/local-gates.sh`
- 全量：`bash scripts/local-gates.sh`
- 任一红即停。

## 禁区

- 不进提交：`.env`、`.env.local`、`api-keys`、`.git-credentials`、`.claude/`、`.claude_keys`、`.cc-config/`、`.aisc/`、`.claude/mihomo/`（凭据、用户配置、运行状态、构建产物）
- 不改写：已发布的 tag（v2.1.20、cli-v0.3.1 等）

## 可写范围

- 可写：`docs/plans/`、`docs/todo.md`、`docs/devlog.md`、`docs/adr/`、`GLOSSARY.md`、`AGENTS.md`、`PROJECT_MAP.md`

## 证据

- 批次证据落在 `docs/plans/<version>-dev-plans/`。

## 测试隔离

- mock `_run_cli`/`git clone` 走安装路径的测试，必须同步 pin 掉 bundled/market 判定（如 `_is_bundled_office_hours`），否则容器里 `/opt/aisc/market/*` 状态会短路 mock、读到真包。

## 共享契约

- 版本事实源（`workbench/src-tauri/tauri.conf.json`、`src/aisc/VERSION`）由主开发独占；变更需先形成 D-N。

## 发布

- 版本事实源：Workbench → `workbench/src-tauri/tauri.conf.json`；CLI → `src/aisc/VERSION`

## Agent skills

### Issue tracker

工单与 spec 落在 GitHub（Wifabric/AISC，用 gh CLI）；用户反馈经反馈站（Wifabric/aisc-issues-feedback）进入。详见 `docs/agents/issue-tracker.md`。

### Domain docs

单上下文：根 `GLOSSARY.md` + `docs/adr/`。详见 `docs/agents/domain.md`。
