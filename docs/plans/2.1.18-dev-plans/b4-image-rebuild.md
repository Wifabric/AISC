# b4 镜像重建与进度

状态：PLANNED。来源 F3.2–4；验收 R-4/H4。依赖 b3 和 U-2。

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

H4 和所有本批验证当前 NOT RUN；操作用户现有工作容器不是测试前提。
