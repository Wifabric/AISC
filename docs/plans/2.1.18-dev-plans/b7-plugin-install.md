# b7 插件安装超时与真实终态

状态：已实现，定向/真实 Docker/前端/Rust 验证通过，Python 全套 1774 passed / 54 skipped / 204 subtests；准备 PR。D-11；F5 / R-7 / H7。基线为 B6 PR #70 合并 `ffc84885`；按 D-14 顺序实施，D-15/D-16 将 GUI/用户验收统一留到 Preview。

## 方案与范围

在隔离 runtime 复现 `mattpocock-skills@claude-plugins-official` 安装，记录目标身份、前后安装清单、各层耗时与脱敏诊断。先区分上游网络/下载、插件进程、容器桥接和宿主请求超时；现 adapter 已设 180 秒，不凭报错盲目提高所有操作超时。

只修复定位到的安装链路。界面保持进行中/成功/失败/结果未知的真实区别；超时后刷新实际安装清单再允许安全重试，同一目标并发点击去重。切换工作区时旧结果不能写入新目标；不新增安装事实库，不自动删除不确定状态的资产。

## 阅读与验证入口

- `workbench/src/stores/extensions.ts`、`src/aisc/application/extensions.py`、`container/aisc-extensions-adapter`；实施时向上追踪 `extensions_call` 的 Rust/IPC 超时。
- 既有 `extensionsOperationRecovery.test.ts`、`extensionsPluginMarket.test.ts` 及 `tests/test_extensions_bridge.py`、`tests/test_extensions_adapter.py`；补能够区分慢成功、明确失败、未知后刷新、重复点击与目标切换的行为回归。
- 实测精确插件安装、慢网/失败恢复和刷新后终态；若改 adapter，按实际变更重建 bundle/测试镜像，不用旧 runtime 验收新代码。
- 本地受影响层门禁、生产候选、远端 CI、H7 Windows CU 分别记账，GUI/用户验收统一留到 Preview。

## 实现与验证（2026-11-08）

- 根因之一是外层 Rust 统一 30 秒，内层插件单次 180 秒且可能三次网络尝试。只将 plugin-install/update/market-add 改为 660 秒并走独立 CLI，覆盖 host 600 秒上限和锁等待，短查询仍保持原超时；不阻塞串行 resident serve。
- 容器插件修改增加跨进程锁；安装子进程继承锁描述符，宿主断开甚至 adapter 父进程被终止时仍可判断实际安装正在运行。超时只终止本次创建的进程组并等待，不能自动镜像重试未知超时；只有已结束的网络错误才走镜像重试，语义失败直接返回。
- 安装前后核对精确 name@marketplace，已安装不重复装，进程返回成功但真实清单缺失也不报成功。超时后前端读取带 mutation_running 的新快照：明确 idle 且存在才恢复成功；明确 idle 且缺失才允许重试；运行中、旧 adapter 或查询失败保留未知。切目标丢弃旧核对结果。
- 隔离容器的首次精确插件检查因尚未配置官方市场而返回 not found；添加官方市场后插件真实安装成功。第一次安装后列表发现新增字段传入固定签名信封的 TypeError，已修正并补回归；最终 `mattpocock-skills@claude-plugins-official` 实际安装为 1.3.1，SHA `49dd158d1076134a641b33efb035946536778336`，安装和官方市场配置共 9.45 秒，清单 mutation_running=false。
- 受控真实进程测试使用独立容器和合成安装器，覆盖 35 秒慢成功、并发拒绝、adapter 父进程终止后子进程仍持锁、完成后重试不重复执行，以及超时清理后代进程。此项不冒充真实上游慢网复现；上述官方插件实测独立记账。
- 最终定向 Python 112 passed / 18 subtests；前端全套 869 passed / 102 files、生产构建通过；Rust 420 passed / 2 ignored。Rust 首次缺少本工作树构建资源，补齐引用后通过；Windows 单测模拟 SIGKILL 修正后通过。所有 QA 容器均核对专属标签后清理。
- 原始证据留本机 `output/verification`：`plugin-real-final.log`、`plugin-baseline.json`、`plugin-process-probe.json`、`python-targeted-final.log`、`frontend-tests.log`、`frontend-build.log`、`rust-tests-retry.log`。自查完成，无独立评审；CI 尚未执行，GUI/H7 和真实 SSH 尚 NOT RUN。反馈站不提前关闭。
- 最终冻结 CLI SHA256 `800f7c3fe588b2e94c75804735bb1f53f9f1fd81f2e8e27646d5ba4e5ad3e6e0`；在隔离容器通过 B6 模块安装/卸载全链和最终插件 mutation_running=false 透传，证据 `frozen-modules-smoke.json`。这是 CLI 真实验证，不是 GUI 测试。

## 远端集成

[PR #71](https://github.com/Wifabric/AISC/pull/71) 精确 head `6c33d6c8a1262159a1b7dde90915a4514734cc0a` 在 [CI run 42405637940](https://github.com/Wifabric/AISC/actions/runs/42405637940) 三项全部 PASS，已合入 develop `61c70540e497c8568be1be55fc99869b1ef863c0`。GUI/H7 仍待 Preview。
