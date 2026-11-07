# 统一候选 GUI 复测记录

2026-11-08，AI 实机自测，不代表用户验收或独立评审。

## 目标与隔离

- 首轮 Workbench：DELIVERY 所列 `2.1.18-preview.1`，产品来源 be39b2a9。
- 窗口 818×669；独立工作区 `D:\AISC\p18\ui-workspace`，数据根 `D:\AISC\p18\qa-data`。
- 预检五项通过，启动 Bash 工作区成功。未输入终端命令或模型提示。
- 测试容器 `66bdec7af68f` / runtime `c4643a4d-ff1e-48a5-897e-241221f06fe0`；inspect 核对挂载仅对应上述 QA 路径。原平台容器未变更。
- 运行时来自已有旧镜像，适配器初始哈希与候选不同。只在该 QA 容器覆盖候选 adapter、default_mcp、github_mcp_auth，adapter SHA256 `035958661f6b7fa05bd8df8bcc02f75df7bc23e2b26e53f13feb153eaba088d9`。以下扩展检查使用此测试部署，不能当作完整镜像升级验收。

## 已观察结果

- H5 子集 PASS：扩展市场 → 基础模块 → 创建模块，保存单技能 `mattpocock/skills:research`；已选成员禁用；重新读取定义仍保留；编辑名称后保存成功。独立配置文件 revision 1 的新定义与 UI 一致。未点击应用前仅改变模块定义。
- H5 未测：三种类型混合、两窗口并发冲突、离线保存、重启持久化及完整删除。默认清单保持为空，U-4 未批准。
- H1 本轮未完成：重命名输入短暂出现后失焦，下一次 UI Automation set_value 报 `0x80040201`，实际名称未改。未据此判断产品通过，也未直接用磁盘改名冒充 GUI 测试。
- H6 预检发现整合缺陷 S3：应用计划约 47 秒后生成，但同时看到后台工作记录“自动记录未同步：AISC CLI 响应超时”。CLI 日志记录扩展请求 47109ms。模块计划在串行 pooled serve 上执行，其所有权快照扫描大规模 bind mount，堵住 30 秒短请求。

## S3 修正

`module-plan` 改走现有独立进程通道，保留 120 秒预算、JSON stdin、超时/取消与日志链；本机和 SSH 使用相同分流。`module-status` 只读取持久日志，仍复用原通道。没有取消资产指纹核对或放宽归属保护。

Rust CLI 定向测试 35 passed，新增本机/远程预检分流及短操作保持 pooled 的回归。真实修后候选验证、构建标识和远端 CI 随后补记；本条不预记通过。

H1–H10 未覆盖部分、安装/升级、SSH、真实 GitHub 授权均保持 NOT RUN。完整步骤见 [HANDTEST](HANDTEST.md)。

S4：真实安装结束后显示“已安装 / 尚未安装”两种相反状态，后者是遗留预检原因。成功 installed/removed/auth_required 终态不再显示旧原因；保护/失败等原因仍显示。前端模块组件与 store 定向 12 passed，包含三种成功终态和共享资产保护说明。H6 首轮实际安装 research 成功，卸载与修后复测另记。

S5：修后独立通道使中文名称经过 Windows 冻结 CLI 的系统编码 stdin，真实预检报 UnicodeEncodeError。模块命令现从 binary stdin 明确读取 UTF-8，常驻 serve 的 StringIO 路径保留；22 个模块/分发测试与 18 subtests 通过，包含中文/日文/emoji 和非法字节在修改前拒绝。首次测试默认临时目录权限失败，改用工作区独立 basetemp 后通过。真实冻结 CLI 多语言预检与新候选复测另记。

## 最终 Preview.3 实测与集成结果

