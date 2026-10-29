# v2.1.17 R2 Implementation Plan: Extension UI Redesign

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Extensions experience around installed-asset management, a categorized market dialog, meaningful bilingual details, and maintainable skill/plugin sources.

**Architecture:** Keep `ExtensionsView.vue` as the quiet installed-asset surface. Move discovery, categorized recommendations, search details, and source maintenance into focused dialog/panel components. Extend the existing adapter → CLI → Rust bridge → Pinia path with repository/marketplace list-and-remove operations; do not bypass the data-plane boundary.

**Tech Stack:** Vue 3 + Pinia + vue-i18n + existing CSS tokens; Python adapter/CLI; Rust Tauri bridge; Vitest / pytest / cargo tests.

**Spec:** User ruling on 2026-10-29: remove the operation log; move recommendations to a separate Extension Market dialog; show a brief Chinese introduction in details; improve the whole layout; maintain added source links; recommendations must be categorized (research / education / etc.) with exactly ten prominent entries per category based on project fit and market heat.

## Non-negotiable requirements

1. The Extensions main view must not embed the historical operation-log list.
2. The main view exposes an `扩展市场` action; recommendations live only in that dialog.
3. Recommendation catalog categories each contain **exactly 10** unique entries.
4. Details opened from installed or market rows must show a non-empty brief Chinese introduction in `zh-CN`, not just the item name.
5. Skill repositories must support list/add/remove. Plugin marketplaces must support list/add/remove. MCP maintains installed-server deletion; Smithery remains a built-in search source, not a deletable local repository.
6. Unknown/timeout operation recovery remains available through a compact current-failure surface, without exposing a persistent operation history.
7. No new UI dependency and no online translation service. First-party summaries are local; unknown market items retain the original market text.
8. Follow the app-screen style: quiet chrome, 1px separation/tone steps, restrained accent use, real metadata, honest empty/error states.

## 2026-10-29 recommendation evidence snapshot

Selection blended:

- project fit to AISC coding/research/document workflows;
- skills.sh install counts observed through the bundled cc-switch market/API on 2026-10-29;
- Smithery MCP usage metadata observed through the existing adapter on 2026-10-29;
- official Claude plugin directory inclusion/category when the source has no public install count.

No popularity number is invented. Plugin entries selected from the bundled official directory are marked `official-directory`; skills/MCP entries carry observed heat where available.

### Category catalog: six categories × 10

| Category | Selected identities |
| --- | --- |
| 科学研究 | `mattpocock/skills:research`; `llllllllama/rigorpilot-skills:ai-research-explore`; `llllllllama/rigorpilot-skills:ai-research-reproduction`; `google-deepmind/science-skills:literature-search-arxiv`; `google-deepmind/science-skills:literature-search-openalex`; `google-deepmind/science-skills:pubmed-database`; `google-deepmind/science-skills:literature-search-europepmc`; `firecrawl/skills:firecrawl-research-index`; MCP `pubmed`; MCP `consensus` |
| 教育学习 | MCP `microsoft/learn_mcp`; MCP `clouatre-labs/math-mcp`; MCP `vocab-voyage/vocab-voyage-mcp`; MCP `flash-cards/flash`; MCP `ltt2019051173/bloom-study-guide`; `github/awesome-copilot:add-educational-comments`; `samber/developer-relations-skills:developer-education-strategy`; plugins `learn-with-coursera`, `explanatory-output-style`, `learning-output-style` |
| 知识文档 | `anthropics/skills:pdf`; `anthropics/skills:docx`; `mattpocock/skills:handoff`; `mattpocock/skills:writing-for-agents`; `firecrawl/skills:firecrawl-knowledge-base`; `firecrawl/skills:firecrawl-knowledge-ingest`; `openclaw/openclaw:summarize`; `tw93/waza:read`; MCP `upstash/context7-mcp`; plugin `desktop-commander` |
| 数据可视化 | `anthropics/knowledge-work-plugins:data-visualization`; `antvis/chart-visualization-skills:chart-visualization`; `anthropics/knowledge-work-plugins:create-viz`; `wshobson/agents:data-storytelling`; `wshobson/agents:kpi-dashboard-design`; `wshobson/agents:grafana-dashboards`; `claude-office-skills/skills:chart-designer`; `jimliu/baoyu-skills:baoyu-diagram`; `github/awesome-copilot:power-bi-report-design-consultation`; `wshobson/agents:service-mesh-observability` |
| 写作表达 | `mattpocock/skills:writing-beats`; `mattpocock/skills:writing-shape`; `mattpocock/skills:writing-fragments`; `mattpocock/skills:writing-great-skills`; `yuan1z0825/nature-skills:nature-writing`; `yuan1z0825/nature-skills:nature-polishing`; MCP `manavm/zero-slop`; MCP `theserverlessdev/wsc`; MCP `prose-coach/prose-coach`; plugin `canva` |
| 开发工程 | plugin `superpowers@claude-plugins-official`; plugins `code-review`, `chrome-devtools-mcp`, `semgrep`; `mattpocock/skills:code-review`; `pbakaus/impeccable:impeccable`; `vercel-labs/agent-skills:vercel-react-best-practices`; `llllllllama/rigorpilot-skills:safe-debug`; `llllllllama/rigorpilot-skills:explore-code`; `mattpocock/skills:domain-modeling` |

