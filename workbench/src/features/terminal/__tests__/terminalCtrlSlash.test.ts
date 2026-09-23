/**
 * b4 (v2.1.14, user feedback 2026-09-22): Ctrl+/ was silently dropped —
 * xterm 6.0's legacy keymap has no ctrl-only entry for '/', so codex's
 * btw↔main toggle (toggle_side_conversation) never saw a byte. The handler
 * now intercepts the combo and direct-sends the payload (legacy 0x1F by
 * default; CTRL_SLASH_CSI_U flips to the kitty CSI-u arm for the handtest
 * A/B). This test pins the handler-boundary behavior.
 *
 * Same harness as terminalPasteKey.test.ts: xterm is faked (jsdom has no
 * canvas) with a mock that CAPTURES the custom key handler.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { useWorkspacesStore } from "../../../stores/workspaces";
import { useRuntimeStore } from "../../../stores/runtime";
import type { LaunchAgent, Tab } from "../../../types";
import Terminal from "../Terminal.vue";

const h = vi.hoisted(() => ({
  writeSession: vi.fn().mockResolvedValue(undefined),
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  keyHandler: null as ((e: KeyboardEvent) => boolean) | null,
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
  readText: vi.fn(),
  writeText: vi.fn(),
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
    options: Record<string, unknown> = {};
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
    refresh() {}
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
    term: { cols: number; rows: number } | null = null;
    activate(t: { cols: number; rows: number }) {
      this.term = t;
    }
    dispose() {}
    fit() {}
    proposeDimensions() {
      return { cols: 118, rows: 30 };
    }
  },
}));
vi.mock("@xterm/addon-webgl", () => ({
  WebglAddon: class {
    onContextLoss() {}
    dispose() {}
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
  const wrapper = mount(Terminal, {
    props: { tabId: tab.tabId, paneId },
    global: { plugins: [i18n] },
  });
  return wrapper;
}

function keyEvent(
  type: "keydown" | "keyup",
  key: string,
  mods: { ctrl?: boolean; shift?: boolean; alt?: boolean } = {},
): KeyboardEvent {
  return {
    type,
    key,
    code: key === "/" ? "Slash" : "",
    ctrlKey: mods.ctrl ?? false,
    metaKey: false,
    shiftKey: mods.shift ?? false,
    altKey: mods.alt ?? false,
    preventDefault: vi.fn(),
  } as unknown as KeyboardEvent;
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  h.keyHandler = null;
  (globalThis as { ResizeObserver?: unknown }).ResizeObserver = ResizeObserverStub;
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Terminal Ctrl+/ direct-send (b4)", () => {
  it("keydown ctrl+/ sends the legacy 0x1F byte, swallows the key", async () => {
    vi.useFakeTimers();
    const wrapper = await mountRunningTerminal();
    await vi.advanceTimersByTimeAsync(0);
    const handler = h.keyHandler!;
    const e = keyEvent("keydown", "/", { ctrl: true });
    expect(handler(e)).toBe(false);
    expect(e.preventDefault).toHaveBeenCalled();
    expect(h.writeSession).toHaveBeenCalledTimes(1);
    expect(h.writeSession).toHaveBeenCalledWith("sid-1", [0x1f]);
    wrapper.unmount();
  });

  it("keyup of the same combo never sends (press-only, S8f filter)", async () => {
    vi.useFakeTimers();
    const wrapper = await mountRunningTerminal();
    await vi.advanceTimersByTimeAsync(0);
    const handler = h.keyHandler!;
    expect(handler(keyEvent("keyup", "/", { ctrl: true }))).toBe(true);
    expect(h.writeSession).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("Ctrl+Shift+/ and bare / stay PTY input", async () => {
    vi.useFakeTimers();
    const wrapper = await mountRunningTerminal();
    await vi.advanceTimersByTimeAsync(0);
    const handler = h.keyHandler!;
    expect(handler(keyEvent("keydown", "/", { ctrl: true, shift: true }))).toBe(true);
    expect(handler(keyEvent("keydown", "/"))).toBe(true);
    expect(h.writeSession).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
