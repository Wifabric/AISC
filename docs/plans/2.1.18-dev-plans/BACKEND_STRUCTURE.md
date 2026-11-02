# 后端边界与数据设计草案

本文新增字段/模型为拟议契约，尚未实现。产品规则以 [decisions](decisions.md) 为门，字段名可在相应批实施前细化并同步文档。

## 保留调用链

| 工作 | 现有入口 | 职责 |
| --- | --- | --- |
| 文件改名 | Rust `workspace.rs::rename_entry`；Remote `serve_fs.py` | 路径解析、containment、条目身份与不覆盖；前端只给最终 basename |
| 镜像管理 | settings store → IPC → Rust `cache.rs` / `docker_admin.rs` → Python `docker_lifecycle.py` | 目标解析、运行锁、ownership 复查、Docker 执行 |
| 流式构建 | workspaceRuntime → buildImage Channel → Rust `runtime.rs` → CLI build | 进度事件、终态、取消；重建应复用而不是只等一个最终 JSON |
| 扩展 | extensions store → Rust/CLI bridge → `application/extensions.py` → `container/aisc-extensions-adapter` | 现有 Skill/MCP/Plugin 安装/删除及 cc-switch 事实；不新增第二套下载逻辑 |

## 镜像操作契约

重建请求需要明确运行目标身份、image reference、预期 image ID、缓存 bool、任务 ID。前端显示的检查快照不能代替执行前复查。默认 `no_cache=true`；现 maintenance 的 `store_true/default=True` 不能表达“使用缓存”，必须补完整的双向参数通路及 CLI 验证。

事件应包含同一任务身份、阶段、可读日志与终态；成功必须有最终 inspect 证据。关闭进度面板与取消任务分开；取消不能误杀其他目标的构建。先保留旧 ID，构建成功后才尝试清理符合范围的旧资源；清理失败与构建成功分开报告。禁止扩大成 `docker system prune`。

## 模块数据（草案）

- 定义：`schema_version`、稳定 `id`、名称/说明/分类、内置或用户来源、`revision`、成员数组。成员身份含 `kind`、市场/仓库、准确条目 ID、必要选择器；展示名称不能作为唯一键。
- 应用记录：工作区和运行目标身份、module ID/revision、operation ID、逐成员状态、安装前是否存在、是否由本次引入、关联模块集合、错误与时间。真实安装状态仍向现有适配器查询，记录不替代它。
- 定义与应用记录分开持久化，最终路径按 U-3 与既有配置/data-root 约定确定；原子写、schema 校验、未知版本保留并报错，不含 API keys/tokens。
- 应用前读真实状态；不存在项安装，已存在项关联而不强制覆盖其配置。没有已证实归属的资产默认保留；新增记录不能倒推出旧资产是本模块创建。
- 卸载先计算计划，逐项解除关联/移除。失败后重新查询实际状态再重试，不能用一次 catch 后返回 void 冒充成功。安装后进程崩溃而归属未落盘时按未知处理，不贸然删除。
- 用户手工卸载、跨模块共享、模块编辑、workspace 重建均需 reconciliation；定义删除不隐式触发资产卸载。
