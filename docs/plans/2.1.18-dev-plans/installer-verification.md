# 2.1.18 Windows 交互安装验证

日期：2026-11-09（Asia/Shanghai）。执行者：开发助手；真实 Windows Sandbox GUI 操作和独立文件/注册表状态检查，自查，无独立评审。

## 环境与产物

用户已授权安装必要组件与权限，并完成重启。Windows Sandbox 与桌面操作通道已恢复。两个独立干净 guest 使用 WDAGUtilityAccount；输入目录只读映射，仅专用 evidence 目录可写，没有映射用户工作区、凭据或日常平台数据。测试结束后两个 guest 均停止。

- 全新安装 guest：`35ddd3be-cc3b-48e4-8c7b-88ded406ece4`。
- 升级 guest：`0a27ad3a-f75a-4d86-9762-d62537617474`。
- 旧版：官方 2.1.17 安装包，SHA256 `ed1955d8fd8a751add9802fc477f45428e8725a5abd1627f4423cdb67d51c6b6`，与正式 Release digest 一致。
- 新版：正式版本构建提交 `fc569ed065f88f252f7201a5ad80c3093511b7f6` 的本地完整 NSIS 包，SHA256 `8095c147f2cc8ea397a83f318869454ffdb4ddf5e732d5ff7134f289e8488f7a`。后续测试 fixture 和文档修改没有改变产品源码与打包输入。
- 安装目录：`%LOCALAPPDATA%/AISC Workbench`；测试数据：`%LOCALAPPDATA%/AISC/data/release18-qa.txt`，内容 `release18-retention-sentinel`。

## 实测结果

| 用例 | 结果 | 实际观察与断言 |
| --- | --- | --- |
| 干净环境交互安装 | PASS | 英文安装向导、默认用户目录安装成功；自动补装 WebView2；完成页成功 |
| 缺 Docker 引导与启动 | PASS | 明确提示未找到 Docker，可稍后安装；选择 No 后客户端正常显示工作区选择页 |
| 取消卸载 | PASS | 取消后 Workbench/CLI/卸载器仍存在，Workbench 为 2.1.18，数据标记未改变，PATH 中安装目录一次 |
| 默认卸载保留数据 | PASS | 删除应用数据默认未勾选；卸载成功，程序文件和 PATH 条目移除，数据标记原样保留 |
| 2.1.17 → 2.1.18 升级 | PASS | 安装旧版并启动；写入数据后关闭客户端；新版向导识别旧版，默认先卸载再安装，完成成功 |
| 升级后的版本与启动 | PASS | Workbench/卸载器版本为 2.1.18；已安装 CLI 实际执行 version，CLI/bundle 均为 0.2.0，exit_code=0、errors=[]；新客户端正常打开 |
| 升级后数据与 PATH | PASS | 数据标记原样保留；PATH 中 AISC 安装目录只有一次 |
| 升级后交互卸载 | PASS | 保留默认选项卸载成功；缺 Docker 时明确说明未执行容器/镜像清理；程序文件和 PATH 条目移除，数据标记保留 |

## 证据与覆盖边界

本地原始证据目录：`D:/AISC/p18/release18-sandbox/evidence`。关键文件为 `fresh-started.json`、`fresh-cancel.json`、`fresh-uninstalled.json`、`upgrade-started.json`、`upgrade-before.json`、`upgrade-after.json`、`upgrade-cli-version.json`、`upgrade-uninstalled.json`。汇总与断言输出保存在发布工作树 `output/verification/release18-installer-evidence.json`。GUI 页面观察记录在本次开发会话的桌面工具返回中。

隔离 guest 内没有 Docker，故本报告不声称验证 guest 内容器运行或真实 Docker 资源删除。缺依赖提示与客户端启动已测；真实容器/产品交互沿用已验收 Preview.13 的独立证据。Windows 静默安装、重装、PATH 和卸载数据保留另有 [正式 NSIS CI](https://github.com/Wifabric/AISC/actions/runs/42496738996) PASS。此前等待重启/桌面工具故障的 NOT RUN 状态由本次实际结果取代，不需要用户重新手测产品。

结论：剩余 Windows 交互安装验证已完成。PR #99 已按用户确认合入 main；当前文档收尾后，正式发布仍需用户最后确认；正式 tag、发布与发布后资产校验尚未执行。详见 [发布准备](release-readiness.md)。
