# b6 模块应用、卸载与恢复

状态：PLANNED。来源 F4；验收 R-6/H6。依赖 b5、U-3。

## 方案

以现有安装/移除方法为唯一执行通路，模块只增加编排与持久化关联。先查询真实安装状态并展示计划；按稳定成员顺序执行，逐项更新状态和日志。Skill 双引擎开关、MCP 认证、Claude Plugin 的能力边界分别显示，不承诺所有成员支持双引擎。

应用是差异补装：用户已有项不强制重装/改配置；失败可只重试失败/未执行项。现有 runOperation 可能内部捕获失败，需返回或暴露明确结果给聚合器，Promise resolve 不代表成功。

卸载按 U-3 的归属规则计算：多个模块共享成员在仍有引用时保留；用户预装/归属未知项保留并显示原因；实际删除前再次查询状态。卸载/取消/崩溃后保留逐项记录，重试时依据真实状态 reconciliation，不能误删其他目标的资产。部分失败不伪装整组成功，也不承诺跨在线市场原子回滚。

删除模块定义不触发卸载；编辑成员后再次应用不自动删除已移出的成员。内置资产、用户数据和凭据均不在模块删除范围。

## 涉及文件与验证

`stores/extensions.ts`、模块 store/定义、市场/模块 UI、`lib/ipc.ts`、`src/aisc/application/extensions.py`、`container/aisc-extensions-adapter`；按需扩展返回协议，保持旧单项操作兼容和长操作 direct 通路。

回归 `extensionsOperationRecovery.test.ts`、`extensionsSkillGroups.test.ts`、`extensionMarketDialog.test.ts`、`tests/test_extensions_adapter.py`。覆盖共享成员、预装项、安装后崩溃未知归属、用户手工变更、断网/认证/部分失败/取消、单项重试、切工作区/机器、模块删除后原资产仍在。

真实隔离容器至少跑一项 Skill/MCP/Plugin 的应用与卸载，并验证失败后刷新结果；有认证要求则已安装与可调用分开计结果。H6、自动化/数据面/CU/用户验收全为 NOT RUN。
