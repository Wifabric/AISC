# v2.1.17 b5 — 网络、显式更新与版本健康报告执行计划

> 执行 agent：使用 superpowers:executing-plans 逐项执行；用户已授权连续完成，仅本批规定的真实产品操作需要产品确认弹窗。

**目标：** 展示 direct/mirror 诊断和 CLI/bundle 配对健康，严格落实 D-2 显式更新合同。
**架构：** 在既有 doctor/version/update 边界添加只读报告；更新状态机与 Windows 启动器分离，以可注入 OS 动作验证调用顺序。
**技术栈：** Rust/Tauri、Python/pytest、Vue/Pinia/Vitest、Windows ShellExecute。

## 范围与源码

- 依据：`README.md` b5、`decisions.md` **D-2**、`DEVELOP_WIKI.md` §1.2–1.4；从前批已集成的 `develop` 建 `2.1.17-b5-update-health-report`，核对 target/账本。
- 更新链：`workbench/src-tauri/src/update.rs`（`get_with_fallback`、`staging_path`、`app_download_update`、`app_install_update`），`workbench/src/stores/update.ts`、`workbench/src/lib/ipc.ts`、`workbench/src/features/settings/SettingsForm.vue`、`workbench/src/components/MenuBar.vue`。
- 健康报告：`src/aisc/application/doctor.py`、`version.py`、`bundle_fetch.py::bundle_compatible`、`workbench/src-tauri/src/doctor.rs`、`workbench/src/stores/doctor.ts`、`workbench/src/features/doctor/DoctorDialog.vue`；必要 IPC 注册在 `workbench/src-tauri/src/lib.rs`。
- 新增小模块 `src/aisc/application/update_health.py` 与 `tests/test_update_health.py`，承载可注入传输的诊断与配对聚合；更新双语 i18n。`workbench/src/stores/network.ts` 目前只探测 Docker engine，不能把它当 GitHub 可达性证据。

## D-2 不可变验收合同

1. 仅 Windows NSIS `AISC-Workbench-<target>-setup.exe` 提供一键显式更新；非 Windows 显示“当前平台请手动安装”，不得进入退出安装路径。
2. 下载固定至 `%TEMP%\aisc-workbench-update\workbench-setup-<safe-target>.exe`，保留安全文件名规则；SHA256 失败删除失败产物及临时文件、显示错误、保持应用运行。
3. 校验成功仅进入 `ready`；不启动安装器、不退出。用户点“退出更新”后显示确认弹窗，取消仍为 ready。
4. 确认后先检查文件存在；Explorer `/select,<path>` 打开父目录并选中安装包；再 ShellExecute `open` 等价双击 exe，**不附加 `/S`，不沿用 `/S /R` 静默链**；两动作均成功后才 `app.exit(0)`。
5. 文件缺失、Explorer 启动失败、ShellExecute 失败（包括 UAC 拒绝）均报错并保持 Workbench 运行；不把进程创建或 shell 返回失败当成功。安装器启动后的正常 NSIS UI、取消、失败、重启提示由安装器负责，AISC 不伪造安装进度。

## 任务与 TDD 验收

- [x] **RED：** 扩展 Rust `update.rs` 内联测试、`workbench/src/stores/__tests__/update.test.ts`、`workbench/src/features/settings/__tests__/SettingsForm.test.ts`、`workbench/src/components/__tests__/MenuBar.test.ts`；新增 health 测试并扩展 `tests/test_repair_and_doctor.py` / `test_version_source.py` / `test_bundle_fetch.py`。先跑 targeted，保留 D-2 旧静默行为导致失败的证据。
- [x] **可读网络报告：** 分开记录宿主更新链和容器扩展链，字段至少 scope/endpoint/route(direct或mirror)/status/latency/errorCode/checkedAt；验证 direct 成功、direct 失败 mirror 成功、全失败、超时及缓存结果。复用已有候选源/超时预算，不改系统代理；主动探测才填实测值，未探测显示未知，不以 Docker ready 代替网络成功。
- [x] **版本配对：** 报告实际运行 CLI 路径/版本、实际解析 bundle 路径/VERSION、manifest schema 与 `compatible_cli_versions`、Workbench 版本及配对原因。复用 `bundle_compatible` 的 fail-closed 规则；测匹配、不匹配、manifest 缺失/损坏、CLI 无法执行。Workbench 2.x 与 CLI 0.x 不比较相等；版本未知不能报健康或已最新。
- [x] **最小实现 D-2：** 用接口注入 fileExists/explorerSelect/shellOpen/exit；断言成功顺序严格一致、失败短路且 exit 次数 0。测空格/中文路径、安全 target、哈希损坏、下载后文件消失、确认取消、重复点击、非 Windows。移除旧静默调用及误导说明。
- [x] **异步竞态：** deferred 测连续检查倒序返回、下载 A 完成前切换目标 B、旧 progress/catch/finally 晚到、关闭重开面板、doctor 切工作区；只当前 generation 写状态。旧安装包不得成为新目标 ready；用户确认期间目标/产物变更则撤销本次执行，不能启动旧包。
- [x] **GREEN/UI：** 设置→更新提供“检查更新→下载更新→退出更新”；doctor 提供结构化报告及脱敏复制。网络失败不由菜单误报“已是最新”；两种语言均有手动安装、ready、错误、配对不兼容文案。

