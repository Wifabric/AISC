# AISC 术语表

本表定义 AISC 项目使用的领域语言；只解释概念，不承载流程或实现细节。

## 产物线

**Workbench**：桌面端应用（Tauri + Vue），主线产物，发布为 Windows 安装器。
_Avoid_: 桌面端、客户端、GUI

**CLI**：命令行工具（Python 包 aisc-cli），独立定版，发布到 PyPI。
_Avoid_: 命令行、终端工具

## 运行时概念

**工作区（workspace）**：引擎会话运行的工作目录，保存 Provider 配置与运行状态。
_Avoid_: 目录、项目

**引擎（engine）**：Claude、Codex、Bash 三种会话类型。
_Avoid_: 会话、模型

**Provider**：模型供应商配置（官方直连或第三方）。
_Avoid_: 供应商、渠道

**集合（collection）**：工作记录的分组。
_Avoid_: 分组、分类

**覆盖升级**：安装器覆盖旧版本安装，保留原工作区数据与配置。
_Avoid_: 升级、更新

## 反馈与交付

**反馈站**：用户问题与需求收集站点（Wifabric/aisc-issues-feedback，文件式存储）。
_Avoid_: 反馈、issue、工单

**统一 Preview**：把多来源输入合并到一个预览版本做验收。
_Avoid_: 预览、候选版
