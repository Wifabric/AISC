# Codesome 专项（D-5）：双订阅模板设计与现状差距

> 状态：初稿 / 2026-09-18 / 待用户验收——§5 拍板前不写实施代码
> 方法：ultracode workflow（8 页官方文档并行抽取 → 仓库实现差距分析 → 2 轮对抗验证逐条驳斥，11 agents）；doc.codesome.ai 为 docsify 站，经 `assets/route-slugs.js` 的 slug→`NN-*.md` 映射直取原文
> 事实分级：✅ = 官方原文逐字证实；⚠️ = AISC 自有约定（官方无出处，模板内须标注）；❌ = 初稿被驳斥说法（已修正不入规格）

## 1. 两类订阅配置事实矩阵

| 维度 | V3（Claude 月卡 / GPT 月卡 / 按量） | 二合一（V5） |
| --- | --- | --- |
| claude base URL | ✅ `https://cc.codesome.ai` | ✅ `https://v5.codesome.cn/api` |
| codex 官方原生 base | ✅ `https://cc.codesome.ai/v1`（漏 `/v1` = 官方常见错误） | ✅ `https://v5.codesome.cn/openai`（用 `/api` 配 Codex = 官方常见错误 #3） |
| key 形态 | ✅ `sk-...`——兑换码先在 `v3.codesome.cn/redeem` 兑换（**兑换码≠Key**，一次一个纯码），再到 `v3.codesome.cn/dashboard`「API 密钥」建 Key 并选分组 | ✅ `cr-...`——订单卡密**直接就是 API Key**：不兑换、不建 Key、不选分组、不显示 V3 余额；下单/查卡密 `meta.codesome.cn`（须下单时注册的新站账号，老站 fk.codesome.cn 已停维护且账号不通用）；一键复制可能带「二合一卡密：」中文前缀，只能粘纯卡密 |
| 分组规则 | ✅ 建 Key 时后台绑定（平台预设不可自建）：Kiro 来源→`lite`/`pro`；Max 来源→当天后台可用具体分组（max 2.2 暂下架，**仅 Claude Code 可用**）；Codex/GPT→`codex`；Grok→`grok`；月卡→`产品-金额-month`（如 claude-50-month；选错扣按量余额）；**倍率动态，以当天后台为准**（❌初稿写死 1x/1.5x/3.5x 已删） | ✅ **无分组**，统一 1.5 倍；cr- Key 不能也不用在 V3 切分组（ccswitch 桌面端教程对比表「二合一分组」措辞与分组专文不一致，以专文为准） |
| claude env | ✅ 核心三行：`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `CLAUDE_CODE_ATTRIBUTION_HEADER=0`（未设 0 = 官方常见错误 #1）；`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` 在「方法 2 手动配置」四件套内（核心块外） | ✅ 同左（地址换 `/api`；token 未替换占位文本 = 常见错误） |
| 模型 | ✅ codex 侧官方指定 `gpt-5.6-terra`（选「自定义」会 503）；claude 侧**不设任何模型键**——官方「大扫除」清单要求清理 `ANTHROPIC_MODEL` / `ANTHROPIC_DEFAULT_*_MODEL` / `CLAUDE_CODE_SUBAGENT_MODEL` / `CLAUDE_CODE_EFFORT_LEVEL` 残留 | ✅ 同左 |
| 混用禁忌 | ✅ 二合一禁用 `cc.codesome.ai`；`sk-`/`cr-` 不可混用（sk- 配二合一 = codex 官方常见错误 #5）；`v3.codesome.cn` 与 `cc.codesome.ai` 同站（.cn 登不进用 .ai） | 同左 |
| 排查口径 | ✅ 403→先查分组；503→模型 ID 须 gpt-5.6-terra；ERR_BAD_REQUEST→地址/教程用错线、token 仍是占位、旧变量残留（❌「401」全站无出处已删）；重连循环→代理规则中 `cc.codesome.ai`/`v5.codesome.cn` 须直连（FAQ §15）；配置后须新开窗口（**切 Max 分组后必须**）；ccswitch 代理开关须开且开完新开终端 | 同左 |
| 官方 CC Switch 供应商名 | ✅ claude：`codesome-v3`；codex：`codesome` | ✅ claude：`codesome-v5`；codex：`codesome-二合一` |

**⚠️ AISC 自有约定（非官方，模板落地时须标注）**：S9a 翻译形态（codex TOML 指向 Anthropic 同址 + cc-switch 本地代理把 Responses 译成 Anthropic，`meta.apiFormat=anthropic`——2026-08-29 用户裁定「实测最稳」，见 preset 模块 v9 注释）；`auth.OPENAI_API_KEY`/`requires_openai_auth`/`model_reasoning_effort="high"`（容器 builder 惯例，官方 codex 写法是 TOML `env_key="CODESOME_API_KEY"`）；`contextWindow=1_000_000`（官方仅载 sol=1,050,000，**terra 窗口官方未记载**，官方且告诫勿给不支持大窗口的模型套 1M 数值）。

## 2. 现状差距（workflow 差距分析，file:line 证据在案）

| # | 严重度 | 问题 | 修法方向 |
| --- | --- | --- | --- |
| 1 | **blocker** | UI 模板清单缺 codesome：`CcSwitchUiTab.vue:111` 硬编码 4 项 vs 容器 5 项预置 | D-1 统一事实源：容器 preset 模块为唯一源，Workbench 经镜像内清单文件+平价测试同步；codesome 双模板置顶（D-3 重点位） |
| 2 | **blocker** | 单一预置混两条互斥产品线：`base_url`=V3 的 cc.codesome.ai 与 `anthropic_base_url`=二合一的 v5.codesome.cn/api 拼在一行（`cc_switch_preset_providers.py:259-260`）——任一线用户拿到的都是交叉配置 | 拆 `codesome-v3` / `codesome-2in1` 两模板，端点/key/模型体系严格隔离 |
| 3 | **blocker** | claude env 被注入 `ANTHROPIC_MODEL=gpt-5.6-sol`（`:371-373`）——官方要求不设模型键且清理残留；sol 亦非文档模型 ID | 新模板 claude 侧不携任何模型键 |
| 4 | major | codex 默认模型 `gpt-5.6-sol`（`:261/:266`）vs 官方 `gpt-5.6-terra`（自定义会 503） | 模型固定 terra；sol 去留待裁 |
| 5 | major | i18n 双语零 codesome 文案；预设下拉裸渲染 id（`ProviderEditPage.vue:251`） | 双语键（显示名/描述/分组速查/key 形态提示）+ 下拉渲染 label |
| 6 | major | simple-add 行 ID 硬绑模板 id（`ProviderEditPage.vue:164`）——官方推荐「多分组各建 Key 一键切」落不了地（后端 id≠provider 已支持，`aisc-cc-provider:1216-1228`） | 预设模式放开行 ID 编辑（预填模板 id + slug 校验 + 查重） |
| 7 | major | 分组选择无 UI 表达位（分组在建 Key 时后台绑定，模板/API 不可编码） | hint 文案 + 官方后台/兑换/文档外链 + 403=分组排查口径进 notes |
| 8 | major | 存量卷迁移未做：旧 DB 的 Codesome-Group 行带错误端点/模型 | D-2：marker bump（v9→v10）按指纹清 codesome 行，保留 official 与用户行 |
| 9 | major | `CLAUDE_CODE_ATTRIBUTION_HEADER=0`（官方核心三行之一）从不落库（现行无 claude_env，simple-add 只写 BASE_URL/MODEL，`aisc-cc-provider:626-632`） | 模板 claude_env 补齐 |
| 10 | minor | `cr-` 不在脱敏正则（`aisc-cc-provider:69` 仅 sk-）；fetch-models/live 目录对 codesome 必烧超时（`/openai` 不在 `_KNOWN_COMPAT_SUFFIXES:2253`） | 正则补 cr-；后缀表补 `/openai` 或 codesome 关 live 合并走静态目录 |
| 11 | minor | 文档漂移：README:94（sol）、README:364（内置预置口径）、v2.1.7.dev0.md:40 | 随实施批同更 |

测试同步：`test_cc_switch_preset_ownership.py:322-336`（现行错误形态断言）与 `test_cc_switch_runtime.py:484`（预置数=5）需重写。

## 3. 双模板规格（seed 已按对抗验证修正）

### 3.1 `codesome-v3`（显示名「Codesome V3（月卡/按量）」）

```json
{
  "template": { "id": "codesome-v3", "product_line": "V3（Claude/GPT 月卡、按量）", "key_prefix": "sk-", "agents": ["claude", "codex"] },
  "claude": { "settings_config": { "env": {
    "ANTHROPIC_BASE_URL": "https://cc.codesome.ai",
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "ANTHROPIC_AUTH_TOKEN": "<USER_SK_KEY>" } } },
  "codex": { "settings_config": {
    "auth": { "OPENAI_API_KEY": "<USER_SK_KEY>" },
    "config": "model_provider=\"codesome-v3\"\nmodel=\"gpt-5.6-terra\"\nmodel_context_window=1000000\nmodel_reasoning_effort=\"high\"\n[model_providers.codesome-v3]\nname=\"codesome-v3\"\nbase_url=\"https://cc.codesome.ai\"\nwire_api=\"responses\"\nrequires_openai_auth=true\napi_key=\"<USER_SK_KEY>\"",
    "modelCatalog": { "models": [ { "model": "gpt-5.6-terra", "contextWindow": 1000000 } ] } },
    "meta": { "apiFormat": "anthropic" } }
}
```

- claude 侧：token 由表单注入（`USER_ONLY_ENV_KEYS` 现成）；**不含任何模型键**（模型由 Key 分组在服务端路由）；env 基座（statusLine 等）由镜像文件注入（现行机制）。
- codex 侧：⚠️ S9a 翻译形态（TOML 指 Anthropic 同址、本地代理翻译）——**AISC 变体非官方路径**（官方原生 = `cc.codesome.ai/v1` + `env_key="CODESOME_API_KEY"`，作高级层回退项）；`context_window`/`reasoning_effort` 为 ⚠️ AISC 自选值。
- hint 文案要点：兑换流程（redeem→dashboard 建 sk- Key）、分组速查（倍率以当天后台为准）、403→查分组、切 Max 后新开窗口、代理直连。

### 3.2 `codesome-2in1`（显示名「Codesome 二合一（V5）」）

```json
{
  "template": { "id": "codesome-2in1", "product_line": "二合一（V5）月卡", "key_prefix": "cr-", "agents": ["claude", "codex"] },
  "claude": { "settings_config": { "env": {
    "ANTHROPIC_BASE_URL": "https://v5.codesome.cn/api",
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "ANTHROPIC_AUTH_TOKEN": "<USER_CR_KEY>" } } },
  "codex": { "settings_config": {
    "auth": { "OPENAI_API_KEY": "<USER_CR_KEY>" },
    "config": "model_provider=\"codesome-2in1\"\nmodel=\"gpt-5.6-terra\"\nmodel_context_window=1000000\nmodel_reasoning_effort=\"high\"\n[model_providers.codesome-2in1]\nname=\"codesome-2in1\"\nbase_url=\"https://v5.codesome.cn/api\"\nwire_api=\"responses\"\nrequires_openai_auth=true\napi_key=\"<USER_CR_KEY>\"",
    "modelCatalog": { "models": [ { "model": "gpt-5.6-terra", "contextWindow": 1000000 } ] } },
    "meta": { "apiFormat": "anthropic" } }
}
```

- codex 侧同上 ⚠️：TOML 指 `/api` 仅在 S9a 本地代理翻译形态下成立，**裸配即复现官方常见错误 #3**——模板内显式标注，官方原生 = `v5.codesome.cn/openai`（回退项）。
- hint 文案要点：cr- 卡密直接当 Key（勿兑换/勿建 Key/勿选分组）、粘纯卡密（防「二合一卡密：」前缀）、统一 1.5 倍、sk- 是 V3 的 Key 请换模板、卡密来源 meta.codesome.cn 订单页。

两模板 UI 共有：API Key（password+reveal、前缀软 warn 不拦截）、行 ID 可编辑（预填模板 id，支持 `codesome-v3-lite`/`codesome-v3-max` 多实例）、分组 hint（仅 v3）、高级层沿用（上游格式/模型映射）。

## 4. 实施批拆分建议（拍板后立项）

1. **preset 模块**：双模板数据 + 去预配置改造（D-1）+ D-2 迁移（marker v10、指纹清旧 codesome 行、AISC_PRESET_PROVIDERS 退役）——vendor 门禁必过
2. **Workbench UI**：清单事实源统一（镜像内清单文件+平价测试）、下拉双语标签+描述+置顶赞助位、行 ID 编辑、key 前缀软 warn、分组 hint+外链、i18n 双语
3. **杂项**：cr- 入脱敏正则、`/openai` 入后缀表或 codesome 关 live 合并、README/releases 文档同步
4. **测试**：preset shape 断言重写、预置数断言更新、前端 vitest

## 5. 待用户拍板（答复后记入 decisions.md 为 D-6+）

1. **模板 id 命名**：`codesome-v3` + `codesome-2in1`（本设计；比官方 claude 侧名 codesome-v5 对用户更直白）？还是跟官方 `codesome-v3`/`codesome-v5`？
2. **UI 外链范围**：doc.codesome.ai（文档）、v3 后台建键/兑换页建议放；**meta.codesome.cn 注册链带 `aff=FAP2ASVX` 是否允许进 Workbench 界面**（D-3 赞助位具体形态）？
3. **双 agent 覆盖**：两模板均覆盖 claude+codex（官方各有独立教程）——确认？
4. **模型目录**：官方指定 `gpt-5.6-terra`；`gpt-5.6-sol`（8-29 实测存在）是否保留为目录第二项？`contextWindow=1_000_000` 为 AISC 自选值（官方未载 terra 窗口）——可接受或改值？
5. **`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`** 入 seed（官方核心三行外、方法 2 四件套内；容器内省流量有益）——保留还是严格对齐核心三行？
6. **codex 默认形态**：沿用 S9a 翻译（你 8-29 裁定实测最稳，本设计默认）+ 官方原生作高级层回退——确认维持？
7. **D-2 迁移交互**：旧 codesome 行指纹清除后由你在 UI 从新模板手动重加（容器不自动重种）——确认？
8. **清单事实源机制**：镜像内清单文件 + 与 PRESET_PROVIDERS 平价测试（r1 §7 中庸项，本设计推荐）？还是 adapter `template-list` op（零漂移但三层+闸门成本）？
9. **key 前缀校验力度**：软 warn 不拦截（粘错时给可读提示优于硬拦）——确认？

---
*调研 2026-09-18；官方文档 8 页原文直取（docsify slug 映射），对抗验证 2 轮驳斥 4 处初稿错误（固定倍率/401 绑定/「官方翻译路」表述/codex 认证形态）后定稿。实施与否由用户裁决。*
