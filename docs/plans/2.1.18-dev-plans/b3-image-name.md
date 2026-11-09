# b3 镜像名称

状态：本批及后续整合修正已合入 main，开发者证据见下方历史记录与 [PROGRESS](PROGRESS.md)；用户已报告统一验收通过。正式发布和反馈闭环见 [发布准备](release-readiness.md)。

以下保留本批实施时的基线、验证和决策过程，不将当时的未测项目改写为 PASS。

## 方案

保留旧 CLI 的新增别名兼容行为，新增可选 old-ref 指定重命名来源。UI 选择具体旧 tag、输入完整新引用；锁内验证所有权、旧引用与镜像 ID 及目标冲突，创建并验证新 tag 后才移除所选旧 tag。失败明确展示部分结果，取消不调用后端；其他标签保持。

现 SettingsForm 的 onImageTag 将字符串按冒号拆分并固定追加 `-renamed`，既不能自选，也不能稳妥处理 registry port。改为显式输入完整引用，前端给出可编辑默认值，后端按 Docker 引用规则校验并返回可读错误。相同名称幂等；目标已指向不同镜像时拒绝覆盖。

底层 tag 是新增别名，不天然等于重命名。U-1 已确认“新 tag 成功后移除指定旧 tag”；多标签镜像的其他标签不动。执行前重新确认目标 machine/image ID、ownership、锁及引用，不能操作列表刷新前已经变化的对象。去旧 tag 失败须显示新标签已创建、旧标签保留的部分结果。

## 涉及文件

- `workbench/src/features/settings/SettingsForm.vue`，`stores/settings.ts`，`lib/ipc.ts`，双语 i18n。
- `workbench/src-tauri/src/cache.rs` 的 image_tag/目标解析。
- `src/aisc/application/docker_lifecycle.py` 的 image_management_tag 及 CLI 对应参数；保留已有 owned-asset 守卫。

## 验证

真实 Docker 首轮发现列表的 12 位短 ID 与 inspect 的完整 sha256 ID 不匹配，导致归属检查拒绝。修复同一 ID 的短/完整表达匹配，仅接受至少 12 位十六进制前缀；错误后缀不视为同一镜像，仍保留后续 inspect 身份核对。

SettingsForm/store：自定义/默认/取消/空白/冲突/重复提交；含 `registry.example:5000/team/image:tag` 的解析。真实 Docker 用隔离测试镜像验证前后 ID 相同、指定 tag 与其他 tag 状态符合 U-1。

已执行：Python 全套 1734 passed / 54 skipped / 201 subtests；随后针对短/完整 ID 修复的镜像重命名/管理 24 项通过。SettingsForm 26 项通过；前端全套 846 项及生产构建通过；Rust 全套 414 项通过、2 项 ignored。Python 本机路径适配只映射已安装 Git Bash/Node 路径，未改断言；跨平台及 clean-install 由 PR CI 补充。

真实 Docker 29.7.2 使用 FROM scratch 的两个唯一命名 QA 镜像，验证成功后新标签与原 ID 相同、选中旧标签消失、其他标签保留；冲突时两个镜像均未改变。测试标签已全部清理。证据：本地 `output/verification/real-image-rename.json`，实测 ID `sha256:bbf28061ff5eed4dc3aa9ac86fe3ad0d1805df47723a31e9cf2d6aa3d5c7d350`。

CU、更新后的冻结 sidecar 界面验证、用户 H3、远端 CI 尚 NOT RUN；组件测试与 Python 真实数据面验证不冒充 GUI 实测。统一候选按 D-12 继续补证据。

PR #67 首轮 CI：frontend/cli PASS，Rust 在原有 `pipe_session_streams_child_stderr_as_output` 失败（399 passed / 1 failed / 1 ignored）。该测试在 child wait 结束后立即 try_recv，但 stderr 的独立读取线程可能尚未投递。按现有 ExitSignal“子进程已回收”的契约，改为有界等待输出通道关闭，再保留原 stderr 内容及 offset 断言；不增加 sleep、不跳过测试、不改 PTY 产品逻辑。修后重跑本地定向和远端门禁。

最终提交 `89971647905822f23c8f7fd671982832d3c3a99c` 的 frontend/rust/cli 全部 PASS：[CI](https://github.com/Wifabric/AISC/actions/runs/42397722859)。[PR #67](https://github.com/Wifabric/AISC/pull/67) 已合入 develop `c0f9ab11b345502832ac114bc422348da1384502`。上述首轮失败保留为历史；GUI 与 H3 仍 NOT RUN，按 D-15 统一 Preview 验证。
