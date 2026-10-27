# b7 依赖版本证据（2026-10-27）

官方来源查询时间：2026-10-27 09:32–10:07 UTC；实际下载校验与镜像兼容性在执行后补记。没有把镜像源返回成功等同官方完整性通过。

| 依赖 | 所选稳定版本 | 官方来源 | 回退版本 |
| --- | --- | --- | --- |
| Node.js | 24.22.1-slim（D-5） | [官方 slim 镜像记录](https://github.com/docker-library/repo-info/blob/master/repos/node/remote/24.22.1-slim.md)、[Node 校验表](https://nodejs.org/dist/v24.22.1/SHASUMS256.txt) | node:22-slim（旧版未固定 digest） |
| Codex CLI | 0.164.0 | [npm latest](https://registry.npmjs.org/-/package/@openai%2Fcodex/dist-tags) | 0.154.0 |
| Claude Code CLI | 2.1.311 | [npm latest](https://registry.npmjs.org/-/package/@anthropic-ai%2Fclaude-code/dist-tags) | 2.1.273 |
| cc-switch-cli | v5.11.3 | [官方 release](https://github.com/SaladDay/cc-switch-cli/releases/tag/v5.11.3) | v5.10.5 |
| Mihomo | v1.19.33 | [官方 release](https://github.com/MetaCubeX/mihomo/releases/tag/v1.19.33) | v1.19.27 |
| yazi | v26.9.1 | [官方 release](https://github.com/sxyazi/yazi/releases/tag/v26.9.1) | v25.2.26 |
| geodata | AISC 快照 20261027 | [固定数据 commit](https://github.com/MetaCubeX/meta-rules-dat/commit/02ae05ac06e8c9287916fbabfe61ef5c8591407f) | 本批父提交保存的旧 latest 字节 |

Node 官方多平台 index digest：`sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205`；amd64 manifest `sha256:2dd9a4f758e173b65fee15388f7706af6fb01ef50cf7a2c0538711d67a6981ae`；arm64/v8 manifest `sha256:294d33a992da016e059121deb0c979dffb4478b77a304376bca41393297c1ea2`。dockerproxy.net 已通过固定 index digest 拉取；1ms/daocloud 本轮超时。宿主开发 Node 保持 22。

| GitHub 资产（linux amd64/x64） | 官方 SHA256 |
| --- | --- |
| cc-switch-cli-v5.11.3-linux-x64-musl.tar.gz | `42531873444c8b3b41ac5969a70752550ef4c307438d7ca7ee45bcddf201061c` |
| mihomo-linux-amd64-v1.19.33.gz | `132f6f3edf9a65e62f04853aed3358472e0b2b7666daa8419edfa2ddf5bb6323` |
| yazi-x86_64-unknown-linux-musl.zip | `9b9c39decccf8cb0ff53a7d637d38f8a79d93bbd0099f4ea9c619ef6bb392f5d` |
| country.mmdb | `ccec4d6fa69de3a79960a460c377ac9a23c1a90e5f9052dae3488921e56201df` |
| geoip.metadb | `f74179989befc93862f7bad4e32ac2ef2e1073b99b5c40483ec8007387df7362` |
| geosite.dat | `c57333596b44aa061e84c3c224e97a4475c759a5e3baab1fcda002e48b4dc313` |

geodata 上游 release ID 为 `424945622`（2026-10-27T01:36:02Z）。上游没有日期 tag，latest/release 分支可变；AISC 日期是快照标识，不能用于构造上游 release tag URL。三文件均取同一完整数据 commit，保留 vendor 字节和三项 checksum。

npm 主包与 Linux companion 以精确 registry metadata 的 `dist.integrity`（SHA512）验证后落盘；Codex companion 是同包平台后缀版本的 npm alias。Codex 要求 Node >=16，Claude 要求 Node >=22，所选 Node 24 满足。实际 payload SHA256/大小与 npm integrity 随 staging 证据补记。

cc-switch 的 SQLite schema 22 迁移可能阻止旧 CLI 读取新 DB。兼容性实验使用隔离配置；真实升级回退必须同时恢复迁移前 DB 备份与旧工具版本，不能只换回二进制。不得删除上游生成的迁移备份。

Debian apt 工具继续从所选稳定基础镜像的 Bookworm 仓库安装；构建后记录实际 dpkg 版本，不把 apt 未固定版本称为完全可复现。

## 实际字节与兼容性（2026-10-27）

- 六份 GitHub/geodata 与四份 npm 字节实际校验 PASS；完整 SHA256、SHA512 integrity、大小和下载源见 dependency-payloads.json。当前本地 bundle 为 linux amd64/x64 闭包；双架构选择路径有隔离回归，未声称本机执行过 arm64 二进制。
- 新镜像 `super-claude:2.1.17-b7`：`sha256:25f42e5157fd74eb7c2ae9add4d2857c6f83a46a59857b9a2b5730011a693f44`。冻结 CLI 执行 `build --no-cache --require-pin --cc-switch-manifest config/cc-switch-manifest.json` 成功，预拉严格验证 Node index digest，cc-switch build receipt 标明 manifest 来源；最新查询另由实时 API 验证。
- 镜像内实际输出：Node v24.22.1；codex-cli 0.164.0；Claude 2.1.311；cc-switch 5.11.3；Mihomo v1.19.33；Yazi 26.9.1。新 cc-switch 下 caveman 首装/重启/内容升级/缺行/重装五路径全部 PASS，升级显式 off 保留。
- 三份 geodata 在最终镜像中重算 SHA256 与表中完全一致。8 份 Git 跟踪 payload 的 index 字节与下载字节完全相同。
- Debian Bookworm 实装：curl 7.88.1-10+deb12u15，git 1:2.39.5-0+deb12u3，python3 3.11.2-1+b1，tmux 3.3a-3，neovim 0.7.2-7，ripgrep 13.0.0-4+b2，zsh 5.9-4+b15。以上为所选发行版仓库的稳定软件包版本。
