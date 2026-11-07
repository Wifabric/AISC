# b3 镜像名称

状态：IN PROGRESS。来源 F3.1；验收 R-3/H3。D-13 已确认 U-1，按 D-14 从本批开始；基线 develop `43fe416c`。

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
