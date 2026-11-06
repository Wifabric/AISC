# b2 工作记录菜单边界

状态：PLANNED。来源 F2；验收 R-2/H2。按 b1 用户下一步裁定后进入。

## 方案

`WorkRecordsView.vue` 的 openMemberMenu 直接保存 clientX/clientY，Teleport 到 body 后固定定位；菜单/子菜单缺少实际尺寸避让。打开后测量布局，下方不足向上，右侧不足向左，最终 clamp 到当前视口留边。菜单太高时设 max-height 与内部滚动；子菜单独立计算左右展开。

点击坐标、getBoundingClientRect 和视口边界采用同一 CSS 坐标系，不把文件侧栏现有 appZoom 除法原样照搬。窗口缩放/resize/相关滚动导致位置失效时重新定位或关闭；Escape、焦点还原及点击外部关闭保持一致。

## 涉及文件与验证

- 主改 `workbench/src/features/workspace-explorer/WorkRecordsView.vue`；阅读 WorkspaceExplorer 菜单实现复用合适部分，避免扩大为全站菜单重写。
- `workRecordsView.test.ts`：底边/右边/四角、主菜单与子菜单、超短视口、关闭焦点、异步动作。
- 自动化模拟 rect 验证 placement；真实 Windows UI 验证缩放/滚动/窄屏，菜单点击执行正确成员动作。
- 回归 2.1.17 新建/分支/重命名动作与失败标签清理，不能为布局改坏归属。
- H2 与用户批次验收全部 NOT RUN；不新增工作记录数据模型。
