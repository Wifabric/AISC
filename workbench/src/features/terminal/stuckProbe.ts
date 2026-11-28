/**
 * b9 (D-8): tab-stuck observability.
 *
 * Backlog #23 ("某个标签突然卡住") is observability-only this release: when a
 * tab/terminal stops making progress, one structured log line must pin down
 * the tab id, pane id, engine, session, state age, last PTY activity and
 * render-queue depth — plus a repro path — so the report can be diagnosed and
 * reproduced. Nothing here changes rendering or the session state machine.
 *
 * Pure by design (store feeds a snapshot): silence alone is NEVER "stuck" — an
 * idle shell is not a bug. Only states that must make progress (`starting`,
 * `closing`) and a visible render queue that stops draining are flagged.
 */
import type { LaunchAgent, TabExit, TabSessionState } from "../../types";

export type TabStuckReason = "starting_timeout" | "closing_timeout" | "output_queue_stalled";

export interface TabStuckThresholds {
  /** A pane may sit in `starting` this long before it is reported. */
  startingMs: number;
  /** A pane may sit in `closing` this long before it is reported. */
  closingMs: number;
  /** Queued render chunks that stop draining this long are reported. */
  queueStallMs: number;
}

export const DEFAULT_TAB_STUCK_THRESHOLDS: TabStuckThresholds = {
  startingMs: 20_000,
  closingMs: 15_000,
  queueStallMs: 3_000,
};

/** One pane's raw state as observed by the store probe. */
export interface ProbePaneInput {
  tabId: string;
  paneId: string;
  /** Launch engine of the pane's leaf (claude / codex / bash / cc-switch). */
  engine: LaunchAgent;
  /** Whether this is the active tab's active pane. */
  active: boolean;
  sessionId: string | null;
  state: TabSessionState;
  exit: TabExit | null;
  /** When the pane entered `state` (store-observed, not guessed). */
  stateSinceAt: number;
  /** Last PTY output observed for this pane. */
  lastActivityAt: number | null;
  /** When the pending output queue was last drained. */
  lastFlushAt: number | null;
  /** Chunks waiting for the next render flush. */
  queueDepth: number;
  /** Queue depth seen on the previous probe (0 when never observed). */
  previousQueueDepth: number;
}

export interface TabStuckProbeContext {
  workspace: string;
  runtimeId: string;
  runtimeState: string;
  activeTabId: string | null;
  /** Whether the window is visible; queue stalls are only meaningful when it is. */
  visible: boolean;
}

/** Per-pane snapshot carried in every report (locating state). */
export interface TabProbeSnapshot {
  tabId: string;
  paneId: string;
  engine: LaunchAgent;
  active: boolean;
  sessionId: string | null;
  state: TabSessionState;
  exit: TabExit | null;
  stateAgeMs: number;
  lastActivityAgeMs: number | null;
  queueDepth: number;
  queueStallMs: number | null;
}

export interface TabStuckFinding extends TabProbeSnapshot {
  reason: TabStuckReason;
  /** One-line repro path (workspace/tab/pane/engine/session/state/timings). */
  repro: string;
}

export interface TabStuckReport {
  generatedAt: string;
  workspace: string;
  runtimeId: string;
  runtimeState: string;
  activeTabId: string | null;
  visible: boolean;
  thresholds: TabStuckThresholds;
  /** Every observed pane — locating context even when only one is stuck. */
  tabs: TabProbeSnapshot[];
  stuck: TabStuckFinding[];
}

/** Identity of a pane's current state phase (state + session id). A transition
 * to a new phase resets the state-age clock. */
export function probePhaseKey(state: TabSessionState, sessionId: string | null): string {
  return `${state}|${sessionId ?? ""}`;
}

function queueStallAge(pane: ProbePaneInput, now: number): number | null {
  if (pane.queueDepth <= 0 || pane.lastFlushAt === null) return null;
  return Math.max(0, now - pane.lastFlushAt);
}

function snapshotPane(pane: ProbePaneInput, now: number): TabProbeSnapshot {
  return {
    tabId: pane.tabId,
    paneId: pane.paneId,
    engine: pane.engine,
    active: pane.active,
    sessionId: pane.sessionId,
    state: pane.state,
    exit: pane.exit,
    stateAgeMs: Math.max(0, now - pane.stateSinceAt),
    lastActivityAgeMs:
      pane.lastActivityAt === null ? null : Math.max(0, now - pane.lastActivityAt),
    queueDepth: pane.queueDepth,
    queueStallMs: queueStallAge(pane, now),
  };
}

