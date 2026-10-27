# v2.1.17 preview 准备材料

状态：开发与本地构建验证完成，统一用户手测待执行；尚未发布。用户宣布阶段收尾尚未发生，发布验收门保持关闭。

拟用 preview 标识 `v2.1.17.dev0`；当前本地 Workbench 2.1.17，配套 CLI/bundle 0.1.10.dev0。发布前按 DEVELOP_WIKI 重新核对版本、tag、三平台安装器及 Release Notes，不以本文件代替发布授权。

## Release Notes 草案

- 改善无代理扩展安装：完整安装多子技能、默认双端开启，更新保留用户关闭选择；网络失败保留具体原因和镜像尝试信息。
- 市场显示来源、缓存时间和详情；有可靠版本源时提供更新标识，Skills/MCP 无可靠比较源时明确说明。
- 扩展操作提供失败项重试、部分成功结果与可复制的脱敏诊断；新增 Skills、MCP、Plugins 三类精选搜索入口。
- Windows 更新下载后等待用户点击“退出更新”：资源管理器选中安装包，正常启动安装器，再退出 Workbench。
- Services 增加“注册服务”分组；健康报告列出更新网络观测与实际 CLI/bundle 配对。
- 刷新 Node、Codex、Claude Code、cc-switch、Mihomo、yazi 与 geodata；离线主包/原生伴生包精确配对，验证官方完整性。

## 验收与产物

- 各批 PASS/FAIL/NOT RUN 见 PRETEST；实际运行步骤及异常判据见 HANDTEST。
- 内置依赖来源、回退版本和 SHA256 见 dependency-evidence.md、dependency-payloads.json。
- 最终 sidecar/NSIS SHA256、bundle 配对、镜像 ID 与实际软件版本已记录于 PRETEST b7；本机 `release-staging/2.1.17-b7/` 已备好常规与专用更新测试启动器，见 HANDTEST。
- 当前续跑 agent 无 Computer Use。真实 Explorer/NSIS/Services/扩展 UI 必须由一次统一用户手测复核；自动化与容器数据面不能替代。

## 发布门

- [x] b7 本地门禁、sidecar/bundle verify、无缓存镜像及 Workbench/NSIS 构建完成。
- [x] 必要远端 CI 通过，开发批次合入 develop（PR #40–#47；b7 修正提交的 Workbench/三平台 sidecar/deb/dmg/NSIS 全通过，详见 PRETEST）。
- [ ] 用户统一手测全部批次通过；未执行项/风险有明确裁定。
- [ ] 用户宣布阶段收尾；按开发手册准备 preview 发布。
- [ ] main 合并及正式发布按独立授权和发布流程执行。

本轮不创建 tag、GitHub Release 或 PyPI/TestPyPI 上传，不清理分支或旧 Release，不把反馈提前标记 resolved。
