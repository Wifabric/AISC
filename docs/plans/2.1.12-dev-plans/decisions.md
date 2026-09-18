# 2.1.12 阶段裁决记录

> 本文件是 v2.1.12 阶段的裁决日志（对齐 0.1.0 周期 decisions.md 惯例）。每条裁决记：问题、裁定、影响面。编号 D-N 阶段内连续。

- **D-1（r1 形态路线，2026-09-18 用户裁定）**：provider 模板化采用**纯静态 AISC 自有模板**路线——维持现有「添加 provider 时选预设」的形态与清单（deepseek / volcengine-ark / zhipu / kimi / codesome），**否决** r1 推荐的 `--config-file` 上游委托混合路；不镜像 cc-switch 内置模板清单。同时执行去预配置改造：`cc_switch_preset_providers.py` 不再向 cc-switch DB 种第三方行（todo 179「不再提供预配置，但是提供添加模板」），preset 数据瘦身为添加模板；前后端清单事实源统一（消灭 CcSwitchUiTab.vue:111 与容器数据的漂移——UI 缺 codesome 已证）。
- **D-2（r1 存量卷迁移，2026-09-18 Claude 代定，用户可否决）**：marker 版本号 bump 触发一次性迁移——清掉既有容器 DB 里的第三方预置行、保留 official 行；用户改过的行视为用户行不动。codesome 行待专项修好后从模板重加。
- **D-3（cc-switch 赞助商模板，2026-09-18 用户裁定）**：上游 8 个带返佣链接的赞助商模板**完全不出现**（无隐藏开关）。**codesome 是 AISC 自有赞助商，例外**——保留于模板清单并作为重点位。
- **D-4（r2 computer use，2026-09-18 用户裁定 = 选项 A）**：**暂不原生实施**，条目闭环转观察。CLI 侧能力依赖上游不稳定捆绑 MCP 插件（openai/codex#20851）；桌面级正主是 Codex 桌面应用。重启先决：上游契约稳定 + 评估路线二（headless 浏览器）；路线三（宿主侧执行）按 §12.1 永久否决。配套：文档写明「用户可自行挂载 MCP 浏览器服务器尝鲜（不改镜像）」。
- **D-5（阶段新增范围，2026-09-18 用户裁定）**：本阶段立项 **codesome 专项**——系统性解决其配置问题（已知：UI 添加列表缺失〔漂移实证〕、历史预配置配置项错误、provider 页切换超时之 codesome 适配、显示异常；完整问题清单待用户开题时补充）。专项产出并入 D-1 模板化实施。
- **D-6（codesome 专项九项裁定，2026-09-18 用户裁定，见 codesome-templates.md §5）**：
  1. 模板 id：`codesome-v3` + `codesome-2in1`（UI 显示名「Codesome V3（月卡/按量）」「Codesome 二合一（V5）」）。
  2. UI 形态：添加 provider 时**默认选中置顶的 codesome 模板**；表单下方加「**获取服务**」按钮，按当前模板导航到获取页（`meta.codesome.cn` 带 aff 参数）；**界面不出现「赞助商」等任何标明字样**（推翻 D-6 前设计稿的 sponsor 标识构想）。
  3. 两模板均覆盖 claude + codex 双 agent。
  4. 模型目录：codesome 提供与 OpenAI 官方**完全一致**的模型列表——catalog 直接**镜像 OpenAI 官方模型列表**（落地时取官方列表快照，contextWindow 从官方元数据；默认模型仍 `gpt-5.6-terra`，codesome 教程指定）；窗口量级 1M 可接受。
  5. `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` 入模板 seed。
  6. codex 默认形态维持 **S9a 翻译**（2026-08-29 裁定实测最稳），官方原生 Responses（`/v1`、`/openai`）作高级层回退项。
  7. D-2 迁移确认，并**升级为全局去预置**：后续镜像**不预置任何不带 key 的 provider 卡片（含 official 行）**——provider 行完全由用户经「添加 provider」创建；preset 模块瘦身为「模板数据源 + 存量迁移」（official seeding、pristine 清扫、proxy 对账等预置职能一并退役；实施时核验 cc-switch 对空 provider 表无隐藏依赖）。
  8. 模板清单事实源 = **镜像内清单文件 + 与模板数据的平价测试**（方案 A；adapter `template-list` op 否决）。
  9. key 前缀校验 = **软拦截**（前缀不符 warn 不拦提交），提示样式须**醒目**。
