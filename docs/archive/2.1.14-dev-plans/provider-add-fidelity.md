# 批 2：provider 新建保真（保存漂移 + 模型拉取，合批）

> 状态：计划待用户验收（2026-09-23 立项）
> 来源：todo v2.1.14-target 两条（「新建的 provider 第一次保存的结果和用户
> 填写的不同（偶发，未复现）」「添加 provider，模型拉取失败，claude 和 codex
> 侧都是这样」）；两项同页（ProviderEditPage）同链路（FALLBACK_TEMPLATES ↔
> 容器 manifest 双真相源、2.1.13 S9a 端点分离），据 D-2/D-4 合批
> 方法：ultracode workflow（研究员 + evidence/alt 双镜头核验；verdict 均
> corrected——含 429 阵亡的首轮 evidence 裁决从 journal 回灌，修正已全部并入
> 本稿；改法基线取**核验员修正版**）
> 对应 target：docs/todo.md「v2.1.14-target」provider 两条

## 1. 现状与关键发现

### 1.1 保存漂移（偶发未复现）——三个假设

- **H1 竞态（模板清单异步替换静默改写 baseUrl）**：add 页挂载时 templates
  是 store 的 FALLBACK_TEMPLATES（ccSwitchUi.ts:183-201，手工第二真相源）；
  `loadTemplates` 的 docker exec 往返（约 1-3s，CcSwitchUiTab.vue:186-191/243）
  返回后整体替换，触发 ProviderEditPage 的
  `watch([templateEndpoint, () => props.templates], applyTemplateEndpoint)`
  （107-114）；新建态 `baseUrlTouched=false`（107）→ `form.baseUrl` 被静默
  重写。同版本已有实际分歧点：FALLBACK 的 codesome-v3
  `codex_endpoint_native="https://cc.codesome.ai/v1"`（ccSwitchUi.ts:189）
  vs 容器 manifest 无 `/v1`（preset_providers.py:315/697）。
  **核验加重的确定性路径**：`onApiFormatChange`（116-119）在 preset 新建态
  无条件重置 `baseUrlTouched` 并重写 baseUrl——「先手填 baseUrl 后切格式」
  的自然顺序即确定性触发，无需竞态窗口（alt 镜头认定为最有威胁替代解释）。
- **H2 新建路径丢字段（buildRequest 缺口）**：custom claude 的 env（roles
  五槽）、custom codex 的 model 不随 add 请求发送（消费侧
  container/aisc-cc-provider:717-724 与 747-748 都吃这些字段）；preset+高级层
  的 roles/catalog 两选一完全不生效（adapter simple 路径不收 / 前端不发送，
  二选一裁决见 D-4）；**custom codex 的 modelCatalog 前后端键名不匹配**，
  全链透传无翻译层（核验发现）。
- **H3 非缺陷**：compact 预填 800k/900k 是 D-7（2.1.12 阶段）既定裁决
  （ProviderEditPage.vue:66-72 注释含裁决编号与修复记录）——只欠 UI 明示
  来源，不构成保存正确性 bug，修复面降权。

### 1.2 模型拉取失败（claude+codex 双侧）

- **结构性缺口**：2.1.12 模板化 + 2.1.13 S9a 端点分离后，add 流程两侧预填
  都是 anthropic 侧端点（6 模板 codex_api_format 全 anthropic：
  preset_providers.py:161/269/283/297/330/354）；而 add 模式内联探测
  `_fetch_models_inline`（aisc-cc-provider:2524-2534）只拿表单 base_url 走
  「URL 形状猜测」候选链（_KNOWN_COMPAT_SUFFIXES 剥后缀至**裸域**——
  核验修正：zhipu 剥 `/api/anthropic` 后根是 `open.bigmodel.cn`，真实路径
  `/api/paas/v4/models` 永不在候选内），不参考模板声明的 OpenAI 侧 base_url。
  行路径不对称：codex 行路径补 preset base（2570-2576）、claude 行路径仅
  env（2581-2588）、**内联路径两者皆无**。
