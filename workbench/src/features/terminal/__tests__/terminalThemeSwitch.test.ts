/**
 * B0 (2026-09-16): switching the app theme left pre-switch terminal output in
 * the OLD palette — dark bands inside a light viewport (user screenshot;
 * v2.1.11). Root cause: addon-webgl 0.19's glyph atlas / row-dirty tracking
 * does not repaint existing cells on an options.theme change, and refresh()
 * alone doesn't reach them. Fix under test: the theme watch recreates the
 * WebglAddon (atlas rebuilds against the new theme; session/PTY untouched,
 * mirroring the context-loss fallback semantics).
 *
 * xterm and addons are faked (jsdom has no canvas) with mocks that capture
 * addon instances and refresh calls, mirroring terminalPasteKey.test.ts.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { useWorkspacesStore } from "../../../stores/workspaces";
import { useRuntimeStore } from "../../../stores/runtime";
import { effectiveTheme } from "../../../theme";
import { LIGHT_TERMINAL_THEME, TERMINAL_THEME } from "../renderer";
import type { LaunchAgent, Tab } from "../../../types";
import Terminal from "../Terminal.vue";

const h = vi.hoisted(() => ({
  writeSession: vi.fn().mockResolvedValue(undefined),
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  keyHandler: null as ((e: KeyboardEvent) => boolean) | null,
  refreshes: 0,
  themeApplied: null as unknown,
  addons: [] as { dispose: ReturnType<typeof vi.fn> }[],
}));

vi.mock("../../../lib/ipc", () => ({
  resizeSession: vi.fn().mockResolvedValue(undefined),
  writeSession: h.writeSession,
  logUiEvent: h.logUiEvent,
  loadHistory: vi.fn().mockResolvedValue({ schema_version: 1, revision: 0, workspaces: [] }),
  saveHistory: vi.fn().mockResolvedValue(1),
  negotiateCapabilities: vi.fn(),
  listRuntimes: vi.fn().mockResolvedValue({ runtimes: [] }),
  openSession: vi.fn().mockResolvedValue({}),
  closeSession: vi.fn().mockResolvedValue({ reason: "user_close", exitCode: null }),
  ackSessionExit: vi.fn().mockResolvedValue("acknowledged"),
  getProviderStatus: vi.fn().mockResolvedValue({}),
  stopRuntime: vi.fn().mockResolvedValue({ state: "stopped" }),
  runtimeInspect: vi.fn().mockResolvedValue({ state: "stopped" }),
  runtimeStatus: vi.fn().mockResolvedValue({ snapshot: { state: "stopped" }, services: null }),
}));

vi.mock("@tauri-apps/plugin-clipboard-manager", () => ({
  readText: vi.fn().mockResolvedValue(""),
  writeText: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({ confirm: vi.fn().mockResolvedValue(true), open: vi.fn() }));
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

vi.mock("@xterm/xterm", () => ({
  Terminal: class {
    cols = 80;
    rows = 24;
    // Proxy so `term.options.theme = X` (nested mutation) is observable.
    options: Record<string, unknown> = new Proxy(
      {},
      {
        set(target: Record<string, unknown>, key: string, value: unknown) {
          target[key] = value;
          if (key === "theme") h.themeApplied = value;
          return true;
        },
      },
    );
    loadAddon(addon: { activate?: (t: unknown) => void }) {
      addon?.activate?.(this);
    }
    resize() {}
    open() {}
    write(_d: unknown, cb?: () => void) {
      cb?.();
    }
    writeln(_d: unknown, cb?: () => void) {
      cb?.();
    }
    onData() {}
    onSelectionChange() {}
    attachCustomKeyEventHandler(fn: (e: KeyboardEvent) => boolean) {
      h.keyHandler = fn;
    }
    dispose() {}
    refresh() {
      h.refreshes++;
    }
    focus() {}
    clear() {}
    getSelection() {
      return "";
    }
    hasSelection() {
      return false;
    }
    paste() {}
  },
}));
vi.mock("@xterm/addon-fit", () => ({
  FitAddon: class {
    activate() {}
    dispose() {}
    fit() {}
    proposeDimensions() {
      return { cols: 118, rows: 30 };
    }
  },
}));
vi.mock("@xterm/addon-webgl", () => ({
  WebglAddon: class {
    disposed = vi.fn();
    constructor() {
      h.addons.push({ dispose: this.disposed });
    }
    onContextLoss() {}
    dispose() {
      this.disposed();
    }
  },
}));
vi.mock("@xterm/addon-search", () => ({
  SearchAddon: class {
    onDidChangeResults() {}
    findNext() {}
    findPrevious() {}
    clearDecorations() {}
    dispose() {}
  },
}));

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

function bareTab(id: string, agent: LaunchAgent = "bash"): Tab {
  const paneId = id;
  return {
    tabId: id,
    agent,
    title: agent,
    sessionId: null,
    sessionState: "idle",
    exit: null,
    savedTabId: null,
    tree: { kind: "pane", paneId, sessionType: agent },
    activePaneId: paneId,
    panes: { [paneId]: { sessionId: null, sessionState: "idle", exit: null } },
  };
}

async function mountRunningTerminal() {
  const ws = useWorkspacesStore();
  ws.launcher.workspace.value = "C:/ws";
  ws.launcher.runtimeId.value = "rid-1";
  await ws.launcher.initTabs([]);
  ws.runtimes[0].tabs.value = [bareTab("t1", "bash")];
  const runtime = useRuntimeStore();
  runtime.activeTabId = "t1";
  const tab = runtime.tabs[0];
  const paneId = tab.activePaneId;
  tab.panes[paneId].sessionState = "running";
  tab.panes[paneId].sessionId = "sid-1";
  tab.sessionState = "running";
  return mount(Terminal, {
    props: { tabId: tab.tabId, paneId },
    global: { plugins: [i18n] },
  });
}

/** No-op: theme application is observed through the options Proxy in the
 * xterm mock (h.themeApplied) and the addon/recycle counters in h. */

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  h.keyHandler = null;
  h.refreshes = 0;
  h.addons.length = 0;
  (globalThis as { ResizeObserver?: unknown }).ResizeObserver = ResizeObserverStub;
  effectiveTheme.value = "dark";
});

