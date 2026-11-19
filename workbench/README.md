# AISC Workbench 开发与验收入口

本目录为 AISC 桌面端（Vue/TypeScript + Tauri/Rust），通过 CLI 和 Docker 运行 Claude/Codex。本分支定版为 **2.1.19**，配套 CLI **0.3.0**；版本事实源是 `src-tauri/tauri.conf.json` 和仓库的 `src/aisc/VERSION`，不要使用前端工具包的 package.json 版本作为产品版本。

用户使用见[根 README](../README.md)，本版变化见[发布说明](../docs/releases/v2.1.19-preview.1.md)，操作参考见[功能验收教程](../docs/plans/2.1.19-dev-plans/HANDTEST.md)，测试证据与发布准备见[交付记录](../docs/plans/2.1.19-dev-plans/DELIVERY.md)。2026-11-19 用户已确认本轮功能及剩余安装交互手测全部通过。

## 准备真实桌面环境

开发需要 Python、Node、Rust/C++ 工具链及 Docker，首次配置与各平台差异见 [DEVELOP_WIKI](../DEVELOP_WIKI.md)。以下命令从仓库根目录执行，前提是工具链和虚拟环境已按手册准备；不是一个会自动安装全部依赖的脚本。

```powershell
. scripts\dev-env.ps1
powershell -File scripts\build-cli.ps1
.venv\Scripts\python.exe packaging\artifact.py stage --root . --output workbench\src-tauri\nsis\bundle
Set-Location workbench
npm ci
npm run tauri dev
```

克隆仓库不带冻结 CLI 和 staged bundle。只运行 `npm run dev` 得到的是前端网页，不能据此验证 Rust、SSH、安装器或容器功能。已有 Workbench/CLI 进程可能锁住 sidecar，重新构建前按脚本提示关闭对应实例。

## 本版变更如何生效

| 改动 | 接续要求 |
| --- | --- |
| Vue/TypeScript 界面 | 使用当前候选前端；桌面拖动需在真实 Tauri 窗口检查 |
| Rust 本地文件与运行时桥接 | 重新构建桌面程序，不能仅重启网页 |
| CLI 文件服务、工作记录和启动目录 | 使用同一候选 CLI；SSH 机器也部署对应版本 |
| 技能、Provider 适配器、代理节点、gh | 将当前 container/config/vendor 资源 stage 到 bundle，再构建并选择测试镜像 |
| NSIS/签名配置 | 按[安装器维护说明](src-tauri/nsis/README.md)构建实际安装包，另行做安装链路验收 |

serve protocol 保持 4，但旧 CLI 不一定支持新增 `fs.move`、`network nodes` 和启动目录。测试时应核对实际 executable 与 bundle 来源，避免运行旧的已安装 AISC。

## 运行与验收

在独立测试目录使用本版配套资源，不覆盖日常数据；源码构建可按开发手册用 `--aisc-cli` 指定候选 CLI。便携测试包同样必须包含正确的 Workbench、CLI 和 bundle，不转发个人配置或已有测试凭据。

前端命令（在本目录执行）：

```bash
npm test
npm run build
```

Rust、Python、真实容器与 GUI 的适用检查见开发手册及本版 HANDTEST。记录实际候选 head、环境、结果和证据；未执行的自动化项不因用户手测通过而改记开发者 PASS。PR #104、#105 均已合入 develop，当前集成提交为 6877334d。Provider 编码单测、Windows 静默安装/升级与用户安装交互验收已通过，具体来源见 DELIVERY。

## 打包与发布

Windows 构建入口为仓库 `scripts/build-installer.ps1`；需先准备 sidecar 与 bundle，签名配置由发布方提供。[Preview Release](https://github.com/Wifabric/AISC/releases/tag/v2.1.19-preview.1) 已公开，候选仍未签名，签名按用户决定暂不处理。[2.1.19 正式版说明](../docs/releases/v2.1.19.md)已定稿，用户已授权正式发布，构建与渠道状态见 DELIVERY。Workbench notes 按 `docs/releases/v<Workbench版本>.md` 命名，CLI notes 独立维护；先同步两个版本事实源，再构建并验证正式包，不能仅重命名 Preview 安装包。创建 PR、推送、tag 和发布沿用用户当次授权。
