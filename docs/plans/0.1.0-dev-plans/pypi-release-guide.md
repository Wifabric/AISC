# AISC CLI 作为 pip 包发布:改动清单与风险指南

> 状态:指导文档(未执行) · 基线:VERSION `2.1.11.dev0` · 编制日期:2026-09-14
> 方法学:6 个子系统并行读取 + 6 维度分析 + 逐条对抗核实 + 完整性审查,共 58 条 findings(全部经代码级核实确认)+ 11 条补充缺口;关键断言(sdist 自包含性、wheel 元数据、PyPI 名称占用)为本机实测。文末附录 A 列出全部实测命令与结果。
> 落位说明:本文是**分析结论与执行指南**。真正启动发布时,可按 repo 惯例将执行部分迁入 `docs/plans/pypi-release/`(七要素骨架),本文的长期事实应同步沉淀到 README / DEVELOP_WIKI / ADR,避免双份漂移。

---

## 0. 结论速览

**结论:可以发布,但不是"改个名字就传上去"。** 包工程基础出人意料地好——wheel/sdist 今天就能构建、CI 已有 clean-room 安装冒烟、Stage-2 dual-track 早已把 pip/pipx 定为一等公民。真正的问题集中在三处:

1. **核心架构缺口(blocker)**:CLI 运行时需要一棵 repo 形态的 "AISC root"(VERSION + `container/Dockerfile` + `config/versions.env` 三个结构标记,Docker build context 是整棵树)。纯 site-packages 安装按设计返回 `None`(`src/aisc/application/resources.py:115-204` 的 docstring 自己写明 "ordinary site-packages wheels return None"),导致用户 `pip install` 后第一条 `aisc build` 即致命失败。**今天发布即产出坏包。**
2. **PyPI 名称已被占用(blocker)**:`aisc` 名下是一个 2019 年起休眠的第三方包("AISC Helper Tools" v0.1.10,最后上传 2019-07-03),PyPI 政策不因休眠收回名称。用户照直觉 `pip install aisc` 会装到**别人的包**。候选 `aisc-cli` 已验证空闲。
3. **版本/tag 格式漂移(high)**:既有 git tag 是 dash 格式(`v2.1.11-dev`)而 VERSION 与 release notes 是 dot 格式(`2.1.11.dev0`),`artifact.yml:359` 的 `body_path` 只有 dot tag 能对上文件;dev 版若误上 PyPI 且 PEP 440 下该项目尚无 final,会成为所有用户的默认安装。

**推荐总体路线(路线 C)**:瘦 wheel(纯 Python,零二进制载荷)+ 新增 `aisc bundle fetch` 运行时从 GitHub Releases 下载同版本 bundle 到 data root + 资源解析链新增 data-root 层级。GPL/unknown-license 载荷(mihomo GPL-3.0 + geodata,38MB linux-amd64 二进制)**绝不进 PyPI 制品**——继续走 GitHub Releases,由 fetch 获取。

**最小可发布路径(若不实现 fetch)**:瘦 wheel + 文档化的"降级模式"(`--aisc-root`/`AISC_ROOT` 指向手动获取的 bundle)+ README 醒目预告。可行但体验差,只应作为路线 C 的离线兜底而非首发定位。

**分批改动量**:批次一(元数据)S · 批次二(VERSION 迁移)M,约 14 个触点 · 批次三(资源模型)L · 批次四(发布流水线)M · 批次五(文档治理)S–M。

---

## 1. 现状盘点:哪些已经就绪

| 已就绪 | 证据 |
|---|---|
| wheel/sdist 构建链完整,`python -m build` 直接可用 | `dist/` 已有 `aisc-2.1.11.dev0-py3-none-any.whl`;纯 Python、py3-none-any |
| sdist 自包含:含 VERSION(170 文件:src 树+VERSION+LICENSE+README+pyproject),从 sdist 重建 wheel 版本号正确 | 附录 A 实测 |
| console script `aisc = aisc.cli.main:main` 存在且零参可调;`python -m aisc` 同样支持 | `pyproject.toml:33-34`;`src/aisc/cli/main.py:2302`;`src/aisc/__main__.py` |
| CI 已有 wheel+sdist clean-room 安装冒烟(安装/重装/卸载/pipx)+ PEP 440 版本一致性断言 + 25 命令 pip-vs-frozen parity + SBOM | `scripts/verify-cli-install.py`;`.github/workflows/workbench-ci.yml:126-129`;`cli-sidecar.yml:84-119` |
| 全部可写状态走用户 data root(`%LOCALAPPDATA%\AISC\data` / XDG),无 repo 相对写入;用户配置在 APPDATA/XDG/`~/.aisc`,repo 的 `config/*.json` 运行时不读 | `src/aisc/application/data_root.py:60-68` |
| 三个声明依赖全部真实使用且惰性导入;PyYAML 仅测试用(已在 dev extra) | `pyproject.toml:26,37` |
| 制品面干净:wheel 实测只含 `src/aisc` + VERSION,零第三方二进制;人工扫描未见真实密钥 | 附录 A;`.gitleaks.toml` |
| 决策依据已存在:Stage-2 CLI-D01"用户可独立 pip/pipx 使用"已接受并验收通过 | `docs/archive/completed/aisc-next/stage-2-cli-dual-track/` |

---

## 2. 必须先拍板的决策点

以下 5 项是单向门或全局性决策,应在动手前定死;每项给出推荐。

### D-1 分发名(blocker,单向门)
- 事实:`aisc` 已被占用(休眠,不可收回);`aisc-cli` 空闲。PyPI 项目名一经发布不可原地改名;pending publisher **不占名**,决策到首发之间有抢注窗口。
- **推荐:分发名 `aisc-cli`,console script 与 import 包保持 `aisc` 不变。** 备选名(如 `aisc-workstation`)必须同样满足"分发名 ≠ aisc、script = aisc"结构。
- 连带必改(改名提交一次落地,漏一处断链):
  - `pyproject.toml:6` → `name = "aisc-cli"`
  - `src/aisc/__init__.py:35` `metadata.version("aisc")` → 只查 `"aisc-cli"`(frozen 产物无 dist-info,旧名兜底无价值;若环境残留 PyPI 休眠包 `aisc` 反而会读出陌生版本)。加单测:包内 VERSION 文件全缺时 fallback 必须返回真实版本而非 `0+unknown`。
  - `scripts/verify-cli-install.py:86`(`metadata.version('aisc')`)与 `:137`(`pip uninstall aisc`)
  - `scripts/verify-sbom.py:31`(`m.requires('aisc')`)与 `:76`(SBOM 输出 `"project": "aisc"`)
  - README `uv tool uninstall aisc` 等口径(:121-129)
  - 建议提取模块级 `DIST_NAME` 常量或统一从 importlib.metadata 读取,一次消除四处字面量
  - **注意不要改过头**:`python -m aisc`(包名)、`aisc.exe`/entry 文件名(script 名)保持 `aisc`。
