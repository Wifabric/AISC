# v2.1.16 preview-fixes b3 — 出厂 caveman 13、无代理链路与按钮动画

> 2026-10-25 preview.3 第三轮反馈 5 项。目标：修复出厂技能集合、无宿主代理时的 skill / 自更新 / 构建链路，以及更新与卸载按钮的动画归属。

## 范围与裁定

1. 出厂 caveman 只包含远程仓库 13 个 `caveman-*` 前缀技能（不含 `cavecrew`、`megacave`、`ultracave` 等非该前缀技能），继续叠加 `grill-me`。
2. Skill 安装 / 更新不再让 `cc-switch` 先直连等待 120 秒：先用短超时 `git ls-remote` 预检直连与镜像，选中可用源后仅对本次子进程注入 Git mirror 配置；宿主 adapter 超时提高到 600 秒。
3. 扩展操作按钮 spinner 同时匹配 `action + target`：更新动画只出现在更新按钮，卸载动画只出现在卸载按钮。
4. Workbench「关于 / 检查更新 / 进行更新」补充无宿主代理兜底：GitHub API 可走 `gh-proxy.com` 镜像，release asset 与 raw 文件可走 `ghfast.top` / `gh-proxy.com`；不默认启用系统代理。
5. 构建链路审计所有 GitHub 网络点；cc-switch resolver 在直连 API 失败后使用 `gh-proxy.com` 的 API 镜像，并保留既有 cache / manifest / receipt 兜底。

## 任务

### Task 1：出厂 caveman 13 个

- 修改：`container/cc_switch_skills.py`、`container/Dockerfile`、`container/_bundle/plugins/marketplaces/caveman/skills/`。
- RED：`tests/test_preview_factory_skills.py` 断言 13 个 `caveman-*` + `grill-me`，且 Dockerfile 校验清单与 vendored 目录完全一致。
- GREEN：从上游 `9b68f7e` 复制 13 个 `caveman-*` 目录；删除不属于该集合的 `cavecrew`；同步描述、校验列表与 entrypoint 文案。
- 验证：`PYTHONPATH=src python -m pytest tests/test_preview_factory_skills.py -q`。

### Task 2：skill 无代理安装 / 更新

- 修改：`container/aisc-extensions-adapter`、`src/aisc/application/extensions.py`。
- RED：`tests/test_extensions_adapter.py` 覆盖短超时预检顺序、镜像环境注入、直连不可用时不再先跑 120 秒 `cc-switch`、`skill-update` 不重新 enable。
- GREEN：实现 GitHub URL 探测函数与 git fallback 复用；host `_exec_adapter` 超时改为 600 秒。
- 验证：`PYTHONPATH=src python -m pytest tests/test_extensions_adapter.py -q`。

### Task 3：按钮动画按 action 区分

- 修改：`workbench/src/features/workspace-explorer/ExtensionsView.vue`。
- RED：Vitest 组件用例模拟 update 操作，断言更新按钮有 spinner、卸载按钮没有；再模拟 remove 反向断言。
- GREEN：模板使用 action + id 的匹配条件，覆盖 skill 组、单项、MCP、插件。
- 验证：`npm run test -- --run src/features/workspace-explorer/__tests__`。

### Task 4：Workbench 自更新无代理兜底

- 修改：`workbench/src-tauri/src/update.rs`。
- RED：Rust 单元测试覆盖 URL fallback 列表：atom 直连、API 直连 + `gh-proxy`、asset / sha256 / raw 直连 + 双镜像。
- GREEN：把「客户端重试」扩展为「URL 候选 × 客户端」，HTTP 4xx/5xx 也继续尝试下一候选；下载仍保留 sha256 校验。
- 验证：`cargo test --lib update`。

### Task 5：构建链路与 cc-switch resolver 兜底

- 修改：`src/aisc/application/cc_switch_resolver.py`，必要时补 `scripts/stage-*.sh`。
- RED：`tests/test_cc_switch_resolver.py` 覆盖直连网络失败后重试 `gh-proxy.com/https://api.github.com`，成功后仍写入 cache；显式 `AISC_GH_API_BASE` 不被覆盖。
- GREEN：resolver 构造 API base 候选并逐页重试；静态契约测试防止新增直连 GitHub 下载点。
- 验证：`PYTHONPATH=src python -m pytest tests/test_cc_switch_resolver.py tests/test_preview_factory_skills.py -q`。

## 收尾门禁

- `powershell -File scripts/local-gates.ps1`
- `powershell -File scripts/build-cli.ps1`
- `bash tools/vendor-refresh.sh`
- `PYTHONPATH=src python -m aisc build --no-cache`
- 实机预复测后准备 `v2.1.16-preview.4`。

## 执行记录（2026-10-25）

- 出厂集合已改为 13 个 `caveman-*` + `grill-me`；`cavecrew` 已移除，vendored 目录、Dockerfile 校验清单、cc-switch 注册表与 entrypoint 文案同步。
- Skill 安装 / 更新前用短超时探测 GitHub archive HEAD：直连可用才走 cc-switch 原生 HTTP；直连不可用时通过可达镜像 shallow Git clone，先把 skill 暂存到 cc-switch source，再走官方 install/sync。host adapter 超时提高到 600 秒。
- 扩展按钮 spinner 已按 `action + target` 匹配，更新与卸载不再同时转动。
- Workbench 自更新的 GitHub API、release asset、sha256、raw VERSION 均有 URL mirror 兜底；保留 sha256 完整性校验。
- cc-switch resolver 直连 API 失败后重试 `gh-proxy.com` API 镜像；显式 API base 不被覆盖。新增构建网络静态契约，覆盖 Dockerfile 与三个 stage 脚本。
- Targeted 验证：Python 79 / Vitest 11 / vue-tsc / Rust update 11 全绿（大文件下载用例按设计 ignored）。
- 实测根因补充：cc-switch 5.11 会自行拼 `github.com/.../archive/...zip`，Git `insteadOf` 环境不会生效；因此仅传 Git mirror env 仍会直连失败。现已改为 archive 探测 + 镜像 Git 暂存。
- 无代理实机验证：容器内安装 `JuliusBrussee/caveman:cavecrew` 成功（85 秒，Claude/Codex 均启用）；先禁用 Codex 后更新同一 skill 成功（24 秒），状态保持 Claude=1、Codex=0。
- 收尾验证：local gates 全绿（Python 1467 / Rust 365 / Vitest 643 / vue-tsc）；vendor 1532 全部通过；sidecar 已重建；`aisc build --no-cache` 成功产出 `super-claude:latest`。
- 最终镜像冒烟：空配置首次同步得到 14 个出厂技能（13 个 caveman + grill-me）且 Claude/Codex 全启用；无代理安装 `cavecrew` 成功（80 秒，双引擎启用）；禁用 Codex 后更新成功（54 秒），状态保持 Claude=1、Codex=0。
