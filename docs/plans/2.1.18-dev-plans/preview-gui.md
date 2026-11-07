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
