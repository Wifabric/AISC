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

## 验证与权限边界

- Windows 交互安装 GUI：PASS。重启后已在两个独立 Windows Sandbox 完成全新安装、2.1.17 升级、首次启动、卸载取消及默认数据保留；详见 [安装验证](installer-verification.md)。桌面工具故障已恢复，不再是待办。
- Windows 静默安装、重装、PATH、卸载数据保留：正式 NSIS CI PASS。交互与自动验证分别记录，不互相冒充。
- 反馈仓库仍为 private / allow_forking=false / push=false / pull=true。回复草稿已准备；final 发布后才追加最终解决回复/置 resolved，当前不发送。写权限限制属于发布后反馈闭环事项。
- 用户本轮批准推进到合并确认，未批准合入 main、正式发布、删除历史 prerelease 或临时分支。

## 状态

发布准备 PR：[#99](https://github.com/Wifabric/AISC/pull/99)，英文描述，目标 main。安装验证已完成，最终文档提交通过适用 CI、复核 base/head 后转为 ready，等待用户合并确认。产品构建提交 `fc569ed065f88f252f7201a5ad80c3093511b7f6`；后续 `daf37b7ee935f4766c57f90a7faf5b7640bbf011` 仅修正两处旧版本测试数据，产品源码及打包配置没有变化。未合入 main、未创建正式 tag、未发布或上传 PyPI。

### 已完成验证（2026-11-09）

- 本地发布/打包测试：227 passed / 9 skipped；版本同步守卫 PASS。
- 初轮 CI 暴露版本 fixture 与 pairing 测试仍写死 0.1.10，已同步 golden fixture，并将实际版本配对测试改为读取当前版本。定向 Python 49 passed / 19 subtests、前端 6 passed。
- 修正提交的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/42497630786) PASS；[Python 跨平台九组合](https://github.com/Wifabric/AISC/actions/runs/42497703252) PASS。
- 产品构建提交的 [Artifact 三平台](https://github.com/Wifabric/AISC/actions/runs/42496746449)、[Linux/macOS bundle](https://github.com/Wifabric/AISC/actions/runs/42496741867)、[CLI sidecar 三平台](https://github.com/Wifabric/AISC/actions/runs/42496736348) PASS。非 tag 构建的公开发布步骤按设计跳过。
- [NSIS 正式版本构建与安装冒烟](https://github.com/Wifabric/AISC/actions/runs/42496738996) PASS，包含静默安装、重装、PATH 与卸载数据保留；公开发布步骤按分支构建规则跳过。
- 本地冻结 CLI、完整 bundle、正式 NSIS 构建 PASS；实际运行冻结 CLI 报 CLI/bundle 均为 0.2.0。Workbench 为 2.1.18。
- wheel/sdist 构建及 `twine check` PASS。隔离审计环境升级自带旧 pip 后，`pip-audit` 未发现已知依赖漏洞；尚未发布的项目 0.2.0 自身不在 PyPI 数据库，因此跳过该项目项，不冒称审计覆盖产品源码。
- 文档检查 51 passed / 0 warnings / 0 failures。

### 最终收尾与合并门

2026-11-09 已完成隔离 GUI 补测，详见 [安装验证](installer-verification.md)。已验收产品未作额外变更；最终文档提交仅收拢证据并更新历史状态说明。最终精确 head 的 Workbench/Python CI、main 基线、全仓 open PR 与 mergeability 以 PR #99 合并前复核记录为准。构建流水线沿用产品构建提交的 PASS，并核对后续差异仅为测试 fixture 与文档。

用户确认后才能合入 main；正式标签/发布、公开资产校验、反馈最终回复及计划归档仍按发布流程执行，不提前标记完成。main 或产品输入变化时重新评估受影响验证。
