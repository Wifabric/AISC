# 进度

- 2026-10-31：登记用户十项手测反馈，拆分六个顺序批次；b1 分支从最新 develop `7cc5a25` 建立。
- b1：确认旧宿主 CLI pin 0.1.9.dev0 不支持 updates-check，空 envelope 稳定复现；补全 extensions argparse JSON 上下文，Workbench 仅在准确旧版本证据下尝试随附新 CLI，成功才写 pin。
- 本地门禁：Python 1699 passed / 53 skipped / 195 subtests；Rust 407 passed / 2 ignored；前端 822 passed；vue-tsc 通过。真实恢复测试另显式执行 1 passed / 9.29秒，含显式覆盖守卫。
- 冻结 CLI、生产 Tauri 静态 UI、匹配镜像完成；Windows CU T1–T4 通过：旧 pin 恢复、三市场/详情、重复/Services/双工作区隔离、适配器真实失败后不重启重试。
- 校验式启动器已备，HANDTEST 有准确路径和字段级结果；原始窗口树和日志位置、限制见 PRETEST。
- 当前：准备提交与远端 CI，用户 b1 验收待确认，b2–b6 未实施。