- #78 head 33227965，CI 42412882668 三项 PASS，合入 fd8e7a0d；#79 head 15b47ab1，CI 42413674608 三项 PASS，合入 a9834710。单代理自查；产品当前集成标识与完整产物哈希见 DELIVERY。
- Preview.3 使用修正的 Workbench 和冻结 CLI，最终窗口 848×745。新测试 runtime 745f2352-c16d-4f34-9308-9e50c355ba69 / 容器 901f6cff8b1b，同样仅使用独立 QA 挂载并部署匹配适配器。
- H5 子集追加 PASS：重启后编辑后的中文名称与单成员定义保留；删除时显示“只删除定义，保留已安装的扩展”，确认后列表为空、磁盘 revision 3 / definitions=[]，技能组仍为两项。未测试混合成员、并发冲突或离线操作。
- H6/S3/S5 子集 PASS：真实窗口提交“QA 模块已编辑”的应用预检，成功显示中文名称、已有 research 的保留计划与保护原因。预检开始后前 30 秒，6 次 topic 请求均成功（最大 30ms）、6 次 runtime 请求均成功（最大 343ms），未再出现原后台同步超时。没有确认重复安装。
- 独立冻结 CLI 多语言探针 PASS：直接发送 UTF-8 中文/日文/emoji，48.38 秒返回名称完整的保留计划；移除 PYTHONUTF8/PYTHONIOENCODING 环境后仍成功。对应二进制与候选相同。
- H9 子集 PASS：旧统一候选的真实市场搜索 grill，grill-me/grill-with-docs/grilling 三项实际摘要可见；展开 grill-me 显示简介和固定来源 4ae2317d 的多层 SKILL.md。未点击安装；断网/恢复/跨查询切换未测。后续 S3–S5 不改变该详情实现。
- About 实测 PASS：Workbench 2.1.18-preview.3、CLI/Bundle 0.1.10；Image 仍为未知，测试环境使用已有旧镜像，不据此宣称镜像升级通过。
- 本地证据：gui-preview3-module-plan.txt、preview3-concurrent-cli.json、frozen-utf8-result.json、gui-preview3-definition-deleted.txt、gui-preview3-about.txt、gui-grill-detail.txt；均位于 DELIVERY 指定 verification 目录。文件包含合成测试名称，无真实凭据。
- S4 成功终态文案修正通过组件回归；修后 installed/removed 的完整真实 GUI 路径仍未重跑。H1 本次输入焦点问题仍待复测；H2–H4/H7/H8/H10 的完整候选 GUI、H6 卸载/故障恢复、安装升级、SSH、真实授权保持未完成。

最终清理：本轮候选正常退出并删除其临时运行时；测试定义已删除，原平台窗口/容器保留。独立 QA 数据和安装的测试技能仅存在 QA 数据根，可用于后续复测。

## Preview.3 追加文件与失败提示复测

2026-11-08，仍为 DELIVERY 所列相同二进制，无产品代码变更；窗口 863×783，工作区与数据根沿用上述独立 QA 路径。以下为 AI 实机自测，不代表用户验收。

- H1 本机流程 PASS：用正常键盘输入完成 `Area.txt → AREA.txt`、`Folder → FOLDER`；刷新、关闭并重新进入工作区后精确名称和内容保留。此前 UI Automation `set_value` 导致行内输入失焦的问题通过正常键盘操作绕开，未作为产品缺陷修复。SSH 路径未测。
- 将 `AREA.txt` 改为已有 `Occupied.txt` 被拒绝，显示“同名文件已存在，未覆盖”；原输入仍可编辑，Escape 取消。准备 40 个合成滚动条目，在最后一行 `zz-qa40.txt` 重复冲突及 `bad/name` 非法名称，错误自动进入视口，分别显示冲突原因和“名称不能包含 / 或 \\”，Escape 恢复原条目。
- 只读磁盘核对：`AREA.txt`、`FOLDER/child.txt`、`Occupied.txt`、`zz-qa40.txt` 内容依次为 qa-file、qa-child、keep-me、scroll-test；没有旧大小写名称、临时名或非法名称。未操作原工作区。
- H10 子集 PASS：在 QA 容器 `98b531b2cfca` / runtime `5b831633-375f-418c-afc8-2bc0fef17881` 中，仅对 plugin-install 注入返回唯一 operation_id 的可控失败；实际安装器不执行，其他调用使用候选 adapter。真实 UI 显示失败卡片和同次重复错误；点击复制诊断出现“诊断已复制”反馈，未检查剪贴板内容。
- 从复制诊断按钮连续 Shift+Tab 到重试、关闭，观察到关闭按钮的焦点环；按 Space 后卡片与重复文案同时消失，焦点回到扩展市场。故障计数仍为 1，未隐式重试。再次主动触发安装测试，新的 failure 2 正常显示；鼠标点击关闭后同时隐藏，故障计数仍为 2。切换文件视图后返回扩展，列表加载完毕，旧失败没有重新出现。
- 插件清单前后 SHA256 均为 `4b3c46d84a7a7af421326c3e9591daf8279204c01fdf9b46a9274763b1ab9ea3`。故障注入已撤销，adapter 恢复为候选哈希 `035958661f6b7fa05bd8df8bcc02f75df7bc23e2b26e53f13feb153eaba088d9`。本项不能计作 H7 真实安装成功；跨目标、未知结果禁止重试和关闭后的历史诊断读取仍依赖既有自动化，未完成对应 GUI 验收。

