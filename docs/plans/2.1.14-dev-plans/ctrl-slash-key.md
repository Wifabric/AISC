# 批 4：Ctrl+/ 从 btw 切回 main（终端键盘修复）

> 状态：计划待用户验收（2026-09-23 立项）
> 来源：反馈站 20260922-codex-从btw切换回main的快捷-Alan（「/btw 切到旁路
> 进程后，只能 ctrl+c 关闭子进程，ctrl+/ 切换无反应」；D-1 纳入）
> 方法：ultracode workflow（研究员 + evidence/alt 双镜头核验，alt 镜头经
> 外部权威源交叉核验；verdict 均 corrected——legacy 别名、conhost 翻译层、
> 上游 PR 编码取向三处关键修正已并入）
> 对应 target：docs/todo.md「v2.1.14-target」反馈 #2 条目

## 1. 根因（核验确认，排除法完备）

**不是** WebView2 加速键拦截（键已到达页面，Ctrl+/ 不在已知加速键集），
**不是**全局 handler 吃键（App.vue:181-213 / Terminal.vue:1735-1857 /
WorkspaceView.vue:288-356 全部 window/容器级 handler 无 Ctrl+/ 分支），
**是 xterm.js 6.0.0 的 legacy 键盘映射表没有 Ctrl+/ 条目**：
node_modules/@xterm/xterm src/common/input/Keyboard.ts ctrl-only 分支只覆盖
A-Z、Space、数字、`[ \ ]` 等键，`'/'`（keyCode 191）无任何分支 →
result.key undefined → CoreBrowserTerminal.ts:1066-1068 `!result.key` 提前
返回静默丢弃 → PTY 零字节（唯一能解释「按键零反应」的环节）。该构建亦无
kitty keyboard protocol / modifyOtherKeys 编码能力（sourcesContent 正则
零命中）。

## 2. 关键核验修正（决定载荷选型）

- **codex 端绑定**：openai/codex `codex-rs/tui/src/keymap.rs`
  `toggle_side_conversation = default_bindings![ctrl(KeyCode::Char('/'))]`，
  且仅存该默认绑定时解析器**自动追加 legacy 别名**——`\x1F`（C0.US）同样
  有效（研究员原稿「裸 \x1F 明确不发」有误，已订正）。
- **上游取向**：xterm PR #5515（issue #5457，milestone 7.0.0）选定的标准
  编码正是 legacy `0x1F` 而非 CSI-u——直发 `\x1F` 与上游 7.0 未来行为一致
  且更简。
- **Windows 部署最大未验证风险**：codex/crossterm 在 Windows 读 console
  INPUT_RECORD（非 unix 字节解析器），CSI 47;5u 直发后必须先被 conhost 的
  ConPTY 输入引擎翻译成 `KEY_EVENT('/')+CTRL` 才能到 codex（现行 conhost
  支持 kitty 输入序列，但**须实测**；研究员未触及该层）。
- **手测语义修正**：`cat -v` 回显在 ConPTY 下不可靠（record vs bytes 两种
  投递语义），降级为参考项；「codex 实际切换」为唯一裁决。

## 3. 方案（D-6）

- Terminal.vue `onTermCustomKey`（keyup 守卫后，现有组合旁）新增分支：
  `mod && !shiftKey && !altKey && (e.key === '/' || e.code === 'Slash')`
  → `e.preventDefault(); writeSession(sessionId.value, bytes); return false;`
  （'/' 码点 47；与 e.code 并列提升非美式布局鲁棒性）。
- **载荷双臂手测定案**：臂 A `ESC[47;5u`（kitty CSI-u）、臂 B `\x1F`
  （legacy；上游一致 + codex 别名接收）。Windows conhost 翻译若只认其中
  一臂，以实测为准定稿（臂 B 预期更稳）。
- 仅修 Ctrl+/、对所有终端会话生效（与 kitty 终端一致，不按 agent gating）
  ——泛化「Ctrl+不可编码标点层」列后续可扩展项。
- 新增单测 `workbench/src/features/terminal/__tests__/terminalCtrlSlash.test.ts`
  （仿 terminalPasteKey.test.ts）：keydown ctrl+'/' → writeSession 字节断言
  + preventDefault + 返回 false；keyup 不发；Ctrl+Shift+/ 不发。
- 可选缓解（升级前）：变更说明附 codex config.toml 换键 workaround
  （绑定 legacy 可达组合），随发布口径定。

## 4. 同批裁决（U-2）

分屏键盘导航 Ctrl+Shift+hjkl / Ctrl+方向键（todo:81，WebView2 加速器层
拦截、COM 方案已放弃）与本项同域（终端键盘链路）：入批一并处理（如 WebView2
层放行方案的最后一试）或显式转期——开题时用户裁决。

## 5. 验收

见 [HANDTEST.md](HANDTEST.md) T4（步骤 1 字节链路基线/对照为参考项，
步骤 2 codex 实际往返切换为唯一裁决；SIGINT/既有快捷键/空 bash 干扰面回归；
vitest 新增用例）。