- 所有对外文档禁用裸 `pip install aisc`,首段写"pip install aisc-cli, 然后运行 aisc"。

### D-2 资源模型路线(blocker,架构决策)
三条路线对比:

| 路线 | 内容 | 判定 |
|---|---|---|
| A. 瘦 wheel + 降级文档 | pip 用户 `build` 不可用,需手动取 bundle 并 `--aisc-root` | 仅作兜底,不作主路线 |
| B. 全载荷入 wheel(~60MB) | container/ 全树(含 GPL/unknown 二进制)进 PyPI 制品 | **否决**,理由记录进 ADR(见 4.2) |
| C. 瘦 wheel + `aisc bundle fetch` | PyPI 发纯 Python;fetch 从 GitHub Releases 取同版本 bundle 到 data root | **推荐** |

- 否决 B 的依据:① mihomo(GPL-3.0)与 geodata(license unknown)进 MIT 标注的 wheel 构成再分发/政策风险,unknown license 直接违反 PyPI 许可披露要求;② linux-amd64 二进制被 macOS/Windows 用户无谓下载;③ 每版本重传 60MB。注意:gitleaks allowlist 实际只排除 `container/_bundle/`、`docs/`、`vendor/`(`.gitleaks.toml:4-8`),`container/downloads/` 照常被扫描。
- 路线 C 的版本纪律:**PyPI 只发 final X.Y.Z**(dev 只上 TestPyPI),bundle 资产由既有 `artifact.yml` tag 流水线保证同版本存在。dev 版本(如 `2.1.11.dev0`)永远没有对应 release 资产,fetch 按精确版本匹配不到 → fail-closed 并提示 `--version` 显式指定。

### D-3 版本兼容承诺(semver)
现状:2.x 版本号 + Alpha classifier("契约仍可能变化")——上 PyPI 后这个组合本身向用户暗示稳定。**推荐:维持 2.x,配一页显式契约文档**(改 0.x 对四渠道存量用户代价大于收益):
- CLI flag 与 `--format json` envelope 按 semver 兼容,破坏性变更必须升 major;
- 配置/state 契约沿用 `data_migration` 兼容机制并在 Release Notes 声明;
- `compatible_cli_versions` 匹配语义首版取**精确匹配**(见 3.3.2),与承诺一页写死。

### D-4 PyPI 长描述内容(readme = README.md 即项目首页)
- 两处相对链接在 PyPI 必然 404:README.md:10 `[VERSION](VERSION)`、:328 `[LICENSE](LICENSE)` → 改绝对 URL。
- `## 推荐服务`(:330-363)含返佣/邀请推广链接,**将原样出现在公开 PyPI 包首页**。**推荐:面向 PyPI 的 readme 去掉该小节**(独立 README-PYPI.md 或发布 checklist 注明);这是观感与信任问题,twine check 不会发现。
- metadata description 是英文而正文纯中文且以 Workbench 为主线 → 首发时确认语言一致性与 CLI 场景落地页适配。

### D-5 sdist 是否含 tests
无 MANIFEST.in,默认 sdist 不含 tests/。**推荐 v1 不含**(维持最小 sdist,下游验证走 GitHub Release 的 SBOM 与源码 tag);若要含,配 MANIFEST.in 并把决策记入新 ADR。

---

## 3. 改动清单(按批次)

### 3.1 批次一:包元数据与依赖(`pyproject.toml`)

| # | 改动 | 依据 |
|---|---|---|
| 1 | `name = "aisc-cli"`(D-1) | PyPI 占名 |
| 2 | `license = { text = "MIT" }` → `license = "MIT"`(SPDX);新增 `license-files = ["LICENSE"]`;**删除** classifier `License :: OSI Approved :: MIT License`(与 License-Expression 互斥);`build-system` requires 提到 `setuptools>=77`(字符串 license 需 ≥77 解析) | setuptools 84 实测告警:`project.license as a TOML table is deprecated — By 2027-Feb-18` + `License classifiers are deprecated` |
| 3 | dependencies 显式加 `requests>=2.26`(三处直接 import 用于异常分类,靠 docker 传递是借来的保证);`docker>=7.1` 加 major 上界 → `docker>=7.1,<8`(应用型分发,major 跳变砸终端用户);watchdog/argcomplete 下界不动、不设上界 | `src/aisc/adapters/docker_gateway.py:336,784`;`docker_.py:503` |
| 4 | 删除 classifier `Programming Language :: Python :: 3.14`(tests 矩阵只到 3.13,3.14 宿主有已知流式测试挂点;矩阵扩绿后再加回);`requires-python >= 3.11` 不动 | `pyproject.toml:18-21`;`.github/workflows/tests.yml:12`;`DEVELOP_WIKI.md:54,161` |
| 5 | watchdog/argcomplete **维持硬依赖不拆 extras**——降级路径为 frozen 轨道而设,拆分只增加支持噪音(明确的不改动决策,记录关闭议题) | `main.py:2330-2339`;`serve_fs.py:232-246` |
| 6 | `[project.urls]` 可选补 `Bug Tracker` 与 `Security`(GitHub Security Advisories);authors 不补个人邮箱(隐私),联系渠道靠 urls + repo 根新增 SECURITY.md | `pyproject.toml:12,28-31` |
| 7 | wheel 与 sdist **双发**(wheel 主产物,sdist 供审计/回退;publish job 在全新 runner 构建产物,勿复用 cli-sidecar 的 dist/——那里混有 frozen exe) | 附录 A |
| 8 | offline 冒烟若启用:offline deps dir 需备 setuptools≥77 的 wheel(否则 `--no-build-isolation` 构建挂) | verify-cli-install.py:111-117 能力已存在 |

### 3.2 批次二:VERSION 迁移为 package-data(约 14 个触点,漏一处断链)

**问题**:现状 `[tool.setuptools.data-files] aisc = ["VERSION"]` 把 VERSION 装到 `<sys.prefix>/aisc/VERSION`(site-packages 之外);`pip install --user` 时实际落 USER_BASE 而代码探针只查 `sys.prefix` → miss,靠 importlib.metadata 兜底救回;与改名耦合后兜底探针也会失效,`--user` 安装将报 `0+unknown`。

