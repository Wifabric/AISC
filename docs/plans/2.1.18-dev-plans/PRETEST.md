# 实测与证据账本

截至 2026-11-02，仅完成只读调研与计划文档准备。四条反馈对应功能尚未执行测试、真实数据面、CU 或用户验收；独立的 2.1.17 个人功能整合验证不计入本表。

| 批次 | 定向/自动化 | 真实数据面 | 候选构建 | Windows CU | 用户验收 | 原因 |
| --- | --- | --- | --- | --- | --- | --- |
| b1 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施 |
| b2 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施 |
| b3 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施；U-1 |
| b4 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施；U-2 |
| b5 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施；U-3/U-4 |
| b6 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | 未实施；依赖 b5/U-3 |

本轮文档检查结果单独记 [PROGRESS](PROGRESS.md)，不填成上表功能 PASS。

## 每次实测记录模板

- 批次/需求/手测编号：
- 时间/执行者/操作系统/窗口尺寸与缩放：
- 实施分支、起点与测试提交 SHA、PR/CI 链接（尚无则明确未创建）：
- Workbench/CLI/bundle 版本、候选路径/哈希、镜像 ID/tag、目标机器/工作区（分享时脱敏）：
- 前置状态与实际执行的命令/点击：
- 预期字段/状态与实际结果：
- 结论 PASS / FAIL / NOT RUN；失败原始输出或 NOT RUN 原因：
- 日志/截图位置；修复提交与复测范围：
- 用户本批结论原意、日期、未测放行/转期项、是否允许下一批：

同一项只测部分环境时拆行记，例如 Local PASS、Remote NOT RUN；不要给整批一个含混的 PASS。不得在证据里存 API keys、真实私人主题内容或未经允许分享的对话。
