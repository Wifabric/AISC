# b6 模块应用、卸载与恢复

状态：实现、自查、本地自动化与真实 Docker 验证通过，准备 PR/CI。来源 F4；验收 R-6/H6。基线为 b5 PR #69 合并 `d3798c06`；U-3 已确认。U-4 默认清单保持独立待批准。

## 本批执行协议

- 通过现有 host CLI / 扩展 adapter 执行单项操作，不另造安装器。新增 module-plan / module-step / module-status：计划从真实三类安装快照生成，确认后按计划 ID 逐项执行，逐项写入持久记录；前端取消在当前项结束后停止，切目标不继续派发旧计划。
- 记录位于目标主机的工作区 state 下，按 runtime UUID 与实际容器 ID 隔离。容器重建不继承删除权限，新实例现有资产按预装/未知归属保留。定义仍用户级；删除定义不删除执行关联，已移出定义的历史成员仍可随原模块显式卸载解除关联。
- 同一 runtime 的模块步骤与普通扩展修改共用可重入跨进程锁。每次执行前重读真实状态；计划后新增的安装/删除动作要求重新预检。成员归属仅在成功并核对实际结果后记录，配置/版本指纹变化时保守保留。
- 每次安装/删除前先持久化 pending 与随机操作标识，通过 Docker exec 环境传给该进程及子进程。中断后刷新先核对容器内该标识进程是否仍在运行；仍运行或无法核实时不重复操作。进程结束后依据真实快照恢复；无法证明由本模块引入的项不取得卸载权限。
- MCP 旧快照没有稳定市场身份时，匹配同名项只作为保留/冲突证据，不猜测来源或覆盖配置。新装后保存实际 ID 与不含凭据的状态指纹；安装与认证可用性分开显示。Skills 同名不同来源、插件同名不同市场也保守阻止覆盖。

## 方案

以现有安装/移除方法为唯一执行通路，模块只增加编排与持久化关联。先查询真实安装状态并展示计划；按稳定成员顺序执行，逐项更新状态和日志。Skill 双引擎开关、MCP 认证、Claude Plugin 的能力边界分别显示，不承诺所有成员支持双引擎。

应用是差异补装：用户已有项不强制重装/改配置；失败可只重试失败/未执行项。现有 runOperation 可能内部捕获失败，需返回或暴露明确结果给聚合器，Promise resolve 不代表成功。

卸载按 U-3 的归属规则计算：多个模块共享成员在仍有引用时保留；用户预装/归属未知项保留并显示原因；实际删除前再次查询状态。卸载/取消/崩溃后保留逐项记录，重试时依据真实状态 reconciliation，不能误删其他目标的资产。部分失败不伪装整组成功，也不承诺跨在线市场原子回滚。

删除模块定义不触发卸载；编辑成员后再次应用不自动删除已移出的成员。内置资产、用户数据和凭据均不在模块删除范围。

## 涉及文件与验证

`stores/extensions.ts`、模块 store/定义、市场/模块 UI、`lib/ipc.ts`、`src/aisc/application/extensions.py`、`container/aisc-extensions-adapter`；按需扩展返回协议，保持旧单项操作兼容和长操作 direct 通路。

回归 `extensionsOperationRecovery.test.ts`、`extensionsSkillGroups.test.ts`、`extensionMarketDialog.test.ts`、`tests/test_extensions_adapter.py`。覆盖共享成员、预装项、安装后崩溃未知归属、用户手工变更、断网/认证/部分失败/取消、单项重试、切工作区/机器、模块删除后原资产仍在。

## 2026-11-08 实现及验证

- 已接入 CLI 三条模块命令、Rust 长操作 direct 通路及前端计划确认/逐项执行/取消/重试/历史。重试重新生成真实计划并要求确认，不重放未知状态的修改。切目标停止派发，释放原目标 busy 状态，不覆盖新目标。
- adapter 的列表增加可选 ownership 证据：Skill/Plugin 核对真实文件内容及相对路径，MCP 在容器内散列配置，只返回摘要；越界符号链接、不可读/超限资产不提供删除依据。普通列表不增加此开销。旧 adapter 不支持证据时仍可应用，但不授予自动卸载权限；用户后续修改内容会撤销归属。
- Python 全套初轮 1763 passed / 54 skipped / 204 subtests；内容指纹补强后四个受影响测试文件 109 passed / 33 subtests。覆盖共享、预装、手工修改、未知进程、旧 adapter、损坏状态和失败恢复。
- 前端全套 865 passed / 102 files；测试中 Array.at 不兼容现有构建目标，改为索引后生产构建通过。指纹提示补充后定向 11 项通过。Rust 全套 420 passed / 2 ignored。
- 真实独立容器 `aisc-b6-qa-8fed6a1d02` 中，通过现有安装器安装 `obra/superpowers:test-driven-development`、本地 QA 市场 `qa-plugin@aisc-b6-qa` 与 `microsoft/learn_mcp`；三类实际安装通过。模块 B 共享插件，卸载 A 保留插件，卸载 B 后移除；前后真实快照一致。没有验证 MCP 认证或实际调用。随机进程标识另测运行中/结束状态均正确。
- 最终冻结 CLI 的 plan → step → status → 卸载全链通过，SHA256 `8454c3eac9980c73589c73cf3f0873c9b74315b25d57d86e8be4eb0c5a506547`。所有 QA 容器均核对专属标签后清理，无用户挂载。
- 原始证据在本工作树 `output/verification`：`ownership-tests-final.log`、`frontend-build-retry.log`、`real-modules.json`、`real-marker-probe.json`、`frozen-modules-smoke.json`；不提交合成数据/产物。
- 自查不是独立评审。远端 CI 尚未执行；真实 Workbench GUI、SSH 目标与用户 H6 均 NOT RUN，按 D-15 留到统一 Preview。U-4 与反馈站写权限仍待后续处理，不以本批实现冒充反馈关闭。
