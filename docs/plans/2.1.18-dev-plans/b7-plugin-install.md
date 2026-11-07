# b7 插件安装超时与真实终态

状态：PLANNED，未实施。D-11；F5 / R-7 / H7。自行开发，下一实施优先项；原 b2 验收状态须按逐批门处理，不把排期确认当作实测通过。

## 方案与范围

在隔离 runtime 复现 `mattpocock-skills@claude-plugins-official` 安装，记录目标身份、前后安装清单、各层耗时与脱敏诊断。先区分上游网络/下载、插件进程、容器桥接和宿主请求超时；现 adapter 已设 180 秒，不凭报错盲目提高所有操作超时。

只修复定位到的安装链路。界面保持进行中/成功/失败/结果未知的真实区别；超时后刷新实际安装清单再允许安全重试，同一目标并发点击去重。切换工作区时旧结果不能写入新目标；不新增安装事实库，不自动删除不确定状态的资产。

## 阅读与验证入口

- `workbench/src/stores/extensions.ts`、`src/aisc/application/extensions.py`、`container/aisc-extensions-adapter`；实施时向上追踪 `extensions_call` 的 Rust/IPC 超时。
- 既有 `extensionsOperationRecovery.test.ts`、`extensionsPluginMarket.test.ts` 及 `tests/test_extensions_bridge.py`、`tests/test_extensions_adapter.py`；补能够区分慢成功、明确失败、未知后刷新、重复点击与目标切换的行为回归。
- 实测精确插件安装、慢网/失败恢复和刷新后终态；若改 adapter，按实际变更重建 bundle/测试镜像，不用旧 runtime 验收新代码。
- 本地受影响层门禁、生产候选、远端 CI、H7 Windows CU 分别记 PRETEST，逐批交用户验收。新增测试是否上传沿用当前仓库/用户约定。
