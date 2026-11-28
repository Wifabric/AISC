/**
 * b9 (D-8): tab-stuck observability at the store seam.
 *
 * Drives the real workspace-runtime factory through a fake IPC Channel:
 * - a pane that never leaves `starting` is surfaced by `probeStuckTabs` with
 *   locating fields + a repro path;
 * - the watchdog logs it once per stuck episode (no polling spam) onto the
 *   shared UI timeline as `tab_stuck_probe`;
 * - live PTY output feeds the snapshot's last-activity + queue depth.
 *
 * Observability only: no rendering behavior is exercised or changed.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useRuntimeStore } from "../runtime";
import { DEFAULT_TAB_STUCK_THRESHOLDS } from "../../features/terminal/stuckProbe";

/** Channels handed to openSession (the store owns them; tests emit events). */
const channels: Array<{ onmessage?: (ev: unknown) => void }> = [];

const mockIpc = vi.hoisted(() => ({
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  getProviderStatus: vi.fn().mockResolvedValue({}),
  closeSession: vi.fn().mockResolvedValue({ reason: "user_close", exitCode: null }),
  loadHistory: vi.fn().mockResolvedValue({ schema_version: 2, revision: 0, workspaces: [] }),
  saveHistory: vi.fn().mockResolvedValue(1),
  negotiateCapabilities: vi.fn(),
  listRuntimes: vi.fn().mockResolvedValue({ runtimes: [] }),
  ackSessionExit: vi.fn().mockResolvedValue("acknowledged"),
  openSession: vi.fn().mockImplementation((...args: unknown[]) => {
    const ch = args[4] as { onmessage?: (ev: unknown) => void };
    channels.push(ch ?? {});
    return Promise.resolve({});
  }),
  writeSession: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../../lib/ipc", () => mockIpc);
vi.mock("@tauri-apps/plugin-dialog", () => ({
  confirm: vi.fn().mockResolvedValue(true),
  open: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ Channel: class {} }));
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: vi.fn(() => ({
    isFocused: vi.fn().mockResolvedValue(true),
    isMinimized: vi.fn().mockResolvedValue(false),
  })),
}));
vi.mock("@tauri-apps/plugin-notification", () => ({
  isPermissionGranted: vi.fn().mockResolvedValue(false),
  requestPermission: vi.fn().mockResolvedValue("denied"),
  sendNotification: vi.fn().mockResolvedValue(undefined),
}));

function tick(): Promise<void> {
  return new Promise((r) => setTimeout(r, 0));
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  channels.length = 0;
  mockIpc.openSession.mockImplementation((...args: unknown[]) => {
    const ch = args[4] as { onmessage?: (ev: unknown) => void };
    channels.push(ch ?? {});
    return Promise.resolve({});
  });
});

describe("probeStuckTabs", () => {
  it("surfaces a pane stuck in starting with locating state and a repro path", async () => {
    mockIpc.openSession.mockImplementationOnce((...args: unknown[]) => {
      channels.push((args[4] as { onmessage?: (ev: unknown) => void }) ?? {});
      return new Promise<void>(() => {}); // the invoke never settles
    });
    const s = useRuntimeStore();
    s.runtimeState = "running";
    s.runtimeId = "rid";
    s.workspace = "/ws/demo";
    const id = s.createTab("bash")!;
    await tick();
    const tab = s.tabs.find((t) => t.tabId === id)!;
    expect(tab.panes[id].sessionState).toBe("starting");

    const base = Date.now();
    const thresholds = { ...DEFAULT_TAB_STUCK_THRESHOLDS, startingMs: 1_000 };
    const report = s.probeStuckTabs(base + 1_500, thresholds);

    expect(report.stuck).toHaveLength(1);
    const finding = report.stuck[0];
    expect(finding.reason).toBe("starting_timeout");
    expect(finding.tabId).toBe(id);
    expect(finding.paneId).toBe(id);
    expect(finding.engine).toBe("bash");
    expect(finding.state).toBe("starting");
    expect(finding.sessionId).not.toBeNull();
    expect(finding.repro).toContain(`tab=${id}`);
    expect(finding.repro).toContain("engine=bash");
    expect(finding.repro).toContain("workspace=/ws/demo");
    expect(finding.repro).toContain("probe=tab_stuck_probe");
    // Report carries the full locating context.
    expect(report.workspace).toBe("/ws/demo");
    expect(report.runtimeId).toBe("rid");
    expect(report.runtimeState).toBe("running");
    expect(report.tabs).toHaveLength(1);
  });

  it("logs one structured line per stuck episode, not once per poll", async () => {
    mockIpc.openSession.mockImplementationOnce((...args: unknown[]) => {
      channels.push((args[4] as { onmessage?: (ev: unknown) => void }) ?? {});
      return new Promise<void>(() => {});
    });
    const s = useRuntimeStore();
    s.runtimeState = "running";
    s.runtimeId = "rid";
    s.workspace = "/ws/demo";
    const id = s.createTab("bash")!;
    await tick();

    const base = Date.now();
    const thresholds = { ...DEFAULT_TAB_STUCK_THRESHOLDS, startingMs: 1_000 };
    s.logTabStuckProbeIfNeeded(base + 1_500, thresholds);
    s.logTabStuckProbeIfNeeded(base + 2_000, thresholds); // still stuck

    const stuckCalls = mockIpc.logUiEvent.mock.calls.filter(
      (c) => c[0] === "tab_stuck_probe",
    );
    expect(stuckCalls).toHaveLength(1);
    expect(stuckCalls[0][1]).toBe("error");
    const logged = JSON.parse(String(stuckCalls[0][2]));
    expect(logged.probe).toBe("tab_stuck");
    expect(logged.reason).toBe("starting_timeout");
    expect(logged.repro).toContain(`tab=${id}`);
    expect(logged.context.workspace).toBe("/ws/demo");
  });

  it("captures live output activity and the pending render-queue depth", async () => {
    const s = useRuntimeStore();
    s.runtimeState = "running";
    s.runtimeId = "rid";
    s.workspace = "/ws/demo";
    const id = s.createTab("bash")!;
    await tick();
    const tab = s.tabs.find((t) => t.tabId === id)!;
    const channel = channels[channels.length - 1];
    channel.onmessage?.({ type: "output", bytes: "aGVsbG8=", offset: 0 }); // "hello"
    expect(tab.panes[id].sessionState).toBe("running");

    const base = Date.now();
    const report = s.probeStuckTabs(base + 5_000);
    const snapshot = report.tabs.find((t) => t.paneId === id)!;
    expect(snapshot.state).toBe("running");
    expect(snapshot.lastActivityAgeMs).toBeGreaterThanOrEqual(4_000);
    // The chunk is still queued: no animation frame ran before this probe.
    expect(snapshot.queueDepth).toBe(1);
    // A running pane with recent output is not stuck.
    expect(report.stuck).toHaveLength(0);
  });

  it("does not flag a healthy running tab", async () => {
    const s = useRuntimeStore();
    s.runtimeState = "running";
    s.runtimeId = "rid";
    s.workspace = "/ws/demo";
    s.createTab("bash")!;
    await tick();
    const report = s.probeStuckTabs(Date.now() + 60_000);
    expect(report.stuck).toHaveLength(0);
  });
});
