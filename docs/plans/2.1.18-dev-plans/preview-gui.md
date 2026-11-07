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
