# ADR 002: 三轨分发与 PyPI 瘦 wheel（0.1.0）

> **状态**：已接受（0.1.0 周期 D-1~D-6、D-26 裁决集）
> **日期**：2026-09-17
> **决策者**：用户批准（docs/plans/0.1.0-dev-plans/decisions.md；执行蓝本 docs/plans/0.1.0-dev-plans/pypi-release-guide.md）

---

## 背景

AISC 此前只经 GitHub Releases 分发（NSIS 安装器 / 便携包 / macOS PKG）与源码安装。
pip 渠道是 CLI-D01 既定的一等公民目标，但从未发布：核心障碍是 CLI 运行时需要
一棵 repo 形态的「AISC root」（`VERSION` + `container/Dockerfile` +
`config/versions.env`，Docker build context 是整棵树），纯 site-packages 安装按设计
返回 `None`（`resources.py` 的 editable/包祖先发现），用户 `pip install` 后第一条
`aisc build` 即致命失败。

另有两个既成事实：PyPI 上 `aisc` 名下是一个 2019 年起休眠的第三方包（政策不收回
名称）；既有 git tag 为 dash 格式（`v0.1.0-dev`）而 VERSION 与 Release notes 为 dot
格式（`0.1.0.dev0`）。

## 决策

### 1. 三轨分发（路线 C，D-3）

| 轨道 | 载荷 | 适用 |
| --- | --- | --- |
| GitHub Releases frozen bundle | aisc exe + aisc-bundle 全树 | NSIS 安装器 / 便携包 / PKG / sidecar |
| PyPI 瘦 wheel（`aisc-cli`） | 纯 Python，零二进制 | pipx / uv / venv 用户 |
| 源码（editable） | git checkout | 贡献者 |

**路线 B（全载荷入 wheel，~60MB）被否决**，理由：
① mihomo（GPL-3.0）与 geodata（license unknown）进 MIT 标注的 wheel 构成再分发/
政策风险，unknown license 直接违反 PyPI 许可披露要求；② linux-amd64 二进制被
macOS/Windows 用户无谓下载；③ 每版本重传 60MB。
（注：曾考虑的 exec-bit 论据**不成立**——downloads/ 内是 gzip 档案、容器内自理
权限，与 wheel 无关。）

pip 轨道的构建资源由 **`aisc bundle fetch`** 运行时补齐：按精确版本从 Releases 拉
`AISC-<ver>-<plat>-<arch>` 档案，API digest 校验（fail-closed），safe-extract 后
原子装入数据根 `bundles/<ver>/`。离线等效路径：`--from-file`（强制 `--sha256`）/
手动 URL / `--aisc-root` 指向解压目录。

### 2. 分发名与版本（D-2/D-4）

- 分发名 **`aisc-cli`**；import 包与 console script 保持 **`aisc`**（`python -m aisc`
  不变）。`aisc` 裸名被休眠第三方包占用，PyPI 项目名首发后不可原地改名。
- **0.x 表达 Alpha**（推翻指南原推荐的 2.x+契约页）：semver 下 0.x 即「一切可变，
  minor 也可能破坏」，无需额外承诺页。起始号 **0.1.0**。升 1.x 的门槛另行成文。
- sdist 不含 tests/（D-6）；下游验证走 GitHub Release 的 SBOM 与源码 tag。

### 3. 资源解析链六级（3.3.1）

```
--aisc-root > AISC_ROOT env > frozen exe 旁 aisc-bundle/ > cwd 向上找 repo(.git+markers)
  > <data-root>/bundles/<ver>/aisc-bundle（fetch 安装） > 包祖先 markers
```

新层级插在 cwd-repo **之后**（开发者在 repo 内运行 pip 版必须命中工作树，不能命中
旧 bundle）、包祖先**之前**（pip 安装的 root 解析必须先到 fetch 层）。marker 为双形
（repo 形 `src/aisc/VERSION`（A2 迁移后）/ bundle 形根 `VERSION`——bundle 内部布局
是已安装产物契约，不随 repo 演化）。frozen/_MEIPASS 分支原样保留（dual-track 是 CI
既定资产）。manifest 运行时门禁（`bundle_compatible`，精确匹配首版）在层级命中后
校验，不匹配则**跳过该候选继续解析链**，全链失败时错误信息列出「发现 bundle X 但
要求 CLI 版本 Y」。

### 4. 依赖立场修订（对 ADR-001 的增量修正）

ADR-001:45 的 stdlib-only 立场在 CLI 主张 frozen 唯一形态时成立；0.1.0 起 pip 渠道
使运行环境不可控，改为：**三硬依赖（docker/requests/watchdog/argcomplete），全部
真实使用、惰性导入兜底**。requests 为异常分类显式声明（曾借 docker 传递保证）；
docker 加 `<8` major 上界（应用型分发，major 跳变不应无预告砸终端用户）。

### 5. bundle fetch 信任模型（3.3.3）

Release 的 `.sha256` sidecar 与档案**同源生成**，校验只能防传输损坏、不防投毒。
因此：① 校验一律以 **GitHub API 返回的资产 digest** 为准（或 sidecar 与 API digest
一致才放行），结果对用户可见；② 文档措辞为「传输完整性 + GitHub 账号信任」，不写
「供应链签名」；③ 复用 `AISC_GH_API_BASE`/`AISC_GH_API_TOKEN` 旋钮（匿名 60 req/h）。

### 6. 发布纪律（D-26/CLI-D08）

- PyPI 上传 = `pypi-publish.yml` **workflow_dispatch**（输入已存在的 `v*` tag），
  绝不挂在 tag push 自动触发。
- 正式 PyPI 只发 final `X.Y.Z`（job 内正则门）；dev 只上 TestPyPI 且每次迭代
  bump `.devN`（同版本号二次上传永久被拒）+ 先推 dot tag `v<VERSION>`。
- Trusted Publishing（OIDC）零 token；`testpypi`/`pypi` 两个 environment，后者
  Required reviewers（人工审批点）。
- tag==VERSION guard 在 artifact.yml release job 与 pypi-publish build job 双设。

## 后果

- `pip install aisc-cli` 后：`version`/`doctor`（含 aisc-bundle WARN）可用，
  `build`/`docker-rebuild` 需先 `aisc bundle fetch`；`stop`/`run` 等动词降级语义
  见 README（契约测试固化，不改代码）。
- dev 迭代节奏：每次 TestPyPI 上传 = 四件套 bump devN → 提交 → 推 dot tag →
  dispatch。develop 上会出现成串 devN 提交与 tag（已裁决接受，D-26）。
- 每版本数据根 `bundles/<ver>/` 增量 ~60MB；`aisc bundle list/remove` 手工管理，
  fetch 清扫 `.tmp-*` 半途残留，不做自动 GC。
- 若日后引入 CI 产物签名（sigstore/PEP 740 attestation 之外），需新 ADR。

## 关联

- 执行蓝本与实测附录：`docs/plans/0.1.0-dev-plans/pypi-release-guide.md`
- 决策记录：`docs/plans/0.1.0-dev-plans/decisions.md`（D-1~D-6、D-17、D-25~D-27）
- 取代 ADR-001 的分发与依赖部分；ADR-001 的 CLI 架构与 frozen 轨道仍然有效
