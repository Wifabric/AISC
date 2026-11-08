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

## Preview.5 / H5 双窗口冲突与 S8 可见性修正

重启候选后 QA-C 的两个成员仍在。通过“操作 → 新建窗口”打开独立 ui-workspace-peer，与原 QA 工作区使用相同用户配置、不同 workspace/runtime；两容器分别为 6bf30965bb6d / c32962952ba7，均使用 keep 62d358f2…，所有挂载位于 p18 QA 范围。原平台容器 2e801ec161c0 保持运行。

两窗口从 revision 9 打开同一 QA-C，分别改名 A/B。A 保存变为 revision 10；B 旧稿保存拒绝，磁盘与 A 保存后的文件完全一致，B 输入仍保留。B 点击“重新读取定义”后列表显示 A 的最新名称，草稿仍为 B；再次明确保存后变为 revision 11。成员和其他模块均不变，check_h5_conflict.py 交叉核对通过。此处验证保存冲突保护与显式恢复，不是合并两个草稿。

B 最后保存期间，仅断开专用 peer 容器的 bridge 网络，inspect 显示无网络端点；本地定义仍成功保存，随后恢复 bridge。未修改 Windows 网络、其他容器或用户配置；该证据为运行目标离线，不扩写为整机离线。证据 h5-two-window-{baseline,a-saved,b-rejected,b-recovered}.json、h5-peer-network-{offline,online}.json、gui-preview5-h5-conflict-reloaded.txt。

S8：803×631 短窗口中，在编辑器底部点击保存后，冲突文本位于上方不可见区域，画面停在保存按钮，必须手动上滚才见错误和恢复入口。数据保护正确，但错误可见性不足。为模块持久化错误在渲染后执行最近边界滚动；空名称拒绝也定位其提示，包括连续重复提交。不改焦点、不清空草稿、不自动重试、不放宽 revision 校验。组件回归覆盖冲突提示定位、草稿保留、用户重新读取前无二次保存、新 revision 显式保存及重复空名称拒绝；相关模块 13 passed，类型和生产构建通过。修正版候选、CI 和真实 GUI 复测另记，Preview.5 不代表修后结果。

旧候选证据 gui-preview5-h5-conflict-offscreen.txt、gui-preview5-h5-conflict-visible.txt；本地测试 module-feedback-tests.log、module-feedback-build.log。U-4、跨目标安装状态和其余 H 项仍按各自记录处理。

## Preview.6 / S8 修后实机验证

PR #87 head 195ff2b6d 的 CI 42425026074 frontend/rust/cli 均 success，合入 develop 5677a6e6。本机 Workbench 与 384429548 字节 NSIS 重建完成，CLI/bundle 与 Preview.5 相同。真实 About 显示 Workbench 2.1.18-preview.6、CLI/Bundle 0.1.10。工作区仍为独立 ui-workspace，QA 容器 c1d5609d21d2、镜像 keep 62d358f2…；原平台进程 40320 保留。

818×669 窗口在 QA-C 编辑器底部提交空名称，提示“请输入模块名称。”自动滚入可见区域；连续再次提交仍定位提示，revision 保持 11。再输入有效名称后，用受控夹具只改独立 QA 配置中的 QA-A 名称并将 revision 置为 12，模拟外部写入。底部保存旧稿被拒绝，冲突提示自动滚入可见区域，QA-C 草稿保留。此轮是新版错误可见性的故障注入，真实双窗口冲突证据仍为上一轮 Preview.5，不混写。

外部写入文件与拒绝后的文件 SHA256 均为 e04bc6fd7e50281cbd954d8ed2405a13e3eb7c200ba5f85ccd542d090bbb312b。点击“重新读取定义”后列表显示 QA-A 的新名称，QA-C 草稿仍为“QA-C Preview6 冲突恢复”；再次明确保存后 revision 13，QA-A 外部修改及其他成员全部保留。check_h5_preview6.py 核对 revision 11→12→12→13、拒绝不覆盖、显式恢复和成员保留均 PASS。QA-A 测试名称留在隔离数据，不还原整份旧配置。

证据：gui-preview6-h5-{empty-visible,conflict-visible,reloaded,recovered}.txt、h5-preview6-{before-conflict,external-definition,conflict-rejected,recovered}.json、gui-preview6-about.txt。S8 真实界面回归 PASS；未代替完整 H5/H6 或 U-4 默认模块验收。

## Preview.6 / H2 侧栏滚动与窗口尺寸

打开未归档 Session 17 的右键菜单后滚动菜单外的工作记录侧栏，菜单正常关闭。重新打开后通过 Windows 原生“大小”操作从 818×669 缩窄到 646×669；进入原生调整模式时应用菜单仍在，完成实际尺寸变化后菜单关闭，没有残留脱离目标的菜单。直接拖边首次未改变尺寸，不将该次尝试计作 resize 通过。

check_workrecords_preview6.py 与 Preview.5 保存后的记录对比：24 个集合 ID/名称/状态/成员以及 30 条未归档会话标题均不变。证据 gui-preview6-h2-sidebar-scroll-closed.txt、gui-preview6-h2-resize-closed.txt、preview6-workrecords-after.json。本轮补齐侧栏滚动和实际窗口缩窄关闭；主菜单最右边缘翻转仍未单独实测，用户最终验收仍待完成。

## Preview.6 / H9 离线失败、显式恢复与来源

重新启动同一 Preview.6，独立 ui-workspace 容器 c8bfc514a6c6 使用完整 keep 62d358f2… 镜像。记录三侧技能文件基线后，仅断开此容器的 bridge 网络；inspect 网络端点为空，未改 Windows 网络或原平台容器。