## Target UX

### Main Extensions view

```text
扩展
┌────────────────────────────────────────────────┐
│ 技能 / MCP / 插件     [检查更新] [扩展市场]      │
├────────────────────────────────────────────────┤
│ Installed groups / rows                         │
│ Row → detail panel                              │
└────────────────────────────────────────────────┘
```

- No recommendation block.
- No persistent operation-history block.
- One compact active-operation progress line.
- One compact latest-failure surface with retry/copy only where safe.
- Quiet groups, aligned metadata, hover/focus action affordances.

### Extension Market dialog

```text
扩展市场
┌───────────────────────────────────────────────┐
│ [推荐] [技能] [MCP] [插件] [来源管理]           │
│ Search current tab                             │
│ Category chips: 科学研究 / 教育学习 / …          │
│ 10 recommendation cards                        │
│ Detail pane: Chinese intro + metadata + action │
└───────────────────────────────────────────────┘
```

- Opening recommendations does not mutate the main view.
- A recommendation opens details first; its market action runs the existing search/install path.
- Search result rows open the same detail pane.
- Source management is a dialog tab, not more main-view clutter.

## File structure

Create:

- `workbench/src/features/workspace-explorer/recommendationCatalog.ts`
- `workbench/src/features/workspace-explorer/extensionSummaries.ts`
- `workbench/src/features/workspace-explorer/ExtensionMarketDialog.vue`
- `workbench/src/features/workspace-explorer/ExtensionDetailPanel.vue`
- `workbench/src/features/workspace-explorer/ExtensionSourceManager.vue`
- `workbench/src/features/workspace-explorer/ExtensionFailureNotice.vue`
- focused tests beside these modules.

Modify:

- `workbench/src/features/workspace-explorer/ExtensionsView.vue`
- `workbench/src/stores/extensions.ts`
- `workbench/src/lib/ipc.ts`
- `workbench/src/i18n/zh-CN.ts`, `en-US.ts`
- `workbench/src-tauri/src/runtime.rs`
- `src/aisc/cli/main.py`
- `src/aisc/cli/commands/extensions.py`
- `src/aisc/application/extensions.py`
- `container/aisc-extensions-adapter`
- plan/ledger docs.

Remove after replacements land:

- `workbench/src/features/workspace-explorer/ExtensionRecommendations.vue`
- `workbench/src/features/workspace-explorer/ExtensionOperationLog.vue`
- their obsolete focused tests.

---

### Task 1: Recommendation catalog contract

**Files:**

- Create: `workbench/src/features/workspace-explorer/recommendationCatalog.ts`
- Modify: `workbench/src/features/workspace-explorer/extensionRecommendations.ts` (replace legacy export or re-export)
- Test: `workbench/src/features/workspace-explorer/__tests__/recommendationCatalog.test.ts`

**Interfaces:**

```ts
export type RecommendationCategoryId =
  | "research" | "education" | "knowledge" | "visualization" | "writing" | "development";

export interface CategorizedRecommendation {
  category: RecommendationCategoryId;
  kind: ExtensionsKind;
  identity: string;
  query: string;
  name: string;
  sourceUrl: string;
  heat?: string;
  heatSource: "skills.sh" | "smithery" | "official-directory";
  summaryZh: string;
  summaryEn: string;
}
```

- [x] RED: assert six category IDs, exactly ten entries per category, unique `(kind, identity)` globally, every name/query/source/summary non-empty, and every category has at least two asset kinds where the selected catalog above provides them.
- [x] Run `npm test -- recommendationCatalog` and confirm the module missing failure.
- [x] Implement the six-category catalog exactly as documented above.
- [x] GREEN: rerun focused test.
- [x] Commit: `feat(workbench): categorize extension recommendations`.

### Task 2: Local detail summaries and fallback

**Files:**

- Create: `workbench/src/features/workspace-explorer/extensionSummaries.ts`
- Test: `workbench/src/features/workspace-explorer/__tests__/extensionSummaries.test.ts`
- Modify: i18n files for fallback labels.

**Interfaces:**

