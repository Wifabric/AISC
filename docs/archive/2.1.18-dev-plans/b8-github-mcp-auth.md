# b8 GitHub MCP 首次认证配置入口

状态：本批及后续整合修正已合入 main，开发者证据见下方历史记录与 [PROGRESS](PROGRESS.md)；用户已报告统一验收通过。正式发布和反馈闭环见 [发布准备](release-readiness.md)。

以下保留本批实施时的基线、验证和决策过程，不将当时的未测项目改写为 PASS。

## 方案与范围

在“扩展 → MCP → github”的已安装项提供可发现的配置入口，复用既有 MCP 配置读写与默认安装模型，不重复实现默认安装或替代 cc-switch。分别显示 Claude/Codex 缺配置、待认证、已配置与实际连接验证结果；保存配置不等于已验证连通。

优先复用当前支持的授权方式；凭据由用户本人输入/授权，敏感值默认不回显，不进入诊断、操作历史、截图证据或源码。取消不改原配置，保存失败保留原配置；用户自定义 server 与未选择的引擎不被覆盖。若实施调查发现必须新增持久化凭据机制或扩大权限，先补设计和对应裁定，不静默切换方案。

## 阅读与验证入口

- `ExtensionsView.vue`、`ExtensionItemDetail.vue`、`extensions.ts`、`src/aisc/application/extensions.py`、`container/aisc-extensions-adapter`、`container/lib/default_mcp.py`。
- `tests/test_default_github_mcp.py`、扩展 store/组件已有回归，覆盖单侧配置、无配置、取消、失效凭据、保存失败、脱敏和目标切换。
- 隔离 runtime 分别验证 Claude/Codex 真实配置生效与授权后的只读连接；真实授权不可用时明确 NOT RUN，不拿模拟凭据当通过。
- 受影响层门禁、生产候选、CI、H8 CU 与用户验收独立记录。

## 本批接口与存储约定

- 已安装 MCP 的 github 行新增“配置认证”。界面按 Claude/Codex 独立选择，仅允许修改已启用的目标；密码框不回显旧令牌，关闭/切目标/发出请求后清空。保存失败不保留含凭据的自动重试闭包或操作历史。
- 复用 cc-switch 现有 SQLite server_config 与现有 live MCP 配置，不建立新凭据文件或系统全局环境变量。Claude 用既有 headers，Codex 用标准 http_headers；只在用户选择的引擎写入 PAT Authorization，保留另一侧文件字节、其他 MCP 和目标既有设置。默认同步与开关路径同步保持这两个引擎的配置。
- 三条 stdin JSON 命令 github-auth-status/save/check。只返回配置/启用标志、版本摘要和稳定错误码，不读取凭据到界面。仅编辑 AISC 管理的默认 github 且 URL 为官方地址；自定义来源/符号链接/损坏配置拒绝覆盖。版本摘要防止旧表单覆盖新配置，SQLite 事务加文件失败回滚覆盖普通保存错误；不将文件/数据库跨进程崩溃称为原子事务。
- “检查连接（只读）”由用户显式触发，按选中引擎现有 live 配置向固定官方地址发 MCP initialize，不调用工具、不跟随重定向；分别显示缺配置、认证失败、拒绝访问、网络/协议错误或握手成功。检查期间配置变化则废弃结果。保存始终显示连接未验证；握手成功也不宣称所有工具权限验证通过。
- 配置字段依据已读取的 [OpenAI MCP 文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) 与 [配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)；官方 GitHub 地址与 PAT 方式参照 [GitHub 安装说明](https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-codex.md)。当前运行时的真实 Codex/Claude CLI 读取另外验证，不仅依赖文档推断。

## 本批当时的真实验证

- 隔离容器 `aisc-b8-auth-bb3f7b560b` 使用合成无效令牌；分别保存 Claude/Codex 时未选择文件逐字节保持，真实 `codex-real mcp get github --json` 和 `claude-real mcp get github` 均识别配置并退出 0。两侧关/开与重新执行默认同步后配置仍在。没有使用真实用户令牌，授权连接仍 NOT RUN。
- 首次 QA 初始化因配置目录未创建而失败，补齐隔离目录后通过；所有 QA 容器核对专属标签后清理。证据 `output/verification/real-auth.json`。
- 首轮定向 Python 96 passed / 11 subtests；前端定向 21 项。全量前端发现组件越层调用 IPC，已移回 store；构建进一步发现私有 refresh 接口和测试类型问题，均修正并定向复验。完整 Rust 420 passed / 2 ignored。最终门禁结果在完成后追加，不提前记全绿。

## 最终本地门禁

- Python 全套 1782 passed / 54 skipped / 207 subtests；最终保护补充后定向 101 passed / 29 subtests。前端最终全套 874 passed / 103 files、类型与生产构建 PASS；Rust 420 passed / 2 ignored。
- 冻结 CLI SHA256 `d729096813d1c9187a37df99d4fb560a3ab716916494d3332526dd6b9d985503`，在独立容器完整复验 status/save、双引擎隔离、真实客户端读取、开关与重新同步；证据 `output/verification/frozen-auth.json`。使用合成无效令牌，不等于授权连接成功。
- 原始日志和合成数据留本机，不入提交。自查不是独立评审；远端 CI 尚未执行，真实 GUI/H8、用户凭据授权和实际 MCP 工具调用、SSH 均 NOT RUN。


PR #72 精确 head `deb15d19` 的 frontend/rust/cli 全部 PASS（run 42407318416），已合入 develop `4ff4881fbe8831ce2f68118eca994dc2cb55a375`。GUI/真实授权仍待 Preview。
