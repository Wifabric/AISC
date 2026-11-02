# b2 工作记录菜单边界

状态：已实现；D-8 后 Windows CU 发现子菜单遮挡误移并修复复测，已执行路径 PASS；最终前端 852 项与 vue-tsc/Vite 通过，用户验收待定。来源 F2；验收 R-2/H2，实测边界见 PRETEST。用户明确保留 PR #62/#63 不合并，直接开发 b2；独立工作树分支 `codex/2.1.18-b2-work-record-menu` 从 develop `1d26f237` 创建后本地快进到依赖起点 `cb528cad`，不修改远端长期线。

## 方案

PR 交接：D-9 用户授权后已创建 [#64](https://github.com/Wifabric/AISC/pull/64)，base 为 b1 分支，保持 #62/#63 不变。测试对应产品提交 `247fbf97`；仅本地新增测试不随 PR 上传。远端 CI/验收状态见 PRETEST。

`WorkRecordsView.vue` 的 openMemberMenu 直接保存 clientX/clientY，Teleport 到 body 后固定定位；菜单/子菜单缺少实际尺寸避让。打开后测量布局，下方不足向上，右侧不足向左，最终 clamp 到当前视口留边。菜单太高时设 max-height 与内部滚动；子菜单独立计算左右展开。

点击坐标、getBoundingClientRect 和视口边界采用同一 CSS 坐标系，不把文件侧栏现有 appZoom 除法原样照搬。窗口缩放/resize/相关滚动导致位置失效时重新定位或关闭；Escape、焦点还原及点击外部关闭保持一致。

实施细化：主菜单和移入子菜单都 Teleport 到 body，子菜单作为独立 fixed 同级节点，避免被主菜单内部滚动裁切。菜单最大宽高由当前 visualViewport（缺失则 window）减留边限制，长文字换行。使用实际 rect 测量；主菜单优先鼠标右下、放不下则翻转，子菜单优先触发项右侧、放不下则左侧，再统一限制在视口内。内部滚动不关闭主菜单，主菜单滚动时关闭已失去锚点的子菜单；外部滚动/resize/visualViewport 变化关闭菜单。Escape 返回原成员，方向键/Home/End 导航，右键或键盘打开不会改成员归属；异步 move 完成只关闭对应原菜单，不关闭后来打开的菜单。

首轮遵守用户停止 CU 的要求；D-8 重新授权后已执行真实桌面测试。子菜单不得覆盖触发按钮：优先能容纳的右/左侧，两侧都不足时选空间较大侧，限制宽度并换行，等待尺寸更新后再落位。该约束来自真实误移复现，不只保证视口边界。

## 涉及文件与验证

- 主改 `workbench/src/features/workspace-explorer/WorkRecordsView.vue`；阅读 WorkspaceExplorer 菜单实现复用合适部分，避免扩大为全站菜单重写。
- `workRecordsView.test.ts`：底边/右边/四角、主菜单与子菜单、超短视口、关闭焦点、异步动作。
- 自动化模拟 rect 验证 placement；真实 Windows UI 验证缩放/滚动/窄屏，菜单点击执行正确成员动作。
- 回归 2.1.17 新建/分支/重命名动作与失败标签清理，不能为布局改坏归属。
- H2 已执行路径与未测项分别见 PRETEST；用户批次验收待定，不新增工作记录数据模型。

## 实施验证

- 主/子菜单分别实际测量定位、限制宽高、内部滚动；子菜单通过嵌套 Teleport 在真实 DOM 中成为 body 子节点，不受主菜单滚动框裁切。
- 菜单可见并完成位置更新后才聚焦；ContextMenu/Shift+F10 打开，方向键/Home/End 导航，Escape 返回原行，Tab 离开。窗口/外部滚动关闭；内部滚动保留菜单。
- 对菜单异步 move 结果增加实例判断，避免操作 A 完成后关闭后来打开的 B 菜单。原 store/IPC/归属规则未改。
- 新增 7 项定向断言先 RED；最终 WorkRecordsView 44 项（含 10 项新增本地回归）、前端全套 98 文件/851 项 PASS；vue-tsc/Vite PASS。
- 新增测试仅留本机，不纳入公开提交；无 Rust/CLI/容器变化，未重跑这些层或沿用其历史数据作为 b2 实测。证据见 PRETEST。
- D-8 实机补测发现长子菜单覆盖触发按钮并误移，修复后定向 45 项、全量 852 项、构建及同路径 CU 通过。新增回归仍留本机；实际改名仅命中指定会话，点击长子菜单末项精确移入目标记录，真实数据面已核对。
