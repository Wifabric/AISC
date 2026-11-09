# 2.1.18 正式发布准备

## 当前授权与状态（2026-11-09）

用户已验收整版及 Preview.13，PR [#99](https://github.com/Wifabric/AISC/pull/99) 已按用户确认合入 main `07d6835c2a0018690ae769c39b7d386f58bbc728`。隔离交互安装已通过，旧“待重启/待 main 批准”状态结束。用户随后批准交付补全，并明确要求正式发布前确认重要内容，得到同意后再发布；此要求覆盖此前 final 时机委托。

本轮从 develop `9a83cbc6` 创建 `codex/2.1.18-delivery-closeout`，同步已批准 main 后补全文档。由同一代理执行与自查，不称独立评审。正式 tag、GitHub Release、TestPyPI/PyPI 上传和反馈 resolved 均未执行。

## 待确认的具体发布内容

| 项目 | 准备内容 |
| --- | --- |
| Workbench | 2.1.18；Windows x86_64；正式 tag `v2.1.18`，只在已核对的 main 提交上创建 |
| CLI | 0.2.0，serve protocol 4；随 Workbench 提供；独立正式 tag `cli-v0.2.0`，通过 PyPI `aisc-cli` 分发 |
| 功能范围 | F1–F8/b1–b10、离线通用技能、在线科研/开发模块、个人能力迭代、S16 主题体验、开发流程/Skill；无新增工具升级或跨平台桌面发行承诺 |
| 发布说明 | [Workbench](../../releases/v2.1.18.md)、[CLI](../../releases/v0.2.0.md)；README 已按实际入口更新 |
| Workbench 资产 | `AISC-Workbench-2.1.18-setup.exe` 与 `.sha256`；正式 Release 非 draft/prerelease，核对 Latest、公开下载和更新发现 |
| CLI 渠道 | wheel/sdist 的守卫、TestPyPI 安装验证、实际 environment 审批、正式 PyPI 及安装验证；不附独立 CLI 安装器/归档/SBOM 到 Workbench Release |
| 反馈 | 本版 F1–F8 八条；[最终回复草稿](feedback-replies-draft.md) 仅在发布验证后追加，当前未发送 |

## 开发者准备清单

- [x] 对照 WIKI、交接、职责、Skill、D-8 后续裁定、本版 35 文件和当前发布渠道界定范围。
- [x] 更新用户教程、现行流程、devlog/TODO 与阶段当前状态，保留历史测试的真实结果。
- [x] 准备八条反馈的具体最终文案和仅本地可审查补丁；写入前仍须复读最新文件及权限。
- [x] 本轮文档检查 51 PASS / 0 warnings / 0 failures；49 份变更文档的 247 个相对链接/锚点通过；CLI 正式 tag 版本守卫和 git diff --check 通过。个人能力/会话现有测试 53 passed / 1 skipped；最初共享 venv 命中其他工作树，指定本工作树 PYTHONPATH 后重跑通过。打包与远端 CI 另列。
- [ ] 文档收尾集成到 develop/main，记录精确提交与 PR。
- [ ] README 属于 bundle 输入，须生成包含新 README 的非发布 NSIS 候选并核对，不能把旧安装包标成新提交构建。
- [ ] 汇总验证、资产标识与遗留项，提交用户最后发布确认。

## 已完成的产品与安装验证

用户功能验收已完成，本轮不改变功能代码、依赖 pin 或 installer 模板；修正 README 和内置主题 Skill 的接入文字，明确普通会话不绑定主题。两者属于打包输入，因此重建候选。已有功能/交互安装证据按不变代码沿用，新候选构建/安装冒烟另外登记，不将旧文件哈希当作新包。

- Windows 交互安装 GUI：两个独立 Windows Sandbox 的新装、2.1.17 升级、首次启动、取消卸载、默认数据保留及 PATH，PASS，见 [安装验证](installer-verification.md)。guest 无 Docker，因此不声称在该 guest 测过真实 Docker 删除。
- Preview.13：Python 1843 passed / 74 skipped，Rust 422 passed / 2 ignored，前端 901 passed；真实进程上下文隔离和 GUI 子集见 PROGRESS/preview-gui；这些是对应候选的历史证据。
- main `07d6835c` 的 [Workbench](https://github.com/Wifabric/AISC/actions/runs/42502975879)、[NSIS](https://github.com/Wifabric/AISC/actions/runs/42502975841)、[sidecar](https://github.com/Wifabric/AISC/actions/runs/42502975813)、[Linux/macOS bundle](https://github.com/Wifabric/AISC/actions/runs/42502975882) 成功。NSIS release job 在分支构建按设计跳过。

### 已完成验证（2026-11-09）

- 本地发布/打包测试：227 passed / 9 skipped；版本同步守卫 PASS。
- 初轮 CI 暴露版本 fixture 与 pairing 测试仍写死 0.1.10，已同步 golden fixture，并将实际版本配对测试改为读取当前版本。定向 Python 49 passed / 19 subtests、前端 6 passed。
- 修正提交的 [Workbench CI](https://github.com/Wifabric/AISC/actions/runs/42497630786) PASS；[Python 跨平台九组合](https://github.com/Wifabric/AISC/actions/runs/42497703252) PASS。
- 产品构建提交的 [Artifact 三平台](https://github.com/Wifabric/AISC/actions/runs/42496746449)、[Linux/macOS bundle](https://github.com/Wifabric/AISC/actions/runs/42496741867)、[CLI sidecar 三平台](https://github.com/Wifabric/AISC/actions/runs/42496736348) PASS。非 tag 构建的公开发布步骤按设计跳过。
- [NSIS 正式版本构建与安装冒烟](https://github.com/Wifabric/AISC/actions/runs/42496738996) PASS，包含静默安装、重装、PATH 与卸载数据保留；公开发布步骤按分支构建规则跳过。
- 本地冻结 CLI、完整 bundle、正式 NSIS 构建 PASS；实际运行冻结 CLI 报 CLI/bundle 均为 0.2.0。Workbench 为 2.1.18。
- wheel/sdist 构建及 `twine check` PASS。隔离审计环境升级自带旧 pip 后，`pip-audit` 未发现已知依赖漏洞；尚未发布的项目 0.2.0 自身不在 PyPI 数据库，因此跳过该项目项，不冒称审计覆盖产品源码。
- 文档检查 51 passed / 0 warnings / 0 failures。


## 发布后执行，不能提前勾选

- [ ] 得到用户对上述具体材料的明确发布同意。
- [ ] Workbench 正式 tag/Release/Latest、下载哈希、随包版本与更新发现验证。
- [ ] CLI 正式 tag、TestPyPI/PyPI 流程及实际索引安装验证。
- [ ] 获得反馈仓库写权限或由有权限维护者应用补丁；发布成功后更新八条，复核列表/详情缓存结果。
- [ ] 回填最终发布事实，归档已完成阶段并修正引用；未完事项明确交接，不用归档隐藏。
- [ ] 同步长期分支；确认本阶段分支无独有成果及占用再清理；当前没有 prerelease Release 可清理，不动稳定 tag。
- [ ] 发布后按 WIKI 开启下一 CLI 开发号（当前规则为 0.2.1.dev0），不改稳定 tag；交付完整链接清单。

## 已知边界与外部条件

- 反馈仓库 `Wifabric/aisc-issues-feedback` 当前仅 pull 权限，不能本机提权解决；补丁准备不等于已回写。原文、投票、附件及旧回复必须保留。
- 真实多人协作未实测；本版交付流程规则/Skill和单代理实际执行，团队试用仍是后续事项，不标 PASS。
- 插件当前仅 Claude；远程镜像重建入口禁用；GitHub MCP 实际访问需要用户本人有效授权。现有用户验收不等于任意凭据均可访问任意仓库。
- 独立 pip CLI 是薄包，不包含镜像构建资源。本版不补发独立 CLI 归档；构建需对应源码/资源或 Workbench bundle，不能承诺 `bundle fetch` 自动取得不存在的资产。
- 自动化跳过/自然竞态未复现等沿用原报告边界。正式发布后的实际下载/更新与索引验证只能发布后执行，当前不预写 PASS。
