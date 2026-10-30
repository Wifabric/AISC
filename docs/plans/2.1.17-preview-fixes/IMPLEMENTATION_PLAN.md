# Preview 修复实施

## 逐批门

每批从最新 develop 独立分支：证据定位 → 回归测试 → 最小修复 → 定向/本地门禁 →
真实数据面 → 生产候选 → Computer Use → 用户单批验收 → 文档/集成。不能将六批堆积验收。
本次工作分支为 `codex/2.1.17-preview-b1-market-envelope`，基线 `7cc5a25`。

## b1

- [x] 用户反馈入 todo、规格和实施计划。
- [x] 复现常驻 serve `cli` 调用 `extensions updates-check` 的空输出，追踪命令出口。
- [x] 添加覆盖真实命令入口的回归（成功、可诊断失败、后续请求/重复调用）。
- [x] 最小协议/调度修复，不吞掉真实失败。
- [x] 定向测试与完整必要门禁。
- [x] 冻结/生产候选与真实容器验证，标识源码/sidecar/镜像。
- [x] Windows CU 覆盖扩展检查更新、独立市场、重复请求及失败后重试。
- [ ] 提交推送与必要远端 CI、记录 PRETEST/HANDTEST，交付用户单批验收。
- [ ] 用户验收或明确放行后集成并进入 b2。

## b2–b6

实施前分别根据 PRD 补充准确文件、回归和实机操作。本轮只登记规格与排期，
不提前跨过上一批验收门。b4 的包大小公开资产/只读归因可以在等待中先收集，
不提前修改打包实现。

## b1 根因与修复边界

本机默认数据根 settings 的 pin 指向 `%LOCALAPPDATA%/AISC Workbench/aisc.exe`。
真实冻结 CLI 报版本 `0.1.9.dev0`，不含 `updates-check`；相同 serve 进程依次发
updates-check/list/updates-check，前后两次稳定返回用户原样空 envelope 错误，
stderr 是 `aisc extensions: ... invalid choice: 'updates-check'`；list 正常返回
runtime-not-found。当前源码与原 closeout 冻结 `0.1.10.dev0` 同请求返回完整协议错误。

1. 对当前 CLI 的 extensions 各级 argparse 传播 JSON 格式，错误参数也返回单个完整
   envelope。未知 op、缺参、不合法字段都不得回到 stderr-only。
2. Rust 在 `updates-check` 的旧 CLI 空输出边界，先用同一目标直连读取准确 argparse
   证据，仅确认缺少该 op 才恢复。Local 非 `--aisc-cli` 显式覆盖时，验证应用附带
   sidecar 并重试这个只读调用，成功后更新旧 pin；本次不实现任意失败自动重试。
3. Remote/显式覆盖/无兼容 sidecar 给可操作升级诊断，不能切换执行机器；权限、
   网络、数据库、未知空输出等保留真实失败。新 CLI 缺参属于参数错误，不能被修复
   成空成功。保留原用户数据根与 workspace，不复制认证或历史数据。