**改动**:`git mv VERSION src/aisc/VERSION`;pyproject 删 `[tool.setuptools.data-files]`,改 `[tool.setuptools.package-data] aisc = ["VERSION"]`。代码侧 `__init__.py:19` 已有 `Path(__file__).with_name("VERSION")` 候选,迁移后成为必然命中项,根治。

**必须逐一同步的触点**(核实方与怀疑者合并清单):

| 触点 | 说明 |
|---|---|
| `packaging/aisc.spec:22` | `--add-data` 路径改 `src/aisc/VERSION`(仍落 _MEIPASS 根,`__init__.py:15` 候选不变) |
| `.github/workflows/artifact.yml:48,54` | 两处 `--add-data VERSION:.` |
| `.github/workflows/artifact.yml:51,97,136` | `--expected-version-file VERSION`、Inno `Get-Content VERSION`、macOS pkg `head -1 VERSION`(易漏) |
| `packaging/artifact.py` | stage 读根 VERSION(:41-42 附近);**repo-root 发现 marker** `:771/:776` 以 `(p/"VERSION").is_file()` 判根,需同步改 |
| `src/aisc/application/resources.py:27` | `_STRUCTURE_MARKERS` 的 `"VERSION"` 改 `"src/aisc/VERSION"`(否则 repo/editable root 识别失效;`_is_root` 用 path/marker 拼接,支持子路径) |
| `src/aisc/__init__.py:20` | `parents[2]/VERSION` 候选失效——无害(with_name 在前兜住),记录或顺手清理 |
| `src/aisc/__init__.py:21` | `sys.prefix/aisc/VERSION` 探针保留一版作旧安装残留兜底 |
| `tests/test_version_source.py` | :34-36 硬断言 pyproject 含 data-files 配置(**必红**,改断言 package-data);:20/:31 读 `PROJECT_ROOT/"VERSION"` 路径改 `src/aisc/VERSION` |
| `scripts/verify-cli-install.py:192` | 读根 VERSION 处 |
| `scripts/build-cli.ps1:71` | 拷贝源 |
| `tests/packaging/test_release_notes.py:21` | 读根 VERSION |
| `DEVELOP_WIKI.md:560-568,666,718,843` | "只改根 VERSION"发版契约文档 |
| 可选加固 | 动态版本可从 `{attr = "aisc.__version__"}` 改 `{file = "src/aisc/VERSION"}`,切断构建期对 `__init__` 的 import(避免 `--no-build-isolation` + 环境已装旧版的漂移通道) |

**验收**:跑通 `scripts/verify-cli-install.py`(wheel+sdist+pipx 全腿)+ `tests/packaging/` 全套。sdist 自包含性由 package_data 同进 sdist/wheel 保持(attr 从 sdist 构建靠 with_name 候选命中)。

### 3.3 批次三:资源模型落地(路线 C)

#### 3.3.1 解析链新增 data-root 层级
`locate_aisc_root()` 从五级变六级,新层级插在 **cwd-repo 之后、包祖先之前**:

```
--aisc-root > AISC_ROOT env > frozen exe 旁 aisc-bundle/ > cwd 向上找 repo(.git+markers)
  > 【新】<data-root>/bundles/<ver>/aisc-bundle > 包祖先 markers
```

- 放 cwd-repo 之前会改变现有语义(开发者在 repo 内运行 pip 版会命中旧 bundle 而非 repo 当前树)——不可放。
- staged bundle 天然满足 `_is_root` 三 marker(stage_bundle 写入 VERSION+config/versions.env+container 全树)。
- 实现为纯函数 + 注入参数(`data_root: Optional[Path]`,默认懒调 `shared_root()`——模块级函数在 `data_root.py:249-256`,仿 `build.py:67` 局部导入),保持 resources.py 零依赖可测。
- data root 本身的 reparse 检查由 `shared_root()`(:253-255)保证;`bundles/<ver>/` 子目录需在新查找函数内显式接线(不会自动生效)。
- frozen 分支与 `_MEIPASS` 分支**原样保留**(dual-track 是 CI 既定资产;frozen 且 bundle 缺失时 fall-through 到 data-root 层级属可接受降级,ADR 写明)。
- root marker 定义**不改**(VERSION 只是三 marker 之一,包内单文件不构成误判);importlib.resources 不适用于 root 探测(候选都在包外)。

#### 3.3.2 manifest 运行时校验(新写——ADR-001:51 声称的启动校验从未实现)
- 现状:`compatible_cli_versions` 只在打包期由 `artifact.py:169` 写入、verify 侧自洽校验,**src/ 全树零读者**——CLI 与 bundle 版本可静默漂移。
- 新增纯函数 `bundle_compatible(bundle_root, cli_version) -> bool`:读 `manifest.json`,要求 `schema_version==1` 且 `cli_version ∈ compatible_cli_versions`,fail-closed(缺失/损坏/不含均不兼容)。data-root 层级命中候选后过此校验,不匹配则**跳过该候选继续解析链**(不报错),全链失败时错误信息列出"发现 bundle X 但要求 CLI 版本 Y"。
- 首版保守:精确匹配;跨版本兼容将来由 stage 侧扩 allowlist 表达(顺带给 `artifact.py stage` 加 `--compatible-with vOld1,vOld2` 透传)。
- 注意:`verify_staged_bundle` 现有 compat 校验是"bundle 自身 VERSION ∈ allowlist"(打包侧自洽),与运行时语义不同,上提共享纯函数时拆成两个检查并保留 `tests/packaging/test_artifact.py` 既有断言路径。

#### 3.3.3 `aisc bundle` 命令组(fetch / list / remove / path)
fetch 流程:按当前 `__version__` 在 GitHub Releases(`wangyuncepu/AISC`)找 `AISC-<ver>-<plat>-<arch>` 资产 → 下载资产+校验 → 解压到临时目录 → 对其中 `aisc-bundle/` 跑校验 → 原子移入 `<data-root>/bundles/<ver>/` → 同版本已存在且校验通过则 no-op(幂等)。

