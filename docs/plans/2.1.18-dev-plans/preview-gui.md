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

## H4 实机发现 S6：重建缺少基础镜像准备

Preview.3、893×859 窗口，独立镜像 `aisc-h4-gui-94db20a7:keep/selected`，旧 ID `sha256:73426400b52c4883bf6762b7a0a013f9f7e6e9dd98e3bc1127a9f5b8f6f2d25a`，测试容器 `f69201ad41c4`。原平台不参与测试。

- 运行中拒绝 PASS：镜像行重建的只读预检列出 `aisc-h4-gui-94db20a7-container`，确认构建禁用，默认无缓存勾选；没有自动停止或删除。取消后通过该容器行的“停止”及确认，inspect 证明它已停止，旧 ID 不变。
- 停止后预检 PASS：对话框显示同一完整 ID 和 keep 标签，确认可用。实际冻结 CLI argv 含 keep、expected-image-id、--guarded、--no-cache、--events，根目录为完整候选 bundle。
- 真实构建到基础镜像元数据阶段，首选源 docker.1ms.run 返回 EOF，31.8 秒后 UI 正确显示失败和日志；两个原标签和停止容器都保留。构建成功仍未完成。
- S6 定位：guarded_rebuild 直接执行 plan.docker_argv，绕过普通 run_build 的镜像源回退、固定 digest 验证和本机 builder 绑定。抽出共用 prepare_build_argv，普通构建与重建都调用；不放宽固定来源校验，不修改用户网络配置或所选镜像替换保护。
- 定向 52 passed：重建生命周期、基础镜像回退和固定版本回归；新增实际接线覆盖首选源失败后 fallback、digest 无法验证和非 docker builder 拒绝，失败前不发布所选标签。完整回归、修后冻结 CLI 的实际构建和 GUI 复测另记，不能用旧 Preview.3 代表修正。

本地证据：gui-h4-running-block.txt、gui-h4-stopped-confirm.txt、h4-nocache-command.json、gui-h4-mirror-failure.txt（临时签名下载 URL 已省略）、h4-gui-before.json。重建 QA 资源暂保留供修后复测，处于停止状态；原平台继续运行。

S6 修后冻结 CLI + 完整候选 bundle 实测 PASS：依次尝试三个配置源，验证固定 digest 后使用 `aisc-node-base:sha256-bc0a2afd…` 和 `--builder desktop-linux --no-cache` 完成构建，610 条输出事件、76 条进度事件，最终 build.complete / exit_code=0。新 ID `sha256:22d36db0de22650fef865e00749879a472efff5e2bb40ebfa90f4d4aad379582` 只发布到 keep；selected 仍指向旧 ID，停止容器仍引用旧 ID，结果 kept_referenced 与实际一致。期间另做同 digest 的官方拉取可达性探针成功，但未修改候选配置或回退链。此处为真实冻结 CLI 数据面，不记修后 GUI 成功路径已完成。

完整 Python 回归 1796 passed、54 skipped、207 subtests；本机路径适配沿用既有验证插件，无断言修改。冻结 CLI SHA256 `ded9ed26f029afb00350e8fa67354cf93cd08e89fa7028e248ea06d5eedc2eaf`。本地补充证据 h4-fixed-frozen-events.jsonl、h4-fixed-docker-command.json、h4-fixed-result.json、rebuild-python-full.log；标准 Preview.3 尚未替换此 CLI，重打包、修后 GUI/取消/第二入口与远端 CI 继续补记。

## Preview.4 / S6 修后真实 GUI

PR #83 的精确 head 51b5cff5 在 CI 42417635698 三项通过后合入 develop 24d03cd3。重新冻结 CLI、构建 Workbench 与 NSIS，更新独立 candidate；完整 SHA256 见 DELIVERY。以下为新二进制的实机自测，窗口 908×897，仍使用独立 QA 数据和镜像。

