# b4 镜像重建与进度

状态：已合入 develop，统一 Preview / H4 待验收。来源 F3.2–4；验收 R-4/H4。U-2 已由 D-13 确认；实施基线 `c0f9ab11`。

## 本批协议与执行细化

- 两入口共用重建对话框和任务状态，固定 Local、完整 ref、预检查 image ID、缓存选择与唯一 task ID。Remote 禁用并由 Rust 再次拒绝；取消按 task ID 路由，不能影响别的构建。
- `maintenance docker-rebuild-check` 只读返回现有 ID、所有引用容器及运行容器列表；可选 expected ID 捕获镜像行陈旧状态。执行使用 `docker-rebuild --guarded --expected-image-id ... --events`；使用缓存显式传 `--use-cache`，默认仍无缓存，保留旧安装器非 guarded JSON 调用。
- guarded 路径在 maintenance 锁内再次检查，运行容器阻止执行。构建使用唯一临时 tag，流式读取 Docker 输出并复用 BuildProgressParser；完成后再次核对旧 ref/引用状态，才发布新 tag。失败/取消不先删除原镜像；仅在无其他 tag、无容器引用时尝试移除旧 ID，失败单独说明。
- 复用已有 BuildProgress 展示组件，事件驱动进度；终态由 Promise 结果确定。任务和目标快照固定，异步返回不写入其他目标的界面。统一候选 GUI/用户验收保持未测，不能提前记 PASS。
- 启动摘要的重建后刷新只重新读取 runtime preflight，不调用会回收旧容器的 runtime reconcile；镜像重建不会借刷新隐式停删容器。

## 当前缺口

磁盘页全局重建经 `docker_admin.rs` 调本地 sidecar，只等最终 JSON，未携带被选镜像完整上下文。启动构建已有 BuildProgress/Channel 事件。CLI maintenance `--no-cache` 的 store_true/default=True 不能表达“使用缓存”。这些缺口必须连通各层解决。

## 方案

1. 以镜像行和 LaunchSummary 两入口生成同一重建请求，固定目标身份、ref/expected ID、缓存选项和任务 ID；移除易误导的无目标旧入口或让其走同一选择流程。
2. 执行前 inspect 镜像及所有引用容器；运行容器按 U-2 阻止并引导停止，不能未经确认停删；已有镜像明确二次确认。镜像已消失则说明实际动作是构建。
3. 复用 build 的阶段事件/BuildProgress 和取消管理；维护重建的 ownership/锁/旧镜像保留语义。补齐使用缓存和无缓存的 UI→Rust→CLI bool 双向传递。
4. 成功后 inspect 新镜像并刷新两处状态；旧 ID 清理受容器引用与标签范围约束，失败清理单独说明。构建失败/取消保留原可用镜像；目标切换不串进度。
5. Remote 按 U-2 决定同批支持或明确禁用；绝不从 Remote 行回退成本机构建。若支持，要用同目标 bundle/executor/事件/取消并真实 SSH 验证。

## 涉及文件与风险

`SettingsForm.vue`、`stores/settings.ts`、`LaunchSummary.vue`、`BuildProgress.vue`、`workspaceRuntime.ts`、`ipc.ts`、Rust `docker_admin.rs`/`runtime.rs`/`cache.rs`、Python `docker_lifecycle.py`、`cli/main.py`。需先比较 maintenance 与 build 的锁和旧 ID 清理差异，不能简单替换调用丢掉保护。

## 验证

settings、runtimeBuild、launchSummary 定向测试；Python docker_lifecycle/docker_management；Rust argv/target/event/取消测试。真实隔离环境验证：有/无镜像、运行/停止引用容器、缓存开关、成功/失败/取消、旧 ID 保留、两个入口及防重入。构建进度采用真实事件，不能只用定时动画。

## 2026-11-08 实现验证

- Python 定向 38 项通过；完整 1749 passed / 54 skipped / 201 subtests（本机 Git Bash/Node 路径适配，无断言修改）。
- 前端全套 851 项及生产构建通过；随后早期取消/切换目标隔离修复相关 26 项与 vue-tsc 通过。Rust 全套 414 passed / 2 ignored；新增 argv 契约单测也已通过。
- 真实 Docker 29.7.2：唯一 QA 镜像 `aisc-b4-qa-c21697c3`，通过运行引用拒绝、停止引用保留、使用缓存/无缓存、失败保持原引用、真实输出回调取消保持原引用五组验证。Docker 执行未 mock；只将无关 cc-switch release resolver 固定到离线 fallback，并保留相应警告。测试容器、所选标签与其他测试标签已清理。
- 冻结 CLI 构建及新命令 smoke PASS：sha256 `c137e41c4f7a6f0b996c16740038cc7d76fe0ed388c66463dc0e7b797b8533a2`。真实只读预检查返回缺失镜像状态；未提供确认身份时输出 `build.failed` / `AISC_ERR_USAGE`，不进行构建。
- 本地证据：`output/verification/real-image-rebuild.json`、`frozen-smoke.json` 及各层测试日志。原始日志/临时 QA 数据不上传。
- 自查修正：刷新启动摘要不触发 reconcile；对话框使用现有主题变量与焦点管理；极早取消未命中时在收到该任务 start 后重发取消；原任务完成后不刷新新目标。
- 远端 CI、真实 GUI 两入口/交互与用户 H4 尚 NOT RUN；按 D-15 留到对应阶段，不能将 DOM、CLI 或数据面结果冒充 GUI PASS。

最终提交 `80e90919016a9e4874a81735d2600161c55f5a12` 的 frontend/rust/cli 全部 PASS：[CI](https://github.com/Wifabric/AISC/actions/runs/42400554462)。[PR #68](https://github.com/Wifabric/AISC/pull/68) 已合入 develop `1efe0904b3770bf1bdc530b8c8b474f48fb00cd6`。上述 CI NOT RUN 为提交前记录；GUI 与 H4 仍 NOT RUN。

## 2026-11-08 H4/S9 Preview 补测与修正

完整无缓存真实 GUI 成功；缓存取消终态与原资源保护通过，但 Windows 强杀绕过 Python finally 导致本次临时 tag 残留。沿用 b4 失败/取消清理要求修正：开始事件提供唯一临时 tag，原生端退出后以新 CLI 精确回收，持锁且不强删、不按 image ID、不清扫其他构建；失败显式提示残留。103 项关联 Python / 19 subtests、2 项 Rust 协议测试和实际源码清理恢复通过，修后候选 GUI 与 CI 待补。既往“GUI NOT RUN”为历史记录，当前逐项结果以 [preview-gui](preview-gui.md) 为准。
