# b8 — 复测第三轮四项修复（2026-10-22）

> 来源：用户复测第三轮。分支 `2.1.16-b8-handtest-round3`。

| # | 反馈 | 根因 | 修复 |
| --- | --- | --- | --- |
| 1 | 清理后空预览行（—）与重复 builder/dangling 日志是噪音 | 预览行无条件渲染；零回收每项都打一行 | 空桶过滤；零回收压缩为一行「24 小时安全窗内无可回收（0B）」 |
| 2 | 构建缓存卡片标「可清理 922 · 2.6GB」但清理后不变 | until=24h 安全窗：刚构建的缓存全在窗口内（reclaimed 0B 属预期），但卡片文字过度承诺 | 卡片标签改「构建缓存」；零回收日志明确解释 24h 窗（既有 disclaimer 保留） |
| 3 | 插件页报 unknown op: plugin-market-list | b7 的 Rust OPS 数组行级编辑未生效（13 op 只写了签名/argv） | 数组修复为 13 op；cargo check/test 绿 |
| 4 | claude-real/codex-real not found | b7 把工厂 npm -g 装进 /opt/aisc/toolchain——project 模式被宿主 toolchain 挂载**遮蔽**，符号链接目标消失 | 工厂安装改 `/opt/aisc/factory-npm`（非挂载路径）；运行时前缀仍指 toolchain（更新持久不变）。空挂载模拟实测 claude/codex 版本正常 |

## 验证
- 模拟 project 空挂载：`PREFIX=/opt/aisc/toolchain/npm-global`、real→factory-npm、claude 2.1.273 / codex 0.154.0、wrapper 头 `#!/bin/bash` ✓
- 全量 pytest（契约更新）/ Vitest 611 / vue-tsc 0 / cargo 362；vendor verify 1520/0。
