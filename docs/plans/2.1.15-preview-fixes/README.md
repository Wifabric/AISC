# v2.1.15 Preview Fixes

Preview 验证窗内的阻断修复索引。按 DEVELOP_WIKI §1.1 preview 迭代纪律执行：
恶性/阻断问题允许直接开分支修复，但必须根因先行、TDD、本地门禁与远程 CI
全绿后并回 develop，再发布下一跳 preview。

| 批 | 内容 | 分支 | 终态 |
| --- | --- | --- | --- |
| b9 | preview.1 反馈四项阻断修复 | `2.1.15-b9-preview-blocking-fixes` | 已发布 preview.2，待 b9-T1–T3 实测 |
| b10 | 远端 target 路由与 workspace 绑定修复 | `2.1.15-b10-remote-routing-and-work-records-ux` | 已合入 develop，待 preview.3 实测 |
| b11 | Work Records 拖拽、右键菜单与呈现一致性 | `2.1.15-b10-remote-routing-and-work-records-ux` | 已发布 preview.3，待实机 |
| b12 | preview.3 四项字段反馈修复 | `2.1.15-b12-preview3-field-fixes` | 已发布 preview.4，b12-T1 已实测通过 |
| b13 | 远程资源导航、机器身份、远端数据面与 Help 反馈 | `2.1.15-b13-remote-workspace-model` | 已发布 preview.5，待 b13 实机 |
| b14 | preview.5 协议提示、远程首载、Recent 机器路由与镜像聚合 | `2.1.15-b14-preview5-field-fixes` | 已发布 preview.6，待 b14 实机 |
| b15 | 更新链路、Work Records 中文/折叠/去 Activate、Claude 树与 Docker 资源 | `2.1.15-b15-preview6-field-fixes` | 已发布 preview.7，待 b15 实机 |