- 设置镜像行入口：预检显示 keep 的完整 ID 22d36db0…，无缓存默认勾选。取消勾选后确认，真实候选 argv 含 `--use-cache`；12.2 秒显示“构建完成 / 100%”，日志实际复用各层缓存。新 ID `sha256:423dd6dfaf44930a1eca28e378e37e8b55e3bd43f420b3f5d9b96627eebdb94c` 发布到 keep；未被引用的上一完整构建 ID 22d36db0… 已删除，UI 提示与 inspect 一致。
- 另一标签 selected 和停止容器仍指向最初 73426400…，未被这次构建覆盖或删除。再次打开 keep，默认恢复无缓存；实际 argv 为 `--no-cache`。构建已传入 context 后点击“取消构建”，19.3 秒明确显示“已取消 / 操作已取消”，没有显示成功。keep 仍为 423dd6df…，selected 和停止容器不变；本次 CLI 进程结束，无 aisc-rebuild 临时标签残留。
- 本次顺序为缓存成功、无缓存取消；不能把它写成 HANDTEST 所列缓存构建取消已执行。无缓存完整成功由上一节冻结 CLI 实测覆盖。

本地证据：gui-preview4-h4-cache-success.txt、h4-gui-cache-command.json、gui-preview4-h4-cancelled.txt、h4-gui-nocache-cancel-command.json、h4-preview4-postcancel.json。原平台镜像和运行容器未修改。

第二入口：在独立 QA 工作区的启动摘要“更改设置”中，将镜像明确改为同一 keep，从“重建镜像”打开的只读预检显示当前完整 ID，默认无缓存勾选。取消勾选后提交，实际 argv 含 `--use-cache`，进度到“导出镜像”，12.5 秒完成；新 ID `sha256:62d358f2b5c5f796de5efe95a28f1257b837645774ce55218d8523432c0ec759`，selected 和停止容器仍为最初旧 ID。尝试取消时已进入发布结束阶段，最终正确显示完成及新 ID，因此本次记第二入口成功，不记缓存取消通过。当前 QA 镜像保留供后续扩展复测；尚未运行此镜像的工作区容器。

“帮助 → 关于”确认 Workbench 2.1.18-preview.4、CLI/Bundle 0.1.10、Claude 2.1.314；Image 仍显示未知（未启动 runtime）。对应 gui-preview4-h4-summary-success.txt、h4-gui-summary-cache-command.json、gui-preview4-about.txt。Remote 入口禁用实机、缓存构建在完成前取消、完整无缓存 GUI 成功、安装/升级仍未由本轮覆盖；保留此前数据面与组件测试证据，不扩写为完整 H4 或用户验收。

## Preview.4 / H7 真实插件安装

从启动摘要明确选择本轮完整构建的 keep，成功启动 runtime `87e27a0f-fdd0-40c6-ac40-6145b37199b9` / 容器 `ff84cabf72c7`。镜像为 62d358f2…；所有工作区/配置挂载均指向独立 p18 QA 目录，adapter 哈希 03595866… 与候选一致，本轮没有适配器注入或替换。插件清单初始 `{}`，与上轮 H10 的模拟失败分开记录。

真实 GUI 搜索 mattpocock-skills，详情核对来源 claude-plugins-official 后点击安装。安装中按钮禁用，再次点击保持禁用；只读进程快照显示一条 adapter plugin-install 与一条实际 claude-real plugin install。完成后已安装列表及展开详情显示版本 1.3.1；磁盘 installed_plugins.json 仅一个对应 user 条目，安装路径下 .claude-plugin/plugin.json 存在且版本一致，记录来源 commit `49dd158d1076134a641b33efb035946536778336`。安装进程已结束，没有将表面成功代替磁盘核对。未采集精确总耗时，不填写推测秒数。

切换文件视图再返回扩展，重新读取后仍显示已安装 1.3.1。证据：h7-preview4-baseline.json、h7-preview4-install-command.json、h7-preview4-installed.json、gui-preview4-h7-installing.txt、gui-preview4-h7-installed.txt、gui-preview4-h7-detail.txt、gui-preview4-h7-reloaded.txt。本轮正常安装成功；慢网/超时、未知结果恢复及安装中跨工作区切换尚未实测，不记完整 H7 PASS。插件仅安装于 QA 数据根，原平台保持运行。

## H6 实机发现 S7：科研推荐的安装标识不匹配目录

同一 Preview.4 真实 GUI 创建“QA-A 科研与预装保护”，选择既有 research 与推荐的 literature-search-arxiv。计划明确保留预装 research、只安装缺少的 arXiv；执行后 research 保留，但 arXiv 显示失败和“部分成员需要处理”，没有伪报整体成功。直接复现返回 SKILL_DIR_NOT_FOUND，路径 literature-search-arxiv 不存在。原始定义与失败历史留在 QA 数据根，未修改用户模块。

