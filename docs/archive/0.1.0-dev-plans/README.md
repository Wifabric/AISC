# 0.1.0 开发计划——pip 首发与自更新链 · Docker 管理产品化 · 调研批

> 2026-09-16 开池（用户 todo V0.1.0-target + 7 路侦察 + 审问裁决 R1-R8）；同日按开池审问修订（A9 发布链补 artifact.yml dispatch、TestPyPI devN tag 前置、工具 pin 权威位置、A5 vendor 门禁无条件化）。
> 上周期 `v2.1.11-dev` Preview 已发布（tag 打 develop 封版提交 0db2b13），plans 归档于 `docs/archive/2.1.11-dev-plans/`。
> 阶段推进惯例：手测 PASS → merge develop → local-gates 全绿后划完成。todo.md:172-183 全部条目落位本表（内置工具更新=与 cli update 合并，见 D-9）。

## 阶段表

| 阶段 | 内容 | 状态 | 文档 |
| --- | --- | --- | --- |
| ~~P0 开池前置~~ | 工作树存量分批提交 / 四件套 bump `0.1.0.dev0` / plans 目录建立与指向修正 / 2.1.11 收口卫生回填 | **门禁全绿，待并 develop（分支 2.1.12-p0-pool-open，6 提交）** | [p0-pool-open.md](p0-pool-open.md) |
| A 链（P0） | **A1-A7 ✅ / A8 文档与渠道治理 ✅（2026-09-17：README pip 节+SOP+FAQ / ADR 001 复活+002 新写 / wiki §1/§4.5/§11 校正+5b / version channel 行 / doctor channel+platform 检查 / install.sh pipx shim 守卫；pytest 1295 + check-docs 39）**；余 A9+ `aisc bundle fetch` 底座 + `aisc update`（sidecar 热换编排）+ 工具更新合一入口 + Workbench 自更新 + 0.1.0 final/PyPI 收口（Release 全量资产 + PyPI 首发） | 待做 | [a-pypi-and-update.md](a-pypi-and-update.md) |
| B 链（P0） | B0 主题切换残留 ✅ · B1 重建按钮 ✅ · B2 超时修正 ✅（均 2026-09-16）+ Docker 资源管理简化 UI（maintenance 产品化，待做） | B0-B2 已交付；B3 待做 | [b-docker-ui-and-rebuild.md](b-docker-ui-and-rebuild.md) |
| C 链（P1 视余力） | provider 模板化调研（验证清单先行，结论后裁实施）+ codex computer use 调研（r0 形式 + 三路线对比 + 安全影响） | 待做 | [c-research.md](c-research.md) |
| 收口 | devlog / 阶段表 / VERSION 四件套 final 冻结 / plans 归档 / v0.1.0 Release（三平台档案 + SHA256SUMS + NSIS + SBOM）+ PyPI 首发 | 待做 | — |

## 关键裁决（2026-09-16 审问浓缩，全文见 [decisions.md](decisions.md)）

- **R1**「docker 管理的简易映射」= Docker 资源管理简化 UI：把 maintenance docker-scan/cleanup/cache-* 产品化为用户可见界面。P0。（D-11）
- **R2** 2.1.11 final 跳过不再单独发；周期末出 0.1.0 final（dot tag `v0.1.0`）+ PyPI 首发同 tag；开发期 VERSION 开池即四件套 bump 到 `0.1.0.dev0`（打破惯例，显式裁决）。（D-1）
- **R3** pip 发布周期内完整首发：批次一~五全做 + TestPyPI dev 迭代（前置 dot tag 链见 D-26）+ 周期末正式上 PyPI；指南 D-1~D-5 本周期拍板（分发名 `aisc-cli`），pending publisher 尽早注册占名。（D-2~D-6）
- **R4** 拆两件：`aisc update` 热换 sidecar（drain→替换→respawn，本地 serve 池 mtime 驱逐已就绪）+ Workbench 本体标准自更新（检查更新→下载→重启完成）；选型推荐自研轻量、留 D 记录。（D-7/D-8）
- **R5** 内置工具定期更新与 cli update 合一入口；versions.env 升级为真正被消费的单事实源（pin 权威位置见 D-27）；修齐 cc-switch 三处漂移（v5.9.0/v5.10.4/v5.10.1）；node:20→22 基底升级评估（EBADENGINE）。（D-9/D-10/D-27）
- **R6** provider 模板化先调研后定（验证 cc-switch v5.10.x 非 TUI `provider add --template` 路径），出结论文档后用户再裁实施。P1。（D-13）
- **R7** codex computer use 调研：原理 + 容器落地可行性（三路线对比）+ 安全影响（DEVELOP_WIKI §12.1 红线）。P1。（D-14）
- **R8** P0 = cli update+自更新、pip 首发链、Docker 资源管理 UI、重建按钮；P1（视余力）= provider 模板化调研、codex 调研。（D-15）

