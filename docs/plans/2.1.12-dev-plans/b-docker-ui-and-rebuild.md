# B 链——主题切换残留修复 × 重建按钮 × Docker 资源管理 UI

> 状态：B0 **手测 PASS（2026-09-16，9c838ba）**；B1 **手测 PASS（2026-09-16，f79a659）**；B2 认可（2026-09-16，a4b08e9）；B3 待做。P0。三块互相独立，可分批并 develop。

## 范围（scope）

- **in**：**B0 v2.1.11 主题切换残留 bug**（2026-09-16 用户截图报障：切换颜色主题后，历史会话视图的消息/终端输出块残留深色底+淡化字样式，不随 data-theme 重绘——定位后修，含主题切换传播链补测）；①BuildProgress failed/cancelled「重新构建」按钮 + 摘要页入口确认 + BUILD_TIMEOUT 600s 矛盾修复；②Docker 资源管理简化 UI（R1：maintenance docker-scan/docker-cleanup/cache-usage/cache-cleanup 产品化，并入设置页「磁盘与缓存」卡片扩展为「Docker 资源」组，含镜像重建入口联动 A5）。
- **out**（显式排除）：失败结构化错误码（网络拉镜像失败 vs Dockerfile 错同码维持——避免动 docs/rfc/aisc-cli-v1.md 与三模式测试，留待独立 RFC）；docker 恢复自动重试构建；端口映射类功能（R1 释义 A/B/D 已否决——web_services 冻结契约与回环安全边界不动，src/aisc/domain/web_services.py:50）；maintenance CLI 契约与 --context 语义变更（installer-facing 面不动）。

## 契约（contracts）

- 重建按钮走 store.startBuild(tag) 既有链，不另起 IPC 调用；遵守 store 层固化测试契约（A-G14：终态只能 Promise settle 写入、buildOpId 防晚到覆盖、后台通知至多一次，workspaceRuntime.ts:356-414/279-281）。
- 重试 tag = store.buildTag（本次失败的 tag；与 store.launch.image 当前等价但来源语义不同，契约定前者）。摘要页 imageNotFound「构建镜像」按钮（LaunchSummary.vue:159，全仓唯一 startBuild 调用点）维持为快捷重试入口。
- BUILD_TIMEOUT 600s→1800s（runtime.rs:35）；i18n durationHint 与超时语义文案对齐（zh-CN.ts:167「通常需要 10-20 分钟」）。
- Docker UI 走 maintenance 同一 application 层（docker_lifecycle.py），IPC 路径实施时定（sidecar CLI envelope 优先，受 serve 闸门 allowlist 现状约束）；CLI maintenance 子命令零改动（main.py:484-527；installer.nsi:1542-1638 与 install.sh:278-321 依赖它）。
- 清理类动作为 destructive：一律 scan 预览 → 确认 → 执行；不动 --context upgrade 专属逻辑（镜像移交语义 docker_lifecycle.py:302-358）。低配模式关系：清理动作即原「磁盘与缓存」诉求强化，不新开入口。
- i18n zh-CN/en-US 同步（P0 已先行收口两文件在途改动，无冲突残留）。

## 实施顺序

0. **B0 主题切换残留修复（先行小批）**：定位历史会话消息/输出块的主题变量消费点（疑点：dim/淡出态样式硬编码深色、xterm 实例主题在创建时固化、或块级内联样式缓存）；修复 = 全部改走主题 CSS 变量 + 切换时失效重绘；vitest 补主题切换重渲染用例。
1. **B1 重建按钮（纯前端）**：BuildProgress.vue 终态 actions 行加「重新构建」（failed + cancelled；dockerError 分支的「启动 Docker」保留）；调 store.startBuild(store.buildTag)；按钮自持 disabled=building（组件级守卫，对齐 dockerStarting 模式）；i18n build.rebuild 双语。
2. **B2 BUILD_TIMEOUT**：常量 600→1800 + 超时终态文案校正（实施时按最小改动定：改提示或区分「已超时」）。
3. **B3 Docker 资源 UI**：Rust IPC 薄封装（scan/cleanup/cache-usage/cache-cleanup/rebuild）→ 设置页「磁盘与缓存」卡片扩展「Docker 资源」组（扫描预览/容器与镜像清理确认制/缓存用量/缓存清理/重建镜像按钮——重建复用 A4 --rebuild 或直接调 maintenance docker-rebuild，视 A 链进度）→ 远程 target 文案差异。
4. **B4 手测轮**：本地 + 低配/资源紧张场景 + 远程 target 各一轮。

## 验收（acceptance）

- B0：`pnpm vitest run` + `pnpm vue-tsc --noEmit`（新增主题切换重渲染用例）；手测：tauri dev 打开含终端输出块的历史会话 → dark/light 往返切换 → 无深色残留、文字对比度正常。
- B1：`pnpm vitest run`（stores/__tests__/runtimeBuild.test.ts 加用例：failed→重新构建再次调用 ipc.buildImage 且 tag 不变；cancelled 同；building 中按钮 disabled）+ `pnpm vue-tsc --noEmit`；手测：tauri dev 下故意改坏 Dockerfile 触发 failed → 点重新构建仍 failed → 修复后点重新构建 → complete；取消构建后重新构建可用。
- B2：`cargo test --lib`；手测：人为构造超 10 分钟构建（限速镜像源）不被超时杀。
- B3：`cargo test --lib` + vitest（卡片渲染/预览→确认流/确认前禁用）；手测：扫描→预览→清理后 `docker images` 与 `docker ps -a` 复核无多删；缓存清理后磁盘占用下降；「升级后清理」场景不误删待重建移交镜像（对齐 upgrade 语境语义）；低配机器走一轮；远程 target 下扫描/清理手测（docker 不在本机——确认文案不误导）。
- 全链：`scripts/local-gates.ps1` 四硬门绿。

## 风险

| 风险 | 证据 | 缓解 |
| --- | --- | --- |
| 绕过 startBuild 破坏 store 测试契约 | workspaceRuntime.ts A-G14 注释组；runtimeBuild.test.ts 锁定 | B1 契约：复用 startBuild 唯一入口 |
| 超时上限提高掩盖挂死构建 | runtime.rs:35；cli.rs:1060-1070（sigint_or_kill） | 保留 cancel 通道；手测确认超时后呈可重试终态 |
| Docker UI 误清安装器管理的资源 | docker_lifecycle.py:302-358（upgrade 镜像移交语义） | scan 预览 + destructive 确认；不动 upgrade 专属逻辑；手测覆盖升级后清理场景 |
| maintenance 契约意外破坏波及安装器 | main.py:484-527；installer.nsi:1542-1638；install.sh:278-321 | 契约零改动；只加用户面 IPC/UI |
| i18n 漏改一侧 | zh-CN.ts/en-US.ts 双文件 | 双语同 PR；vue-tsc 兜底 |
| 远程 target 行为差异 | build 走 resolve_target_for（本地/远程同路） | B4 远程手测项 |

## 决策引用

D-11、D-12、D-15（见 decisions.md）。

## 回滚（rollback）

B1/B2 纯前端 + 一个 Rust 常量，revert 零协议成本（未动 CLI 错误码与 RFC，DEVELOP_WIKI §6.1/§8.6 不触发）；B3 卡片整组 revert 不影响 maintenance CLI 面（安装器链路无感）；若 B3 IPC 走 sidecar envelope 路径，revert 仅移除 UI 与 IPC 命令，sidecar 命令面不动。两块各自独立分支独立手测（D-4 惯例）。
