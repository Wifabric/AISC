# v2.1.17-target — 生态与可靠性（反馈驱动重启）

> 2026-10-26 用户裁定：按方案 A 重启本阶段；先读取反馈站新增 5 条，撤销误触的
> b1 market-cache 实现后再从无代理扩展可靠性开始。此前 `7534863` / `f9af814`
> 只是误触历史，不作为本阶段完成态。

## 目标

把 v2.1.16 已具备的 Skills / MCP / Plugins、自更新与无代理链路从“可用”推进到
“可安装完整、可诊断、可恢复、可长期维护”，并把反馈站 2026-10-26 的生态类反馈
纳入同一版本闭环。

## 反馈来源

- 来源：`https://feedback.alanevergarden.xyz`
- 数据仓库：`Wifabric/aisc-issues-feedback`
- 抓取基线：`ab8f3f1`（2026-10-26 13:20）
- 新反馈 5 条：N1–N5，明细见 [feedback-intake.md](feedback-intake.md)。
- N1–N4 纳入本阶段；N5 转后续终端体验专项，不伪装关闭。

## 批次计划

| 批 | 内容 | 优先级 | 分支 | 终态 |
| --- | --- | --- | --- | --- |
| b1 | 无代理 skill 安装/更新完整性与诊断 | P0 | `2.1.17-b1-proxyless-extension-reliability` | 代码/自动化/真实容器数据面/远端 CI/Computer Use 关键 UI 路径通过；用户统一手测待全部批次预测试后 |
| b2 | 市场元数据、已安装项更新标识与详情中文化 | P1 | `2.1.17-b2-market-metadata-update-signals` | 待开工 |
| b3 | 扩展安装 / 更新 / 卸载失败恢复、单项重试与操作日志 | P1 | `2.1.17-b3-extension-operation-recovery` | 待开工 |
| b4 | Skills / MCP / Plugins 统一推荐与发现 | P2 | `2.1.17-b4-unified-extension-recommendations` | 待开工 |
| b5 | 网络、显式自更新与版本配对健康报告 | P1 | `2.1.17-b5-update-health-report` | 待开工 |
| b6 | Services 标签补齐与 caveman 默认开启修复 | P1 | `2.1.17-b6-service-caveman-defaults` | 待开工 |
| b7 | 镜像内置工具稳定最新版刷新、高频冒烟与 preview 准备 | P2 | `2.1.17-b7-release-readiness` | 待开工 |

## 开工前账本门

以下范围已进入 `docs/todo.md` 的当前 `v2.1.17-target` 区，满足 DEVELOP_WIKI §1.2
“计划外项先入 target 再实施”门：

- N1 → b1；N2 + N4 → b2；N3 → b4；N5 → 后续终端体验 intake。
- 显式自更新 → b5；Services 标签与 caveman 默认开启 → b6；
  镜像内置工具稳定最新版刷新 → b7。
- b1 开工前必须确认 `git status --short` 为空，且本 README / todo / decisions /
  feedback-intake 四处批次编号一致。

## 2026-10-26 用户追加裁定

1. **显式更新流程**：Workbench「检查更新 → 下载更新」完成后，用户点击“退出更新”
   才退出 AISC Workbench；随后打开资源管理器到安装包所在位置，并默认以等价双击
   exe 的方式运行刚下载的安装包。不得下载完成后静默安装或静默退出。
2. **Services 信息层级**：宿主工具与注册服务必须同类可见；注册服务也需要类似
   宿主工具 F2 的标签/分组显示，避免用户误解为缺失。
3. **caveman 默认开启**：出厂/默认安装 caveman 时，必须在安装阶段设置默认开启；
   不能只落盘后在 UI 中处于关闭状态。
4. **发布前工具版本刷新**：准备最新版发布时刷新 `config/versions.env` 与镜像
   内置软件版本，至少覆盖 cc-switch、Codex CLI、Claude Code CLI、Node.js：
   - Node 选择 nodejs.org 当前 **Active LTS** 的官方 `node:<lts>-slim` 镜像；
   - Codex / Claude Code npm 包选择各自 registry `latest` dist-tag，不追
     prerelease / beta / canary；
   - cc-switch 选择 GitHub Releases 最高稳定 semver，排除 prerelease；
   - 其余 `config/versions.env` 已声明依赖同步刷新，geodata 必须从 `latest`
     改为可追溯 dated release。
   - 每项记录来源 URL、版本、SHA256（可获取时）、回退版本与兼容性验证结果。
   - 若稳定最新版因兼容性不能采用，必须在 decisions 记录原因、替代版本、
     回退版本和验证证据；涉及行为取舍时先请用户裁定，不得静默降级。

## 非目标

- 不默认启用系统代理。
- 不引入账号制或重型远程推荐服务。
- 不在本阶段重写终端渲染层；N5 转后续专项。
- 不重构 cc-switch SSOT；继续通过官方 CLI / SQLite 快照边界交互。
- 不把误触的 market-cache 首片当作已完成批次；b2 重新按测试与批次文档实施。

## 验收基线

- 每批保持 TDD：先写失败测试，再实现。
- b1 必须覆盖：无代理直连失败、镜像成功、多子技能组安装、部分失败诊断、安装后
  Claude/Codex 默认开启状态。
- b5 Windows 显式更新合同：
  - 适用形态为 Windows NSIS `AISC-Workbench-<target>-setup.exe`；非 Windows
    不提供一键安装，显示“当前平台请手动安装”且不得退出应用。
  - 下载产物固定为
    `%TEMP%\aisc-workbench-update\workbench-setup-<safe-target>.exe`；
    SHA256 校验失败则删除产物、保持应用运行并显示错误。
  - 下载完成只进入 ready 状态，不退出、不运行安装器；确认弹窗可取消，取消后
    仍停留在 ready。
  - 点击“退出更新”后：先验证文件仍存在；Explorer 以 `/select,<path>` 打开
    父目录并选中安装包；再用 ShellExecute（等价双击，不附加 `/S`）启动该
    exe；Explorer 或安装器启动失败则报错并保持 Workbench 运行；两者成功后
    Workbench 才退出。
  - NSIS 按其 manifest/UAC 语义显示正常安装 UI；安装器自身的取消、失败、
    重启提示由安装器负责，AISC 不伪造进度。
- b6 Services 验收：Services 视图在“宿主工具（F2）”后显示
  “注册服务”分组；数据源为 `runtime.webServices.services`，按端口升序，
  label 为非空 `name`，否则“端口 {port}”；协议/状态有中英文 i18n，
  capability 缺失时显示 unsupported 文案。
- b6 caveman 验收：工厂镜像、全新默认工作区、卸载重装/缺行重建均以
  Claude=on、Codex=on 落库；已有用户显式 off 的升级路径保持 off，不得反向
  覆盖用户选择。
- b7 发布前刷新并记录 cc-switch / Codex / Claude / Node 稳定最新版，执行 sidecar
  重建、vendor verify、`scripts/local-gates.ps1` 与真实容器冒烟。
- 收尾前记录无代理市场搜索、安装、更新、卸载与自更新检查结果。

## 开工纪律提醒

- 纯 docs 账本更新可直接落 `develop`。
- b1 实施分支第一笔变更撤销 `7534863` 的误触实现和 `f9af814` 的误触执行记录；
  保留 `e91d1fe` 的阶段开题、CLI `0.1.10.dev0` 与本 README。
- 撤销后如 b2 需要缓存能力，必须重新以失败测试驱动设计，不直接复活旧提交。