## 版本策略（R2 展开）

- **开池 bump（P0 批）**：四件套从 `2.1.11.dev0` 同步 bump 到 `0.1.0.dev0`——①根 VERSION（A2 批次二将迁至 `src/aisc/VERSION`）②`workbench/src-tauri/tauri.conf.json` version（`0.1.0-dev`，dash 语义保留、归一化比对兜底）③`tests/fixtures/cli/envelope-version.json` 三字段 ④新增 `docs/releases/v0.1.0.dev0.md` 占位；此后每次 TestPyPI 迭代四件套随 `.devN` 逐次同步 bump（D-26）。
- **打破惯例的理由**：2.1.10/2.1.11 惯例是「开发期保持上一版 dev0、封版统一 bump」（archive/2.1.11-dev-plans/README.md:4）。本周期提前 bump 的动因有二：TestPyPI dev 迭代要求 dev 版元数据（同 dev 版二次上传会被拒，指南 3.4.1 devN 纪律——必须从 `0.1.0.dev0` 起逐次 +1）；且 pypi-publish 是「dispatch 输入已存在 tag」的形态（指南 3.4.1），每次上传前必须推送 dot tag `v0.1.0.devN` 指向 VERSION 已 bump 的提交（D-26）。保持 `2.1.11.dev0` 则 A 链流水线验证无从做起。显式裁决见 decisions.md D-1/D-26。
- **周期末 final**：发布提交 VERSION 改 `0.1.0` + 新增 `docs/releases/v0.1.0.md`（含「安装与获取」节，指南 3.5.4；该文件必须随 tag 提交在内——artifact.yml release job 按标签名取它作 body，artifact.yml:359）+ annotated dot tag `v0.1.0` + **dispatch artifact.yml（ref 选 v0.1.0 tag）**——tag push 不自动出产物（artifact.yml 仅 workflow_dispatch，aggregate/release 仅 tag ref 运行），由它出三平台 AISC-0.1.0-* 档案 + .sha256 + SHA256SUMS 的完整 Release（指南 §5 阶段 3、§7.1 Release 先行；fetch/update 的数据源）+ Workbench NSIS 产物补附 + dispatch pypi-publish（TestPyPI 复验 → PyPI environment 人工审批；SBOM 由该 workflow 附 Release）。历史 dash tag 不迁移（指南附录 B）；此后新 tag 一律 `v+VERSION` 原文（指南 3.4.2）。发布后紧跟提交 bump `2.1.13.dev0`。
- **2.1.11 final 永不发**：`v2.1.11-dev` Preview（2026-09-12）即 2.1.11 周期最终对外产物。
- Slurm/PBS 保持阻塞（2026-09-12 顺延裁决，todo.md:168），等用户提供实际工作流，本计划不排期。

## 待裁决项索引（不阻塞开池，阻塞对应批次）

D-22 检查更新执行者与节流 · D-23 运行中容器镜像陈旧提示 · D-24 赞助商返佣模板处置（随 C 链）· D-25 中段 dev 预览 Release（随 D-26 于 A6 开工前拍板）· D-26 TestPyPI devN tag 前置链（阻塞 A6）· D-27 工具 pin 权威位置与 update 覆盖语义（阻塞 A5）——见 decisions.md。
