# v2.1.17 preview 收尾发布

## 授权与版本

2026-10-31 D-7 用户取消剩余补测并放行收尾。已有全门禁、最终镜像和精确集成
`bc189a3` 的四条 CI 全 SUCCESS；之后仅 docs 变化，产品树不变。
发布必需的构建/完整性/安装验证照常执行，不追加已取消的手测。

- CLI `0.1.10.dev0`，GitHub prerelease/tag `v0.1.10.dev0`，Artifact workflow 在此
  tag dispatch，发布三平台 archive、CLI Windows setup、macOS pkg 和 SHA256SUMS。
- Workbench prerelease/tag `v2.1.17.dev0`，现有 NSIS tag workflow 自动构建并发布
  Workbench setup 与 SHA256。两个 annotated tag 指向同一已同步 develop 提交。
- CLI v* tag 也会匹配 NSIS 的宽泛 tag 触发器。为避免把 CLI 版本写入 Workbench 和
  两个 workflow 争用同一 release，主动取消仅 `v0.1.10.dev0` 的重复 NSIS run；
  Workbench 正常 NSIS 以 `v2.1.17.dev0` 为准。不取消必要构建/检查或掩盖产品失败。
- CLI GitHub Release 成功后，dispatch `pypi-publish.yml`，输入 `v0.1.10.dev0`；
  验证 TestPyPI wheel/sdist 与真实安装结果，确认正式 PyPI job skipped。
- 两个 tag、TestPyPI 版本先确认不存在，不覆盖引用或同名资产。失败时只按证据修复/重试，
  不 force tag；需要新源码时使用新的 `.devN`。

## 执行账本

- [x] D-7 记录；发布说明与已验证产品树核对。
- [x] 远端两个 tag、对应 TestPyPI 版本不存在。
- [ ] 同提交 annotated tags 已推送。
- [ ] Workbench preview/NSIS 发布与 SHA256 复核。
- [ ] CLI 三平台 archive/setup/pkg/SHA256SUMS 发布复核。
- [ ] TestPyPI 发布与真实 index 安装验证；正式 PyPI skipped。
- [ ] todo/devlog/发布记录更新，计划归档，develop 同步且工作树干净。

正式 final/main 合并尚未授权；最终反馈 resolved、删除 prerelease 记录与临时分支只在
正式 final 验证后进行。
