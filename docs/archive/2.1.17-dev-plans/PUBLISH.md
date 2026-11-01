# v2.1.17 preview 收尾发布

## 授权与版本

2026-10-31 D-7 用户取消剩余补测并放行收尾。已有全门禁、最终镜像和精确集成
`bc189a3` 的四条 CI 全 SUCCESS；之后仅 docs 变化，产品树不变。
发布必需的构建/完整性/安装验证照常执行，不追加已取消的手测。

- CLI `0.1.10.dev0`，GitHub prerelease/tag `v0.1.10.dev0`，Artifact workflow 在此
  tag dispatch，发布三平台 archive、CLI Windows setup、macOS pkg 和 SHA256SUMS。
- Workbench prerelease/tag `v2.1.17-preview.1`，现有 NSIS tag workflow 自动构建并发布
  Workbench setup 与 SHA256。Workbench 使用现有 SemVer `-preview.N` 契约；
  CLI 继续 `.devN`。两个版本的产品树相同，后续 docs 提交不改变产品字节。
- CLI v* tag 也会匹配 NSIS 的宽泛 tag 触发器。为避免把 CLI 版本写入 Workbench 和
  两个 workflow 争用同一 release，主动取消仅 `v0.1.10.dev0` 的重复 NSIS run；
  Workbench 正常 NSIS 以 `v2.1.17-preview.1` 为准。不取消必要构建/检查或掩盖产品失败。
- CLI GitHub Release 成功后，dispatch `pypi-publish.yml`，输入 `v0.1.10.dev0`；
  验证 TestPyPI wheel/sdist 与真实安装结果，确认正式 PyPI job skipped。
- 两个 tag、TestPyPI 版本先确认不存在，不覆盖引用或同名资产。失败时只按证据修复/重试，
  不 force tag；需要新源码时使用新的 `.devN`。

## 执行账本

- [x] D-7 记录；发布说明与已验证产品树核对。
- [x] 远端两个 tag、对应 TestPyPI 版本不存在。
- [x] CLI annotated tag 已推送：`2c0088d127652d8e11ff1c01f2c7ead59cf52714`。
- [x] Workbench 正确 `-preview.1` annotated tag 已推送，提交 `051157fec4e1a4a895878f6f2c1f8aa4ade535b9`（相对 CLI tag 仅 docs 变化）。
- [x] Workbench preview/NSIS 发布与 SHA256 复核。
- [x] CLI 三平台 archive/setup/pkg/SHA256SUMS 发布复核。
- [x] TestPyPI 发布与真实 index 安装验证；正式 PyPI skipped。
- [x] todo/devlog/发布记录更新，计划归档，develop 同步且工作树干净。

正式 final/main 合并尚未授权；最终反馈 resolved、删除 prerelease 记录与临时分支只在
正式 final 验证后进行。

### 已启动任务

- 首次 Workbench tag 误用了 CLI `.devN` 后缀：`v2.1.17.dev0`，run `41094919913`。
  该 run 已失败，日志明确 `tauri.conf.json > version must be a semver string`。
  `update.rs` 也明确拒绝 dot-dev 标签、Tauri 需要 SemVer，因此不重跑该不适用任务，
  改用既有 `v2.1.17-preview.1`，不改产品解析器、不覆盖或删除旧 tag。此项保留为发布准备错误。
- 正确 Workbench NSIS：`41095888035`，tag `v2.1.17-preview.1`。
- CLI Artifact：`41094996589`，tag `v0.1.10.dev0`，dispatch 已接受。
- 重复 CLI-tag NSIS：`41094919766`，已按上述发布设计主动取消（不是产品测试失败）。

## 发布结果（2026-10-31）

- Workbench：<https://github.com/Wifabric/AISC/releases/tag/v2.1.17-preview.1>，NSIS 与 SHA256 完整，prerelease=true。
- CLI：<https://github.com/Wifabric/AISC/releases/tag/v0.1.10.dev0>，三平台 archive、Windows CLI setup、macOS pkg 与 SHA256SUMS 完整，prerelease=true。
- 两条 Release 的实际 checksum 文本均与 GitHub 对应资产 digest 一致；证据见同目录 release-proof JSON。未下载/运行全部大体积资产，不声称本机重复安装通过。
- TestPyPI：<https://test.pypi.org/project/aisc-cli/0.1.10.dev0/>；wheel/sdist 已可获取，流水线真实 index 安装验证通过，正式 PyPI job skipped。
- publication-ci.json 保存三条发布流水线各步结果；无产品源码或运行时行为变更。main/final 与最终清理保持待独立授权。
- D-7 免补测放行后阶段目标闭环，计划归档；历史 NOT RUN/失败/修正不改写为 PASS。