只读获取 google-deepmind/science-skills 的提交 4de6786171f1479026da5d3a00f110703c8ba35e，确认实际目录为 literature_search_arxiv、literature_search_openalex、pubmed_database、literature_search_europepmc，均包含 SKILL.md；未执行上游技能指令。S7 将四个现有推荐的安装 identity 改为这些实际目录，保持显示名与推荐顺序。仅修正已知推荐数据，不自动改写已有用户定义，不启用 U-4 默认模块，也不宣称任意市场别名都可安装。

新增真实编辑器组件回归验证四个推荐保存的安装 identity、显示名和来源，且保存不触发安装。受影响前端 28 passed，类型检查和生产构建通过。修后冻结 CLI 实际安装/移除及新版候选 GUI 复测另记；Preview.4 本身尚不包含这项前端修正。

证据：h6-arxiv-install-failure.json、h6-science-source-paths.json、science-catalog-frontend.log、science-catalog-build.log。本轮预装项保留和部分失败的实际行为通过，不将未完成的全量应用/卸载记为 H6 PASS。

修后安装标识数据面 PASS：使用当前冻结 CLI（ded9ed26…）和完整候选镜像，新建无用户挂载的独立临时容器，四项分别通过模块计划、逐项 installed、状态回读，再逐项 removed、状态回读。不存在的 plan_id 明确拒绝。测试容器按本轮唯一 QA 标签核对后已清理，证据 science-members-install.json。资产安装/移除通过不代表技能内部科研任务或外部 API 已验收；GUI 仍须用含 S7 的新候选复测。

## Preview.5 / S7 与 H6 继续复测

PR #85 head d06b3269 在 CI 42420724178 三项通过后合入 5467c9cf。本机 Preview.5 Workbench/NSIS 已重新构建；CLI 和 bundle 相对 Preview.4 未变。窗口 923×935，仍用独立 QA 数据；当前 runtime d8106f6f-c0fd-4e93-b9e8-780afdc63398 / 容器 f351f02d56e1，镜像 keep 62d358f2…，原平台保持运行。

- 推荐与编辑器显示四个实际下划线目录，原先保存的错误 QA 定义未被自动改写。通过界面删除旧 arXiv 成员、加入修正后的 arXiv 和 OpenAlex 并保存，QA-A 变为三项：预装 research、待装 arXiv/OpenAlex。滚动后保存按钮可正常操作。
- 应用计划明确保留预装 research，只补 arXiv/OpenAlex。research 完成保留、arXiv 正在处理时点击“当前项完成后停止”；最终显示“已停止后续步骤”，research 已保留、arXiv 已安装、OpenAlex 尚未执行。磁盘三侧 skills 目录确认 arXiv 存在、OpenAlex 不存在，research 的 SKILL.md 哈希仍为 1f629e18…。
- 执行期间正常创建并保存只含 arXiv 的“QA-B 共享科研成员”，仅保存定义；所有模块执行按钮在 A 运行时禁用。后续重新预检/补齐和共享卸载另记，不预写通过。

证据：gui-preview5-h6-a-plan.txt、gui-preview5-h6-a-stopped.txt、h6-preview5-baseline.json、h6-preview5-stopped.json；本轮 QA 定义保留供继续验证。

恢复子集 PASS：点击“重新预检／重试”，新计划将 arXiv 标为“已安装，模块归属可核对 / 保留”，只补 OpenAlex。执行期间关闭市场并切换工作记录，返回模块面板后仍显示完整终态：research/arXiv 已保留、OpenAlex 已安装。三侧 SKILL.md 均与各自源内容一致；research 和首次安装 arXiv 的哈希不变。证据 gui-preview5-h6-a-retry-plan.txt、gui-preview5-h6-a-complete.txt、h6-preview5-a-progress.json。此处为手动停止后的继续，不混写为网络故障或未知结果恢复。

## Preview.5 / H2 工作记录增量复测

在同一独立 QA 工作区准备 30 条仅含合成标题的 Codex 会话和 24 个空集合，另有环境自带 init 会话；没有模型调用或私人会话内容。后台模块执行期间进入工作记录，列表可正常读取和操作。

