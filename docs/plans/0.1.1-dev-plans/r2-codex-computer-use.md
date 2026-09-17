# R2 调研：codex computer use 实现原理与容器落地（codex 0.154.0 基线）

> 状态：初稿 / 2026-09-17 / 待用户验收（D-14 裁决门：评审通过前不写任何实施代码）
> 版本基线：AISC 容器 pin `@openai/codex` 0.154.0（`config/versions.env`，npm registry 元数据实测）；Workbench 侧 agent 无关。检索日期 2026-09-17。
> 方法：官方文档/仓库检索 + 本仓库 file:line 事实（容器现状、wrapper、安全红线）。

## 1. 原理：Codex 侧的 computer use 机制（2026 年形态）

**关键结论：OpenAI 的 computer use 主体在 Codex 桌面应用，不在开源 CLI；CLI 侧的现状是「MCP 服务器可挂载」而非原生内置。**

- **Codex 桌面应用**（macOS 首发、2026-03-04 登陆 Windows）原生具备 computer use：申请系统 **Accessibility 与 Screenshot 权限**后，可视觉驱动 Figma/Notion/浏览器等任意应用（"see, click, and type"）。三种控制形态：全桌面控制、Chrome 扩展、应用内浏览器。来源：[Introducing the Codex App（OpenAI 官方）](https://openai.com/index/introducing-the-codex-app/)、[Digital Applied 解读](https://www.digitalapplied.com/blog/openai-codex-desktop-computer-use-plugins-guide)、[Totalum Windows 篇](https://www.totalum.app/blog/codex-computer-use-windows-totalum)。
- **Codex CLI（openai/codex，AISC 所用的就是它）**：仓库无原生 computer use 子命令；社区追踪 issue [openai/codex#20851](https://github.com/openai/codex/issues/20851) 报告 `codex mcp list` 可见 OpenAI 捆绑插件缓存里的 computer-use MCP 服务器（版本依赖，非稳定公开契约）。CLI 是 MCP 客户端——**computer use 能力经 MCP 服务器挂载**（官方捆版或第三方如 [open-codex-computer-use](https://mcpservers.org/servers/ifuryst/open-codex-computer-use)，后者支持 mac/Linux/Windows 截图驱动）。
- **Anthropic 侧机制对照**（AISC 容器 vendored claude-api skill 已含）：computer use tool 是 **client-side tool**——API 请求中定义工具，模型返回动作请求（screenshot / left_click / type / key），**执行发生在应用方环境**，结果回传。来源：[Claude Platform Docs — computer use tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)、[tool reference（client tool 定义）](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-reference)。

**一句话原理**：模型只「看截图、发动作」；桌面环境、鼠标键盘执行、截屏通道全部由宿主侧（我们）提供——两条 CLI（claude/codex）在这一点上机制同构。

## 2. 容器落地三路线对比表

现状底座：容器 `node:22-slim`，apt 清单**零图形组件**（container/Dockerfile，无 X11/Wayland/VNC/Chromium）；`/usr/local/bin/codex` 是 wrapper（真身 codex-real，Dockerfile:303-310 拦截结构）。

| 维度 | 路线一：容器加显示栈（Xvfb + 虚拟桌面 + 截屏工具） | 路线二：headless 浏览器（CDP，Playwright/Chromium 类） | 路线三：宿主侧视觉通道（容器外截图/执行，回传图像） |
| --- | --- | --- | --- |
| 镜像体积增量 | +100~300MB（Xvfb/x11-utils/xdotool + 字体；对照：Xvfb+VNC 组合增量约 100-300MB，来源 [Testing Academy](https://app.thetestingacademy.com/playwright/learn-docker/index.html)/[Medium 实践](https://realsanjeev.medium.com/run-playwright-in-headed-gui-inside-docker-using-vnc-eef860fb4f33)） | +750MB~2GB（Playwright 官方镜像 ~750MB slim / ~1.5-2GB 全量；Alpine 不兼容） | **~0**（工具在宿主） |
| 实现复杂度 | 高：虚拟显示编排 + 截屏工具选型 + MCP server 包装（自研或引入 open-codex-computer-use）+ 字体/中文渲染 | 中：Chromium 就绪 + CDP MCP server（生态成熟）；但只覆盖「浏览器内」任务，桌面级任务做不了 | 高：Workbench↔容器↔宿主三段图像回传通道 + 权限模型全新；与 AISC「CLI 在容器、UI 在宿主」架构冲突最大 |
| 与 wrapper 拦截冲突 | 需改 codex-wrapper：注入 MCP server 配置（`--mcp` 或 config），wrapper 结构可保留（拦截层外挂） | 同左；浏览器进程在 wrapper 之外，冲突最小 | 无容器内冲突，但绕过容器隔离本身 |
| vendor + versions.env 成本 | 高：Dockerfile/entrypoint/新增下载物全部进 vendor checksums 链（§6.4），且截图工具需钉版本 | 高：同左 + Chromium 版本钉版（上游发版频繁，漂移最快） | 低：容器不动，宿主侧独立分发 |
| 安全面扩大 | **最大**：agent 获得容器内「鼠标键盘级」控制 + 截屏（见 §3） | 中：控制范围限浏览器内（cookie/登录态集中地——仍高危但可审计） | 最大且跨边界：宿主侧执行 = 突破容器隔离，等于直接操作用户真机 |

## 3. 安全影响章节（对齐 DEVELOP_WIKI §12.1 红线）

现状红线：容器以 **root** 运行（bind mount 写权限兼容性）；codex-wrapper 默认 `--dangerously-bypass-approvals-and-sandbox`（container/codex-wrapper:33-52）—— approvals 与沙箱双绕过。

**叠加 computer use 的威胁面**：
1. **权限乘法**：现状 agent 已能任意读写挂载的工作区；computer use 再加「截取屏幕内容 + 模拟输入」。工作区外逃逸面不变（仍在容器内），但**信息泄露面质变**——若走路线三（宿主视觉通道），截到的可能是用户真机任意窗口（密码管理器、私聊、银行页面）。
2. **提示注入升级**：网页/文档中的恶意指令（"请截图确认"）从「影响文本输出」升级为「驱动鼠标键盘」——钓鱼页面可以直接诱导 agent 点击授权按钮。
3. **不可审计性**：鼠标键盘动作序列比文本命令更难事后追责（终端 spool 有完整回放；GUI 动作无对等记录）。

**最小化方案（任何后续实施的强制前提）**：
- **默认关、显式开**：能力以设置项/环境变量门控，默认不装载对应 MCP server（doctor 检查项报告状态）。
- **范围限定**：只走路线一或二（**否决路线三**——宿主执行突破容器边界，与 §12.1「容器不是强沙箱」的坦诚定位叠加后无任何边界可言）。
- **截屏脱敏义务**：实施时 README 警告 + wrapper 注入显式横幅（agent 会话首行声明「本会话具备屏幕视觉能力」），联动 wrappers 的义务按 §12.1 执行。
- **审计**：动作序列写入数据根 op-trace（复用 REL-01 时间线）。

## 4. AISC 对照结论

- **是否值得做**：**暂不做原生实施**。理由：① CLI 侧能力依赖上游捆绑 MCP 插件（#20851 未稳定，契约随版本漂移——与 D-9 钉版联动后可锁定，但收益/成本比差）；② 用户主诉求（浏览器内任务）可用更轻的 MCP 浏览器服务器在**不改镜像**的前提下由用户自行挂载试验；③ 桌面级 computer use 的正主是 Codex 桌面应用（宿主产品），容器内复刻是低配高险。
- **先决条件（若未来重启）**：codex 版本钉版并验证其 MCP computer-use 插件契约（D-9 的 pin 基建已就绪）；node 基底已 22（无阻塞）；vendor 门禁预算一次（路线一 +100-300MB 或路线二 +750MB）。
- **建议形态**：先以「文档 + 用户自挂 MCP 服务器」满足尝鲜（不改 container/，零 vendor 成本）；观察上游 #20851 稳定化为公开契约后再评估路线二（headless 浏览器，面最小）。
- **不做门槛**：路线三（宿主侧执行）永久否决，除非安全模型重立。

---
*检索日期 2026-09-17；来源均为官方文档/仓库（URL 内嵌）。实施与否由用户另行裁决。*
