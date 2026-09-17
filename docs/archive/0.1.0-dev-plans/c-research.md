# C 链——P1 调研批（provider 模板化 × codex computer use）

> 状态：待做。P1（视余力，R8）。**调研不附带实施承诺**：两条均为「出结论文档 → 用户单独裁实施」的门式工作（D-13/D-14）；结论文档评审通过前不写任何实施代码。

## 范围（scope）

- **in**：①r1 provider 模板化调研（验证清单 + 结论文档 + 实施裁决门材料）；②r2 codex computer use 调研（原理 + 容器落地三路线对比 + 安全影响章节）。
- **out**（显式排除）：任何实施代码；赞助商返佣模板引入决定（D-24 随结论一起裁）；AISC 自有 5 preset 的去留决定（随结论裁）；Slurm/PBS（阻塞等用户工作流，不排期）。

## 契约（contracts）

- 产出物：`r1-provider-templates.md`、`r2-codex-computer-use.md`，落本目录；表单沿 r0 先例（标题「R0/Rn 调研：主题」+ 引用块状态头（初稿/日期/待用户验收）+ 编号调研问题 + 对比表 + 工程要点提炼 + AISC 对照/可行性判断，docs/archive/2.1.10-dev-plans/r0-vscode-remote-and-hpc.md:1-6）。
- 结论必须标注版本基线（cc-switch v5.10.x；codex 调研时的实际 latest 版本号——config/versions.env:19 未钉，能力随上游漂移）。
- 允许联网检索上游官方文档与开源实现；仓库内参考起点：vendored claude-api skill 的 computer use 章节（container/_bundle/plugins/cache/anthropic-agent-skills/.../tool-use-concepts.md:278-284，client-side tool 机制，Anthropic 侧对照）；gstack 的运行时 headless Chromium 模式（仅文档，SKILL.md:534）。
- 调研文档不改 container/ 任何被校验文件（不触发 vendor-refresh/vendor-verify 门禁链，DEVELOP_WIKI §6.4/§14）。
- 结论若建议未来动 container/，文档中预列门禁成本（vendor checksums + .gitattributes 行尾纪律）。

## 实施顺序与验收

### C1 r1 provider 模板化调研
验证清单（结论文档必须逐项给证据）：
1. cc-switch v5.10.x 非交互 `provider add --template <id>` 是否存在于该版本、ProviderAddTemplate 14 枚举值是否齐（上游 provider_input.rs）；
2. 模板路径字段完整性：应用后的行是否含 AISC 侧必需结构（role_env/model_catalog/api_format——workbench/src-tauri/src/runtime.rs:542-576 全字段透传形态、aisc-model-shim 按 role_env 角色映射依赖 DB 行）；
3. secret 是否只走 stdin（D8-09 契约：argv 不带密钥）；
4. 失败语义（模板不存在/字段缺/上游非零退出）能否 fail-closed 映射到 adapter 错误面；
5. 上游清单与 AISC 自有 5 preset 的映射差距表（volcengine-ark/zhipu/kimi/codesome 及 claude 侧 DeepSeek Anthropic 形态均不在上游清单，cc_switch_preset_providers.py:133-297）；
6. 去预配置后 preset 模块 must-keep 职责的承接方案（official 行 seeding、pristine default 清扫、proxy 对账、catalog-sync、patrol 恢复——entrypoint.sh:480-509,511-532,581-584 三调用点耦合）；
7. UI 模板清单事实源选项对比（前端硬编码现状已漂移漏 codesome：CcSwitchUiTab.vue:111 硬编码 4 项 vs 容器 5 项；备选：共享常量/adapter template-list op 过 serve 闸门 allowlist 与 Rust 边界/镜像内清单文件）；
8. 静态复制 vs 委托上游 --template 的取舍结论（静态清单随上游 release 漂移 vs 委托天然同步但受上游字段演进制约）。
验收：文档评审（用户过目）；每条断言附上游 file/commit 证据或容器内实测命令输出（可 `docker run` 临时容器实测 --template 行为）；实施裁决门：用户拍板后才立实施批（本周期余力或下周期）。

### C2 r2 codex computer use 调研
内容骨架：
1. **原理**：Codex CLI 侧 computer use / agent-UI 能力机制（标注版本）；Anthropic 侧机制对照（client-side tool：应用方提供桌面环境并执行动作，模型只处理截图与动作请求）；
2. **容器落地三路线对比表**（必给维度：镜像体积增量 / 实现复杂度 / 与 wrapper 拦截结构冲突（container/Dockerfile:303-310，真身 claude-real/codex-real 被 wrapper 顶替）/ vendor 门禁与 versions.env 同步成本 / 安全面扩大程度）：路线一=容器加显示栈（X11/Xvfb/VNC——现状零显示栈，Dockerfile:9-10 node:20-slim 基底 + :72-83 apt 清单无任何图形组件）；路线二=headless 浏览器（CDP 类，参照 gstack 运行时 Chromium 模式——不预装、运行时 setup）；路线三=宿主侧截图/视觉通道（容器外执行、回传图像）；
3. **安全影响章节（必含）**：对齐 DEVELOP_WIKI §12.1 红线——现状容器以 root 运行且 codex 默认 --dangerously-bypass-approvals-and-sandbox（container/codex-wrapper:33-52），computer use 等于在此之上再给鼠标/键盘/截屏级控制；评估威胁面、最小化方案、以及任何后续实施须联动 README 警告与 wrappers 的义务；
4. **AISC 对照**：是否值得做 / 先决条件（含 node 基底、CLI 版本钉版依赖——与 D-9 联动）/ 建议形态与不做门槛。
验收：文档评审；三路线对比表四列完整；安全章节经用户确认覆盖 §12.1 关注点；结论段明确「实施与否另行裁决」。

## 风险

| 风险 | 证据 | 缓解 |
| --- | --- | --- |
| 上游版本漂移致结论速朽 | config/versions.env:16,19 latest 未钉；镜像实际版本由 live resolver 决定（cc_switch_resolver.py:9-21） | 结论锁定版本号 + 注明时效；与 D-9 版本钉版工作联动 |
| 联网信息不可达/时效差 | 仓库内零先例（devlog grep computer/CUA 零命中） | 预设网络条件为前提；引用官方文档 URL + 检索日期 |
| 调研滑向实施 | — | 契约锁定只出文档；实施门 = D-13/D-14 用户裁决 |

## 决策引用

D-13、D-14、D-24（见 decisions.md）。

## 回滚（rollback）

纯文档产出，无运行时行为，无回滚需求；结论被否即随周期收口归档（docs/archive/0.1.0-dev-plans/）。C 链中途放弃不影响 A/B 任何环节。
