# 技术基线与环境

这是 2026-11-02 对仓库锁文件的读取快照，不是“最新版”声明。当前计划不更新依赖。

| 层 | 使用基线/来源 | 本阶段约束 |
| --- | --- | --- |
| Workbench 发布号 | `workbench/src-tauri/tauri.conf.json` = 2.1.17 | 2.1.18 是阶段名；实施时按版本规则统一变更，不以 npm package 旧号作发行号 |
| CLI | `src/aisc/VERSION` = 0.1.10 | 与 Workbench 双轨；新增 CLI 接口后依指南决定下一 CLI 版本 |
| Node | `.nvmrc` = 22 | CI/本地开发对齐；初查宿主 PATH 是 24.14.0，实施前使用项目级 Node22 |
| Python | 手册/CI 3.12；pyproject 要求 >=3.11 | 项目隔离 venv；不依赖原工作目录环境隐式可用 |
| 前端 | lock：Vue 3.5.41、Pinia 4.0.2、TypeScript 5.6.3、Vite 6.4.3、Vitest 4.1.10 | `npm ci` 按已有 package-lock；此次不改 lock |
| 桌面桥 | Tauri Rust lock 2.11.5、JS API lock 2.11.1；Rust stable | Cargo.lock 保留；记录实施时 `rustc -V`，仓库未锁到具体 rustc 补丁号 |
| 运行层 | sidecar Python CLI + bundle + Docker/SSH executor | 同目标执行、已有锁/ownership/取消语义保留 |

首次调研时 clone 尚无工具/依赖与构建产物；个人功能整合期间的环境准备另记整合记录。实施前按 [开发环境](../../../DEVELOP_WIKI.md) 配置，明确工具路径、Docker/WebView2 与编译器版本。

不拷贝原目录的凭据、真实工作区、未审核依赖或安装产物来冒充可重现构建。先运行所需批次的定向验证，再完成手册及 CI 要求的门禁；具体命令按该批最终文件调整。
