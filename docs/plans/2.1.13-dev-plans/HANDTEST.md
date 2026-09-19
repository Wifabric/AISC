# v2.1.13 批 1–6 手测清单（2026-09-19 自动化交付后统一手测）

> 覆盖批 1（发布链）/批 2（zip 恢复）/批 3（远程 CLI 配对）/批 4（docker 检测）/
> 批 5（变更页 + D-11）/批 6（拖图/粘贴图）。全部已过 local-gates + 远程 CI；
> 以下为实机确认项。每项通过后在行尾记 ✅ + 日期，失败项贴报错截图并回填 devlog。

## 批 1：发布链准备

- [ ] `aisc run` 在已有运行中容器的工作区 → exit 6 + 中文指引（进入/生命周期/多实例）
- [ ] 停止容器后 `aisc run` 正常激活；`--label` 多开不受影响
- [ ] （首发 tag 时）装机 preview.1 → 检查更新能检出 v2.1.13-preview.1 → 下载/校验/
      退出安装/手动重启后 About 显示 2.1.13-preview.1，数据与 PATH 保留（详见
      selfupdate-e2e.md §3）
- [ ] 设置页「关于与更新」文案为新表述（preview 范围说明 / 最新版本 / 退出并安装）

## 批 2：zip 恢复工作区

- [ ] 对工作区 A「彻底忘记」前先导出 zip → 恢复到新路径 B（目录预先不存在）→
      preflight/启动成功
- [ ] B 的会话选择器列出 A 的历史会话，claude 与 codex 各 resume 一条可正常收发
- [ ] provider 配置与 CLAUDE.md 记忆在位；toolchain 由启动自动重建
- [ ] 恢复对话框：目标 hash 已存在 → 明确拒绝；含 `../` 的 zip → 拒绝；
      旧版无 manifest 的 zip → 可恢复（来源信息为空）
- [ ] 首次成功启动前，B 不出现在最近列表（R4）
- [ ] 远程 target 下「从 zip 恢复…」按钮不显示

## 批 3：远程 CLI 版本配对

- [ ] NAS（CLI 落后一版）设置页 machines 组「检测」→ 显示远程版本/本机版本 +
      「需更新」+ 升级命令复制按钮
- [ ] 切换到该远程机器 → toast 一次（同机器同版本不重复弹）
- [ ] 远程手动 `pip install -U aisc-cli` 后重新检测 → 提示消失，且后续操作走新代码
- [ ] 版本一致 → 无提示；本机 dev 构建（0.1.2.dev0）→ 无提示噪音
- [ ] WorkspacePicker 远程 target 行「CLI 需更新」角标与设置页判定一致

## 批 4：docker 资源检测精细化

- [ ] 启动 Docker Desktop → 设置页磁盘组「详细检测」→ 五类分组逐项可见
      （镜像/容器/卷/构建缓存/网络），大小与 `docker system df -v` 人工对照一致
- [ ] 悬空镜像行「现有一键清理会命中」徽标准确（跑一次一键清理后复查徽标消失）
- [ ] 扫描期间无任何删除发生；「一键清理 / Docker 资源」原有按钮行为不变
- [ ] Docker 未运行 → 优雅降级文案（不崩溃）
- [ ] 卷行标注「AISC 永不删除」；网络只计数

## 批 5：变更页 + D-11

- [ ] repo 工作区：agent 改/增/删/重命名文件 → 变更树实时更新、徽标正确、
      点文件出 diff（±着色、二进制占位、大文件截断）
- [ ] 源指示行：repo=「git · 分支 · N」；非 repo/远程/宿主无 git →「会话变更 · N」
      且无报错
- [ ] 变更列表随 git 回滚自净（vscode 当前态语义）；agent 回滚后旧条目消失
- [ ] git 严格只读：任何位置都没有 stage/commit/discard 按钮
- [ ] **D-11 底部预览零残留**：文件树单击不弹预览；变更面板单击不弹预览
      （git 源下弹出的是 diff 面板，不是原始文件预览）；⌫搜索已清
- [ ] CRLF 仓库 diff 无全文件行尾噪音；会话中途 `git init` 源热切换；切工作区清理
- [ ] 非 git 工作区：watcher 行为与之前一致（1.5s poll、重命名识别不回退）

## 批 6：拖图/粘贴图给 agent

- [ ] Windows 资源管理器拖 png/jpg/gif/webp 进 claude/codex 会话 → 灰字提示
      「已上传 N 张」+ 终端出现 `'/root/app/.aisc/uploads/...'` token → agent 能读图
- [ ] 截图后 Ctrl+V → 落盘 + 插路径；纯文本粘贴不受影响
- [ ] 拖非图片 → 「仅支持图片文件」拒绝；无会话/dead pane → 拒绝不写 PTY
- [ ] explorer 内拖文件仍走纯路径引用链路（受控 MIME 优先）
- [ ] 多张（≤10）框选拖入 → 逐个落盘、token 一次插入
- [ ] 远程 target 拖图 → 上传到远程 `.aisc/uploads/` 成功
- [ ] git 仓工作区：`.aisc/uploads` 未出现在 git status（info/exclude 或观察）
- [ ] 超过 20MiB 的图片 → 明确失败提示

## 回归底线

- [ ] claude/codex/bash/cc-switch 四类会话开/关/分屏正常
- [ ] provider 页/cc-switch 切换正常（批 3-6 未触碰其数据面）
- [ ] pytest / cargo / vitest / vue-tsc 四门绿（已在交付时验证）