实现要点(全部有 repo 内已测试的模板):
- **safe-extract/verify 逻辑必须从 `packaging/` 搬进 `src/aisc/`**(sdist/wheel 不含 packaging/,pip 环境 import 不到);建议 `src/aisc/application/bundle_fetch.py`,`packaging/artifact.py` 改 thin wrapper 调同一实现,但**保留原符号**(`_write_manifest`/`verify_staged_bundle`/`safe_extract_archive`——`tests/packaging/test_artifact.py` 直接调用)。
- 下载器照抄 `cc_switch_resolver.py` 的 transport 注入/UA/错误映射/rate-limit 处理,但 **default_transport 是 JSON API 全量读入内存的实现,60MB 资产必须新增流式分块落盘**,不可照抄读法。
- **信任模型(必须写进 ADR,不能留在代码)**:release 的 `.sha256` sidecar 与档案同源生成,校验只能防传输损坏,不防投毒。要求:① 校验一律用 **GitHub API 返回的资产 digest**(或同时校验 sidecar 与 API digest 一致),输出让用户可见;② 文档措辞"传输完整性 + GitHub 账号信任",不写"供应链签名";③ 复用 `AISC_GH_API_BASE`/`AISC_GH_API_TOKEN` 旋钮(匿名 api.github.com 60 次/小时限额适用)。
- 离线/CN 网络:fetch **fail-closed 但给足手动路径**——`--from-file <archive>`(须同时提供 sidecar 或 `--sha256`,保持与在线路径同等强度;也是 CI 离线冒烟注入点)+ 错误文案列三条路(手动下载 URL / --from-file / --aisc-root 指向解压目录)+ 文档写明可直接解压到 `bundles/<ver>/`。CN 镜像前缀留 v2,首版不做(与 T8a/S8b "显式暴露+替代路径"哲学一致)。
- 版本匹配:严格按 CLI 版本找同名资产(资产名版本取自 VERSION 文件 dot 格式,与 tag 名无关);找不到 fail-closed,列最近 N 个可用版本并提示 `--version` 显式指定(指定其它版本仍过 manifest 校验,默认拒绝,`--allow-mismatch` 逃生门)。
- 平台选择:windows→zip,linux/macos→tar.gz(`_parse_archive_name` 已支持)。
- 磁盘策略:解压后单版本 >60MB;v1 提供 `list/remove`(remove 拒绝删当前解析链在用版本),不做自动 GC;fetch 启动时清扫历史遗留的 `bundles/.tmp-*`(半途崩溃残留,否则永久留 60MB 垃圾);原子安装用 tmp+rename(先例:`application/artifact.py` `_atomic_replace` :130-139)。
- **v1 复用完整 release archive**(顶层 {aisc exe, aisc-bundle/},verify 强制 exe 存在),fetch 只取 `aisc-bundle/` 子目录、忽略 exe——零管线改动,代价多下载 ~15MB。bundle-only 资产留 v2(届时 `_parse_archive_name` 后缀表与 aggregate `expected_platforms` 需同步扩展)。

#### 3.3.4 降级 UX 治理(未 fetch 前的体验)
- `build` 的 root=None 错误文案按安装形态分流:frozen/源码保持现文案;检测到非 frozen 且包位于 site-packages 时改为"pip 安装需要先运行 `aisc bundle fetch`(或 `--aisc-root` 指向已有 bundle)"(`main.py:1122-1127`)。
- doctor 的 aisc-root WARN 文案同理分支(`doctor.py:252-257` 现文案 "no repo in parent directories" 以 repo 为中心,误导 pip 用户);pip 形态下新增独立 `aisc-bundle` 检查项(存在性+版本兼容,**作为独立 CheckResult 追加**,不改写 `_check_aisc_root`,避免破坏既有测试)。
- `version` 契约不变(bundle_version 保持 nullable——Workbench 与冒烟脚本消费此字段)。
- **降级影响面(28 个动词实测分档,写入 README)**:
  - 不可用:`build`、`maintenance docker-rebuild`
  - 降级:`version`(bundle_version=null)、`doctor`(aisc-root WARN)、`stop`(registry 注销跳过)、`run`(legacy mihomo 采认跳过;端口排除/registry 维护 best-effort 跳过)
  - 完全可用:其余动词(maintenance 仅 docker-rebuild 不可用,docker-scan/cleanup/cache-* 均可用)——这些命令的降级语义已发布就绪,**不改代码,只固化契约测试**。

### 3.4 批次四:发布流水线

#### 3.4.1 新增独立 `.github/workflows/pypi-publish.yml`(不并入 artifact.yml)
- **触发**:`workflow_dispatch`,input 为已存在的 `v*` tag;job checkout 该 ref,在 tag 上 `python -m build`(build-in-job,provenance 清晰)。**不要挂在 tag push 自动触发上**——CLI-D08 明文"push、PyPI、tag、真实升级属于外发操作,不能自动发生"。
- **认证**:pypa/gh-action-pypi-publish@release/v1 + **Trusted Publishing(OIDC)**,零 token;publisher 绑定 owner/repo + workflow 文件名 + environment 名,三者逐字匹配。
- **人工门**:两个 GitHub Environments——`testpypi`(无 reviewer)与 `pypi`(**Required reviewers** 勾维护者;单人可自批,但审批仍是独立显式步骤,即 CLI-D08 的"用户显式确认")。
- **job 链**:build(+guard) → publish-testpypi(environment: testpypi,`repository-url: test.pypi.org/legacy/`,`skip-existing: true`) → verify-testpypi → publish-pypi(environment: pypi) → verify-pypi。人工审批点自然落在两段之间。
- **权限**:job 级 `id-token: write + contents: read`(green-check guard 另需 `actions: read`);加 `concurrency` 限 publish 串行。
- **版本门**:publish-pypi 仅当 VERSION 严格匹配 `^\d+\.\d+\.\d+$`(final);dev/rc 只到 TestPyPI。**TestPyPI 的 dev 迭代纪律:每次推 TestPyPI 前 bump `.devN`**(同 dev 版二次上传会被拒——文件名不可变;不依赖删项目)。
- **attestations:显式写 `true`**(PEP 740,默认开启但显式固化意图,防未来被"顺手"关掉);SBOM(`aisc-sbom.json`)同时附到对应 GitHub Release 资产。

