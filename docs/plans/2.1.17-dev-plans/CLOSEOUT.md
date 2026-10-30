# v2.1.17 收尾与统一回归

2026-10-30 用户明确宣布“开始收尾”，并确认“R3、R4 已手测通过，未测项留统一回归”。
此裁定允许集成 R4 并开始收尾；不把未执行项目改成 PASS，也不追溯伪造其它批次用户验收。

## 执行顺序

1. 回写 R3/R4 用户验收，核对并集成 PR #51 到 develop；检查精确集成提交的 CI。
2. 发布前重新查询依赖稳定版本，按 D-4/D-5 记录采用/保留理由；如有实际变化，先补计划再按现有锁版、完整性和镜像验证流程实施。
3. 最终源码全门禁、sidecar/bundle、三平台构建和安装器检查；基于最新产物进行统一回归。
4. 本地 CU 优先复核扩展市场/来源维护、Services、Work Record 阅读和恢复的交叉影响，记录真实 PASS/FAIL/NOT RUN。
5. 发起用户统一回归窗口，列出剩余环境验证项。通过或用户明确延后后，按 DEVELOP_WIKI 发布 preview / TestPyPI 并归档已闭环计划。

## 当前验收与边界

- R3、R4：用户手测通过（本轮明确回复）；R4 两提供商已认证进程/容器中断恢复与原生上下文召回预测试通过。
- b1–b7、R1/R2：已有代码、门禁、CI、容器与部分 CU 证据沿用原记录；本次统一回归不伪造既往逐批验收。
- 全局 Docker 引擎断连、真实大历史、Remote SSH、故障网络/缓存和工作区隔离等未执行项仍是 NOT RUN，汇总后由统一回归完成或显式裁定。
- 不为测试主动退出宿主 Docker Desktop，避免影响其它工作区；不自动处理认证/信任请求。
- 正式 final、main 合并、最终清理反馈/Release/临时分支按开发手册独立门执行；未达门前保持候选状态。

## 检查账本

- [x] 用户宣布收尾，确认 R3/R4 手测通过。
- [x] R4 集成 develop，集成 CI 通过（`81c43e7` 四条 CI 全成功）。
- [x] 发布依赖重查与必要刷新验证（`cf25671`，PR #52 合入 `bc189a3`）。
- [x] 最终门禁、构建与已执行统一预测试（本地门禁/最终镜像/三轮数据面及 CU 已执行项 PASS，develop 四条集成 CI 全 SUCCESS）。
- [ ] 剩余环境/交互项补测或明确裁定（保留 NOT RUN，不以已执行项替代）。
- [ ] 用户统一回归通过 / 剩余项明确裁定。
- [ ] Preview / TestPyPI 发布与产物复核。
- [ ] 计划归档与阶段账本闭环。

## 发布依赖刷新规格（2026-10-30，D-4 原范围）

本轮从 develop 集成提交 `81c43e7` 切 `codex/2.1.17-closeout` 实施。
官方 npm latest 查询选 Codex `0.166.0`、Claude Code `2.1.314`；主包与 Linux
companion 精确配对，沿用 stage_npm.py 的官方 SHA512 与事务替换流程。
Node 官方计划显示 v26 已于 10-28 进入 Active LTS，采用 `26.13.0-bookworm-slim`，
固定官方多平台 index `sha256:bc0a2afd3b74ce12222fc8bab99271e66257f021078f5f4a5d687a77d280c1d9`。
显式 Bookworm 保持现有发行版依赖基础；宿主构建 Node 仍为 22。D-5 的时间空档已结束。

GitHub 认证查询确认 cc-switch `v5.11.3`、Mihomo `v1.19.33`、Yazi `v26.9.1`
仍为稳定最新版，保留已验证 payload。geodata 选 `20261030` 快照，固定 release
commit `10f120b9f0cd1bcae8b8ff88b3f999237b919702`；三份文件必须同时符合官方
Release digest 和固定 commit 字节，不混用可变 latest 数据。

同步 versions.env、Dockerfile 默认 ARG、vendor manifest、payload 与校验账本；
同步 BuildPlan 的缺配置回退默认值；既有固定版本夹具保持原样，仅更新当前默认值断言。
保留 b7 原证据作为回退基线。刷新后执行 vendor verify、依赖/构建回归、全门禁、
真实 no-cache 镜像构建、工具版本与 caveman 首装/显式 off 保留验证。
最终发布构建及 CU 统一回归使用该新 bundle；任一失败先修复再推进。

