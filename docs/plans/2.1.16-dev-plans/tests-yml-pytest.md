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
