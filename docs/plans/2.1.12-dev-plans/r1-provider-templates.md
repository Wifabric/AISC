# R1 调研：provider 模板化（cc-switch v5.10.4 基线）

> 状态：已裁决（2026-09-18，D-1/D-2/D-3，见 decisions.md）——纯静态 AISC 自有模板路线，上游委托混合路与赞助商模板被否决；实施批待立。
> 版本基线：上游 [SaladDay/cc-switch-cli **v5.10.4**](https://github.com/SaladDay/cc-switch-cli/tree/v5.10.4)（与 `config/versions.env` / `config/cc-switch-manifest.json` 统一后的 pin 一致）；AISC 侧引用当前 develop。
> 方法：上游 v5.10.4 tag 源码逐文件核实（`gh api` 拉取原文）+ 本仓库 file:line 证据。

## 调研问题与结论（8 项逐项）

### 1. 非交互 `provider add --template <id>` 是否存在？

**结论：存在，v5.10.4 原生支持。**

- `src-tauri/src/cli/commands/provider.rs:685-689`：`Add { /// Provider template to apply before creation #[arg(long, value_enum)] template: Option<ProviderAddTemplate>, ... }`，命令 help 原文标注 *"Add a new provider (non-interactive; use the TUI for interactive add)"*。
- 枚举值 15 个（**勘误**：侦察阶段记 14——v5.10.4 实际含 `Fenno`）：
  `Custom, ClaudeOfficial, CodexOauth, OpenaiOfficial, GoogleOauth, Claudeapi, Packycode, Runapi, Aicodemirror, Cubence, Openmodel, Dds, Qiniu, Fenno, Deepseek`（`provider_input.rs:30-46`，kebab-case CLI 名如 `claude-official`）。

### 2. 模板路径字段完整性（role_env / model_catalog / api_format）

**结论：模板 seed 只填「env.ANTHROPIC_BASE_URL + 展示性字段」；role_env 模型、model_catalog、api_format 有**独立 CLI 旗标**可补，但模板本身不预填 AISC 需要的完整形态。**

- Claude 赞助商模板 seed 仅 `{"env": {"ANTHROPIC_BASE_URL": <preset>}}`（`provider_input.rs:533-537`）；ClaudeOfficial/GoogleOauth seed 为空 `{"env": {}}`（:495/:505）。
- 角色模型走 `--haiku-model/--sonnet-model/--opus-model/--fable-model/--subagent-model` 旗标（`provider.rs:704-722`），落到 `env.ANTHROPIC_DEFAULT_*_MODEL`（`provider_input.rs:4118-4129` `set_claude_role_model`；测试断言 :1530/:1632 可见完整键名）——**与 AISC preset 行的 role_env 结构同源**（AISC `cc_switch_preset_providers.py` 写同样的 env 键）。
- `api_format` 是显式旗标（`provider.rs:735-737`，Claude: anthropic|openai_chat|openai_responses|gemini_native；Codex: responses|chat|anthropic）；模板 meta 仅对部分模板预置 `openai_responses`（`provider_input.rs:404-445`）。
- `model_catalog`：**上游无此概念**（grep `model_catalog` 上游文件零命中）——这是 AISC 侧自有结构（codex `/model` 列表源）。**委托模板路径无法产出 model_catalog**，需 AISC 后置写入。

### 3. secret 输入方式（D8-09 契约：argv 不带密钥）

**结论：⚠️ 上游非交互 add 的 `--api-key <value>` 走 argv——直接委托违反 D8-09。但有合规逃生路：`--config-file`。**

- `provider.rs:699-700`：`/// API key or token (Claude/Codex/Gemini field mode) #[arg(long, conflicts_with_all = [...])] api_key: Option<String>`——argv 传密钥。
- 逃生路：`--config-file <path>`（`provider.rs:726-727`）读完整 `settings_config` JSON（含 token env）。AISC adapter 可将密钥写 **root-only 临时文件** 传 `--config-file` 后即删——密钥不出现在 argv/磁盘日志（ps/argv 审计面干净）。这是委托路线满足 D8-09 的**唯一**形态。

### 4. 失败语义（模板不存在 / 字段缺 / 非零退出）

**结论：fail-closed，错误信息结构化可映射。**

- 模板对 app 不支持：`validate_provider_add_template` 返回 `AppError::InvalidInput("Provider template 'X' is not supported for Y. Supported templates: ...")`（`provider_input.rs:264-288`）。
- Custom 模板要求交互：`"Custom provider templates require interactive field prompts"`（:306-310）。
- sponsor preset 缺失：`unsupported_template_error`（:352-354）。均经 cc-switch 统一错误面退出非零——AISC adapter 可按 stderr 文本映射到既有错误枚举（同 simple-add 现行映射模式）。

### 5. 上游清单 vs AISC 自有 5 preset 差距表

| AISC preset | 上游对应 | 差距 |
| --- | --- | --- |
| DeepSeek（claude 侧 Anthropic 形态） | `deepseek` 模板（meta.api_format=openai_responses，`provider_input.rs:419-422`）+ Codex 内置 seed（:522-526） | **形态不同**：AISC 走 claude app 的 Anthropic 直连；上游 deepseek 模板是 codex 侧/官方 API 形态。需验证 claude app 下 `--template deepseek` 是否可用（`provider_add_template_choices(app_type)` 按 app 过滤，`provider_input.rs:173-248`——codex 内置枚举不含 claude 侧 deepseek，初步判断 **claude app 下不可用**） |
| volcengine-ark（火山方舟） | 无 | AISC 扩展模板保留 |
| zhipu（智谱） | 无 | AISC 扩展模板保留 |
| kimi（月之暗面） | 无 | AISC 扩展模板保留 |
| codesome | 无 | AISC 扩展模板保留 |
| （对照）8 个赞助商模板 | packycode/runapi/aicodemirror/cubence/openmodel/dds/qiniu/fenno | 带返佣注册链接（`partner_promotion_key`，:438）——**引入决定 = D-24，独立裁决，默认不引入** |

### 6. 去预配置后 preset 模块 must-keep 职责的承接方案

| 职责（entrypoint 三个调用点 :480-509/:511-532/:581-584） | 去预设行后归属 |
| --- | --- |
| official 行 seeding（claude/codex 官方入口行） | 独立 seeding 函数保留在精简后的 preset 模块（数据源不变，只是不再写 5 个第三方行） |
| pristine default 清扫（升级后旧默认行回收） | 同上保留 |
| proxy on/off 对账（mihomo 开关时 provider 行一致性） | 同上保留 |
| reconcile 对账（启动 + patrol 恢复） | 保留但**缩窄**：只对 official 行与 marker 文件对账；第三方行不再有 ownership marker（模板添加的行天然无 marker，视为用户行） |
| AISC_PRESET_PROVIDERS 环境变量 | 随预配置一起退役 |
| vendor checksums | `vendor/checksums.txt` 覆盖 `cc_switch_preset_providers.py`——改动后必须 vendor-refresh/verify（DEVELOP_WIKI §6.4） |

### 7. UI 模板清单事实源四选项对比

| 选项 | 漂移风险 | 三层同步成本 | 备注 |
| --- | --- | --- | --- |
| 前端硬编码（现状） | **已发生**（CcSwitchUiTab.vue:111 四项 vs 容器五项，漏 codesome） | 无 | 零成本但证伪 |
| Rust/TS 共享常量文件 | 中（仍需随镜像版本手更） | 中 | 构建期注入 |
| adapter `template-list` op（过 serve 闸门 allowlist + Rust 边界结构体） | **零**（清单由容器内 cc-switch 自报） | 高（新增 op 三层 + 闸门） | 天然同步，但按第 3 项结论**清单本身意义下降**（见推荐） |
| 镜像内清单文件（versions.env 伴生） | 中（随 pin 一起动） | 低 | 中庸 |

### 8. 静态复制 vs 委托上游 `--template`：取舍结论

**推荐：混合——上游官方/DeepSeek 入口委托 `--config-file` 全量配置（非 `--template` 裸路径），AISC 自有 5 家保留为本地扩展模板（现有 preset 数据瘦身复用），赞助商模板不引入（D-24 待裁）。**

理由：
- 委托 `--template` 裸路径 **必须** 补 argv api_key（违反 D8-09）或后置 patch 行（等于自己再写一遍 settings_config）——`--config-file` 一步到位且密钥合规。
- 模板 seed 太薄（仅 base_url），AISC 侧反正要拼完整 settings_config（role_env/known_models）——委托的「天然同步」收益只剩**模板 id 清单**本身，不值三层 op 成本。
- 静态扩展模板的漂移风险仅存在于「上游改了官方端点」场景——官方端点极少变，且 AISC 可在 `--check` 输出提示上游新模板版本。

## 实施裁决门材料（供用户拍板）

1. **裁决一（形态）**：是否接受「`--config-file` 委托 + AISC 扩展模板混合」路线？（拒绝则回退纯静态扩展模板——实现最简，漂移自担）
2. **裁决二（存量卷迁移）**：已有容器 DB 里的 5 个 preset 行（带 marker）如何处置？建议：marker 版本号 bump 一次性触发「去第三方行保留 official」迁移（PRESET_FORMAT_VERSION 机制现成）。
3. **裁决三（D-24）**：赞助商返佣模板默认**不**出现在 AISC UI（除非用户显式开启开关）——确认或否决。
4. 实施成本预估：adapter 改造 + preset 模块瘦身 + UI 双语 + 三层测试 ≈ 一个中型批次（对标 B3 体量）；vendor 门禁必过。

## 实施裁决（2026-09-18，用户裁定，详见 decisions.md）

1. **裁决一（形态）**：**否决**混合路线——采用**纯静态 AISC 自有模板**：维持现有「添加时选预设」形态与清单（5 家含 codesome），不委托上游 `--config-file`，不镜像上游内置清单。
2. **裁决二（存量卷迁移）**：采纳推荐——marker 版本 bump 一次性迁移：去第三方预置行、保留 official、用户行不动（Claude 代定，可否决）。
3. **裁决三（D-24 赞助商）**：**完全不出现**（比默认隐藏+开关更强：无开关）。codesome 为 AISC 自有赞助商例外保留，并立项本阶段专项修复（D-5）。

## 容器内实测（2026-09-17 补充，镜像 cc-switch v5.10.5，super-claude:latest 全量构建成功后）

1. **claude app 下 `deepseek` 模板：实测确认不可用**。错误原文：
   `Provider template 'deepseek' is not supported for claude. Supported templates: custom, claude-official, codex-oauth, aicodemirror, claudeapi, pewayai, cubence, openmodel, runapi, qiniu, fenno, packycode, dds`
   ——同时证实上游漂移仍在继续：v5.10.5 的 claude 可用清单出现 **`pewayai`**（v5.10.4 源码尚无此枚举），`openai-official`/`google-oauth`/`deepseek` 均不在 claude 名单（codex/gemini 专属）。
2. **`--template` + `--config-file` 组合：实测确认可用且 config-file 覆盖模板 seed**。`provider add --app claude --template claudeapi --config-file /tmp/t.json`（文件内 `ANTHROPIC_BASE_URL=r1test.example.com`）添加成功，list 显示该行 API URL 即配置文件值（模板 preset 的 base_url 被覆盖），且新行自动成为 current。**D8-09 合规委托路径实证成立**（密钥可走 config-file 临时文件，不进 argv）。
3. 附带发现：非交互 add 裸用 `--base-url`（无 `--api-key`）会被拒：`non-interactive provider add is missing required flag --api-key`——argv 密钥是上游硬性设计，进一步坐实第 3 项结论。

（实测命令记录：`docker run --rm --entrypoint /bin/bash -v cfg:/tmp/t.json super-claude:latest -c "cc-switch-real provider add ..."`；`provider list --format json` 在容器版不存在，用 TUI 表格 `provider list --app claude` 验证。）

## 未能验证项

（无——原两项均已实测收口，见上节。）

---
*检索日期 2026-09-17；上游源码为 v5.10.4 tag 原文（gh api contents 拉取）；容器实测基于 v5.10.5 镜像（resolver live 解析）。实施与否由用户另行裁决。*
