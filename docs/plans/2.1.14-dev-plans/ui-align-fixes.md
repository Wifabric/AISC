# 批 3：UI 对齐三小项（高级槽位间距 / 历史页徽标 / 关于弹窗超高）

> 状态：计划待用户验收（2026-09-23 立项）
> 来源：todo v2.1.14-target 两条 + 反馈站 20260922-历史记录页-徽标按钮未对齐
> （D-1 纳入）；三 size 均 S、验收形态相同，据 D-2/D-5 合批
> 方法：ultracode workflow（研究员 + 独立证据核验 + 图像分析；verdict 均
> corrected——批号归属冲突、越界阈值、版本窗口归属等修正已并入；本稿历史
> 归属一律用 commit 哈希）
> 对应 target：docs/todo.md「v2.1.14-target」UI 两条 + 反馈 #3

## A. claude provider 高级槽位输入框间距

- **根因（一处生效于全部 claude 模板）**：ModelMappingEditor.vue:103 高级
  展开区 `<div v-if="advancedOpen">` 是**无 class、无样式的裸包装 div**。
  容器 `.mapping`（169：`display:flex; flex-direction:column; gap:8px`）的
  gap 只作用于直接子元素——SONNET/OPUS/HAIKU 三主行正常吃 8px，MODEL/
  SUBAGENT 两行是包装 div 的子级，包装 div 无 gap，`.row`（171）无纵向
  margin → 零间距贴合。核验确认：无其他样式来源反向推翻，机制唯一。
- **修法**：包装 div 加 class（如 `adv`），scoped 样式
  `.adv { display:flex; flex-direction:column; gap: var(--space-2); }`——
  与主行节奏一致；不改模板结构、不动 i18n、不影响 codex 分支。
- **可选顺带**（纯等值令牌化，视觉零变化）：该文件硬编码 `gap:8px`
  （.mapping:169 / .row:171 / .cat-head:195-196 / .cat-row:197-198）迁移
  `--space-2`（styles.css:9-12 令牌注释明文要求 var() 而非裸值）。

## B. 历史页徽标/按钮未对齐（反馈 #3，截图 393×275）

- **根因分层（非批 9 回归；组头 .conversation-group-label 无错位）**：
  1. **胶囊规格不统一**（7ddd73c 引入 hover chip 起）：`.cv-view-chip`
     1px 边框 + 上下 1px padding（盒高比徽标多约 4px）、radius 999px；
     `.explorer-badge`/`.agent-glyph` 零垂直 padding、`--radius-sm`——两套
     胶囊高度/圆角/内边距三不同；
  2. **徽标字形度量污染**（6ecb789 / c54579b 起，一直存在）：✳(U+2733)/
     ◈(U+25C8) 与文字同 span，Windows/Chrome 回退 Segoe UI Symbol/emoji
     字体撑大行盒；flex `align-items:center` 居中盒子而非墨迹 → 徽标整体
     偏高、✳ 顶部上凸；
  3. **混排字号光学落差**（e7d8dbd 起）：13px 标题与 11px 条数/徽标按盒
     居中而非基线对齐，天然 ~1px 落差；
  4. 散值违规：`gap:6px`（令牌表只有 4/8px 档）、`1px 8px`、`0 4px`、
     `999px` 均为令牌外裸值（WorkspaceExplorer.vue:1468-1473 区域）。
- **修法**（全部落 WorkspaceExplorer.vue + styles.css 一枚新令牌）：
  新增共享胶囊基类（chip 与 agent-glyph 共用 `height:20px; line-height:1;
  padding:0 var(--space-2); border-radius:var(--radius-pill)`，chip 保留边框、
  徽标补同宽 transparent 边框保证严格等高）；✳/◈ 独立内层 span（line-height:1）
  或按 TypeIcon.vue 先例改 SVG（根治回退字体度量）；条数 label 同款 inline-flex；
  散值全部映射 `--space-*`/`--radius-pill`（styles.css 令牌区新增
  `--radius-pill: 999px`）。徽标是否 `margin-left:auto` 右锚消除常驻空隙、
  `.conversation-row` 的 `flex-wrap:wrap` 去留——视觉设计项，随批验收时定。
- **待手测复核**：截图⑤「悬停行更高」与代码结构（chip 常驻占位 +
  min-height 24px 应等高）矛盾，疑视错觉；①④精确像素根因建议 DevTools
  getBoundingClientRect 复核（影响是否必须 SVG 化）。

## C. 关于弹窗超高无滚动条（回归）

- **定位**：症状对象是 帮助→「关于 AISC Workbench」的 **DoctorDialog**
  （诊断结果弹窗），非设置页「关于与更新」（后者已有定高+内部滚动）。
- **根因（结构缺陷 + 内容推高显性化）**：DoctorDialog 无 Teleport，直接渲染
  在 App 的 `ui.font_scale` zoom 作用域内（FloatingPane/CommandPalette/
  ToastHost 均已 Teleport 逃逸并自挂 zoom，唯独它漏掉）。zoom 把 `.panel` 的
  `max-height:84vh` 连同弹层整体按字号系数放大：**竖向越界需 84vh×k>100vh
  即 k>约 1.19**（核验修正：字号滑杆 0.8-1.5 步进 0.05，**≥1.20 档必现**，
  1.05-1.15 不越界）；内容未超 max-height 前 overflow:auto 永不触发——无
  滚动条、尾部不可达。内容推高来自 ee8ce35/d6b7005 给 doctor 新增
  bundle-store、channel-confusion 检查项（14+ 组×至多 4 行；核验修正：
  两提交属 **2.1.12 窗口**，2.1.13 只是显性化，回归叙述勿找错版本）。
- **修法（照 FloatingPane 惯例，FloatingPane.vue:51 先例）**：模板外包
  `<Teleport to="body">`；`.panel` 自挂 `:style="{ zoom: uiScale }"`；
  `.panel` 改定高 `height: min(620px, 84vh)`、overflow 收 hidden，`.body`
  （flex:1; min-height:0; overflow-y:auto）成为唯一滚动容器。
- **前置确认**：用户实际 `ui.font_scale` 需手测确认（若 ≤1.19 则 zoom 机制
  不成立，需另查——alt 镜头已标注此不确定性）。

## 验收

见 [HANDTEST.md](HANDTEST.md) T3（字号 1.25/1.5 + 800×600 小窗、DevTools
getBoundingClientRect 字段级断言、双主题往返、vitest 基线不降）。
