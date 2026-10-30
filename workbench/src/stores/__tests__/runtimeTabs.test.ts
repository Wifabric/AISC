/**
 * G-08 dynamic-tab store tests (Step 5, A-G08-1/2/6/8): createTab cap and
 * duplicate types, provider gate routing claude/codex to guide, removeTab
 * active-tab fallback (right -> left -> empty), live-session close on
 * removal.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useRuntimeStore } from "../runtime";
import { normalizePath } from "../tabLayout";
import type { HistoryPatch, WorkbenchHistory } from "../../types";

const mockIpc = vi.hoisted(() => ({
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  closeSession: vi.fn().mockResolvedValue({ reason: "user_close", exitCode: null }),
  getProviderStatus: vi.fn().mockResolvedValue({}),
  conversationList: vi.fn().mockResolvedValue({ schema_version: 1, conversations: [] }),
  loadHistory: vi.fn().mockResolvedValue({ schema_version: 2, revision: 0, workspaces: [] }),
  saveHistory: vi.fn().mockResolvedValue(1),
  negotiateCapabilities: vi.fn(),
  listRuntimes: vi.fn().mockResolvedValue({ runtimes: [] }),
  openSession: vi.fn().mockResolvedValue({}),
  writeSession: vi.fn().mockResolvedValue(undefined),
  ackSessionExit: vi.fn().mockResolvedValue("acknowledged"),
  stopRuntime: vi.fn().mockResolvedValue({ state: "stopped" }),
  runtimeInspect: vi.fn().mockResolvedValue({ state: "stopped" }),
  runtimeRestart: vi.fn().mockResolvedValue({ state: "running" }),
  runtimeStatus: vi.fn().mockResolvedValue({ snapshot: { state: "stopped" }, services: null }),
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
  mockIpc.getProviderStatus.mockResolvedValue({});
});

describe("createTab (A-G08-1/8)", () => {
  it("recovers only the stopped runtime before a history resume and invalidates dead exec attachments", async () => {
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid"; s.workspace = "/ws";
    const id = s.createTab("bash")!; await tick();
    await s.prepareConversationResume();
    expect(mockIpc.runtimeRestart).toHaveBeenCalledWith("/ws", "rid");
    expect(s.runtimeState).toBe("running");
    expect(s.tabs.find(t => t.tabId === id)?.sessionState).toBe("disconnected");
  });
  it("preserves resume identity through a disconnected pane reopen", async () => {
    mockIpc.getProviderStatus.mockResolvedValue({ auth_status: "configured" });
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid"; s.workspace = "/ws";
    const id = s.createTab("claude", "original")!; await tick(); await tick();
    const tab = s.tabs.find(t => t.tabId === id)!;
    s.onTabSessionExit(tab.activePaneId, "transport_error", null);
    expect(s.findLiveResumeTab("original")).toBeNull();
    s.reopenTab(id); await tick();
    const calls = mockIpc.openSession.mock.calls;
    expect(calls[calls.length - 1]?.[5]).toBe("original");
    expect(s.findLiveResumeTab("original")?.tabId).toBe(id);
  });
  it("does not restart or create tabs when Docker inspect fails", async () => {
    const s = useRuntimeStore(); s.runtimeId = "rid"; s.workspace = "/ws";
    mockIpc.runtimeInspect.mockRejectedValueOnce(new Error("Docker offline"));
    await expect(s.prepareConversationResume()).rejects.toThrow("Docker offline");
    expect(mockIpc.runtimeRestart).not.toHaveBeenCalled();
    expect(s.tabs).toHaveLength(0);
  });
  it("cannot report a live resume because an unrelated split pane is running", async () => {
    mockIpc.getProviderStatus.mockResolvedValue({ auth_status: "configured" });
    const s = useRuntimeStore(); s.runtimeId = "rid"; s.runtimeState = "running"; s.workspace = "/ws";
    const id = s.createTab("codex", "original")!; await tick(); await tick();
    const tab = s.tabs.find(t => t.tabId === id)!;
    tab.panes[tab.activePaneId].sessionState = "disconnected";
    tab.panes.other = { sessionId: "other", sessionState: "running", exit: null };
    expect(s.findLiveResumeTab("original")).toBeNull();
  });
  it("adds an activated tab and opens the session immediately (bash)", async () => {
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid";
    const id = s.createTab("bash");
    expect(id).not.toBeNull();
    await tick();
    const tab = s.tabs.find((t) => t.tabId === id);
    expect(tab?.agent).toBe("bash");
    expect(tab?.sessionId).not.toBeNull();
    expect(s.activeTabId).toBe(id);
  });

  it("allows duplicate session types with distinct ids", async () => {
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid";
    const a = s.createTab("bash");
    const b = s.createTab("bash");
    expect(a).not.toBe(b);
    expect(s.tabs.filter((t) => t.agent === "bash")).toHaveLength(2);
  });

  it("refuses the 9th tab (per-Runtime leaf cap)", () => {
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid";
    for (let i = 0; i < 8; i++) expect(s.createTab("bash")).not.toBeNull();
    expect(s.createTab("bash")).toBeNull();
    expect(s.tabs).toHaveLength(8);
  });
});

describe("provider gate (A-G08-2)", () => {
  it("keeps the original conversation when a provider guide is retried after interruption", async () => {
    mockIpc.getProviderStatus.mockResolvedValue({ auth_status: "unknown" });
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid"; s.workspace = "/ws";
    const tabId = s.createTab("codex", "original-conversation")!;
    await tick(); await tick();
    expect(s.tabs.find(t => t.tabId === tabId)?.sessionState).toBe("guide");
    s.openTab(tabId);
    await tick();
    const calls = mockIpc.openSession.mock.calls;
    expect(calls[calls.length - 1]?.[5]).toBe("original-conversation");
  });
  it("routes unconfigured claude to the guide state without open_session", async () => {
    mockIpc.getProviderStatus.mockResolvedValue({
      provider_name: null,
      route_mode: "unknown",
      auth_status: "not_configured",
      observed_at: "x",
    });
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid";
    s.runtimeId = "rid";
    s.workspace = "/ws";
    const id = s.createTab("claude");
    await tick();
    await tick();
    const tab = s.tabs.find((t) => t.tabId === id);
    expect(tab?.sessionState).toBe("guide");
    expect(tab?.sessionId).toBeNull();
    expect(mockIpc.getProviderStatus).toHaveBeenCalledWith("/ws", "rid", "claude");
  });

  it("restore layout gates unconfigured claude/codex to guide (A-G08-3)", async () => {
    mockIpc.getProviderStatus.mockResolvedValue({
      provider_name: null,
      route_mode: "unknown",
      auth_status: "not_configured",
      observed_at: "x",
    });
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid";
    s.runtimeId = "rid";
    s.workspace = "/ws";
    s.initTabs(
      [
        { tab_id: "a", agent: "bash", title: "Bash", position: 0 },
        { tab_id: "b", agent: "codex", title: "Codex", position: 1 },
      ],
      { openAgents: ["bash", "codex"] }
    );
    await tick();
    await tick();
    const bash = s.tabs.find((t) => t.agent === "bash");
    const codex = s.tabs.find((t) => t.agent === "codex");
    expect(["starting", "running"]).toContain(bash?.sessionState); // bash opens directly
    expect(bash?.sessionId).not.toBeNull();
    expect(codex?.sessionState).toBe("guide"); // codex gated, no session
    expect(codex?.sessionId).toBeNull();
  });

  it("opens the session when the provider is configured", async () => {
    mockIpc.getProviderStatus.mockResolvedValue({
      provider_name: "official",
      route_mode: "official-direct",
      auth_status: "configured",
      observed_at: "x",
    });
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid";
    s.runtimeId = "rid";
    s.workspace = "/ws";
    const id = s.createTab("codex");
    await tick();
    await tick();
    const tab = s.tabs.find((t) => t.tabId === id);
    expect(["starting", "running"]).toContain(tab?.sessionState);
    expect(tab?.sessionId).not.toBeNull();
  });
});

describe("fork resume (b8 R2)", () => {
  it("passes the fork flag to open_session and does not bind the source id", async () => {
    mockIpc.getProviderStatus.mockResolvedValue({
      provider_name: "official",
      route_mode: "official-direct",
      auth_status: "configured",
      observed_at: "x",
    });
    mockIpc.openSession.mockClear();
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid";
    s.workspace = "/ws";
    const id = s.createTab("claude", "24b70882-2d45-4cec-a9e2-66f8c012481f", true)!;
    await tick();
    await tick();
    expect(mockIpc.openSession).toHaveBeenCalledWith(
      "rid",
      expect.any(String),
      "claude",
      "/ws",
      expect.anything(),
      "24b70882-2d45-4cec-a9e2-66f8c012481f",
      true,
    );
    expect(s.tabs.find((tab) => tab.tabId === id)?.resumeConversationId).toBeUndefined();
  });
});

describe("removeTab (A-G08-6)", () => {
  async function threeTabs() {
    const s = useRuntimeStore();
    s.runtimeState = "running"; s.runtimeId = "rid";
    const a = s.createTab("bash")!;
    const b = s.createTab("bash")!;
    const c = s.createTab("bash")!;
    await tick();
    return { s, a, b, c };
  }

  it("removes the tab; active falls to the right neighbor", async () => {
    const { s, a, b, c } = await threeTabs();
    s.activateTab(a);
    await s.removeTab(a);
    expect(s.tabs.find((t) => t.tabId === a)).toBeUndefined();
    expect(s.activeTabId).toBe(b); // right neighbor
    void c;
  });

  it("active at the end falls to the left neighbor", async () => {
    const { s, b, c } = await threeTabs();
    s.activateTab(c);
    await s.removeTab(c);
    expect(s.activeTabId).toBe(b);
  });

  it("removing the last tab yields the empty state", async () => {
    const { s, a } = await threeTabs();
    await s.removeTab(a);
    await s.removeTab(s.tabs[0].tabId);
    await s.removeTab(s.tabs[0].tabId);
    expect(s.tabs).toHaveLength(0);
    expect(s.activeTabId).toBeNull();
  });

  it("closes a live session best-effort and removes immediately", async () => {
    const { s, a, b } = await threeTabs();
    const running = s.tabs.find((t) => t.tabId === a)!;
    expect(["starting", "running"]).toContain(running.sessionState);
    await s.removeTab(a);
    expect(mockIpc.closeSession).toHaveBeenCalledWith(running.sessionId);
    expect(s.tabs.find((t) => t.tabId === a)).toBeUndefined();
    expect(s.tabs).toHaveLength(2);
    void b;
  });
});

describe("pending new provider conversation association (b6)", () => {
  const configured = {
    provider_name: "official",
    route_mode: "official-direct",
    auth_status: "configured",
    observed_at: "x",
  };

  beforeEach(() => {
    mockIpc.getProviderStatus.mockResolvedValue(configured);
  });

  it("links one pending live tab when the provider list gains exactly one conversation", async () => {
    mockIpc.conversationList.mockResolvedValue({
      schema_version: 1,
      conversations: [{ agent: "codex", conversation_id: "old" }],
    });
    const s = useRuntimeStore();
    s.runtimeState = "running";
    s.runtimeId = "rid";
    s.workspace = "/ws";
    const tabId = s.createTab("codex")!;
    await tick();
    await tick();

    const resolved = await s.resolvePendingConversationAssociations([
      { agent: "codex", conversation_id: "old" } as any,
      { agent: "codex", conversation_id: "new" } as any,
    ]);

    expect(mockIpc.conversationList).toHaveBeenCalledWith("/ws");
    expect(resolved).toBe(1);
    expect(s.tabs.find((tab) => tab.tabId === tabId)?.resumeConversationId).toBe("new");
    expect(s.findLiveResumeTab("new")?.tabId).toBe(tabId);
    const associated = s.tabs.find((tab) => tab.tabId === tabId)!;
    s.onTabSessionExit(associated.activePaneId, "transport_error", null);
    expect(s.findRecoverableResumePane("new")).toEqual({ tabId, paneId: associated.activePaneId });
  });

  it("does not link when new provider conversations are ambiguous", async () => {
    mockIpc.conversationList.mockResolvedValue({
      schema_version: 1,
      conversations: [{ agent: "codex", conversation_id: "old" }],
    });
    const s = useRuntimeStore();
    s.runtimeState = "running";
    s.runtimeId = "rid";
    s.workspace = "/ws";
    const first = s.createTab("codex")!;
    await tick();
    await tick();
    const second = s.createTab("codex")!;
    await tick();
    await tick();

    const resolved = await s.resolvePendingConversationAssociations([
      { agent: "codex", conversation_id: "old" } as any,
      { agent: "codex", conversation_id: "new" } as any,
    ]);

    expect(resolved).toBe(0);
    expect(s.tabs.find((tab) => tab.tabId === first)?.resumeConversationId).toBeUndefined();
    expect(s.tabs.find((tab) => tab.tabId === second)?.resumeConversationId).toBeUndefined();
  });
});

describe("closeLiveConversationSessions (b6 delete)", () => {
  it("closes live panes only for matching resumed conversations", async () => {
    mockIpc.getProviderStatus.mockResolvedValue({
      provider_name: "official",
      route_mode: "official-direct",
      auth_status: "configured",
      observed_at: "x",
    });
    const s = useRuntimeStore();
    s.runtimeState = "running";
    s.runtimeId = "rid";
    s.workspace = "/ws";
    const matchedId = s.createTab("codex")!;
    const otherId = s.createTab("codex")!;
    await tick();
    await tick();
    const matched = s.tabs.find((tab) => tab.tabId === matchedId)!;
    const other = s.tabs.find((tab) => tab.tabId === otherId)!;
    matched.resumeConversationId = "Conversation-1";
    other.resumeConversationId = "conversation-2";

    await s.closeLiveConversationSessions(["conversation-1", "conversation-3"]);

    expect(mockIpc.closeSession).toHaveBeenCalledWith(matched.sessionId);
    expect(mockIpc.closeSession).not.toHaveBeenCalledWith(other.sessionId);
    expect(matched.sessionState).toBe("closing");
    expect(other.sessionState).not.toBe("closing");
  });
});

describe("history memory stays in sync with disk (G-07 last-layout fallback)", () => {
  it("doSave reloads history.value, so a runtime stop preserves the multi-tab layout", async () => {
    // Disk starts with a stale single-codex layout (e.g. from a prior session).
    const wsPath = normalizePath("/ws");
    let disk: WorkbenchHistory = {
      schema_version: 2,
      revision: 0,
      workspaces: [
        {
          path: wsPath,
          last_used_at: "t",
          pinned: false,
          last_agent: "codex",
          runtime: null,
          layout: {
            active_tab_id: null,
            tabs: [{ tab_id: "old", agent: "codex", title: "Codex", position: 0 }],
          },
        },
      ],
    };
    mockIpc.loadHistory.mockImplementation(async () => disk);
    mockIpc.saveHistory.mockImplementation(async (_rev: number, patch: HistoryPatch) => {
      const patched = patch.workspaces[0];
      const others = disk.workspaces.filter((w) => w.path !== patched.path);
      disk = { schema_version: 2, revision: disk.revision + 1, workspaces: [patched, ...others] };
      return disk.revision;
    });

    const s = useRuntimeStore();
    s.runtimeState = "running";
    s.runtimeId = "rid";
    s.workspace = "/ws";
    await s.loadHistory(); // memory seeded from disk = single [codex]

    // Open two tabs; the debounced save must carry BOTH and doSave must reload
    // history.value so the in-memory copy mirrors the freshly-saved disk state.
    await s.initTabs(
      [
        { tab_id: "a", agent: "bash", title: "Bash", position: 0 },
        { tab_id: "b", agent: "codex", title: "Codex", position: 1 },
      ],
      { openAgents: ["bash", "codex"] }
    );
    await tick();
    await tick();
    await s.flushSave();
    await tick();

    const rec = s.history?.workspaces.find((w) => w.path === wsPath);
    expect(rec?.layout?.tabs).toHaveLength(2); // memory synced, NOT the stale [codex]
    expect(disk.workspaces[0].layout?.tabs).toHaveLength(2); // disk too
  });

  it("stopRuntime flushes the CURRENT layout before clearing tabs", async () => {
    // Disk starts with a stale single-codex layout; the current session opens
    // two tabs and stops immediately (before the 300ms debounce fires).
    const wsPath = normalizePath("/ws");
    let disk: WorkbenchHistory = {
      schema_version: 2,
      revision: 0,
      workspaces: [
        {
          path: wsPath,
          last_used_at: "t",
          pinned: false,
          last_agent: "codex",
          runtime: null,
          layout: {
            active_tab_id: null,
            tabs: [{ tab_id: "old", agent: "codex", title: "Codex", position: 0 }],
          },
        },
      ],
    };
    mockIpc.loadHistory.mockImplementation(async () => disk);
    mockIpc.saveHistory.mockImplementation(async (_rev: number, patch: HistoryPatch) => {
      const patched = patch.workspaces[0];
      const others = disk.workspaces.filter((w) => w.path !== patched.path);
      disk = { schema_version: 2, revision: disk.revision + 1, workspaces: [patched, ...others] };
      return disk.revision;
    });

    const s = useRuntimeStore();
    s.runtimeState = "running";
    s.runtimeId = "rid";
    s.workspace = "/ws";
    await s.loadHistory();
    await s.initTabs(
      [
        { tab_id: "a", agent: "bash", title: "Bash", position: 0 },
        { tab_id: "b", agent: "codex", title: "Codex", position: 1 },
      ],
      { openAgents: ["bash", "codex"] }
    );
    await tick();
    await tick();

    await s.stopRuntime(); // no wait for the debounce - flushSave must persist the 2 tabs

    expect(s.tabs).toHaveLength(0); // runtime stopped, tabs cleared
    const rec = s.history?.workspaces.find((w) => w.path === wsPath);
    expect(rec?.layout?.tabs).toHaveLength(2); // current layout survived the stop
    expect(disk.workspaces[0].layout?.tabs).toHaveLength(2); // disk too
  });
});