真实界面搜索 grill，显示“缓存结果”、上次成功时间与 DNS 失败说明，仍保留已缓存结果。展开 grill-me 后先显示读取中，随后明确显示 Cannot read upstream SKILL.md 错误、来源仓库链接及“重新读取”按钮，未将占位文案记成功。恢复同一容器 bridge 后首次明确重试仍返回读取失败；本轮未定位该次请求失败的底层原因。随后只读探测同容器的公开 GitHub commit/raw 接口均返回 200，再次点击“重新读取”成功，错误消失，显示实际简介。不能把恢复网络后的第一次尝试写成成功。

切换 caveman 查询后结果不含旧 grill 详情；再搜索 grill，grill-me 简介仍在，另外两条 grill-with-docs/grilling 简介恢复。重新打开 grill-me 的来源链接指向固定提交 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d 的 skills/productivity/grill-me/SKILL.md。可访问性读取器曾在原链接节点更新后保留旧仓库地址，重新打开的新节点与直接只读适配器结果一致，未据此改产品代码。

市场还返回 batch-grill-me，但该固定提交的 tree 中只有 grill-me、grill-with-docs、grilling 三个匹配路径，没有 batch-grill-me。展开该陈旧条目明确显示 No unique matching skill path 并保留重试/来源入口。此项是市场元数据与上游目录差异，不编造成功内容。曾尝试在其读取期间切换查询，但错误在提交新查询前已返回，因此本轮只证明普通查询切换隔离，不记迟到响应竞态 PASS。

1,545 个三侧已安装技能文件的路径/哈希前后一致，未执行安装/卸载。网络已恢复；证据 gui-preview6-h9-{offline-detail,first-reconnect-failure,recovered-detail,query-caveman,reopened-source}.txt、h9-preview6-network-{offline,online}.json、h9-preview6-online-probe.jsonl、h9-preview6-upstream-paths.json、h9-preview6-assets-{before,after}.json。H9 离线失败、明确重试恢复、缓存/固定来源子集 PASS；跨工作区切换和真实迟到响应仍由自动化覆盖，GUI 未补齐。用户最终验收继续待完成。

## Preview.6 / H4/S9 完整无缓存与取消清理缺陷

真实启动摘要入口默认无缓存，CLI 实际带 --no-cache。完整 bundle 经准备、73 步、导出到 100%，123.8 秒完成；所选 QA tag 从 73426400… 更新到 82352869…，另一个 keep tag 62d358f2… 不变，停止容器 f69201ad… 仍引用原镜像，界面明确提示旧镜像因引用而保留。此路径 PASS。证据 gui-preview6-h4-nocache-{confirm,progress,phase,success}.txt、h4-preview6-{before,after,start-command,build-command}.json 及 nocache-build.log。

随后取消勾选无缓存，首次缓存重建 12.5 秒先完成（实际 --use-cache），所选 tag 更新为 cd42b288…，无其他引用的上一镜像按规则移除。该次没有成功取消，不计取消 PASS。第二次缓存构建在导出阶段点击取消，界面 9.8 秒显示“已取消”；所选 cd42b288…、keep 与停止容器保持不变，但留下该次临时 tag aisc-rebuild:8b913b4cd5214457ab57b4ccd8f41e23（1779cc6f…）。因此取消终态/原资源保护通过，临时资源清理 FAIL，登记 S9，不将整个取消路径记通过。

根因：Windows 强制终止 CLI/Docker 进程树，Python finally 可能未执行。修复由 build.start 传递本次唯一临时 tag，Workbench 等待子进程退出、事件排空后用独立 CLI 回收；严格限制保留命名空间和 32 位小写十六进制，只删除该 tag，不按镜像 ID、不强制、不扫描其他临时资源。清理仍持维护锁，失败保留原取消/失败状态并显示残留 tag 提示；操作锁直到清理完成才释放。

保存原始残留证据后，新源码清理命令实际回收上述 QA tag，再次 inspect 证明所选/keep/停止容器不变。此项是源码 CLI 恢复验证，不能代替修后冻结候选 GUI。隔离工作区镜像恢复 keep，候选窗口正常关闭，原用户平台 PID 40320 保留。证据 gui-preview6-h4-cache-{completed-first,cancelled}.txt、h4-preview6-cache-command.json、h4-preview6-cache-cancel-build.log、h4-preview6-cancel-audit.json。修后 GUI/远程入口/最终用户验收仍待完成。

## Preview.7 / H4/S9 修后取消与受控残留恢复

PR #91 head 5414a099192da1372380426fa2006b0f58c28016 的 CI 42429010839 三项 success，合入 develop 3b26609e7f0aef9f5eec449a91638c11eadb048e。重新冻结 CLI、Workbench/NSIS 打包成功，完整 bundle 未变化。真实 About 显示 2.1.18-preview.7 / CLI/Bundle 0.1.10，四项产物大小/哈希核对 PASS；旧 Preview.6 保留历史备份。

启动摘要选择同一专用 selected tag cd42b288…，取消默认无缓存勾选后启动，真实界面点击取消，9.5 秒显示“已取消”；日志证明此次在导出前取消，未生成临时 tag。selected/keep 62d358f2… 与原停止容器 f69201ad… 不变，无构建进程残留。此项覆盖缓存构建的正常取消与原资源保护，未重现自然导出阶段的精确竞态时间窗。

为实际覆盖“临时 tag 已存在”的恢复分支，另一次真实无缓存构建启动后，从候选 CLI 的 Docker 子进程命令行读取本次唯一临时 tag e936ef3b…，确认尚不存在，再将已知 QA keep 镜像临时加此 tag，模拟中断时残留。未改产品代码、CLI 或 Docker 执行器，也没有替换 selected。通过真实界面的取消按钮终止，27.5 秒显示“已取消”；Workbench 的恢复处理移除了此精确 tag，keep 共享镜像、selected 和停止容器均保留，三项构建进程全部结束。没有在取消后手动清理该 tag。该项为受控残留 GUI 测试，不冒充自然导出竞态复现。

