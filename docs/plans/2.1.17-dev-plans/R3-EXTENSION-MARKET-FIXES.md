# v2.1.17 R3 Implementation Plan: Extension Market Batch Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the R3 user-reported extension-market failures in one batch: classify old-runtime source maintenance cleanly, remove the redundant installed-empty market button, and make recommendations expand inline in full-width cards.

**Architecture:** Keep the existing adapter → Python CLI → Rust bridge → Pinia → Vue boundary. Python converts only the exact legacy in-container adapter argparse boundary to the stable unsupported code; Vue removes the empty-state action and moves recommendation details from a fixed right pane into the selected card.

**Tech Stack:** Python argparse/stdout contract tests; Vue 3 + Pinia + existing CSS tokens; Vitest.

**Spec:** User ruling on 2026-10-30 after R2 handtest, executed under DEVELOP_WIKI §1.4 as batch R3. The user's three required outcomes are: no raw `aisc-extensions-adapter` usage error for skill source maintenance; installed empty state has no “打开扩展市场” button; recommendation cards contain their information and expand details in place rather than reserving/showing a right detail pane.

## Evidence and root cause

- The R2 handtest data root logged runtime `20bc95af-c719-44a2-b520-74b55a49273a` as `super-claude:latest` (`610cd7ebfa39…`, b7), not `super-claude:2.1.17-r2-final`. Its old adapter rejects source-maintenance ops through argparse.
- `src/aisc/application/extensions.py` already maps an envelope-form legacy `unhandled op`, but the old adapter exits nonzero with empty stdout and argparse usage on stderr. That path currently returns `AISC_ERR_EXTENSIONS_EXEC_FAILED` with the raw usage text.
- Product fix: convert only the exact legacy adapter argparse boundary for the five source ops to `AISC_ERR_EXTENSIONS_UNSUPPORTED_OP` with a clear message. Do not reinterpret database/network failures as unsupported.

## Non-negotiable requirements

1. R3 is batch-gated: implementation, targeted/full appropriate gates, CU attempt or recorded CU blocker, then this user handtest. Do not start another product batch before the user accepts or explicitly defers R3.
2. The old-runtime classifier must match only source-maintenance ops and the exact adapter argparse form; transient failures remain retryable/original errors.
3. Installed Skills/MCP/Plugins empty states show only “暂无内容” (or locale equivalent); the toolbar remains the sole Extension Market opener.
4. Recommendation tab uses full-width cards. Name, kind, summary, identity/source and heat/evidence metadata stay in the card; clicking a native card header expands/collapses detail in that card.
5. No fixed right detail pane appears on the Recommendations tab. Skills/MCP/Plugins search tabs keep their existing detail behavior.
6. No new dependency, transport op, or translation service.

---

### Task 1: Stable old-runtime source-maintenance classification

**Files:**

- Modify: `src/aisc/application/extensions.py`
- Test: `tests/test_extensions_bridge.py`

**Requirements:**

- Simulate adapter exit 2, empty stdout, and stderr containing `usage: aisc-extensions-adapter` plus `invalid choice: 'skill-repos-list'`.
- Expect `CliError.error_code == AISC_ERR_EXTENSIONS_UNSUPPORTED_OP`.
- Expect user-facing message to say the runtime image does not support extension source maintenance, without exposing argparse usage.
- Add a transient stderr case (for example database locked) and assert it remains `AISC_ERR_EXTENSIONS_EXEC_FAILED`.
- Existing Rust already maps the envelope code for source ops; no Rust behavior change is expected.

- [x] RED: add exact failing tests.
- [x] Run `python -m pytest tests/test_extensions_bridge.py -q` and confirm failures.
- [x] Implement the narrow classifier.
- [x] GREEN: rerun targeted Python tests.
- [x] Commit.

### Task 2: Installed empty state has no market button

**Files:**

- Modify: `workbench/src/features/workspace-explorer/ExtensionsView.vue`
- Test: `workbench/src/features/workspace-explorer/__tests__/extensionsView.test.ts`

**Requirements:**

- Empty installed list renders text only (`extensions.empty`).
- `[data-testid='open-extension-market-empty']` does not exist.
- Closing the market restores focus to the toolbar opener.
- Remove the now-unused empty opener ref/type if applicable.

- [x] RED: update tests and confirm the empty button/focus expectation fails.
- [x] Implement.
- [x] GREEN: run `extensionsView` targeted Vitest.
- [x] Commit.

### Task 3: Recommendation cards expand inline

**Files:**

- Modify: `workbench/src/features/workspace-explorer/ExtensionMarketDialog.vue`
- Test: `workbench/src/features/workspace-explorer/__tests__/extensionMarketDialog.test.ts`

**Requirements:**

- Recommendations tab body uses one full-width column; no `market-detail` pane renders there.
- Each collapsed card shows title, kind, Chinese summary, heat/evidence, and identity/source in one card.
- The card header is a native button with `aria-expanded`/`aria-controls`; Enter/Space use native activation.
- Selecting a card expands `ExtensionDetailPanel` inside that same card and exposes the existing “搜索市场” action.
- Selecting another card collapses the previous card; clicking the selected header or panel Close collapses it.
- Category change clears selection.
- Search tabs retain the existing right detail pane.

- [x] RED: rewrite recommendation DOM/behavior expectations and confirm failures.
- [x] Implement card and CSS changes.
- [x] GREEN: run `extensionMarketDialog` targeted Vitest.
- [x] Commit.

### Task 4: R3 batch verification and handoff

- [ ] Targeted Python + frontend tests.
- [ ] Full frontend Vitest and production build.
- [ ] Python tests appropriate to the touched data plane; run the full repository Python gate if runtime allows.
- [ ] `tools/check-docs.sh`, `git diff --check`.
- [ ] Build a direct R3 Workbench executable.
- [ ] Attempt CU. If `node_repl` remains unavailable, record the exact blocker and all UI checks NOT RUN in `PRETEST.md`; do not fake UI evidence.
- [ ] Start the R3 build for this user's batch handtest and wait for user acceptance before any R4 work.

## R3 user handtest

Precondition: close earlier R2 windows. Launch only the provided R3 direct build and use the R3 final adapter image. Use a fresh isolated workspace so the runtime image is not inherited from R2.

1. Start a runtime with the R3 image. Open Extensions → Extension Market → Sources. Using an old b7 image is an additional negative check, not the main path. On the old image, Sources must show the clear unsupported/upgrade banner and must not show raw argparse usage.
2. On the R3 image, Sources loads skill repositories and plugin markets without the reported `skill-repos-list failed: usage...` error.
3. In installed Skills, MCP, and Plugins tabs with no items, only “暂无内容” appears. No “打开扩展市场” button follows the empty text.
4. Open Extension Market → Recommendations. Cards fill the content area; no permanently empty right column exists. Click one Skill, one MCP, and one Plugin recommendation in different categories. Each expands inside its own card, shows Chinese summary/metadata/evidence and “搜索市场”; clicking another card collapses the previous one; clicking again or Close collapses detail.
5. Narrow the dialog below 720px. Recommendation cards and inline details remain readable without horizontal text overlap.