#### 3.4.2 版本/tag 收敛(下次发布起)
- 历史 dash tag(`v2.1.11-dev` 等)**不迁移不改写**;下次发布收敛为 final:发布提交 VERSION 改 `2.1.11`(去 .dev0)、新增 `docs/releases/v2.1.11.md`、打 annotated tag `v2.1.11`(与历史 dash tag 并存无冲突;`artifact.yml:358,360` 的 prerelease 判断已兼容两种格式)。此后新 tag 一律 `v + VERSION 原文`;发布后紧跟一提交 bump 到 `0.1.0.dev0`。
- **两道 guard**:
  - publish 与 release job 前加 step:`[ "v$(cat VERSION)" = "$tag" ]` 否则 exit 1(publish 侧校验 dispatch input;artifact.yml 侧在 release job 内用 `github.ref_name` 比对)——同时天然挡掉 dev 误发;
  - 新增版本一致性检查(归入 `tests/packaging/` 或 `scripts/check-version-sync.py`):VERSION == tauri.conf.json version 的 PEP 440 归一化形式 == `docs/releases/v<VERSION>.md` 存在 == git tag(若在 tag 上)。**注意与 `test_release_notes.py:20-27` 已覆盖的 notes 存在性去重,聚焦 tauri.conf 与 tag**;该测试落地当天会红(README v2.1.7-dev 与 tauri 2.1.11-dev 归一化后都不等于 VERSION),必须与修两处字面量同一 PR。
- README 版本字面量全部改版本无关写法;`tauri.conf.json` 的 dash 格式可保留(语义是 Workbench 应用版本),由归一化比对兜住。

#### 3.4.3 冒烟补强(现有 clean-room 的假覆盖)
- **事实**:workbench-ci 的 clean-room 冒烟在 repo checkout 内执行,root 靠 cwd 向上发现;`verify-cli-install.py:74-75` 断言 `bundle_version == VERSION` **靠"碰巧在 repo 内"通过**,从未覆盖"site-packages 安装 + 无 repo"——pip 用户的真实首体验零 CI 验证。
- **off-checkout pass**:入口与 `python -m` 调用显式传 `cwd=临时目录`,`_run` 增加 env 参数并剔除 `AISC_ROOT`;断言:`aisc version --format json` exit 0 + cli_version==VERSION + dist metadata==VERSION(importlib.metadata)+ **bundle_version is None**(把"pip 轨道无 bundle"固化为契约,写进脚本 docstring);`aisc doctor --format json` 非崩溃降级;`aisc build` exit 1 且错误文案含 `aisc bundle fetch` 指引(**依赖 3.3.4 文案先行**,否则首版断言现文案)。
- **off-checkout + fetch 冒烟**:fetch 支持 `--from-file` 注入本地 archive(CI 用 `artifact.py stage+archive` 现场生成),断言 fetch 后 bundle_version==expected 且 `aisc build --dry-run` 成功。降级契约同场固化:run --dry-run、container ls、doctor 无 root 下 exit code 符合契约(run 冒烟显式 `--network direct`,避免订阅状态污染断言)。
- **post-publish 真实 index 冒烟**(自动化进 publish workflow,不留在 runbook):新增 `scripts/verify-pypi-install.py`(复用 pipx_verify 骨架,参数化 `--index-url/--extra-index-url/--requirement`);TestPyPI 段 `pipx install --index-url test.pypi.org/simple --pip-args '--extra-index-url https://pypi.org/simple/' 'aisc-cli==X.Y.Z'`(依赖从真 PyPI 补齐——TestPyPI 没有第三方依赖);PyPI 段直接 pin 安装;每段在临时 cwd 跑 version/doctor;**加重试容忍 index 传播延迟**(如 30s×10 轮)。保留一项人工:PyPI 项目页渲染目检。
- **twine check 内建进 verify-cli-install.py**(构建后立即对 wheel+sdist 跑;本地 twine 缺失时显式 FAIL 报"pip install twine",勿静默跳过);workbench-ci 的 pip install 行加 twine。local-gates 不加必跑步骤,按既有"按改动面提示"模式加一条:src/aisc/ 或 pyproject 改动 → 提示发布前跑 verify-cli-install.py。
- **发布前绿检查 guard**:publish 前用 `gh run list --workflow cli-sidecar.yml --commit <tag-sha> --status success` 同查 workbench-ci;任一无成功 run 即 fail。豁免:tag commit 未触及该 workflow 触发路径(比较改动文件列表,merge commit 用 first-parent 基准)。注意 `test_workflow_contract.py` 的 WORKFLOWS_REQUIRING_PATHS **不含** cli-sidecar——其 paths filter 无静态保护,guard 不能假设 filter 恒在。

#### 3.4.4 制品守卫
- **内容正向断言**(新增,建议落 `tests/packaging/`):解包 build 产物,断言必含 `src/aisc/VERSION`(迁移后)、entry_points.txt 中 `aisc=aisc.cli.main:main`、LICENSE;必不含 packaging/、tests/、vendor/、container/。
- **负向守卫**:断言制品清单不含 `container/`、`downloads/`、`_bundle`、`mihomo`、`geoip/metadb` 路径——把"PyPI 制品永远 thin"从口头约定变 CI 硬门(防未来有人为修 root 问题"顺手"塞载荷)。
- **密钥终扫**:publish 的 build 与 upload 之间,解包 sdist+wheel 跑 `gitleaks detect --source <解包目录> --no-git`,非零即挡;显式 `--config` 指定空配置或 cd 到解包目录,避免意外继承 repo allowlist 语义。
- **pip-audit**:publish 前置加一步扫构建产物依赖,策略"Critical/High 阻断、其余记录";与 SBOM 同 job,输出附到 release(SBOM 现只做清点与完整性,无漏洞判定)。

### 3.5 批次五:文档与渠道治理

#### 3.5.1 README
- 新增 "PyPI(pip/pipx/uv)" 安装小节,**推荐次序定为政策**:pipx(首选,自动隔离+bin 目录,Windows 亦然)→ uv tool → 裸 pip(需 venv)。醒目三点:① 命令名仍是 `aisc`(分发名不同);② Docker 硬前置,装完先 `aisc doctor`;③ pip 安装不含 bundle,`build`/`docker-rebuild` 需先 `aisc bundle fetch`,version 的 bundle_version=null 与 doctor WARN 属预期。
- **同步修**:README.md:46 "安装 AISC 本身不需要 Python、uv 或 Git" 与 pip 渠道直接矛盾 → 改"官方 installer/便携包不需要 Python;pip/pipx 渠道需要 Python 3.11+";过期版本字面量(:10,:58 等);相对链接(:10,:328);推广小节处置(D-4)。
- 升级节/卸载表补 pipx/uv/pip 行;资源根查找顺序(:271)链尾补 "site-packages 安装 → bundle fetch/降级" 一支。
- **安装陷阱 FAQ 三行**(公开包最高频支持负担):EXTERNALLY-MANAGED(PEP 668)→ 改 pipx;Windows `pip install --user` 的 Scripts 目录(%APPDATA%\Python\Scripts)不在 PATH → 给路径或改 pipx;`python -m aisc` 作为 shim 失效时的诊断后门。
- **卸载 SOP**(顺序陷阱:pip uninstall 会把清理工具一起删掉):① 先 `aisc maintenance docker-scan --context uninstall` 预览、`docker-cleanup` 清 Docker 资源;② 再 pipx/pip uninstall aisc-cli;③ 手动删数据根(三平台路径引用 README:258-262,含凭据相关 cc-switch 状态)。
- 排障表加行:"装了多个渠道后版本错乱 → `aisc doctor` 的 channel 检查列出全部 PATH 命中"。
- 改后跑 `bash tools/check-docs.sh`(新增 pip 小节零触发;新写 docs/ 活跃文档只用 `container/Dockerfile` 全称——注意 Check 4a 排除 `docs/plans/*`,plans 内文档归档进 archive 后才被扫)。

