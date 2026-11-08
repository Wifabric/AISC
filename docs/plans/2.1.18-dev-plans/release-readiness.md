# 2.1.18 正式发布准备

## 授权与基线

用户已明确确认 Preview.13 验收无问题，并要求完成剩余工作，推进到可确认合并。此前旧一轮验收同样由用户报告通过。本轮记录这两个用户结论，不把它们改写为开发者未执行项目的 PASS。

- develop：`9a83cbc603ab760089181c53636d5662aa37b9f9`；main：`bf95ce0aa9eaca0439b52679f97b91c46a25adeb`。
- 分支：`codex/2.1.18-release-prep`，从上述 develop 创建；发布 PR 目标 main。只准备可审查的合并，不合入 main、不打 tag、不公开发布或上传 PyPI。
- 主开发/自查：当前开发助手；无独立审查。维持已验收产品行为，只做版本、说明、验收账本和必要发布验证。
- Workbench 版本 `2.1.18`；CLI `0.2.0`。CLI 新增模块与个人/主题等功能，按 WIKI §8.4 的 0.x minor 功能版本约定升级；协议仍为 4。预检确认该 CLI 版本尚未占用、两个正式标签不存在。

## 本轮执行

1. 回写 b1–b10、S12–S16 的用户验收，保留历史验证范围；完成正式发布说明及版本一致性。
2. 运行版本/打包/安装相关验证。以正式版本号重新构建 CLI、bundle、Workbench/NSIS；容器内容保持已验收版本。准确记录文件哈希和源码，不覆盖 Preview.13。
3. 创建英文发布 PR，检查精确提交 Workbench、跨平台 Python、CLI sidecar、NSIS、Linux/macOS bundle 和 Artifact 流水线；非 tag dispatch 不进入 release jobs。
4. 复核发布 PR base/head、main 未漂移、合并预览及全部适用 CI；准备 main/tag/发布后资产校验和反馈闭环步骤。归档和 final 发布在用户合并批准与发布条件满足后执行。

## 未测与权限边界

- Windows 交互安装 GUI：NOT RUN。本轮复核没有 WindowsSandbox.exe、未发现 VirtualBox/VMware/QEMU 可用入口；Get-VM 被系统管理权限拒绝，Get-WindowsOptionalFeature 要求提升。不能据此断言机器没有任何不可访问 VM。不得在日常主机运行会替换用户安装/结束用户平台的安装器；开发者保留补测责任。
- Windows 静默安装、重装、PATH、卸载数据保留已有 Preview.13 精确提交及 develop CI PASS；正式版本构建仍重跑。自动安装不冒充交互 GUI 验证。若交互环境仍无法取得，最终合并确认时单列是否接受该验证缺口，不能自行记为放行。
- 反馈仓库仍为 private / allow_forking=false / push=false / pull=true。回复草稿可更新，final 发布后才追加最终解决回复/置 resolved；当前不发送，不把权限问题归为产品开发未完成。
- 用户本轮仅批准推进到合并确认，未批准合入 main、正式发布、删除历史 prerelease 或临时分支。

## 状态

发布准备进行中。用户补充授权解决安装/权限后，已用正常 UAC 启用 Windows Sandbox：Disabled → Enabled，RestartNeeded=true，NoRestart=true；重启前 WindowsSandbox.exe 仍不存在。证据 `output/verification/release18-sandbox-enable.json` 和同名日志。先完成不依赖重启的工作，保存进度后再请求用户保存当前工作并重启；不把“启用成功”当成交互安装测试通过。验证结果、发布 PR 和最终确认项完成后补充。