额外冻结 CLI 的真实 Docker 精确 tag 回收和重复调用（removed→absent）通过，共享镜像不受影响。check_h4_preview7.py 核对两次资源结果和四项候选哈希 PASS。证据 gui-preview7-h4-{cache,seeded}-cancelled.txt、gui-preview7-about.txt、h4-preview7-{seeded-residual,result}.json、h4-preview7-{cache,seeded}-cancel-build.log、frozen-cancel-cleanup.json。QA 镜像设置恢复 keep，候选正常退出，原用户平台保留。

S9 已修复并完成上述实际回归；远程入口 GUI、自然导出竞态时间窗再次复现、清理失败的真实 GUI 仍未执行（拒绝/失败可见已有自动化测试）。不将本条扩大为完整 H4、整版用户验收或发布批准。

## Preview.7 / H7、H10 与 S10 首次安装登记格式

在独立 ui-workspace-peer（runtime e2415038、容器 9928be8f111c、keep 62d358f2 镜像）测试，初始插件列表为空。当前真实目录未返回历史 mattpocock-skills@claude-plugins-official，改用同仓库但不同市场身份 skills-for-real-engineers@anthropic-plugin-directory；不把两者当作同一插件版本。上游当前版本为 1.2.3 / c55ee46073ed923f86ce59a5eb3b6d895095d1b7。

通过独立进程持有真实插件操作锁，界面安装返回 unknown，提示操作仍在运行、刷新后重试，失败卡片没有重试按钮；真实列表仍为空、mutation_running=true。详情安装按钮仍可点击，但后端锁拒绝操作，不宣称所有入口均禁用。点击关闭失败提示后，卡片和重复行内提示消失，锁和安装状态不变。释放受控锁后 mutation_running=false，未启动重复安装。H7 未知结果保护、H10 未知结果关闭子集通过；不等同于网络超时后的最终恢复。

锁释放后正常安装明确失败：当前目录安装器拒绝读取平台工厂预置的 installed_plugins.json 空对象 `{}`。最初检查了非实际配置路径；实际 CLAUDE_CONFIG_DIR=/root/.claude，文件存在且为三字节空对象，不能归因为文件缺失。S10 修正工厂初始格式为 version=2、plugins={}；旧工作区仅在明确安装操作、已有插件锁内将准确的空对象原子升级。不补造缺失文件，不覆盖已有记录、损坏内容或符号链接；替换前复核原字节，异常明确失败，清理仅限本次创建的临时文件。

把修复适配器部署到该 QA 容器后，在真实市场界面再次点击安装，成功显示 1.2.3-c55ee46073ed。冻结 CLI 回读、v2 磁盘登记及真实插件 manifest 一致，mutation_running=false；另一个 QA 工作区插件登记 SHA256 e558f007a32be4b4ad14851e2d6e12ab2f44ae35dcbb2d8e5a2ff348c0ca493f 不变。历史失败卡片仍保留，不写成自动清除成功。本轮是 Preview.7 GUI + 源码适配器测试部署，标准候选 bundle 尚未更新，不代表旧包自带此修复。

适配器/工厂相关测试 94 passed、16 subtests，覆盖首次安装、重复安装幂等、缺失/非空/损坏保护、替换失败、外部内容变化以及临时名称碰撞不删他人文件。单代理自查，无独立评审。完整门禁、精确 head CI、新候选与镜像工厂验证另记。证据 h7-preview7-{peer-baseline,current-market,registry-deployment,registry-recovered}.json、gui-preview7-h7-{busy-card,registry-failure,registry-recovered}.txt、gui-preview7-h10-unknown-dismissed.txt。未改用户平台或 Windows 网络。

## Preview.8 / S10 新镜像与标准候选

PR #93 head 43f5934029a9b2594ea5bce6467e880a2848b40c 的 CI 42432013590 frontend/rust/cli 全部 success，合入 develop e5c17c3eb7eb13bebf2a42db0556caea92b77633。本地完整 Python 1812 passed / 54 skipped / 212 subtests、Rust 422 passed / 2 ignored、前端 888 passed，类型/生产构建通过。资源清单 1534 项，仅 Dockerfile 与适配器两项变化。

新完整 bundle 校验通过，冻结 CLI 使用该 bundle 构建专用镜像 aisc-s10-43f59340:preview8（6df61d6a8181de5df038ff4f2f6ca421397176f2852e140824ab747fdc4479e9）。无挂载容器检查 factory installed_plugins.json 已为 v2 空对象，adapter SHA256 32942114b713e91e8d5b6d8f38f8c211aa6cba27188f5225c356ccd59f3fc607 与产品源码一致。

Preview.8 首次构建 0b87b3de… 在全新 ui-workspace-fresh8 启动此镜像，runtime a70605ce、容器 755328f2835f。没有部署覆盖适配器或手工修改登记，真实初始化后 v2/plugins={}、列表为空；从市场正常安装 skills-for-real-engineers@anthropic-plugin-directory 成功，版本 1.2.3-c55ee46073ed，真实磁盘/冻结 CLI 一致，操作锁已释放，其他两个 QA 工作区登记哈希不变。

打包前逐文件对比发现本轮 checksum 脚本的临时文件被带入初次 stage；精确移除并完整校验后重新构建 NSIS，旧初次安装包不交付。误收集测试产生的 QA 字节码也由 bundle verify 明确拒绝并清理。最终标准目录相对 Preview.7 恰好只改变 Dockerfile、适配器和 checksum 三个 bundle 文件；其他资源逐文件哈希一致，旧可执行程序/manifest/三项资源已备份。最终 Workbench SHA256 为 9ed704cf0dd575a5f17be6f80f5258c091acc0c410e8aeda85f37eb42582104e，与首次 GUI 构建的二进制哈希不同，分别记账，不声称首次安装发生在最终二进制上。