function describeRepro(
  reason: TabStuckReason,
  snapshot: TabProbeSnapshot,
  context: TabStuckProbeContext,
): string {
  const secs = (ms: number) => `${Math.round(ms / 1_000)}s`;
  return [
    `reason=${reason}`,
    `workspace=${context.workspace || "<none>"}`,
    `runtime=${context.runtimeId || "<none>"}`,
    `tab=${snapshot.tabId}`,
    `pane=${snapshot.paneId}`,
    `engine=${snapshot.engine}`,
    `session=${snapshot.sessionId ?? "<none>"}`,
    `state=${snapshot.state}`,
    `stateAge=${secs(snapshot.stateAgeMs)}`,
    `lastActivity=${snapshot.lastActivityAgeMs === null ? "<none>" : secs(snapshot.lastActivityAgeMs)}`,
    `queueDepth=${snapshot.queueDepth}`,
    `probe=tab_stuck_probe`,
  ].join(" ");
}

/** Classify one pane. Returns null unless it is genuinely stuck. */
export function classifyPane(
  pane: ProbePaneInput,
  now: number,
  thresholds: TabStuckThresholds,
  context: TabStuckProbeContext,
): TabStuckFinding | null {
  const snapshot = snapshotPane(pane, now);
  let reason: TabStuckReason | null = null;
  if (pane.state === "starting" && snapshot.stateAgeMs >= thresholds.startingMs) {
    reason = "starting_timeout";
  } else if (pane.state === "closing" && snapshot.stateAgeMs >= thresholds.closingMs) {
    reason = "closing_timeout";
  } else if (
    context.visible &&
    pane.queueDepth > 0 &&
    pane.previousQueueDepth > 0 &&
    pane.queueDepth >= pane.previousQueueDepth &&
    snapshot.queueStallMs !== null &&
    snapshot.queueStallMs >= thresholds.queueStallMs
  ) {
    // Two consecutive visible observations with no drain: the render loop is
    // not consuming output (first observation is only a baseline, so a normal
    // one-frame backlog can never trip this).
    reason = "output_queue_stalled";
  }
  if (!reason) return null;
  return { ...snapshot, reason, repro: describeRepro(reason, snapshot, context) };
}

/** Build the full report for a set of observed panes. */
export function buildTabStuckReport(
  context: TabStuckProbeContext,
  panes: ProbePaneInput[],
  now: number,
  thresholds: TabStuckThresholds = DEFAULT_TAB_STUCK_THRESHOLDS,
): TabStuckReport {
  const stuck: TabStuckFinding[] = [];
  for (const pane of panes) {
    const finding = classifyPane(pane, now, thresholds, context);
    if (finding) stuck.push(finding);
  }
  return {
    generatedAt: new Date(now).toISOString(),
    workspace: context.workspace,
    runtimeId: context.runtimeId,
    runtimeState: context.runtimeState,
    activeTabId: context.activeTabId,
    visible: context.visible,
    thresholds,
    tabs: panes.map((p) => snapshotPane(p, now)),
    stuck,
  };
}

/** One-line JSON payload for the shared UI timeline (`log_ui_event`). The
 * repro path is duplicated at the top level so it survives log tailing. */
export function formatTabStuckLog(finding: TabStuckFinding, report: TabStuckReport): string {
  return JSON.stringify({
    probe: "tab_stuck",
    reason: finding.reason,
    repro: finding.repro,
    tab: {
      id: finding.tabId,
      pane: finding.paneId,
      engine: finding.engine,
      active: finding.active,
      session: finding.sessionId,
      state: finding.state,
      exit: finding.exit,
      state_age_ms: finding.stateAgeMs,
      last_activity_age_ms: finding.lastActivityAgeMs,
      queue_depth: finding.queueDepth,
      queue_stall_ms: finding.queueStallMs,
    },
    context: {
      generated_at: report.generatedAt,
      workspace: report.workspace,
      runtime_id: report.runtimeId,
      runtime_state: report.runtimeState,
      active_tab: report.activeTabId,
      visible: report.visible,
      thresholds: report.thresholds,
      tabs: report.tabs,
    },
  });
}
