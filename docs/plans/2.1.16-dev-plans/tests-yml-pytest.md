# tests.yml 框架收敛为 pytest（方案 B）

> 2026-10-18 用户裁定：按方案 B 修复——tests.yml 由 `unittest discover`
> 改跑 pytest，与 workbench-ci 同构。本批为 b1 门禁发现的既有漂移收口，
> 非 b1 引入（develop 上先于 b1 存在；develop 上次 tests.yml 绿跑 2026-08-09）。

## 问题

- `tests.yml`（dispatch-only）：`pip install -e .`（无 pytest）→
  `python -m unittest discover`。
- 2.1.15 合入的 5 个测试模块模块级 `import pytest` 并使用原生写法
  （raises ×23 / fixture ×3 / parametrize ×4；`test_work_collection` 的
  测试类不继承 TestCase、方法签名吃 fixture 注入）：
  `test_artifact_record_env` / `test_conversation` / `test_docker_cache_cleanup`
  / `test_work_collection` / `test_workflow_contract`。
- 后果：tests.yml 下 5 模块 loader error，9 组 OS × Python 矩阵全红。
- 「只装 pytest 继续 unittest」不可行：非 TestCase 类与函数式测试被
  unittest 静默跳过 → 假绿（用户裁定否决）。

## 修复（方案 B）

1. `tests.yml`：`pip install -e ".[dev]"` + `python -m pytest tests -q`
   （与 workbench-ci Python tests step 逐字对齐）。
2. wiki §9.1/§9.2/§9.3/§14 按「文档先行」同步：运行器统一 pytest；
   unittest 仅保留为源文件级单测调试形态（且只对 unittest 风格模块可用）。

## 验证

- 本地：`pip install -e ".[dev]"` 后跑 `python -m pytest tests -q` 全绿。
- 远程：dispatch tests.yml 于本分支，3 OS × 3 Python 九组矩阵全绿后并回。

## 明确不做

- 不移植 5 个模块回 unittest（方案 C 否决）。
- 不退役 tests.yml（保留矩阵覆盖；方案 D 否决）。

## 执行状态（2026-10-18）

- 本地同构验证：`pip install -e ".[dev]"` + `python -m pytest tests -q`
  → 1417 passed / 69 skipped（pytest 9.1.1，无 PYTHONPATH）。
- 首次分支 dispatch（run 39092763847）：ubuntu 3/3 绿（5 个 import pytest
  模块 loader 漂移已消除）；win/mac 暴露三处此前从未在该矩阵运行过的
  平台问题，随批修复：
  1. `tests/features/test_runtime_compat.py` / `test_runtime_json_contract.py`
     模块级 `AISC_DATA_ROOT=mkdtemp()` 在 macOS 经 `/var` 符号链接触发
     data-root reparse 守卫 → `Path(...).resolve()` 后再设 env。
  2. `tests/test_update.py::test_frozen_with_adjacent_bundle` 在 GH Windows
     runner 两侧 8.3 短名/长名不一致 → 比较前双侧 resolve。
  3. `src/aisc/cli/commands/artifact.py::_normalize_record_path` 产品侧
     8.3 短名路径 containment 误判（real bug）→ relpath 前对入参 resolve，
     与已 resolve 的 workspace 同构。
- 定向 + 全量本地复跑全绿。
- 第二轮 dispatch 后残余定位：conftest 会话级隔离根（`aisc-conftest-data-`）
  先于模块级 env 生效且未 resolve——补 `os.path.realpath`；
  `test_serve.py` 在 Win/Py3.11 无 `os.set_blocking` → skip 守卫。
- 第三轮 dispatch 后 macOS 残余为同型问题的其他模块（applog / artifact_contract /
  cli_data_root / cli_fixtures 直接以原始 TemporaryDirectory 作 data root）。
  最终收敛：conftest 将会话级 ``tempfile.TemporaryDirectory`` 替换为返回
  ``os.path.realpath`` 的子类，一次性覆盖全部同型调用点。
- 第四轮后仅剩 ``test_cli_logs``：其 setUp 直接读 ``TemporaryDirectory.name``
  绕过 ``__enter__``。wrapper 改在 ``__init__`` 内 resolve ``self.name``，
  同时覆盖上下文与直读两种消费形态。