#### 3.5.2 ADR 治理
- `docs/adr/` 目录已消失(DEVELOP_WIKI:778 文档地图指向失效路径),ADR-001 状态仍是"已接受"但三处与现状矛盾(:19 反 pip、:45 stdlib-only、:71 零依赖)。
- **恢复 live `docs/adr/`,新写 `docs/adr/002-pypi-distribution.md`**,内容:① 三轨分发(Releases frozen bundle / PyPI 瘦 wheel+fetch / 源码);② 解析链升级六级(data-root 为新增,其余语义不变——逐条映射 ADR-001:53-61 原始五级,避免读者误判包祖先层级也是新增);③ 依赖立场修订(3 硬依赖+惰性导入兜底);④ 路线 A/B/C 对比与 B 否决理由(GPL/体积;exec-bit 论据**不成立**——downloads 内是 gzip 档案、容器内自理权限,勿写入);⑤ bundle fetch 信任模型(见 3.3.3);⑥ semver 承诺(D-3);⑦ 引用 CLI-D08。archive 的 001 头部加一行 superseded 注记指向 002;修 DEVELOP_WIKI:778 路径。

#### 3.5.3 DEVELOP_WIKI
- §11.2 发布流程新增 PyPI 步骤(5b)与 pre-tag gate 追加:`pip install build pipx twine` + `python scripts/verify-cli-install.py`;注明 clean-room 的 repo 内/repo 外两场景方向相反的断言,repo 外冒烟前 unset AISC_ROOT。
- §10.3 产物契约补 PyPI 行;§11.1 "唯一 workflow"陈述改 6-workflow 清单。
- 版本契约段(批次二触点表已列)。

#### 3.5.4 release notes 模板
- 从首个含 PyPI 的版本起,`docs/releases/v<VERSION>.md` 固定加 "## 安装与获取" 小节(h1/引言后):Release 链接 + `pipx install aisc-cli` 变体 + "需自备 Docker;pip 安装不含构建资源,见 README 降级模式"。注意:notes **不随包**(sdist 不含 docs/releases/),其受众是 GitHub Release 页;pip 用户的主载体是 README。`# AISC v<VERSION>` h1 逐字保留(测试断言用 assertIn 只查包含,但首行是渲染惯例,遵守)。

#### 3.5.5 渠道共存(代码侧小改)
- **doctor 新增 channel 检查**:枚举 PATH 上全部 `aisc`/`aisc.exe`,>1 个即 WARN 列路径;默认只列路径+文件信息(`--verbose` 才逐个执行 version 探测——避免运行未知二进制);同时报告自身来源(frozen 旁有 aisc-bundle → 便携/PKG/sidecar;site-packages → pip/pipx)。让"pipx 升级了但还在跑旧版"变成可诊断的 WARN。
- `aisc version` 文本输出加一行 "Install channel/path"(Workbench 走 --format json,不受影响)。
- **`packaging/install.sh` 修补**:升级时无条件 `rm -f ~/.local/bin/aisc` 会删掉 pipx 的 shim(:323-338);改为 readlink 目标比对(复用 build_pkg 内嵌 macOS uninstaller 的 :142-151 模式),不在自方安装目录下则不删+WARN。**`uninstall.sh` 同样要修**——归属判定只覆盖 regular-file 分支(:74-87),symlink 分支(:70-73)是无条件 rm,而 pipx 在 Linux 的 shim 恰是 symlink。
- **数据根 writer 版本防护**(pip 版与 exe/workbench 版共享同一 data root,版本交错风险):`cli-runs.json` 已有 `schema_version` 字段——在 `_load` 里做"不等于即 WARN"比较;`containers.json` 无版本位,新增并在读取时发现更高版本即 WARN 提示 `aisc doctor`。doctor 加多通道并存提示。**不按渠道隔离 data root**(数据分裂比交错更糟)。
- doctor 新增 **platform-support 检查**:`sys.platform`+`machine()` 对照支持矩阵(py3-none-any wheel 会装进 Linux arm64/Win arm64/Intel macOS,载荷是 linux-amd64 需 qemu 仿真),命中未支持组合 WARN"构建与运行可能极慢或不稳定"。仿 `_check_tun_device` 的 SKIP/PASS/WARN 形态;不搞安装期硬拦(纯 Python wheel 无可靠钩子)。
- doctor 的 Docker 代装行为(get.docker.com+sudo / brew cask / winget+UAC)是 opt-in 交互确认且非管道不触发,设计克制,但**必须在 README pip 节显式披露**(公开包语境下"刚装完就提议 sudo 改系统"是信任敏感点);README:36-46 既有"不代装"口径改为"可在 doctor 中协助安装,需确认与权限"。

---

## 4. 风险登记册

### 4.1 Blocker(不解决不可发布)

| 风险 | 说明 | 缓解 |
|---|---|---|
| pip 包核心命令致命失败 | root=None 时 `aisc build` exit 1(`main.py:1114-1127`,带指引的 CliError,非崩溃);`maintenance docker-rebuild` 同;CI 从未覆盖此场景 | 路线 C(3.3)+ off-checkout 冒烟(3.4.3)作为发布 **gate** 而非优化 |
| PyPI 名称被占 | `aisc` = 休眠第三方包;用户直觉安装装错包;名不可收回 | D-1 定名 aisc-cli + 文档写全名 + 决策到首发间尽快占名 |

### 4.2 High