最终标准候选重新启动相同工作区，镜像设置仍指向专用新镜像。实际 GUI 显示已安装插件及相同版本，没有失败提示；磁盘登记及两个其他工作区哈希不变，最终容器 0895fe4b9e12 / runtime 839170dd-498d-40ea-a213-673055dc7a71。帮助 → 关于显示 Workbench 2.1.18-preview.8、CLI/Bundle 0.1.10，四项产物哈希核验通过。两次构建采用相同产品源码/适配器；此处最终二进制验证的是重启、状态回读与 About，不替代全量手测。

证据 s10-image-build.jsonl、s10-image-verification.json、h7-preview8-{baseline,installed}.json、gui-preview8-first-build-installed.txt、gui-preview8-final-{installed,about}.txt、preview8-final-verification.json。旧空登记迁移证据仍归属前文 Preview.7 测试部署，新工厂路径归属本节。S10 已修；其他 H 项未测边界、U-4、本人认证、最终验收与发布保持原状态。

## S11 / 已有工作区切换新镜像时登记被覆盖

Preview.8 标准 GUI 在主 QA 工作区切换到 S10 镜像后，模块预检正确显示 research/arXiv 保留、OpenAlex 缺失，尚未确认执行。文件基线比对却失败：启动前插件登记 SHA256 为 e558f007…，启动后变成工厂 v2 空登记。发生于容器初始化、早于模块预检；本次跨目标用例中断，不能记录为通过。原用户平台未改动。

根因是 entrypoint 在工厂版本变化时对整个 plugins 目录执行 cp -ru，较新的工厂登记覆盖用户运行态。同源检查还确认，skills/plugins 目录缺失时的完整补全也会覆盖既有登记和 settings。修复把两项登记（installed_plugins.json、known_marketplaces.json）改为只补缺失，其他工厂资产保持原增量规则；非强制补全使用不覆盖复制，显式 FORCE_COPY_CLAUDE 保持原重置语义。

测试直接执行产品 entrypoint 的作用域初始化段。无网络、只读挂载的临时 Linux 容器：旧代码 6 failed / 5 passed；修后 11 passed，涵盖非空/空/损坏登记保留、符号链接及悬空链接、缺目录补全、缺登记补种、正常新工作区和显式强制复制。Windows 关联 92 passed / 3 skipped / 41 subtests，符号链接的两项 Windows 跳过由上述 Linux 实跑覆盖。测试只证明初始化段；完整启动、真实 GUI 与新候选仍待验证，不提前记为完成。

证据 target-isolation-baseline.json、gui-preview8-isolation-primary-plan.txt、s11-preview8-registry-reset.json、s11-linux-{before,after}.log、s11-linux-results.json、s11-related.log。历史 h7-preview4-installed.json 可重建与故障前哈希完全相同的 QA 登记备份 s11-primary-registry-before.json；后续恢复/升级回归另记。按本轮执行调整，剩余代码和验证文档集中同一整合分支，完成后统一提交收尾 PR。

### S11 完整镜像启动与重启的数据面验证

完整 stage9 bundle 校验通过：1534 项清单仅 entrypoint.sh 一项变化，启动脚本 SHA256 `70b826e84f18fd920b726d9ebf9cab7f3b20b6a81eed9740c26a7fa80edfb00e`。冻结 CLI 使用既有固定依赖 receipt 构建独立 `aisc-s11-entrypoint:preview9` 镜像 `7f60b3472290ea5f8fc1d58b5f1034d2d94d703abd20bc57e6ab575e995481f6`，镜像内脚本与修复源码逐字节相同；未覆盖用户镜像或标准 Preview.8 bundle。

在 QA 容器关闭后，恢复与故障前哈希完全一致的插件登记，确认旧插件缓存 manifest 仍为 1.3.1；明确将 QA 工厂标记设回旧 QA 镜像的实际值，以受控重现旧→新同步。随后冻结 CLI 正常启动完整修复镜像，容器 `dc6a5660ef97` 日志确认执行出厂增量同步，工厂标记推进至 `007ebc9e7b6c7b9d708d06f9d5ac689fad3844c7`。两项登记、两项设置、插件 manifest 和三引擎指定技能共 14 个存在性/哈希状态与基线一致；两份其他 QA 工作区插件登记及模块定义不变。

初次直接 docker exec 适配器未继承 PID 1 作用域，读到了默认路径的空列表；改用产品同一 `_SCOPE_WRAPPER` 后回读原 `mattpocock-skills@claude-plugins-official` 正确。这是验证入口修正，不另记产品缺陷。产品 CLI 对指定测试容器执行 restart 后再次比对通过，最后 stop 正常结束并移除该临时容器，持久数据保留；原用户平台容器 `2e801ec161c0` 仍运行。

本轮 GUI 重新连接新 QA 窗口时返回 `foreground window did not report a process id`，遵循工具恢复边界停止 UI 输入。上述为完整镜像真实 CLI 数据面证据，不写成 GUI PASS；标准 Preview.8 仍不包含 S11，未新建 PR。证据 s11-image-build.jsonl、s11-runtime-{start,restart,stop}.json、s11-upgrade-baseline.json、s11-{upgrade,restart}-result.json 及初始化日志。下一步继续同分支整合、GUI/候选验证和统一 PR/CI。

## Preview.9 / S11 标准候选续测

重新初始化 CU 后恢复窗口读取与输入。为本地提交 `11b5b18ff19732c803cf89387f2c5ea73e9bf7ff` 构建 Preview.9；逐文件部署校验发现 CLI 数据面测试在 stage9 bundle 内产生了两个空状态文件 containers.json / .containers.lock，部署在复制前被拒绝。确认内容并备份移除后重新校验、重建安装包；第一包未交付。最终 bundle 与 Preview.8 相比仅 entrypoint.sh 和 vendor/checksums.txt 两项变化，四项产物哈希见 DELIVERY/本机 manifest，旧 Preview.8 备份保留。NSIS 为 384421234 字节；尚未执行安装/升级向导，不把构建完成当作安装验收。