```ts
export function extensionSummary(
  item: Pick<ExtensionsItem, "kind" | "id" | "name" | "repo" | "description">,
  locale: "zh-CN" | "en-US",
): { summary: string; marketOriginal?: string; source: "first-party" | "fallback" };
```

- [x] RED: known recommendation identity returns its first-party Chinese summary; all 13 caveman children return distinct non-empty Chinese summaries; unknown item returns a useful local fallback plus original description; English locale returns English first-party/fallback copy.
- [x] Implement alias matching by full market ID, directory/name, and repo/name.
- [ ] GREEN.
- [x] Commit: `feat(workbench): add local extension detail summaries`.

### Task 3: Source maintenance data plane

**Files:**

- Modify: `container/aisc-extensions-adapter`
- Modify: `src/aisc/application/extensions.py`
- Modify: `src/aisc/cli/commands/extensions.py`, `src/aisc/cli/main.py`
- Modify: `workbench/src-tauri/src/runtime.rs`
- Tests: `tests/test_extensions_adapter.py`, `tests/test_extensions_bridge.py`, `tests/test_extensions_dispatch.py`, Rust runtime test.

**New ops:**

- `skill-repos-list`
- `skill-repo-remove`
- `plugin-market-remove`

**Adapter semantics:**

- `skill-repos-list`: read `skill_repos(owner, name, branch, enabled)` from cc-switch SQLite and emit `kind:"skill-repo"`, `id:"owner/name"`, `name`, `repo`, `branch`, `enabled`.
- `skill-repo-remove <owner/name-or-URL>`: call `cc-switch skills repos remove <id>`; it only unregisters the source and does not uninstall installed skills.
- `plugin-market-remove <name>`: call `claude-real plugin marketplace remove <name>`, then the UI refreshes marketplace list.

- [x] RED adapter: seeded SQLite repo list shape; remove argv; plugin remove argv; malformed IDs fail closed; main envelope choices.
- [x] Implement adapter.
- [x] RED bridge/dispatch/Rust allowlist: argv and op pass-through.
- [x] Implement bridge/CLI/Rust allowlist.
- [x] Run focused Python and Rust tests.
- [x] Commit: `feat(extensions): maintain skill and plugin sources`.

### Task 4: Store source state and operations

**Files:**

- Modify: `workbench/src/stores/extensions.ts`
- Modify: `workbench/src/lib/ipc.ts`
- Test: store-focused Vitest under `workbench/src/stores/__tests__` or existing extension tests.

**Interfaces added to the Pinia store:**

```ts
skillRepos: ExtensionsItem[];
skillReposBusy: boolean;
skillReposError: string | null;
loadSkillRepos(): Promise<void>;
removeSkillRepo(id: string): Promise<void>;
removePluginMarket(id: string): Promise<void>;
```

- Reuse `pluginMarkets` state for plugin marketplace list/add/remove.
- Context switch clears both source states.
- Remove actions use the normal operation/bus/toast path and refresh source lists after success.

- [x] RED: IPC op assertions, busy/error state, context reset, successful list refresh.
- [x] Implement.
- [ ] GREEN.
- [x] Commit: `feat(workbench): manage extension sources in store`.

### Task 5: Extension detail panel

**Files:**

- Create: `ExtensionDetailPanel.vue`
- Test: `__tests__/extensionDetailPanel.test.ts`

**Requirements:**

- Accept installed or market item plus optional recommendation.
- Show title, kind, source/repo/marketplace, install count, updated time, version/update state.
- First visual block is the local summary; Chinese locale always starts with a Chinese sentence.
- Keep `市场原文` in a separate subdued block.
- Actions are supplied by parent so installed and market contexts reuse one component.
- Escape closes only when the panel owns focus; parent dialog remains open.

- [x] RED test content/actions/accessibility.
- [x] Implement.
- [x] GREEN.
- [x] Commit: `feat(workbench): add extension detail panel`.

### Task 6: Extension Market dialog

**Files:**

- Create: `ExtensionMarketDialog.vue`
- Test: `__tests__/extensionMarketDialog.test.ts`
- Modify i18n.

**Requirements:**

- Teleported modal, labelled `扩展市场`, focus trapped, Escape/Close works.
- Tabs: 推荐 / 技能 / MCP / 插件 / 来源管理.
- Recommendation tab shows six category chips and ten cards per category.
- Cards display name, kind, source, observed heat badge when available, and one-line Chinese summary.
- Clicking a recommendation opens detail; search action keeps the exact identity highlighted in results.
- Search result click opens detail; install/update actions remain disabled during busy state.
- Source management renders Task 7 component.
- Dialog state is local; closing does not erase main installed lists.