| 风险 | 说明 | 缓解 |
|---|---|---|
| GPL/unknown 载荷进制品 | 未来"顺手"把 container/ 塞进制品 → MIT 元数据不符 + takedown/法律暴露;Apache-2.0 快照再分发要求保留 LICENSE/NOTICE | 负向清单守卫(3.4.4)+ ADR 记录否决与未来 bundling 义务清单(geodata 疑似 MaxMind GeoLite2 EULA,须先审计) |
| 发布供应链 | 长期 token 泄漏;pull_request 触发的 workflow 申请 id-token(fork PR 借 OIDC 投毒);repo write 被攻破篡改 workflow | Trusted Publishing(零 token)+ environment 审批 + job 级最小权限 + `test_workflow_contract.py` 加断言"pull_request 触发者不得有 id-token: write" |
| tag/版本格式漂移毒化自动化 | dash tag 与 dot 期望互斥;最危险:tag v2.1.11 而 VERSION 仍 2.1.11.dev0 → dev 号上 PyPI 不可撤回 | 3.4.2 两道 guard + 下次发布收敛 final |
| dev 版成为默认安装 | 项目无 final 时裸 pip install 会装上仅有的 prerelease | PyPI 只发 final(正则门)|
| clean-room 假覆盖 | 冒烟在 repo 内通过 = pip 主场景零验证 | off-checkout pass 固化契约 |
| manifest 运行时零消费 | CLI/bundle 版本静默漂移;ADR-001 声称的校验从未实现 | 3.3.2 新写校验(精确匹配首版) |
| PATH 同名冲突 | Linux 三方争 `~/.local/bin/aisc`;macOS PKG 的 `/usr/local/bin/aisc` 遮蔽 pipx 新版(升级后仍跑旧版,无提示);install.sh 升级误删 pipx shim | doctor channel 检查 + version 加 channel 行 + install.sh/uninstall.sh 归属判定修补 |
| AISC_ROOT 指错目录 | 便携包解压根目录顶层无 VERSION(markers 不满足)——文档必须写明 AISC_ROOT 指向解压出的 **`aisc-bundle/` 子目录**或 repo 根 | 降级文档明确(3.5.1) |
| 四渠道版本漂移 | pip 版与 GitHub Release 产物不同 commit → "pip 装的 0.1.0 配 2.1.11 的 bundle" | 渠道治理政策(§7)+ 同 tag 一次产出全部产物 + manifest 校验兜底 |

### 4.3 Medium

| 风险 | 说明 | 缓解 |
|---|---|---|
| 公开 PyPI = 公开支持面 | Alpha 契约 vs 用户预期;弃坑则名称被死包永久占用 | README 支持政策一节(best-effort + Release Notes 声明 breaking);停维护时发 final 标注 unmaintained |
| 数据根版本交错 | 多通道共享 data root,旧版读新版写入的状态前向兼容未验证 | writer 版本 WARN(3.5.5);Alpha 契约已声明,状态多可重建 |
| 非支持平台误装 | py3-none-any 装进 arm64/Intel-mac,首跑踩 qemu 仿真层疑难失败 | platform-support 检查 + 支持面写进 README/PyPI 描述 |
| 制品密钥面 | gitleaks 扫 repo 不扫制品;未来 packaging 变更可能把未扫区域带进制品 | dist 终扫(3.4.4) |
| bundle fetch 信任根 | 同源 sidecar 只防传输损坏不防投毒;公开包首次引入"运行时下载可执行内容" | API digest 校验 + 信任模型进 ADR + fake-transport 单测矩阵(离线/限流/损坏档案) |
| 3.14 overclaim | classifier 声称但零绿灯证据(tests.yml 还是 manual dispatch,连 3.11-3.13 都非自动触发) | 删 classifier;后续扩矩阵(建议顺手把 tests.yml 加 push 触发) |
| fetch 网络失败变模糊失败 | CN 直连 GitHub 困难是项目主网络约束 | fail-closed + 三条手动路径 + --from-file |
| PyPI 页面内容 | 过期版本号、404 相对链接、返佣推广链接、中英混杂 | D-4 全部处置 |

### 4.4 Low

| 风险 | 说明 | 缓解 |
|---|---|---|
| docker 硬依赖无安装期提示 | pip 装完 `aisc version` 正常 → 以为装好了,build 才发现 | README pip 节首条前置 + doctor(FAIL+指引 hint 现状已够) |
| 无安全联系渠道 | authors 无邮箱,安全研究者无入口 | urls 加 Security + SECURITY.md(GitHub 私有 vulnerability reporting) |
| bundle 磁盘膨胀 | 每版本 >60MB 无限累积 | list/remove + .tmp 清扫;不做自动 GC(文档说明占用) |
| requires-python 上限的不可逆性 | 一旦加 `<3.14` 类上限,旧 lock 里固定后不自动消失 | 优先走"删 classifier+扩矩阵"路径,不轻易动 requires-python |

---

## 5. 首次发布 checklist(时序)

**阶段 0 · 决策与一次性准备**
- [ ] 拍板 D-1~D-5(分发名/资源路线/semver/长描述/sdist 政策)
- [ ] 维护者 PyPI 账号开 2FA 并保存恢复码
- [ ] TestPyPI 与 PyPI 分别注册 **pending publisher**(repo `wangyuncepu/AISC` + workflow `.github/workflows/pypi-publish.yml` + environment 名,逐字匹配)
- [ ] workflow 先合入 main(default branch)再触发——pending publisher 对未合入默认分支的 workflow 不生效
- [ ] 首发通过后把 pending publisher 转正,核对 maintainers 列表

**阶段 1 · 代码与配置(按批次一→二→三合入,每批过 local-gates + verify-cli-install)**
- [ ] 批次一元数据 + D-1 改名(含 4 处脚本硬编码与 `__init__.py:35`)
- [ ] 批次二 VERSION 迁移(14 触点清单逐项)
- [ ] 批次三资源模型(解析链 → manifest 校验 → bundle 命令组 → 降级文案)
- [ ] 批次四流水线(pypi-publish.yml + guard + 冒烟补强 + 制品守卫)
- [ ] 批次五文档(README / ADR 002 / DEVELOP_WIKI / notes 模板 / install.sh 修补)

**阶段 2 · pre-tag gate(在 §11.2 既有清单之上追加)**
- [ ] full unittest + `tools/check-docs.sh` + `tools/vendor-verify.sh` + artifact stage+verify + `git diff --check`
- [ ] `pip install build pipx twine` + `python scripts/verify-cli-install.py`(含 off-checkout pass)
- [ ] `twine check dist/*`
- [ ] 版本一致性检查(VERSION == tauri.conf 归一化 == notes 存在 == tag)
- [ ] repo 外降级冒烟:临时目录(unset AISC_ROOT)`aisc version --format json` exit 0 且 bundle_version=null