CLI 测试使用显式容器名 stop 后，实际 QA 工作区仍留有一条属于该已删除容器的旧登记；GUI 预检正确以 unknown_owner 阻止自动删除。核对专属名称、镜像、工作区与 Docker 不存在结果并备份后，仅用产品 unregister API 清理此测试登记；重试预检通过。未删除其他登记、实际容器或持久资产。

通过真实启动设置把主 QA 工作区指向完整 S11 镜像。标准 Preview.9 启动容器 cc6e6f94f28d / runtime bcc5055e-4775-49c5-abd3-3902b778da51，插件页显示原 mattpocock-skills@claude-plugins-official 1.3.1。同一时刻验证镜像、四项产物哈希、14 个受保护文件状态、另外两个工作区登记及模块定义全部一致；证据 preview9-primary-verification.json、gui-preview9-plugin-preserved.txt。这是 S11 数据面升级后的标准 GUI 启动/状态回读，未声明已完成全部 H6/H7。

### H6 同窗跨工作区预检隔离

主 QA 工作区对 QA-A 生成计划 a91f29c7：research/arXiv 保留，OpenAlex 缺失；未点击确认执行。正常关闭工作区后，在同一窗口切到 ui-workspace-fresh8，并通过启动设置选同一完整 S11 镜像；新容器 36f66d47579a / runtime a13da003-477c-4c36-ab13-22ef6294e809。相同用户的两份模块定义可见，旧待确认计划未带入；操作记录显示历史结果区但无前一目标的步骤。新预检生成计划 3989cf79，三项均按该目标的实际快照列为缺失。不能因插件内可能包含同名能力，就把它记作已安装的同来源独立技能。

两计划 ID、容器和 runtime 各自独立，所有行仍为 planned；主目标动作为 retain/retain/install，第二目标为 install/install/install。两侧指定的 18 个技能路径存在性/哈希、插件登记及模块定义前后匹配，未隐式安装或卸载。About 显示 2.1.18-preview.9 / CLI 与 Bundle 0.1.10，最终四项产物哈希匹配；正常退出后两个 QA 容器均结束，原平台仍运行。证据 gui-preview9-isolation-{primary-plan,fresh-before-plan,fresh-history,fresh-plan}.txt、target-isolation-{primary-plan,fresh-plan,final}.json、preview9-isolation-result.json、gui-preview9-about.txt。本项只覆盖跨目标预检/计划/记录隔离，不包含安装执行中切换。

### H7/H10 受控原生超时、安装中关闭切换与恢复

标准 Preview.9 / 同一完整 S11 镜像启动全新 ui-workspace-timeout9，容器 9762d4e99b9b / runtime 9e566d02-2f89-48f8-b248-58091bcf771d，实际插件列表为空。在此可丢弃容器中把 claude-real 入口改为仅对 skills-for-real-engineers@anthropic-plugin-directory 的 plugin install 调用延迟 195 秒后转交原生程序；所有其他命令直接转交，产品 adapter、180 秒原生超时、冻结 CLI 和 GUI 均未改变。其他三个 QA 工作区登记先取哈希基线。此夹具模拟慢安装，不是自然慢网复现。

真实市场界面点击安装后，按钮禁用；记录只有一次调用，PID 899 存活、mutation_running=true、插件列表为空。原有超时机制结束进程后，界面明确显示“安装进程已结束，核对后插件尚未安装，可以重试。”，卡片提供重试，详情安装按钮恢复。检查时距调用开始 202.59 秒，这是观察时间而非精确终止耗时；PID 已消失、锁释放、列表仍为空，没有误报成功或执行镜像重试。

同一夹具延迟改成 35 秒，从失败卡片点击重试：第二次调用 PID 1249 存活且持锁，界面显示安装中，卡片重试按钮消失。趁其仍运行时正常关闭工作区并确认结束临时环境，旧容器实际移除，持久登记仍为 v2 空列表。工作区选择页曾短暂出现旧调用结束的失败 toast；不声称整个退出期间没有通知。在同一窗口启动 fresh8 后，实际容器 a5cd881feae4 / runtime 6740f800-b78d-4bad-a419-a75f6b420350，插件页显示该目标既有的 1.2.3-c55ee46073ed，旧失败卡片、安装中状态和 toast 均未带入；三个其他工作区登记哈希匹配。

再次正常关闭 fresh8，重新打开 timeout9，容器 de1aee8a1d6c / runtime 475cfb7a-a074-476f-872d-dd4bf9f24e8e。此容器不存在延迟夹具，原生 claude-real SHA256 4487042b4c4f5d88d4568f68ae98aae0b1ffae58864cf57fb868641bc5f84594 与部署前相同，adapter 仍为 32942114…。界面列表为空，再从真实市场安装同一插件；实际原生进程完成下载，GUI 和作用域适配器一致显示 1.2.3-c55ee46073ed，锁释放。正常退出候选后，三次 QA runtime 均已移除；其他工作区登记、候选四项哈希保持一致，原用户平台 PID 40320 和容器仍运行。

证据 h7-timeout9-{deployment,running,timed-out,retry-running,switched,final,result}.json、gui-h7-timeout9-{running,failed,retrying,switched,recovered}.txt。通过范围为受控原生超时、明确重试、安装进行中正常关闭再切目标、失败卡片隔离和重启后正常安装恢复；不覆盖模块安装进行中切换、两个目标同时存活时的迟到响应、自然慢网或用户本人验收。没有新增产品代码、构建或 PR，文档保留在同一收尾分支。

### H9 详情迟到响应与跨工作区隔离