## 门禁与预测试

```powershell
python -m pytest tests/test_update_health.py tests/test_repair_and_doctor.py tests/test_version_source.py tests/test_bundle_fetch.py tests/test_update.py -q
Push-Location workbench
npx vitest run src/stores/__tests__/update.test.ts src/stores/__tests__/doctor.test.ts src/features/settings/__tests__/SettingsForm.test.ts src/components/__tests__/MenuBar.test.ts src/features/doctor/__tests__/doctorDialog.test.ts
Pop-Location
Push-Location workbench/src-tauri
cargo test --lib update::
Pop-Location
powershell -File scripts/build-cli.ps1
python packaging/artifact.py stage --root . --output workbench/src-tauri/nsis/bundle
powershell -File scripts/local-gates.ps1
git diff --check
```

- [ ] 所有门禁 exit 0；必要远端 CI 通过后并回 `develop`。改容器则另做 vendor verify 与镜像重建；使用当前 sidecar 的 doctor/version 验证配对，记录路径而非仅源码版本。
- [ ] **CU 前置：** Windows/CU、可牺牲测试安装目录/工作区、真实 NSIS 测试产物及 SHA256。**操作：** ①设置→检查→下载；②等待 ready，确认应用仍运行；③点退出更新→取消；④再次确认→观察 Explorer 选中文件、正常 NSIS UI、Workbench 退出。另以缺失包/受控启动失败复测，并开 doctor→复制报告。**理想：** 取消仍 ready；任一启动失败应用仍运行；报告逐项区分 direct/mirror 与配对原因。**异常：** 静默安装、下载即退出、失败后退出均 FAIL。
- [ ] 写阶段 `PRETEST.md` 的时间、构建/sidecar/镜像、步骤、理想/实际、截图/窗口树和 PASS/FAIL。无 CU 写 `NOT RUN — b5 Explorer/NSIS/退出顺序 UI：当前 agent 无 Computer Use`；无可用 NSIS 产物写 `NOT RUN — b5 真实更新链：缺少目标 NSIS 安装包及校验文件`；非 Windows写 `NOT RUN — b5 Windows NSIS 实机：当前宿主非 Windows`，仍验证手动安装分支。不得以 mock 代替实机 PASS；继续 b6，统一用户手测最后安排。

## 实施细化（2026-10-27，实施前记录）

- 网络报告采用更新传输的真实被动观测：每次 direct/mirror 请求记录 endpoint、transport、状态、耗时、错误码和时间；只读快照保留原时间，不把缓存报告当新探测。未探测的容器扩展网络明确 unknown，doctor 不因打开面板自动增加慢网络请求。
- CLI 配对在实际运行进程读取 sys.executable/entrypoint、CLI 版本、实际解析 root/VERSION 与 manifest，并复用 bundle_compatible。源码根没有发布 manifest 时报告 unknown；发布 bundle 缺失/损坏 manifest 为不兼容。Workbench 版本从本地 AppHandle 独立报告，不与 CLI 版本比较相等。
- 显式更新启动器与状态机分别实现；OS 调用不使用 cmd/start 或静默参数。
- 传输观测的成功响应明确记为 `headers-received`，耗时截止响应头；不得把它当作完整下载/安装成功。后续 body 超时/截断由更新页显示，报告提示明确说明这一边界。

## 执行记录（2026-10-27）

- 显式更新实现 exists → Explorer /select → ShellExecuteEx(open，无参数) → exit；文件缺失、Explorer/安装器失败、UAC 取消均不退出。非 Windows 保留手动安装分支。下载使用独立 requestId/UUID 临时文件，失败仅清理本请求。
- ready 与确认身份绑定目标/路径/哈希/大小/代次；迟到检查、下载、progress、catch/finally 不覆盖当前状态，确认期间切换目标不能启动旧包。
- 网络报告为只读本机历史观测（最多 100 条），区分 direct/mirror 与系统代理；endpoint 仅保留 origin。响应头成功明确 headers-received，body 失败仍由更新页说明。未探测容器不伪报成功。
- CLI/bundle 报告使用真实运行路径、资源根、VERSION、精确整数 schema 和 allowlist；未知/非法版本不报健康。Doctor 全文消息/详情/提示脱敏；关闭重开/切工作区/重复读取均有代次守卫。
- RED/GREEN 包括静默启动旧行为、未知 CLI 最新误报、manifest true/1.0、迟到健康快照、敏感 allowlist、真实 WorkbenchError 详情和无效代理。
- 最终全门禁：Python **1528 passed / 57 skipped / 140 subtests**；Rust **398 passed / 1 ignored**；Vitest **747 passed**；vue-tsc 通过，输出 LOCAL GATES: ALL GREEN。sidecar/bundle stage+verify、前端生产构建、Workbench debug 构建通过。
- 冻结 CLI doctor 实际配对 PASS；Computer Use 未提供，Explorer/NSIS/退出顺序实机 UI 为 NOT RUN，详见 PRETEST；HANDTEST b5 已补齐统一复核步骤。未发布 preview/final。
