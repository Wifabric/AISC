# AISC 小版本开发生命流程（交接文档）

> 导出于 2026-09-25。**权威依据是仓库内 `DEVELOP_WIKI.md` §1.1–§1.3**，本文为可直接上手的流程快照，两者冲突时以仓库文档为准。
> 交接背景：2.1.14 已 final（2026-09-24）、CLI 0.1.3 已上 PyPI（2026-09-25）；develop 为干净基线。

## 一、角色与分支

| 引用 | 角色 | 说明 |
| --- | --- | --- |
| `develop` | 开发基线 | 日常开发、集成、验证；push 触发各 CI（按 paths 过滤） |
| `main` | 稳定线 | 只通过 PR 接收已验证变更；无自动构建 |
| `v*` tag | 发布标识 | push tag 触发构建并发布 GitHub Release |

**合并纪律**：阶段分支 → develop 可自主合并；**main 的合并/推送必须经负责人（alan）批准**。纯账本文档（todo / plans / decisions / devlog）可直接落 develop。

**双轨版本**：Workbench（如 2.1.14，`workbench/src-tauri/tauri.conf.json`）与 CLI（如 0.1.3，`src/aisc/VERSION` → PyPI `aisc-cli`）**独立定版、互不联动**。大阶段以 Workbench 版本号命名，一个大阶段内可含多个 CLI 版本迭代。CLI 的 0.x 语义：minor = 功能，patch = 修复/维护。

## 二、生命流程（七阶段）

### ① 开题（立项研究）

- 输入三源：`docs/todo.md` 下一版 target 区；**反馈站仓库**（`E:\Windows\Users\alan\Documents\aisc-issues-feedback`，只看 `issues/` 文件夹，`feedback/` 是杂项无意义）；上一版悬账清单。
- 模糊/高风险项先做调研（多角度调研 + 独立证据核验），不要凭假设排期。
- 产出：重新整理的版本 todo + **U-N 待裁决清单**，逐条报 alan 裁定 → 落成 **D-N 裁决记录**。拿不准就问，严禁按 assumed 默认推进。

### ② 计划落档

- 建 `docs/plans/<版本>-dev-plans/` 文件夹：
  - `README.md`——批次表（批 / 内容 / 分支 / 终态）、阶段范围、流程项；
  - `decisions.md`——裁决日志，每条记**问题 / 裁定 / 影响面**；D-N 阶段内连续编号，U-N 为待用户裁决项（裁定后转 D-N）；
  - 每批一份计划文档（技术路线、验收形态）；
  - `HANDTEST.md`——统一手测清单（见阶段④的四要素）。
- **后续开发永远以文档为准**：代码与文档漂移时，先改文档再改码。

### ③ 批次实施（b1…bN）

- **分支先行**：每批从 develop 切 `<版本>-bN-<主题>` 分支（如 `2.1.14-b6-build-network`），本地门禁 + 远程 CI 全绿后并回 develop。
- **计划外项纪律**：不得自行把未排期项拔高进当前版本；任何新工作项先经 alan 确认排期、落入 todo 本版本 target 区、补计划文档，然后才可实施。**小项同规**（单点修复也要有文档依据）。
- **测试分工**：凡命令行可完成的测试全部由开发者执行并回报结果；alan 只做无法 CLI 化的交互式 UI 验证（按键手感 / 视觉 / 真实 key 端到端）。

### ④ 手测反馈轮

- 推进到**只剩手测反馈**时停下，等 alan 测试。
- HANDTEST 每条必须四要素（这是硬规范，抽象描述不合格——那会把设计成本转嫁给验收人）：
  1. **操作**：编号步骤，精确到 UI 位置或可直接复制执行的命令（PowerShell 形式；路径用变量并给示例值）；
  2. **理想结果（到字段级）**：JSON 写明哪个数组几条、哪个字段取什么值；UI 写明看到什么文案/状态；
  3. **前置准备**：环境状态单独成段（Docker 是否启动、工作区状态等）；
  4. **异常判定**：什么算异常、「记录上报」的触发条件。
- 失败项 triage → 追加修复批次（b7、b8…连续编号），重大形态问题记新裁决；复测通过后该域收口，进下一个验证域。

### ⑤ 收尾（由 alan 宣布触发）

Claude/开发者执行清单：