标准 Preview.9 在主 QA 工作区启动完整 S11 镜像，容器 b3ad035cd769。实际适配器读取 grill-me 成功，来源仍为固定提交 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d 的 skills/productivity/grill-me/SKILL.md。部署前记录四个 QA 工作区三引擎 skills 文件和顶层插件 JSON 登记共 1,942 项路径/哈希。在此临时容器中保留原适配器逐字节副本，用透明入口仅对 mattpocock/skills 的 skill-describe 调用缓冲真实 stdout/stderr，至少到调用开始后 35 秒再原样交付；没有编造内容、修改 GUI、正式 bundle 或超时参数。

真实 GUI 搜索 grill，展开 grill-me 显示“正在读取上游功能介绍…”。输入新查询 caveman 后，首个 grill-me 响应先完成，因此不将它写作成功撞中迟到窗口。旧查询的串行后台第二项 grill-with-docs（PID 508）仍在延迟交付时，新 caveman 查询已显示完整结果；当时实际上游成功响应已保存，但 wrapper 尚存活、没有 response-delivered 事件。随后该响应按原样成功交付，wrapper 退出，新界面仍只有 caveman 结果，没有旧 grill 条目/详情。这一交叠顺序有独立进程事件和前后 GUI 文本佐证，区别于 Preview.6 的普通查询切换。

再展开 mattpocock/skills 的 caveman 条目，真实界面显示详情加载中，wrapper PID 717 存活。该市场条目在固定上游目录中未找到唯一路径，实际响应为 AISC_ERR_EXTENSIONS_NOT_FOUND；响应尚未交付时正常关闭工作区，旧容器随运行环境结束而移除。随后同窗打开 fresh8，容器 b662dfd2513c / runtime a976fff7-66e2-476f-bae2-c4445d6717dd，适配器哈希与未修改产品一致。新目标技能市场查询框为空、暂无搜索结果，旧加载/错误未带入。重新搜索 grill，真实原生链正常显示 grill-me、grill-with-docs、grilling 简介，展开 grill-me 来源为上述固定提交。没有把陈旧 caveman 条目记为详情成功，也不把关闭旧 runtime 的场景写成两目标同时存活时的成功迟到回调。

正常退出后两个 QA runtime 均结束；1,942 项资产和候选四项哈希不变，用户原平台 PID 40320 / 容器仍运行。本轮只读详情，未执行任何安装或卸载。证据 h9-preview9-{deployment,query-pending,query-submitted,new-query-visible,query-delivered,workspace-pending,switched,final}.json、gui-h9-preview9-{query-loading,new-query,query-after-delivery,workspace-loading,switched-empty,switched-loaded}.txt。H9 受控迟到查询响应、详情读取中关闭切换、新目标独立读取通过；最终用户验收待完成。候选二进制未重建，验证记录仍集中收尾分支。


### D-17 / Preview.10–11 三层能力

Preview.10 真实新工作区显示 16 项离线技能、两项默认模块；科研模块 arXiv/OpenAlex 从缺失经在线安装变为已安装。个人通用协作模板建立副本，GUI 保存 V1，再按反馈保存 V2，恢复 V1 后保存为 V3，三版历史保留。GUI Claude 被未认证门拦下，没有操作登录；另用实际冻结 CLI 创建隔离原生 Claude/Codex 会话，生产参数与 GUI V3 快照完全匹配（SHA256 d213f1c6f180ee9348139393a3543ac059f9740a7562259e7f38c8bbc7b07b2a），随后正常结束。没有发送模型任务，不能视为认证后的效果验证。

最终 Preview.11 产品提交 7edb677d，完整镜像 sha256:22891f8aa447f6d3c09f3b9a53bb40a7edc00a20192d36f9acfe8548dd44db14。Preview.10 正常退出后，GUI 选择已有 ui-personal10、改为新镜像并启动。容器 d9342ac154ff，个人能力与主题入口、三模板和 V3 显示正常；个人登记文件重启前后 SHA256 均为 99e0ec3e1f886a285aeee210999358cba5dda31d0b8628a67790f97e61ec0561。扩展列表保留 caveman 13 / mattpocock 2 / Karpathy 1 / 科研在线技能 2。证据 gui-personal11-restarted.txt、gui-personal11-extensions.txt、personal11-before-restart.json；产物哈希见 DELIVERY。用户原平台容器 2e801ec161c0 保持运行。

上述为开发者真实界面和数据链验证，不是最终用户验收；安装器 GUI、真实提供者/GitHub 认证、模型任务及前文未测边界仍未完成。

Preview.11 帮助 → 关于的真实截图确认 Workbench 2.1.18-preview.11、AISC CLI/Bundle 0.1.10、Claude Code 2.1.314；Workbench Image 字段仍为“未知”，镜像身份另以实际容器/image inspect 记录核对，没有把该字段记为成功。

### Preview.11 开发者续测：H2 / H5 / H6

候选二进制与完整镜像不变，PR #95 已合入 develop c9b21cf2；精确最终 head 55561c22 的三项 CI 成功，合并树相同。以下均为隔离 QA 环境中的开发者验证，不是最终用户验收。

- H5：真实 GUI 将默认科研模块另存为“QA Final 科研副本”，隐藏默认模块再恢复；副本保留两个成员，默认模块重新显示。配置 revision 13→14→15→16，原有两份定义及 272 项技能/插件资产文件哈希不变。证据 `final-h5-{baseline,hidden,result}.json`、`gui-final-h5-{hidden,restored}.txt`。
- H2：694 像素宽窗口右侧 x540 触发菜单，主菜单翻到 x380，六项动作均可见；779 像素宽窗口的移入子菜单左展，两项目的地可见。Escape 返回原记录可见焦点，磁盘记录逐项相同。首轮核对因 D:/ 与 D:\\ 参数表示不同失败，统一入口后通过，属于测试比较修正。证据 `final-h2-{baseline,result}.json`、`gui-final-h2-{right-edge,main-left-flip}.txt`。
- H6：在 ui-personal10 专用容器以真实适配器准备四个无凭据 QA 插件与 Context7 MCP；模块 A 安装、B 引用共享插件后，受控修改一个插件文件和 MCP URL。真实 GUI 卸载 A，预装、共享、用户修改插件、用户修改 MCP、既有 GitHub 均保留，仅独占测试插件移除；六行终态与真实安装清单一致。GitHub 仍待本人认证，未声称可调用。证据 `final-h6-result.json`、`gui-final-h6-{plan,complete}.txt`。
- H6 旧适配器：透明入口仅拒绝 --ownership，其余操作转交原始适配器；真实 GUI 卸载预检在缺少指纹证据时保留共享测试插件，没有执行破坏性卸载。原适配器恢复后 SHA256 仍为 32942114b713e91e8d5b6d8f38f8c211aa6cba27188f5225c356ccd59f3fc607。证据 `gui-final-h6-legacy-plan.txt` 及 `final-h6-result.json`。