**阶段 3 · 发布**
- [ ] 发布提交:VERSION 改 final + 新增 `docs/releases/v<VERSION>.md`(含"安装与获取"节)
- [ ] annotated tag `v<VERSION>`(dot 格式,与 VERSION 逐字一致)→ 推送 → 等 artifact.yml 出全部平台产物
- [ ] dispatch pypi-publish.yml 选 tag → build+guard → TestPyPI(自动)→ verify-testpypi → **pypi environment 人工审批** → publish-pypi → verify-pypi
- [ ] 发布后紧跟提交:bump VERSION 到 `X.Y.(Z+1).dev0`

**阶段 4 · 发布后人工验证**
- [ ] 全新环境 `pipx install aisc-cli==X.Y.Z`(临时目录)→ `aisc version` / `aisc doctor` / `aisc bundle fetch` + `aisc build --dry-run`
- [ ] PyPI 项目页目检:README 渲染、链接、版本号、attestation 徽标、maintainers
- [ ] `docs/plans/` 索引与 DEVELOP_WIKI §13 登记;playbook 归档

---

## 6. 发布后事故处理(PyPI 硬约束)

1. **坏包但可升级**:立即发 `X.Y.Z+1` hotfix(tag 打在 main 含 cherry-pick 修复),旧版 **yank**。
2. **yank 的边界**:已装用户不受影响;精确 pin 版本的用户 `pip install aisc-cli==X.Y.Z` **仍可装回 yanked 版**——yank 不是撤回。
3. **版本烧录**:版本号一经上传任何 index 即永久占用,同名文件永不可重传(即使 yank 或删项目后);修复重发必须换版本号。
4. **dev 迭代**:TestPyPI 同样文件名不可变——每次迭代 bump `.devN`(0.1.0.dev0 → dev1),不依赖删项目。
5. **半发布状态**(tag 已推、PyPI 步骤失败,出现"GitHub Release 已出、PyPI 无包"):修 workflow 后 **re-run**,不重打 tag、不改版本号。
6. **PyPI 页面描述错误**:项目页 long_description 只在上传时刷新,发版后发现 README 错误只能随下一版修正。
7. **bundle 资产缺失**(GitHub Release 有、fetch 找不到):确认资产名版本段(dot 格式)与 CLI `__version__` 一致;fetch 的 `--version`/`--from-file` 逃生门兜底。

---

## 7. 长期政策

### 7.1 渠道治理(VERSION 文件为唯一版本真源)

| 渠道 | 受众 | 版本来源 |
|---|---|---|
| Workbench NSIS 安装器 | Windows 普通用户(无 Python 前提) | tauri.conf(归一化须等于 VERSION) |
| 便携包 / macOS PKG | 脚本化与服务器用户(无 Python 前提) | Release tag |
| PyPI(pipx/uv/pip) | 已有 Python 3.11+ 的开发者与自动化 | final tag,与 Release 同 commit 一次产出 |
| 源码 uv tool --editable | 贡献者 | VERSION |

每个 tag 在同一 commit 上一次性产出全部渠道产物;GitHub Release 先行(aggregate 校验 SHA256SUMS),PyPI 上传是同一 tag 的后续手动步骤(CLI-D08);PyPI 版本号必须严格等于 tag 内嵌版本。

### 7.2 支持预期
- Development Status 保持 `3 - Alpha`(与 README 自述一致,pip 路径稳定后再与 README 一起升 Beta)。
- Alpha 期承诺:GitHub Issues best-effort 响应;breaking change 在 Release Notes 声明;pip 用户升级前看 Release Notes。
- 停维护预案:发 final 标注 unmaintained 并同步 PyPI 描述,不直接消失。

---

## 附录 A:实测验证的事实(本机,2026-09-14)

| # | 事实 | 命令/方法 |
|---|---|---|
| 1 | PyPI `aisc` 被占:"AISC Helper Tools", author MB, v0.1.10, last upload 2019-07-03 | `curl https://pypi.org/pypi/aisc/json` → 200 |
| 2 | `aisc-cli`、`aiscs` 空闲 | 同上 → 404 |
| 3 | sdist 自包含:170 文件(src/aisc 全树+VERSION+LICENSE+README+pyproject),无 container/、config/ | `python -m build --sdist` + `tar -tzf` |
| 4 | 从 sdist 提取目录重建 wheel → `aisc-2.1.11.dev0-py3-none-any.whl`(动态版本不退化) | 提取到临时目录后 `python -m build --wheel` |
| 5 | wheel 元数据:Name=aisc, Version=2.1.11.dev0, Requires-Python>=3.11, deps 三项+dev extra;VERSION 落 `.data/data/aisc/VERSION`(即 sys.prefix/aisc/,site-packages 外) | 解包 METADATA 与文件清单 |
| 6 | setuptools 84 构建告警:license TOML table 弃用(2027-02-18 大限)+ License classifier 弃用 | `python -m build` stderr |
| 7 | README 推广小节含返佣/邀请链接(:330-363);相对链接 :10 `[VERSION](VERSION)`、:328 `[LICENSE](LICENSE)`;"安装 AISC 本身不需要 Python"( :46) | sed/grep |
| 8 | `__init__.py:35` 硬编码 `metadata.version("aisc")`;tauri.conf.json:4 `"2.1.11-dev"` | sed |

其余代码级行为断言(解析链、降级行为、硬编码位置、CI 结构等)均由分析-核实双 agent 对照源码逐条确认,证据随 finding 保留(58/58 confirmed)。

## 附录 B:明确不做/否决的事

- **路线 B(载荷入 wheel)**:license 与体积双否决(理由进 ADR 002)。
- **watchdog/argcomplete 拆 extras**:降级路径为 frozen 轨道而设,拆分收益为负。
- **按渠道隔离 data root**:数据分裂比版本交错更糟。
- **非支持平台安装期硬拦**:纯 Python wheel 无可靠钩子,doctor WARN + 文档兜底。
- **CN 镜像 fetch(--mirror)**:留 v2。
- **rc 上 PyPI**:项目当前无 rc 流程,引入时再议。
- **历史 dash tag 迁移/改写**:不可变历史,下次发布起收敛即可。
- **改用 0.x 版本号表达 Alpha**:存量四渠道用户,代价大于收益;用显式契约文档替代。
