# b8 GitHub MCP 首次认证配置入口

状态：PLANNED，未实施。D-11；F6 / R-8 / H8。自行开发，排在 b7 后；不依赖模块需求 U-3/U-4。

## 方案与范围

在“扩展 → MCP → github”的已安装项提供可发现的配置入口，复用既有 MCP 配置读写与默认安装模型，不重复实现默认安装或替代 cc-switch。分别显示 Claude/Codex 缺配置、待认证、已配置与实际连接验证结果；保存配置不等于已验证连通。

优先复用当前支持的授权方式；凭据由用户本人输入/授权，敏感值默认不回显，不进入诊断、操作历史、截图证据或源码。取消不改原配置，保存失败保留原配置；用户自定义 server 与未选择的引擎不被覆盖。若实施调查发现必须新增持久化凭据机制或扩大权限，先补设计和对应裁定，不静默切换方案。

## 阅读与验证入口

- `ExtensionsView.vue`、`ExtensionItemDetail.vue`、`extensions.ts`、`src/aisc/application/extensions.py`、`container/aisc-extensions-adapter`、`container/lib/default_mcp.py`。
- `tests/test_default_github_mcp.py`、扩展 store/组件已有回归，覆盖单侧配置、无配置、取消、失效凭据、保存失败、脱敏和目标切换。
- 隔离 runtime 分别验证 Claude/Codex 真实配置生效与授权后的只读连接；真实授权不可用时明确 NOT RUN，不拿模拟凭据当通过。
- 受影响层门禁、生产候选、CI、H8 CU 与用户验收独立记录。