1. develop 已推送、工作树干净、远程 CI 全绿；
2. `docs/todo.md` 本版条目全部打勾或**显式转期**（不强制打勾）；
3. `docs/devlog.md` 更新到位；
4. 发 **preview 版本**：Workbench tag `v<版本>-preview.N`（CI 产多平台产物 + NSIS 安装器，自动标 prerelease）；CLI 用 `.devN` 走 TestPyPI，**不触正式 PyPI**；
5. plans 文件夹移入 `docs/archive/<版本>-dev-plans/` 归档。

### ⑥ Preview 迭代（质量验证窗）★ 2026-09-25 alan 补充裁定

**preview 阶段的目的是确定本版本的开发是否有问题**：

- 有问题，就在随后的一个 preview 版本中解决；
- preview 期间突发的、target 未规划的**恶性 bug**，也允许在 preview 阶段直接修复——这是「计划外项纪律」的例外通道，**仅限恶性 bug**，修复仍走分支先行并记档；
- 可专为一条验证链路发 preview（如 2.1.14 用同源码打 tag 验证自更新跳变、进度条），每跳装机取证；
- 实例：2.1.14 的 b12 下载超时修复（用户报「参数无效」）、b13 下载进度条，都是 preview 验证中暴露、在 preview 版本内收掉的。

### ⑦ Final 发布（仅 alan 明确要求才发）

- 走 DEVELOP_WIKI §11.2 流程 + main 合并批准门；
- release notes 落 `docs/releases/<版本>.md`；
- **顺序：先 bump CLI 版本，再构建 final 安装器**——让安装器自然携带最新 CLI（2.1.14 教训：顺序颠倒导致装机带旧 CLI 0.1.2）；
- 发布后整理 release 页：命名统一、清理陈旧 release；
- CLI 同周期变更累积发正式 PyPI（用户侧 `pip install -U aisc-cli`）；
- 收口后观察项挂账（断网模拟等专项 + 随日常使用回归的 UI 项）；反馈站条目 status 维护到位。

## 三、关键文件地图

| 路径 | 用途 |
| --- | --- |
| `docs/todo.md` | 版本 target 区 + 悬账清单 |
| `docs/plans/<版本>-dev-plans/` | 当前阶段计划（收口后归档） |
| `docs/archive/<版本>-dev-plans/` | 历史阶段计划 + 裁决记录（decisions.md 是翻旧账的第一站） |
| `docs/releases/` | 每版 release notes |
| `docs/devlog.md` | 开发日志 |
| `DEVELOP_WIKI.md` | 开发者手册：架构 / 调用链 / 契约 / CI / 打包 / 常见修改流程 |
| `E:\Windows\Users\wangyu\Documents\aisc-issues-feedback` | 反馈站：改 md + push 即生效（≤5min）；维护 status 与开发者回复区，`pending` 勿动 |

## 四、CI 工作流（`.github/workflows/`）

`tests.yml`（unittest）· `workbench-ci.yml`（pytest 门禁）· `cli-sidecar.yml` · `nsis-installer.yml`（Windows 安装器）· `bundle-linux-macos.yml` · `artifact.yml`（dispatch-only）· `pypi-publish.yml`（final-only 门，preview 不触正式 PyPI）

## 五、快速验证命令

```powershell
# Python 语法 + 单测
$env:PYTHONPATH="src"; python -m unittest discover -s tests -p "test_*.py" -v

# Workbench 门禁（pytest，忽略 integration）
# 见 DEVELOP_WIKI §9
```

## 六、坑位备忘（2.1.14 实测踩过）

- **vendor/checksums**：改了 `container/` 下任何进 bundle 的文件后必须跑 `tools/vendor-refresh.sh` 重生成 `checksums.txt`，否则 NSIS CI 必挂。
- **macOS CI 是 Bash 3.2**：不支持 `${!var:-}` 间接展开；变量名后紧跟全角字符（中文标点等）会让 Apple 补丁版 bash 报错——echo 行保持 ASCII 分隔。
- **快照测试**：CI 上 venv 路径是 Windows 形态（`.venv/Scripts/python.exe`），要留 `python3`/`python` 回退候选；裸名 python 在 runner 上会解析成 `<root>/python3` 报 ENOENT，只对含 `/` 的路径做 resolve。
- **自更新下载超时**：大载荷（292MB）不能用总时长 30s 的 `client().timeout`，要拆 `connect_timeout(10s)` + `read_timeout(60s)`。

---

*本文档是记忆导出快照，供接手人快速上手；一切以仓库内 `DEVELOP_WIKI.md` 与 `docs/archive/*/decisions.md` 为准。*
