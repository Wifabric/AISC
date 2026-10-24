# b7 — MCP 卸载修复 + 更新跨重启持久 + 扩展商城

> 来源：用户复测第二轮（2026-10-21）三项反馈。分支 `2.1.16-b7-mcp-delete-and-market`。

## 反馈 → 方案

| # | 反馈 | 根因 | 修复 |
| --- | --- | --- | --- |
| 1 | 卸载 MCP 报 `Prompt failed: not a TTY` | `cc-switch mcp delete` 无 force 旗标，dialoguer 交互确认要真 TTY（管道 y 无效，实测） | 适配器经 `script -qec` 伪 PTY 执行并喂 `y`（镜像实测通过） |
| 2 | codex/claude 更新后重启 runtime 版本复原 | b1 把镜像层 `NPM_CONFIG_PREFIX` 设为 `/tmp/aisc-toolchain/npm-global`——exec 会话继承镜像 ENV → 更新落容器本地 tmp，随容器消亡 | 镜像层改指 `/opt/aisc/toolchain/npm-global`（project=持久挂载，temporary=镜像目录随容器）；entrypoint 临时态仍覆盖为 /tmp |
| 3 | 三资产需要默认安装+检索商城、支持链接安装 | cc-switch/claude 已有原生命令面 | 见下 |

## 商城命令面（全部镜像实测）

| 资产 | 检索 | 链接/安装 |
| --- | --- | --- |
| Skills | `cc-switch skills market <query>`（表格：Key/Directory/Name/Installs/Repo） | `cc-switch skills install <owner/name:dir>`；`skills repos add <GitHub URL|owner/name[@branch]>`；`cc-switch deeplink ccswitch://…` |
| MCP | —（配置对象） | `cc-switch deeplink ccswitch://…`（保留 JSON 表单） |
| Plugins | `claude plugin marketplace list`（非交互） | `claude plugin install name@marketplace`；`claude plugin marketplace add <URL|GitHub repo>` |

## 实施

- 适配器新 op：`skill-search` / `deeplink` / `skill-repo-add` / `plugin-market-list` / `plugin-market-add`；mcp delete 走 PTY。
- 宿主 CLI 与 Rust extensions_call 同步扩展（同单命令透传）。
- ExtensionsView 每页签加「商城」区：技能=搜索+结果点击安装+链接框；MCP=ccswitch:// 链接框（保留 JSON）；插件=安装框（name@market 或市场 URL/GitHub）+ 市场列表。

## 测试

- 适配器：PTY delete（mock script）、market 表解析、deeplink argv、repos add、marketplace list 解析。
- Vitest：商城交互（搜索→结果→安装调用、链接分发）。
- Dockerfile 变更 → vendor-refresh。
- 实机：cuse-test 卸载、super-claude 镜像重建后更新持久。