- 923×935 窗口底部 Session 15 右键菜单向上避让，子菜单向右展开，24 项可见。Home/Down/Up/End 分别将可见焦点环移至 01/02/01/24；Left 返回父菜单，Escape 返回原会话行焦点，Shift+F10 从该行重新打开菜单。菜单重命名实际命中 Session 15，保存为 Preview QA Session 15 renamed。
- 通过 Windows 原生窗口菜单调整至 647×593，底部 Session 30 的子菜单独立向左展开，保留父菜单可点击区域；内部滚动后 24 项长名称完整换行可见。点击第 24 项后，只有 Session 30 移入对应集合。
- 数据核对 PASS：24 个集合的 ID/名称/状态不变，只有 Collection 24 新增 Session 30，未归档从 31 减至 30；其余会话标题不变，只有 Session 15 发生指定改名。证据 preview5-workrecords-baseline.json、preview5-workrecords-after.json，以及 gui-preview5-h2-submenu.txt、gui-preview5-h2-left-scroll.txt。
- 本轮主菜单最右边缘翻转、菜单打开时由 resize 事件关闭、侧栏滚动关闭未单独验证。首次角部拖动未改变尺寸，未记 resize PASS；最大化后可访问性树一度不可用，恢复普通窗口后继续。工具状态不作产品缺陷；本轮也不替代用户最终验收。

## Preview.5 / H6 共享卸载与版本核对

QA-B 应用完成，arXiv 保留而非重复安装；持久化记录显示同一资产由 A/B 两个模块引用，仍保留已验证的归属指纹。A 卸载预检明确给出 research 预装保留、arXiv 共享保留、OpenAlex 独占移除。确认后逐项终态与磁盘一致：三侧 research/arXiv 的 SKILL.md 哈希不变，三侧 OpenAlex 已不存在，A 的三项关联解除；B 的 arXiv 关联保留。操作期间可关闭市场、查看 About，再返回读取执行终态。

本轮使用当前完整 QA 镜像与真实适配器，无模拟卸载。证据 gui-preview5-h6-b-complete.txt、gui-preview5-h6-a-uninstall-plan.txt、gui-preview5-h6-a-uninstalled.txt、h6-preview5-b-complete.json、h6-preview5-a-uninstalled.json。H6 的技能共享/预装/独占卸载子集 PASS，其他种类成员和跨目标边界不据此记通过。

帮助 → 关于实机显示 Workbench 2.1.18-preview.5、CLI/Bundle 0.1.10、Claude 2.1.314、Python 3.12.9；Workbench Image 显示未知，实际测试镜像按 Docker inspect 证据标识，不由该字段推测。版本证据 gui-preview5-about.txt。

用户修改保护 PASS：A 已卸载后，仅向 QA Claude 侧 arXiv 的 SKILL.md 追加可恢复注释，未改归属记录。B 此时为唯一引用，预检却正确改为“解除关联，保留资产 / 预装、归属不明，或已被模块外操作修改”；确认执行后仍保留修改内容，三侧文件均在，归属记录 owned=false、关联清空。之后通过 B 的“删除定义 → 确认移除”删除定义，界面先明确保留已安装扩展；磁盘比对只有定义与 revision 变化，资产与执行历史完全不变。QA 注释与原文备份留在隔离数据/证据目录，不写入产品源码。

证据 h6-user-edit.json、gui-preview5-h6-user-edit-plan.txt、gui-preview5-h6-user-edit-retained.txt、gui-preview5-h6-delete-definition-confirm.txt、h6-preview5-user-edit-retained.json、h6-preview5-b-definition-deleted.json。check_h6_preview5.py 对共享/预装/独占、修改保护和删除定义进行了交叉断言；MCP 配置修改保护、旧 adapter 与跨目标 GUI 仍不由本轮代替。

## Preview.5 / H5 混合类型定义

真实界面创建 QA-C，依次加入 research 技能、PubMed MCP、learn-with-coursera 插件，三者均显示实际安装标识及来源 URL，已选项按钮禁用。保存后磁盘定义含三种类型；再打开编辑器移除 PubMed，保存后显示两个成员，磁盘只保留技能和插件。期间没有为 C 创建或执行任何模块计划，技能文件状态不变；此处为定义编辑，不宣称 PubMed/Coursera 实际安装或调用已通过。

证据 gui-preview5-h5-mixed-editor.txt、h6-preview5-c-saved-user-edited.json、h6-preview5-c-two-saved.json。离线编辑、双窗口冲突及 U-4 默认模块仍未实测/未批准，继续保留边界。