本地证据：gui-file-conflict.txt、gui-file-bottom-conflict.txt、gui-file-bottom-invalid.txt、gui-h1-disk.json、gui-h1-reenter.txt、gui-h1-reenter-disk.json；gui-h10-failure1.txt、gui-h10-keyboard-dismiss.txt、gui-h10-failure2.txt、gui-h10-mouse-dismiss.txt、gui-h10-view-return.txt、h10-postcheck.json。位置同 DELIVERY；截图在本轮工具记录。完整未覆盖范围继续按 HANDTEST 保留，不将子集通过扩写成 H1–H10 全部通过。

重入时启动摘要出现“已自动回收上次未正常关闭的运行环境”，尽管前一步通过正常“关闭工作区”返回选择页。五项预检通过，后续启动与文件读取正常；本轮未定位该回收提示的原因，不以此宣称运行时清理文案验收通过。

追加轮清理完成：重入创建的 QA 容器 `7ea6c1ad5673` 随候选正常退出而删除，QA workspace-key 下无残留容器。原平台 PID 40320 与容器 `2e801ec161c0` 仍运行；测试文件与本地证据保留供复核。

## Preview.3 追加镜像命名复测

同一候选，窗口 878×821，从选择工作区页的“编辑 → 设置 → 磁盘与缓存”进入。只读扫描后仅操作专门创建的两个 FROM scratch 测试镜像；它们具有 org.aisc.managed=true 和本轮唯一 qa 标签，不运行容器、不推送镜像。

- H3 本机流程 PASS：首次默认名 `super-claude:d2apok2o`，取消后 keep/old 两标签未变。再次进入生成新的八位小写字母数字默认名；从下拉框明确选择 old，输入完整 `aisc-h3-gui-714c6981:new` 后提交。界面刷新显示 keep/new，Docker inspect 确认 old 消失、new 与 keep 保持原 ID。
- `INVALID NAME:bad` 被前端拒绝，行内显示完整镜像引用格式说明。目标为另一 ID 的 `aisc-h3-gui-714c6981:conflict` 被后端拒绝并显示 image reference already exists；两个镜像的 ID 和标签均未被覆盖。
- 继续将选中的 keep 改为 `registry.example:5000/aisc-qa-714c6981/image:port`，UI 刷新后存在完整引用，new 保留，keep 消失。这里只创建本地标签，没有连接或推送到 registry.example。
- 原测试镜像 ID 为 `sha256:7d7558a50973945ce3b6c8362111a3fe3f65dd77cba3bee228e8dd9fbca3210c`，冲突镜像为 `sha256:9e0370d3abccfa543737434a04f24a709c2a2e5ea883ec64555a930cf1a91673`。验证后按精确 ID/qa 标签清理三项测试引用，两镜像均已不存在；候选退出，原平台窗口保留。
- WebView 原生下拉弹层的鼠标输入被自动化工具目标窗口检查拒绝，改用 End/Enter 正常选择，实际旧标签在提交前已核对；没有绕过工具检查或把它记作产品故障。

证据：h3-gui-before.json、gui-h3-default.txt、gui-h3-renamed.txt、gui-h3-invalid.txt、gui-h3-conflict.txt、gui-h3-port.txt、h3-gui-after.json、h3-gui-cleanup.json，均在本机 verification 目录。部分失败时旧标签删除失败的 GUI、SSH 及 H4 重建未由本轮覆盖。设置页保留历次操作结果文案，冲突错误出现在成功后的历史结果区域；未将该区域误记为扩展失败提示 H10。
