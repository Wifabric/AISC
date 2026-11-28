/**
 * b9 (D-8): tab-stuck probe — pure classification + log formatting.
 *
 * The probe must, when a tab/terminal stops making progress, emit structured
 * locating state (tab id, pane id, engine, session, state age, last PTY
 * activity, render queue depth) plus a repro path. It is observability-only:
 * no rendering/state-machine behavior is asserted here.
 */
import { describe, expect, it } from "vitest";
import {
  DEFAULT_TAB_STUCK_THRESHOLDS,
  buildTabStuckReport,
  classifyPane,
  formatTabStuckLog,
  type ProbePaneInput,
  type TabStuckProbeContext,
} from "../stuckProbe";

const ctx: TabStuckProbeContext = {
  workspace: "/ws/demo",
  runtimeId: "rid-1",
  runtimeState: "running",
  activeTabId: "tab-1",
  visible: true,
};

function pane(over: Partial<ProbePaneInput> = {}): ProbePaneInput {
  return {
    tabId: "tab-1",
    paneId: "pane-1",
    engine: "claude",
    active: true,
    sessionId: "sess-1",
    state: "running",
    exit: null,
    stateSinceAt: 0,
    lastActivityAt: 1_000,
    lastFlushAt: 1_000,
    queueDepth: 0,
    previousQueueDepth: 0,
    ...over,
  };
}

describe("classifyPane", () => {
  it("flags a pane stuck in `starting` past the threshold with locating fields", () => {
    const f = classifyPane(
      pane({ state: "starting", stateSinceAt: 1_000, lastActivityAt: 1_500 }),
      22_000,
      DEFAULT_TAB_STUCK_THRESHOLDS,
      ctx,
    );
    expect(f).not.toBeNull();
    expect(f!.reason).toBe("starting_timeout");
    expect(f!.tabId).toBe("tab-1");
    expect(f!.paneId).toBe("pane-1");
    expect(f!.engine).toBe("claude");
    expect(f!.sessionId).toBe("sess-1");
    expect(f!.state).toBe("starting");
    expect(f!.stateAgeMs).toBe(21_000);
    expect(f!.lastActivityAgeMs).toBe(20_500);
    // The repro path pins every coordinate a tester needs to reproduce.
    expect(f!.repro).toContain("workspace=/ws/demo");
    expect(f!.repro).toContain("tab=tab-1");
    expect(f!.repro).toContain("pane=pane-1");
    expect(f!.repro).toContain("engine=claude");
    expect(f!.repro).toContain("session=sess-1");
    expect(f!.repro).toContain("state=starting");
    expect(f!.repro).toContain("probe=tab_stuck_probe");
  });

  it("does not flag `starting` below the threshold", () => {
    const f = classifyPane(
      pane({ state: "starting", stateSinceAt: 10_000 }),
      20_000,
      DEFAULT_TAB_STUCK_THRESHOLDS,
      ctx,
    );
    expect(f).toBeNull();
  });

  it("flags a pane stuck in `closing` past the threshold", () => {
    const f = classifyPane(
      pane({ state: "closing", stateSinceAt: 0 }),
      15_000,
      DEFAULT_TAB_STUCK_THRESHOLDS,
      ctx,
    );
    expect(f!.reason).toBe("closing_timeout");
  });

  it("flags a visible render queue that stops draining", () => {
    const f = classifyPane(
      pane({ queueDepth: 4, previousQueueDepth: 2, lastFlushAt: 1_000 }),
      5_000,
      DEFAULT_TAB_STUCK_THRESHOLDS,
      ctx,
    );
    expect(f!.reason).toBe("output_queue_stalled");
    expect(f!.queueDepth).toBe(4);
    expect(f!.queueStallMs).toBe(4_000);
  });

  it("never flags queue backlog while hidden or while the queue drains", () => {
    const hidden = classifyPane(
      pane({ queueDepth: 4, previousQueueDepth: 2, lastFlushAt: 1_000 }),
      5_000,
      DEFAULT_TAB_STUCK_THRESHOLDS,
      { ...ctx, visible: false },
    );
    expect(hidden).toBeNull();
    const draining = classifyPane(
      pane({ queueDepth: 1, previousQueueDepth: 3, lastFlushAt: 1_000 }),
      5_000,
      DEFAULT_TAB_STUCK_THRESHOLDS,
      ctx,
    );
    expect(draining).toBeNull();
    // First observation (no previous depth) is never a stall.
    const first = classifyPane(
      pane({ queueDepth: 4, previousQueueDepth: 0, lastFlushAt: 1_000 }),
      5_000,
      DEFAULT_TAB_STUCK_THRESHOLDS,
      ctx,
    );
    expect(first).toBeNull();
  });

  it("does not treat a silent idle/running tab as stuck", () => {
    const f = classifyPane(
      pane({ state: "running", lastActivityAt: 1_000, lastFlushAt: 1_000 }),
      600_000,
      DEFAULT_TAB_STUCK_THRESHOLDS,
      ctx,
    );
    expect(f).toBeNull();
  });
});

describe("buildTabStuckReport + formatTabStuckLog", () => {
  const healthy = pane({ tabId: "tab-2", paneId: "pane-2", engine: "bash", state: "running" });
  const stuck = pane({ state: "starting", stateSinceAt: 1_000 });

  it("snapshots every tab and carries the stuck findings", () => {
    const report = buildTabStuckReport(ctx, [healthy, stuck], 22_000);
    expect(report.tabs).toHaveLength(2);
    expect(report.stuck).toHaveLength(1);
    expect(report.stuck[0].stateAgeMs).toBe(21_000);
    expect(report.thresholds).toEqual(DEFAULT_TAB_STUCK_THRESHOLDS);
  });

  it("formats one JSON log line with the repro path and context", () => {
    const report = buildTabStuckReport(ctx, [stuck], 22_000);
    const line = formatTabStuckLog(report.stuck[0], report);
    const parsed = JSON.parse(line);
    expect(parsed.probe).toBe("tab_stuck");
    expect(parsed.reason).toBe("starting_timeout");
    expect(parsed.repro).toContain("tab=tab-1");
    expect(parsed.tab.id).toBe("tab-1");
    expect(parsed.tab.engine).toBe("claude");
    expect(parsed.tab.state).toBe("starting");
    expect(parsed.tab.session).toBe("sess-1");
    expect(parsed.tab.state_age_ms).toBe(21_000);
    expect(parsed.context.workspace).toBe("/ws/demo");
    expect(parsed.context.runtime_state).toBe("running");
    expect(parsed.context.active_tab).toBe("tab-1");
    // One line only — the JSONL appender expects a single line.
    expect(line).not.toContain("\n");
  });
});
