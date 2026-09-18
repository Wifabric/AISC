# 2.1.12 阶段开发计划（开池占位）

> 2026-09-17 开池（原名 `0.1.1-dev-plans`）；2026-09-18 按阶段命名规约（DEVELOP_WIKI §1.1）改名——大阶段以 Workbench 版本号命名，阶段内 CLI 版本线独立演进（当前 `0.1.2.dev0`）。
> 开池首个内容为 0.1.0 周期顺延的 C 链调研批（两条结论文档，均处「初稿待用户验收」状态）：

- [decisions.md](decisions.md) — 阶段裁决日志（D-1~D-5，2026-09-18 r1/r2 开题裁决 + codesome 专项立项）
- [r1-provider-templates.md](r1-provider-templates.md) — provider 模板化调研（**已裁决 D-1/D-2/D-3**：纯静态 AISC 自有模板路线；上游委托混合路否决；赞助商模板完全排除、codesome 例外；实施批待立）
- [r2-codex-computer-use.md](r2-codex-computer-use.md) — codex computer use 调研（**已裁决 D-4**：暂不原生实施，闭环转观察；路线三永久否决）

## 已实施

- **codesome 专项（D-5→D-6 已实施并手测通过 2026-09-18）**：[codesome-templates.md](codesome-templates.md)——双模板 + 全局去预置 + provider 模板化 UI 全部并入 develop（四流水线全绿）；手测三轮修复（opener 外链 / baseUrl 响应式预填 / 端点跟随格式联动 / 每模型思考等级多选 / claude 压缩水位 800k）后**用户确认通过**。专项闭环。
