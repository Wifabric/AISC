# v2.1.17 裁定记录

## D-6 2026-10-30 用户宣布收尾与 R3/R4 验收

用户宣布“开始收尾”，并明确回复“R3、R4 已手测通过，未测项留统一回归”。
R3/R4 用户验收据此通过，R4 可集成 develop；未执行项目不改写为 PASS。
本阶段进入收尾统一回归，执行账本见 CLOSEOUT.md。正式 final/main 与发布前统一回归门保持按 DEVELOP_WIKI 执行。

## D-0 2026-10-26 target 账本门

用户批准的 N1–N4、N5 转期、显式更新、Services 标签、caveman 默认开启与
内置工具版本刷新均已写入 `docs/todo.md` 当前 `v2.1.17-target` 区；实施前以
README / todo / decisions / feedback-intake 四处一致为开工门。

## D-1 2026-10-26 反馈驱动重启

用户裁定采用方案 A：保留 `e91d1fe` 的阶段开题和 CLI `0.1.10.dev0`，撤销误触的
market-cache b1 实现，从反馈 N1（无代理 skill 安装/更新 blocker）重新开始。反馈
N1–N4 纳入本阶段，N5 转后续终端体验专项。

## D-2 2026-10-26 自更新必须显式

仅 Windows NSIS 产物提供一键显式更新。下载到
`%TEMP%\aisc-workbench-update\workbench-setup-<safe-target>.exe` 并通过 SHA256
后停在 ready；用户点击“退出更新”才执行：Explorer `/select,<path>` 选中文件，
用 ShellExecute 等价双击启动安装器（不带 `/S`），两个动作均成功后退出
Workbench。任一动作失败则保持 Workbench 运行并报错；非 Windows 不提供退出安装
路径。下载完成本身不得退出或启动安装器。

## D-3 2026-10-26 Services 与 caveman 默认态

- Services 视图在“宿主工具（F2）”下增加“注册服务”分组。数据源为
  `runtime.webServices.services`，端口升序；label 用非空 `name`，否则
  “端口 {port}”；协议/状态走 zh-CN/en-US i18n，capability 缺失显示 unsupported。
- caveman 工厂安装、全新默认工作区、卸载重装/缺行重建均默认 Claude=on、
  Codex=on；升级时已有用户显式 off 的行保持 off。

## D-4 2026-10-26 发布前内置工具刷新

准备 v2.1.17 最新版发布时刷新 `config/versions.env` 与镜像内置依赖。稳定口径：
Node 用 nodejs.org Active LTS 官方 slim 镜像；Codex/Claude 用 npm latest
dist-tag；cc-switch 用 GitHub 最高稳定 semver（排除 prerelease）；其余已声明依赖
同步刷新且 geodata 改为 dated release。若稳定最新版不兼容，必须在 decisions 记录
来源、原因、替代版本、回退版本、SHA256 与验证证据；行为取舍需用户裁定。

## D-5 2026-10-27 Node LTS 时间空档裁定

用户明确选择采用最新 LTS 24.22.1。Node 官方计划中 v24 在 10-20 进入 Maintenance LTS、v26 在 10-28 才进入 LTS，因此 10-27 没有 Active LTS；本批以已发布且稳定的最新 LTS 24.22.1 替代 D-4 的严格 Active LTS 条件，记录官方 schedule、镜像 digest 和 Node 22 回退路径。不提前把 Node 26 当成 LTS。
