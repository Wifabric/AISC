# b3 镜像名称

状态：PLANNED。来源 F3.1；验收 R-3/H3。U-1 裁定前不实现命名/旧 tag 策略。

## 方案

现 SettingsForm 的 onImageTag 将字符串按冒号拆分并固定追加 `-renamed`，既不能自选，也不能稳妥处理 registry port。改为显式输入完整引用，前端给出可编辑默认值，后端按 Docker 引用规则校验并返回可读错误。相同名称幂等；目标已指向不同镜像时拒绝覆盖。

底层 tag 是新增别名，不天然等于重命名。按 U-1 确认后实现“只加别名”或“新 tag 成功后移除指定旧 tag”；多标签镜像的其他标签不动。执行前重新确认目标 machine/image ID、ownership、锁及引用，不能操作列表刷新前已经变化的对象。去旧 tag 失败须显示新标签已创建、旧标签保留的部分结果。

## 涉及文件

- `workbench/src/features/settings/SettingsForm.vue`，`stores/settings.ts`，`lib/ipc.ts`，双语 i18n。
- `workbench/src-tauri/src/cache.rs` 的 image_tag/目标解析。
- `src/aisc/application/docker_lifecycle.py` 的 image_management_tag 及 CLI 对应参数；保留已有 owned-asset 守卫。

## 验证

SettingsForm/store：自定义/默认/取消/空白/冲突/重复提交；含 `registry.example:5000/team/image:tag` 的解析。真实 Docker 用隔离测试镜像验证前后 ID 相同、指定 tag 与其他 tag 状态符合 U-1。

定向 Python `tests/test_docker_management.py` 与 Rust cache 相关测试；错误/目标切换不能误改另一机器。H3、自动化、Docker、CU、用户验收当前全部 NOT RUN。
