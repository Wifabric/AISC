# b7 最终镜像真实扩展冒烟（2026-10-27）

固定镜像 `sha256:25f42e5157fd74eb7c2ae9add4d2857c6f83a46a59857b9a2b5730011a693f44`，标签 `super-claude:2.1.17-b7`。宿主 inspect 确认实际容器 image ID；仅挂载只读脚本及外部结果目录，无宿主工作区、配置、凭据或 Docker socket。HOME/Claude/Codex/cc-switch 配置均隔离于 `/tmp/aisc-home`，完成后两测试容器已移除。

## 实际结果

| 阶段 | 结论 | 秒 |
| --- | --- | ---: |
| round-1-skills | PASS | 398.090 |
| round-1-mcp | PASS | 15.606 |
| round-1-plugins | PASS | 366.403 |
| round-2-skills | PASS | 303.126 |
| round-2-mcp | PASS | 10.357 |
| round-2-plugins | PASS | 227.880 |
| round-3-skills | PASS | 179.548 |
| round-3-mcp | PASS | 13.315 |
| round-3-plugins | PASS | 257.140 |
| 版本/源码 hash/启动检查 | PASS | 0.563 |
| 工厂双开/强制同步保留 off | PASS | 0.649 |
| 原裸名称部分失败夹具 | FAIL（保留） | 43.056 |
| 修正完整身份部分失败/仅失败项重试 | PASS（独立重跑） | 101.999 |

主运行 106 个子进程步骤，1815.739 秒，原始 summary=FAIL / exit 1；唯一失败为受控夹具，三轮分类阶段 9/9 PASS，无子进程超时。独立 controlled-only 补充运行 19 步，103.483 秒，summary=PASS / exit 0。上述是组合证据，不能称为单次完整 exit 0。

裸 `caveman-help` 的上游查找返回 `juliusbrussee/caveman`，与工厂 SSOT `JuliusBrussee/caveman` 产生 `SKILL_DIRECTORY_CONFLICT`。改为实际市场完整身份 `JuliusBrussee/caveman:caveman-help` 后真实远端安装：total=2/completed=1，另一不存在项失败；仅提交失败项重试 total=1/completed=0，已成功项整行 SSOT 不变、双端开启。无效项保持无效，不声称重试恢复成功，也不声称裸名称冲突已修复；未为夹具改产品代码。

## 覆盖与边界

- 三轮 Skills：真实搜索 caveman，远端安装 caveman-help/caveman-review，核对 SQLite/adapter/双端文件；关闭相反 agent 后真实组更新，off 保留；卸载后 SSOT/文件清理通过。
- 三轮 MCP：Smithery 真实搜索 context7，导入 `upstash/context7-mcp` 元数据、双端启用、检查更新、真实 PTY 删除；未测试服务握手、认证或工具调用。
- 三轮 Plugins：`superpowers@claude-plugins-official` 真实安装/检查/更新/卸载。首轮 6.0.3（`896224c4b1879920ab573417e68fd51d2ccc9072`）→7.0.0（`bb92a77741419a4ab5f06e711a283343f1ada0c3`），后两轮 7.0.0；卸载注册核对通过。搜索是新执行的本地工厂 marketplace 查询，不证明在线目录已刷新。
- Skills/MCP 更新检查 unsupported：`market does not expose a comparable version field`；Plugin unsupported：`marketplace metadata unavailable`，latest 为空，未虚构最新版。
- Services 与 caveman 五路径由父任务另测，见 PRETEST。日志 100 条/8 KiB、乱序与工作区隔离由自动化覆盖；本次不是 UI 测试。Windows Explorer/NSIS/退出顺序没有 CU 证据；直连/镜像受控故障不在本 harness 覆盖范围，b1 历史及自动化证据分别记录。

## 本机原始证据

- 主运行：`C:\pt\aisc-217-b7-smoke-results-20261027-205011\run\summary.json`、同目录 `events.jsonl` 与编号 stdout/stderr；外层 `container-inspect.json` 保存容器身份和挂载。
- 原失败：主运行 `017-controlled-local-partial.stdout`。
- 修正运行：`C:\pt\aisc-217-b7-controlled-results-20261027-205947\run\summary.json`、`017-controlled-canonical-partial.stdout`、`018-controlled-only-failed-retry.stdout`。
- 完整报告/结构化结果：`C:\pt\aisc-217-b7-smoke-report.md` / `.json`；脚本 `C:\pt\aisc-217-b7-smoke.py`；启动说明 `C:\pt\aisc-217-b7-smoke-notes.md`。两次运行各自保留精确脚本快照，原失败未覆盖。
