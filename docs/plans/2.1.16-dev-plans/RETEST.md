# v2.1.16 统一复测手册（2026-10-20）

> 适用：develop ≥ i18n 渲染修复提交（b6+预复测修复）。前置：Docker Desktop
> 运行；dev 实例或含本阶段代码的安装包；测试工作区 `e:\projects`。
> 记录方式：每项 PASS/FAIL + 异常截图/文字；FAIL 立即反馈 Claude。

## 第一部分：b6 修复复测（R1–R4，用户上轮反馈）

### R1 TabBar 只保留 bash/codex/claude
1. Ready 视图顶部「+ ▾」→ 展开菜单。
2. **期望**：仅 Claude / Codex / Bash 三项；无「Provider 管理」、无分隔线。
3. 侧栏状态信息抽屉（ⓘ）→ 未配置供应商时点「打开 cc-switch」。
4. **期望**：不新增终端页签；左侧 dock 展开并切到「供应商」视图。

### R2 供应商视图
1. 左侧 rail 点「供应商」。
2. **期望**：标题「供应商」；Claude/Codex 切换 + Provider 卡片 + 「添加
   Provider」；整页无「暂无已注册服务（容器内运行 aisc-web-expose …）」。

### R3 关工作区 → 立即重进
1. 点「关闭工作区」→ 确认（结束会话+删除临时环境）。
2. **3 秒内**重选 `e:\projects` → 下一步。
3. **期望**：直达「启动摘要」→ 启动成功；全程无「启动已被阻断」/
   「另一个 Workbench 实例」。（预复测：+3.4s 重进 PASS）

### R4 扩展三页签
1. rail 点「扩展」。
2. 依次点「技能」「MCP」「插件」。
3. **期望**：三页签均保持渲染（视图不消失）；技能 ≥4 项（caveman 等，
   含 repo 与 C/X 开关）；MCP 列表（stdio/http 徽标）；插件 ≥4 项
   （name/marketplace/版本）；无 services 空文案。
   （预复测发现并已修：i18n 文案 `{mcpServers…}` 与 `name@marketplace`
   被 vue-i18n 当语法解析 → 渲染崩溃 → 切页签视图消失。）

## 第二部分：全阶段回归（T1–T15）

### b1 容器内自更新（T1–T4）
- T1 codex：进 codex 页签触发更新提示→确认→**无 EEXIST**；更新后重开
  页签版本已升；`which codex` 仍 `/usr/local/bin/codex`。
- T2 claude：同 T1（claude 页签）。
- T3 落点：Bash 页签 `npm config get prefix` → `/tmp/aisc-toolchain/npm-global`
  （temporary）或 `/opt/aisc/toolchain/npm-global`（project）。
- T4 持久：project 模式更新 codex 后关/开工作区，版本保持。

### b2 Work Records（T5–T9）
- T5 左键行 → 只读 viewer 弹出（非 resume）。
- T6 拖父节点 → 整树移动（目标记录按序出现，源记录清空）。
- T7 右键 → 「新建会话」（新空页签）/「分支会话」（fork）；操作后列表即时刷新。
- T8 打开/刷新瞬间显示「加载中…」而非「引用缺失」。
- T9 右键删除同名会话 → 确认弹窗显示数量（如 2）→ 确认后全部消失；
  另一 agent 同名不受影响。

### b3 Docker 资源面板（T10–T12）
- T10 设置→磁盘与缓存→「扫描 Docker 资源」：卡片网格（合计卡 + 六类）；
  「构建缓存（可清理）」中文；无裸 "Build Cache"。
- T11 「清理构建缓存」：确认→日志 builder/dangling 回收量→卡片刷新；
  容器与正常镜像不变。
- T12 按钮序：扫描 / 清理AISC / 清理构建缓存 / 重建（最右）；未扫描时
  三操作禁用。

### b5 扩展管理（T13–T15）
- T13 rail 六视图 + 供应商/扩展可进入；TabBar 无 Provider 虚拟页签。
- T14 技能 C/X 开关往返；列表与 `docker exec <ct> cc-switch skills list` 一致。
- T15（破坏性，按需）：
  - MCP 新增：粘贴 `{"mcpServers":{"test2":{"command":"echo"}}}` → 新增 →
    列表出现 + 容器内 `grep -A3 test2 /root/.codex/config.toml` 可见。
  - 删除 `cuse-test`（预复测遗留）：右键/删除按钮 → 确认 → 列表与
    config.toml 同步消失。
  - 插件：装一个小插件（如 `skill-creator@claude-plugins-official`）→
    出现→卸载→消失。
  - 技能安装：`owner/name:directory` 形态（需网络）。

### tests.yml 矩阵（可选，Claude 侧）
- 无需手测；九组矩阵最近一次全绿记录在 GitHub Actions。

## 第三部分：验收口径
- R1–R4 + T1–T15 全 PASS → 可宣布收尾（§1.1.3，由你宣布）。
- 个别 FAIL → 反馈 Claude，修复后只需复测对应项。
- T15 破坏性项如暂不方便可标注「延后」，不阻塞收尾裁决。