H6 执行中跨目标：第一轮 125 秒延迟已在新工作区启动前返回，不算交叠通过。第二轮保留两个运行环境 d9342ac154ff / 71553d5c60d5（相同 Preview.11 完整镜像）。GUI 原目标显示 3/6 执行中，真实插件安装响应已成功产生、由透明 QA 入口缓冲；通过命令面板“选择工作区…”切到已运行的 fresh8。独立记录确认新界面出现时两容器均运行、旧响应尚未交付，再主动释放。旧计划 7763c55c 的第 4 项完成为 installed，第 5/6 项仍 planned；新目标 module-status.latest 为 null，插件页仅有该目标原先的 skills-for-real-engineers，旧测试插件和加载状态没有带入。此项实际覆盖两个目标同时存活时的成功迟到响应与后续步骤停止。没有改变产品超时或伪造成功结果。

证据 `final-h6-cross-{pending,delivered}.json`、`gui-final-h6-cross-{running,new-before-delivery,new-after-delivery,new-plugins}.txt`。原适配器已恢复；四个测试插件、模拟 Context7 配置、本地测试市场及三份本轮测试模块定义通过明确身份清理，原有两份模块定义和 GitHub 配置保留。候选正常退出后两套 QA runtime 均已移除，原用户平台 PID 40320 / 容器 2e801ec161c0 仍运行，候选三文件及安装包 SHA256 与 manifest 一致。`final-qa-cleanup.json` 记录最终核对结果。

### Preview.11 开发者续测：H3 / H4 异常清理

仍使用冻结的 Preview.11 Workbench、CLI 和完整 bundle。独立 QA 启动使用透明 CLI/Docker 转发入口，仅对明确测试标签注入 rmi 失败；真实 Docker 状态同时取证，没有改动正式产物或全局 PATH。初版夹具因 stdin 未及时 flush 导致协议超时，修正转发后重跑；这些尝试不作为产品失败或验证通过。

- H3：真实 GUI 将 `aisc-final-fault-2b7702c3:keep` 改为 `:gui-partial`，仅旧 tag 删除被注入失败。界面表单与历史显示 `new tag created; old tag retained`，没有报全成功。Docker 核对新旧标签与其他三项标签均指向原镜像 `0582b629adcf…`。解除注入后在相同 GUI 表单重试，只有选中的 `:keep` 被移除，其余四个 tag 和镜像 ID 不变；表单关闭，新增“操作完成，列表已刷新。”，旧错误历史保留。
- H4：对专用 QA 镜像执行 GUI 重建。夹具在生产代码生成的临时 tag `aisc-rebuild:2d3504c2bba3426096ac24b6b75e473a` 上创建真实 Docker 别名并暂缓 build，点击“取消构建”；只使该临时 tag 的 rmi 失败。界面终态“已取消”，明确显示“临时构建标签可能仍存在”及准确标签，技术详情保留清理错误。Docker 中实际残留与提示一致，原标签/镜像不变。解除注入后，冻结 CLI `maintenance docker-rebuild-cleanup` 返回 removed，再执行返回 absent。此测试覆盖取消清理失败路径，不是自然构建导出竞态复现，也不声称本次完成了一次真实全量构建。

证据目录 `output/verification/final-docker-fault/`：`gui-h3-partial.txt`、`gui-h3-retry.txt`、`h3-{partial,retry}-inspect.json`、`gui-h4-cleanup-failure.txt`、`h4-{before,after}-cancel.json`、`h4-cleanup-{retry,absent}.json`、`events.log`。核对镜像 ID、专属 tag 前缀且无容器引用后，已移除本轮所有 QA 镜像标签；故障进程全部退出，测试开关移除，四项产物哈希与原平台存活记录见 `final-result.json`。SSH/远程 GUI 与自然导出竞态仍未覆盖。

### Preview.11 开发者续测：H7 / H9 两个存活目标的迟到响应

标准启动脚本开启 Preview.11，两个 QA 工作区 `ui-personal10` / `ui-workspace-fresh8` 分别运行容器 `359760eaf200` / `f18765722d0b`，实际镜像均为 `22891f8aa447…`。通过命令面板“选择工作区…”保留旧 runtime，并在同一窗口切到另一已运行目标。只在临时容器中用透明适配器入口缓冲真实响应，不改变产品超时或编造成功状态。

H9：真实市场搜索 grill、展开 grill-me，GUI 显示“正在读取上游功能介绍…”。第一次尝试缓冲超过 60 秒接口预算，只保留为超时边界记录，不能证明成功回调晚到。两目标预先连接后重新执行：PID 627 于 `1794118586.087` 开始，上游于 `1794118591.627` 成功；新工作区已显示就绪后释放旧响应，于 `1794118626.304` 原样交付，总耗时 40.22 秒，早于 `runtime.rs` 的 60 秒期限。新目标技能市场查询为空、暂无搜索结果，没有旧 grill 条目或详情；原固定来源仍为提交 `4ae2317d…` 的 `skills/productivity/grill-me/SKILL.md`。2,203 项技能文件/插件登记哈希与本轮基线一致，wrapper 无存活进程，原适配器 SHA256 恢复为 `32942114b713e91e8d5b6d8f38f8c211aa6cba27188f5225c356ccd59f3fc607`。证据 `final-h9-{deployment,fast-delivered,final-check}.json`、`gui-final-h9-fast-{loading,new-before,new-after}.txt`；首次未达成功条件的记录也保留。