afterEach(() => {
  effectiveTheme.value = "dark";
});

describe("B0: theme switch recreates the WebglAddon (dark-band residue)", () => {
  it("dark->light recycles the addon and repaints (atlas rebuild)", async () => {
    const wrapper = await mountRunningTerminal();
    await flushPromises();
    // renderer defaults to auto -> webgl; one addon mounted at startup.
    expect(h.addons.length).toBe(1);
    const before = h.refreshes;

    effectiveTheme.value = "light";
    await flushPromises();

    // Theme applied is the light palette (contrast-locked tokens).
    expect(h.themeApplied).toBe(LIGHT_TERMINAL_THEME);
    // Old addon disposed, a fresh one mounted against the new theme.
    expect(h.addons[0].dispose).toHaveBeenCalled();
    expect(h.addons.length).toBe(2);
    // Viewport repaint still requested alongside the recycle.
    expect(h.refreshes).toBeGreaterThan(before);
    wrapper.unmount();
  });

  it("light->dark recycles back to the dark palette", async () => {
    effectiveTheme.value = "light";
    const wrapper = await mountRunningTerminal();
    await flushPromises();
    expect(h.addons.length).toBe(1);

    effectiveTheme.value = "dark";
    await flushPromises();

    expect(h.themeApplied).toBe(TERMINAL_THEME);
    expect(h.addons[0].dispose).toHaveBeenCalled();
    expect(h.addons.length).toBe(2);
    wrapper.unmount();
  });
});