- [ ] RED tests for dialog shell, category counts, cards, details, close/focus basics.
- [ ] Implement.
- [ ] GREEN.
- [ ] Commit: `feat(workbench): add categorized extension market dialog`.

### Task 7: Source manager UI

**Files:**

- Create: `ExtensionSourceManager.vue`
- Test: `__tests__/extensionSourceManager.test.ts`

**Requirements:**

- Two clear sections: 技能仓库 and 插件市场.
- Existing add forms move here from the main view.
- Rows show source, branch/name, and enabled state where available.
- Delete uses explicit confirm text:
  - skill repo delete explains it does not uninstall installed skills;
  - plugin marketplace delete explains installed plugins remain installed but future discovery from that market disappears.
- MCP section explains Smithery is built in and installed MCP servers are managed from the MCP installed list.
- Busy/error rows are honest; no delete button before identity is loaded.

- [ ] RED test list/add/remove and confirmation text.
- [ ] Implement.
- [ ] GREEN.
- [ ] Commit: `feat(workbench): add extension source manager`.

### Task 8: Main view cleanup and failure surface

**Files:**

- Modify: `ExtensionsView.vue`
- Create: `ExtensionFailureNotice.vue`
- Remove: `ExtensionRecommendations.vue`, `ExtensionOperationLog.vue`
- Update/remove obsolete tests; modify preview contracts.

**Requirements:**

- Main view header has tabs and two primary actions: 检查更新, 扩展市场.
- No operation-log/details element appears in the main view.
- Active operation remains a single compact progress status.
- Latest failed/unknown operation appears in `ExtensionFailureNotice`; it supports copy and retry only for known retryable failures.
- Installed row click opens detail panel; child row click opens child detail.
- Market/search forms are removed from the main view; all discovery lives in dialog.
- Empty state offers `打开扩展市场`.

- [ ] RED tests assert removed nodes, header actions, detail opening, failure copy/retry behavior.
- [ ] Implement.
- [ ] GREEN.
- [ ] Commit: `refactor(workbench): focus extensions view on installed assets`.

### Task 9: Visual refinement and responsive contracts

**Files:**

- Modify created components and `ExtensionsView.vue`
- Update `extensionsPreviewContracts.test.ts`
- Optionally add `extensionMarketDialog.visual.test.ts`.

**Checks:**

- At narrow sidebar width, installed rows remain readable and actions do not overlap identity.
- Dialog grid collapses from two columns to one below 720px.
- Recommendation cards use one repeated quiet card recipe; no rainbow category colors.
- Metadata is sentence case/subtle; accent only on active category, update, or primary action.
- Hover/focus states reveal row actions; keyboard users can reach every action.
- Empty/search/error states keep their frame.

- [ ] RED structural CSS/DOM tests.
- [ ] Implement with existing tokens only.
- [ ] GREEN.
- [ ] Commit: `style(workbench): refine extension experience`.

### Task 10: Full verification and Computer Use pretest

**Local gates:**

- [ ] `npm test`
- [ ] `npm run build`
- [ ] Targeted plus full Rust tests if bridge changed: `cargo test --manifest-path workbench/src-tauri/Cargo.toml --lib`
- [ ] Focused/full Python extensions tests, then repository local Python gate appropriate to touched files.
- [ ] `bash tools/check-docs.sh`
- [ ] `git diff --check`
- [ ] Production Workbench build.

**Computer Use pretest:**

1. Fresh isolated workspace and runtime.
2. Main Extensions view:
   - no 精选推荐 block;
   - no 操作日志;
   - three tabs usable;
   - installed skill group and child detail show Chinese summaries.
3. Extension Market:
   - six categories visible;
   - each shows exactly 10 recommendations;
   - research and education category content matches catalog;
   - recommendation detail opens;
   - search executes from recommendation;
   - result detail shows Chinese intro and market original.
4. Sources:
   - list skill repositories;
   - add then remove a disposable skill repository;
   - list plugin marketplaces;
   - add then remove a disposable marketplace;
   - explanatory copy is visible before confirm.
5. MCP installed row delete remains available and does not show fake repository deletion.
6. Width/narrow spot checks and bilingual spot checks.
7. Record truthful PASS/FAIL/NOT RUN in `PRETEST.md`; any product FAIL is fixed before handoff.

**Documentation:**

- Update `R2-EXTENSION-UI-REDESIGN.md` progress/evidence.
- Update `PRETEST.md`, `devlog.md`, `README.md`, `todo.md`, and `HANDTEST.md`.
- Request independent code review after implementation.
- Open PR to `develop`; wait CI; merge only after review and checks.

## Out of scope

- No concurrent Python serve redesign.
- No online translation.
- No arbitrary third-party summary fabrication.
- No change to extension install/update transport semantics from R1.
- No release/tag/phase closeout.
