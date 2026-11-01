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

- [x] Targeted Python + frontend tests.
- [x] Full frontend Vitest and production build.
- [x] Python tests appropriate to the touched data plane; run the full repository Python gate if runtime allows.
- [x] `tools/check-docs.sh`, `git diff --check`.
- [x] Build a direct R3 Workbench executable.
- [x] Attempt CU. If `node_repl` remains unavailable, record the exact blocker and all UI checks NOT RUN in `PRETEST.md`; do not fake UI evidence.
- [ ] Start the R3 build for this user's batch handtest and wait for user acceptance before any R4 work.

## R3 user handtest

Precondition: close earlier R2 windows. Launch only the provided R3 direct build and use the R3 final adapter image. Use a fresh isolated workspace so the runtime image is not inherited from R2.

1. Start a runtime with the R3 image. Open Extensions → Extension Market → Sources. Using an old b7 image is an additional negative check, not the main path. On the old image, Sources must show the clear unsupported/upgrade banner and must not show raw argparse usage.
2. On the R3 image, Sources loads skill repositories and plugin markets without the reported `skill-repos-list failed: usage...` error.
3. In installed Skills, MCP, and Plugins tabs with no items, only “暂无内容” appears. No “打开扩展市场” button follows the empty text.
4. Open Extension Market → Recommendations. Cards fill the content area; no permanently empty right column exists. Click one Skill, one MCP, and one Plugin recommendation in different categories. Each expands inside its own card, shows Chinese summary/metadata/evidence and “搜索市场”; clicking another card collapses the previous one; clicking again or Close collapses detail.
5. Narrow the dialog below 720px. Recommendation cards and inline details remain readable without horizontal text overlap.

## Verification evidence (2026-10-30)

- TDD: Task 1 legacy argparse classifier and Task 2/3 UI contracts all failed on the pre-fix source, then passed after implementation.
- Full local gates on final source: Python **1694 passed / 53 skipped / 191 subtests**, Rust **404 passed / 1 ignored**, Vitest **95 files / 808 tests**, and `vue-tsc --noEmit` all passed (`LOCAL GATES: ALL GREEN`) on review-fix source `7482301`.
- Production build: `npm run build` plus Tauri release `--no-bundle` passed.
- R3 frozen CLI: `release-staging/2.1.17-r3/aisc-r3-final.exe`, SHA256 `1f6032257026537bfd7840965c1087f96c4028f8005fc3d9b5b82bf38552107f`. Built in an isolated PyInstaller output because the older running Workbench retained inaccessible `aisc.exe` children; no user process was terminated.
- R3 direct GUI: `release-staging/2.1.17-r3/AISC-Workbench-2.1.17-R3-FINAL.exe`, SHA256 `73ec51edce9fcf699a3c2c7413763590232c2251d8f4474c65f5a9b284676942`.
- Real frozen-CLI/container smoke:
  - Old b7 `super-claude:latest @ 610cd7ebfa39…`: `skill-repos-list` exited 1 with stable `AISC_ERR_EXTENSIONS_UNSUPPORTED_OP` and clear upgrade/rebuild message; no argparse usage leaked.
  - R3 adapter image `2f54fad6…`: the same op exited 0 and returned the four expected repositories.
  - Both disposable runtimes were stopped; evidence is under `release-staging/2.1.17-r3/`.
- CU attempt: the Computer Use skill and required guidance/confirmation docs were read, but this session exposes no `node_repl` tool, so `@oai/sky` cannot be initialized. R3 GUI layout/keyboard/focus checks remain **NOT RUN (tool unavailable)**. User batch handtest is still required.

## Independent review and final integration evidence (2026-10-30)

- Initial independent review found one Critical (missing inline Close/focus path) and three Important findings (native-button content model, interaction test gaps, and one-op classifier coverage). They were fixed in `7482301`: explicit Close with focus restoration, valid phrasing-only native disclosure content, Enter/Space/native-ARIA contracts, five-op argparse parameterization plus `skill-repo-add` negative, shared source-op set, shared recommendation converter, and narrow metadata wrapping.
- Follow-up review found invalid collapsed-state `aria-controls` IDREFs. `ed3ed71` omits the optional attribute while collapsed and emits it only when the detail node is mounted; the runtime test resolves the expanded ID through `document.getElementById`.
- Final independent review at `ed3ed71`: **Critical=0 / Important=0, ready to merge from code review**, subject to user batch handtest.
- After the ARIA-only change, targeted dialog/preview tests **22/22**, `vue-tsc`, and a fresh production Tauri build passed. Python/Rust sources were unchanged from the fully gated `7482301` revision.
- PR [#50](https://github.com/Wifabric/AISC/pull/50); Workbench CI [40989333294](https://github.com/Wifabric/AISC/actions/runs/40989333294) on exact product head `ed3ed714fcfeb9241e0238e96edcaa684ca23981`: **SUCCESS**.
- Final CLI old-image negative smoke using SHA256 `1f603225…52107f`: b7 returned stable `AISC_ERR_EXTENSIONS_UNSUPPORTED_OP`; evidence `release-staging/2.1.17-r3/final-cli-old-image-source-result.json`.

## Develop integration final result (2026-10-30)

PR [#50](https://github.com/Wifabric/AISC/pull/50) merged into `develop` as `c3b297b935207b268a0846e22019040a5b3d6be5`.

| Workflow | Run | Result |
| --- | --- | --- |
| Workbench CLI/Rust/frontend | [40990054633](https://github.com/Wifabric/AISC/actions/runs/40990054633) | SUCCESS |
| CLI sidecar Windows/Linux/macOS | [40990054524](https://github.com/Wifabric/AISC/actions/runs/40990054524) | SUCCESS |
| Bundle deb/dmg | [40990054583](https://github.com/Wifabric/AISC/actions/runs/40990054583) | SUCCESS |
| NSIS installed-app smoke | [40990054531](https://github.com/Wifabric/AISC/actions/runs/40990054531) | SUCCESS attempt 2; attempt 1 failed dependency staging with upstream npm `HTTP 403 rate limit exceeded` |

The attempt-1 NSIS failure is retained as evidence; only the failed job was rerun and no source changed. On 2026-10-30 the user explicitly confirmed that R3 and R4 handtests passed and requested closeout; unrun checks remain in the unified regression ledger (CLOSEOUT.md). No main merge or publication is implied by this handtest result.