- **放大因素**：①HTTP 发自容器内 urllib 直连（15s 超时、双认证头），宿主
  TUN 默认不覆盖容器出口（批 6 同环境）；最坏 3 候选×2 头×15s=90s，超
  Rust `PROVIDER_TIMEOUT=30s`（runtime.rs:34，700-705 确套在调用路径）——
  「优雅回退 available=false」恶化成超时硬错误。②前端 catch 统一降级
  （ccSwitchUi.ts:159-165），失败 message 固定文案，无从判别。
- **最强替代解释（核验提出，必须先判别）**：**adapter 版本偏差**——
  commit 5f168f4（2026-09-19）修前，add 页拉模型被 id 门一刀切拒
  （requires --id），任何模板任何 agent 确定性失败；adapter 仅经镜像构建
  进容器（Dockerfile:326 COPY），无运行时同步——**旧镜像上本症状与结构
  缺口不可区分**。⇒ 手测第 0 步固定为 adapter 新旧判别。
- 其余核验修正：S9b 日志先例实际是 `/tmp/aisc-live-catalog.log`
  （aisc-cc-provider:1978-1985，timeout=6.0——docstring 写 3s 与代码不符，
  预算先例取 6s）；候选链 URL 两处拼错已订正（承重结论不受影响、反而更稳）。

## 2. 方案（D-4，核验员修正版基线）

1. **容器侧数据先行**：`preset_providers.py` codesome-v3 native 端点补
   `/v1`（与其余 5 家自带版本路径对齐）；新增 FALLBACK↔manifest 快照一致性
   单测（防第二真相源再漂移）。
2. **前端预填守卫**：`applyTemplateEndpoint` 改 **lastAutoPrefilled** 方案
   （记录上次自动预填值，仅当 `form.baseUrl === lastAutoPrefilled` 才允许
   自动覆盖）——不动「切格式/模板端点跟随」的 D-6 语义（用户手改值永不被
   静默覆盖，格式切换仍重指端点）；add 页模板未就绪**仅提示不阻断**
   （「模板清单不可用，显示的是内置兜底」），不动 FALLBACK 降级设计。
3. **buildRequest 新建路径补发**：custom claude env（五槽）、custom codex
   model/model_catalog（键名对齐 adapter 契约）；preset 模式高级层映射
   编辑器：前端禁用并提示「模板模式不保存映射」（改动小、语义清晰；随
   请求发送并扩 adapter simple 路径列二期，二选一按此落地）。
4. **模型拉取**：`fetchNow` 附带选中模板 id（stdin request 增字段）→
   `_fetch_models_inline` 按 `_preset_provider(id)` 把模板声明 base 追加为
   候选（照抄 2570-2576 既有做法，零新机制）；claude 行路径对称补；
   单请求 15s→6s、总预算 <25s（早于 Rust 30s 杀线返回 available=false）；
   候选请求写 `/tmp/aisc-fetch-models.log`（base/status/shape 行，新增行为
   已在裁决）。
5. **UI 明示**：compact 预填与模板扇出值在编辑页标注来源（H3 只补透明度）。

## 3. 风险

- 「模板声明端点参与候选」仍属猜测链延伸——若某模板真实 models 路径与
  声明 base 仍不匹配（codesome-2in1 未实测，openQ），失败语义仍是优雅回退，
  日志可定位；
- adapter 契约字段扩展需旧容器兼容（未知字段忽略即可，协议字符串不变）；
- H1 复现依赖 1-3s 窗口——手测路径 A 提供「切格式后手填再等 5s」第三对照
  分支（验证 onApiFormatChange 重臂后 watch 是否覆盖手填值）。

## 4. 回访结果（2026-09-23，U-5 关闭）

用户回忆：新建走**模板 + 高级模式**，claude 与 codex 侧似乎都有发生（无
明确记录）。⇒ **H2（preset+高级层 roles/catalog 不随保存生效）升为最可能
根因**——与现场（模板模式 + 展开高级层填写映射）完全吻合，双侧发生与前端
buildRequest 单一共因一致；H1 端点竞态仍由路径 A 复现确认。修复方案不变
（三假设全覆盖 + 第 0 步 adapter 判别）。

## 5. 验收

见 [HANDTEST.md](HANDTEST.md) T2（第 0 步 adapter 判别 → 复现路径 A/B/C →
6 模板拉取矩阵 → 降级路径 → 日志可解释性）。