H7：fresh8 注册一个只含插件元数据的本地 QA 市场，从真实 GUI 搜索并安装 `late-response@aisc-final-h7`。原生安装于 `1794118820.656` 成功，界面仍显示安装中、安装按钮禁用，透明入口暂不交付结果。切到 personal10 后，两容器均运行、旧响应仍未交付；主动释放后于 `1794118868.157` 成功返回，距调用开始 49.01 秒，未到生产超时。新目标插件页仍为“暂无内容”，没有旧安装状态；切回 fresh8，真实 GUI 显示测试插件 1.0.0 和原有 skills-for-real-engineers。数据面同时确认新目标清单为空，旧目标只有预期新增插件。证据 `final-h7-{baseline,pending,new-before,delivered}.json`、`gui-final-h7-{running,new-before,new-after,returned}.txt`。这是本地插件的受控成功延迟交付，不是自然慢网复现。

随后恢复原适配器，通过实际适配器卸载唯一测试插件、原生客户端移除 QA 市场，原插件清单与另一目标清单恢复/保持基线，两侧锁释放。首轮清理比较把每次变化的 operation_id 也纳入相等判断，导致夹具断言失败；改为比较完整 items 后通过，没有重复执行卸载。`final-h7-cleanup.json` 记录稳定状态核验。候选正常退出结束两活动会话，两个 QA 容器实际移除，原平台 PID 40320 / 容器 2e801ec161c0 保持运行；三项候选文件与安装包哈希不变，见 `final-boundaries-result.json`。

上述 Preview.11 GUI 续测没有产品修改或重建。随后仓库文档门禁修正经 #96 合入；下面记录新一轮远程验证及 S15 修复，取代“缺隔离 SSH 目标”的旧阻塞。

### Preview.12 / S15：真实 SSH 改名与远程镜像维护

2026-11-08，在仅监听 127.0.0.1:22228 的专用 SSH 容器中运行独立 Docker 引擎；外层容器无宿主目录或 Docker socket 挂载。导入完整 Preview.11 镜像，78 层 RootFS 与宿主候选相同。远端使用同一候选源码 CLI / bundle 0.1.10，Workbench 使用独立数据根。只有 QA 文件、镜像标签受操作；用户原平台保持运行。

- **修前 FAIL**：Preview.11 GUI 把 `AREA.txt` 改为已有 `Occupied.txt`，后端 `os.replace` 覆盖 `keep-me` 为 `qa-file` 且报成功。保留 `s15-before-gui-data.json`，恢复 QA 夹具后修复 S15。此前 Docker 下层目录大小写改名 EXDEV 在直接系统调用中也复现，改用可写层夹具后验证，不把夹具限制记为产品修复。
- **修后 PASS**：Preview.12 GUI 同样冲突显示“同名文件已存在，未覆盖”；两个文件内容均保持。文件 `Area.txt → AREA.txt`、目录 `Folder → FOLDER` 成功，目录内 `child.txt` 保持 `qa-child`。Windows 定向 39 passed / 3 skipped；Linux 新增本地回归 11 passed，覆盖独立大小写条目、硬链接、悬空链接、空目录、竞争中新建目标与平台不支持时拒绝覆盖。新增回归没有上传。
- **H3 远程 PASS**：真实设置 → 磁盘与缓存扫描只列出远端 1 个运行容器和 1 个镜像。默认名称为 `super-claude:<8位字母数字>`；选中 `super-claude:qa-remote-old` 改为 `:qa-remote-new` 后显示“操作完成，列表已刷新。”。实际 RepoTags 仅旧标签被替换，`aisc-personal:preview11`、`:latest`、`:qa-remote-keep` 保留，镜像 ID `d63cf511274c…` 不变。
- **H4 远程 PASS**：扫描前后两个重建入口均 disabled，说明“目标：本机。暂不支持远程重建。”；没有执行远程构建或停止引用容器。
- **版本 PASS**：帮助 → 关于显示 Workbench `2.1.18-preview.12`、CLI/Bundle `0.1.10`。Workbench Image 字段仍“未知”，以实际 inspect 取证，不把该字段记为成功。

日志位于 `output/verification/` 的 `s15-*`、`remote-qa/gui-preview12-*`。本轮同时修正两个既有 shell 测试硬编码的 Git Bash 路径，Node 从已激活工具链发现；Windows staging 测试的子进程预算由 30 秒改为 120 秒，断言和 POSIX 预算不变。早期前端一次 Python 启动失败来自沙箱，原生环境复验 893 passed；Rust 422 passed / 2 ignored。最终完整 Python `tests`（不含 integration）1833 passed / 58 skipped / 218 subtests，前轮失败日志保留。精确 head CI 结果在集成账本补录。

正常退出并重新启动 Preview.12 后，通过最近工作区重新进入远端，刷新文件列表并展开 `FOLDER`，`AREA.txt`、`Occupied.txt` 与 `FOLDER/child.txt` 均保持精确名称；启动摘要中的远程重建入口也 disabled。证据 `gui-preview12-reopened.txt`、`gui-preview12-summary.txt`。

独立 Windows runner 的 NSIS 安装、重装、卸载保留检查在 develop `1fad34f7` 的 [run 42456585925](https://github.com/Wifabric/AISC/actions/runs/42456585925) 全部成功，release job 跳过。这是 CI 重建安装包的自动安装验证，不是本机 Preview.12 交互式安装 GUI，也不能替代 S15 新 head 的 CI。真实本人认证、模型任务、最终用户验收及发布批准仍未执行。