### 官方来源与已完成校验

- Node：[官方 LTS 计划](https://github.com/nodejs/Release/blob/main/schedule.json)、
  [26.13.0 Bookworm slim 镜像记录](https://github.com/docker-library/repo-info/blob/master/repos/node/remote/26.13.0-bookworm-slim.md)；
  官方 registry 固定 index digest 拉取成功（dockerproxy.net TLS 超时保留为失败尝试）。
- Codex/Claude：官方 npm exact metadata 的 SHA512 均校验成功，主包和 x64
  companion 共四份。详细 SHA256、大小、源地址与 engines 见 closeout-dependency-payloads.json。
- geodata：三份固定 commit 下载字节与 GitHub Release `428580064` 官方 SHA256
  一致，全组验证后事务替换。旧快照可从 b7/develop 父提交恢复。
- cc-switch/Mihomo/Yazi：认证 GitHub latest 查询确认版本未变，资产 SHA256
  与 b7 记录一致。匿名 API 限流/TLS 错误未当成“没有更新”。
- 定向依赖回归 80 passed。首次未激活 dev-env 的调用误导入旧 E: editable
  源码，19 failed/61 passed，已纠正为显式当前 worktree PYTHONPATH；真实重跑 80 passed。
- 首轮全测 1696 passed/1 failed，为仍固定旧发布默认值的测试；更新默认值断言后
  staging/build 定向 48 passed。重跑全门禁：Python 1697 passed/53 skipped/191 subtests，
  Rust 405 passed/1 ignored，Vitest 97 files/822 tests，vue-tsc 通过。
- 冻结 CLI 构建成功。首轮镜像因本轮生成的 geodata checksum 表 CRLF 在 Linux awk
  中匹配失败，规范为 LF 后 frozen CLI no-cache 构建成功；未修改校验算法放宽验证。
- vendor-refresh 第二次报告 9 verified/0 missing；vendor-verify 1533 项通过。
  首次 refresh 报告受 Windows Python stdout CRLF 干扰，使用本机 LF shim 后重跑。
- bundle 首轮拒绝遗留的两处 caveman 测试 __pycache__；确认均为未跟踪生成缓存并清理后，
  stage/verify 与版本检查通过。最终干净 bundle 无缓存镜像构建和统一预回归已执行，见下文。

## 收尾候选与统一回归交付（2026-10-31）

- [CLOSEOUT-PRETEST.md](CLOSEOUT-PRETEST.md) 记录最终产物 hash、镜像 ID、真实
  容器 12 phases/三轮 9/9 全 PASS、Services 双端口 HTTP、市场/来源/阅读 CU 与 NOT RUN。
- 本地 clean-room wheel/sdist/pipx/重复安装/off-checkout 全部 PASS；最终镜像为
  `super-claude:2.1.17-closeout-final @ sha256:7f82194edeeda7a2668a071c73ba63c92f99485ebb95aafb06807c03b7377e64`。
- 产品 SHA `cf25671` 的 Workbench CI、三平台 sidecar、deb/dmg、NSIS 均 SUCCESS，
  已核对实际 artifact 元数据与安装/解包 smoke；[远程证据](closeout-ci-evidence.json)。
- PR [#52](https://github.com/Wifabric/AISC/pull/52) 已合入 develop `bc189a3`。
  精确集成 CI：Workbench `41089936055`、sidecar `41089936117`、
  Bundle `41089936114`、NSIS `41089936325` 全部 SUCCESS；
  [集成证据](closeout-integration-ci-evidence.json) 包含实际 artifact 和每步结果。
  随后的收尾记录提交仅修改 docs，产品树与该已验证集成提交一致；未触发路径过滤之外的重复构建。
- [HANDTEST.md](HANDTEST.md) 文首 C0–C5 替换旧 R2 入口；本地启动器
  `release-staging/2.1.17-closeout/start-handtest.ps1 -VerifyOnly` 校验成功；当前真窗口
  保留给用户整体回归。旧 b5 专用副本仅验证交互合同，不能冒充当前候选安装包。
- 用户统一回归和剩余环境项裁定尚未完成；preview/TestPyPI、归档、main/final 与最终清理
  保持各自门，不提前关闭反馈或删除历史分支/tag。
