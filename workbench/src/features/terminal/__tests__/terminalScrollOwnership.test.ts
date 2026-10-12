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
  dataHandler: null as ((data: string) => void) | null,
  scrollHandler: null as ((position: number) => void) | null,
  keyHandler: null as ((event: KeyboardEvent) => boolean) | null,
  csiHandler: null as ((params: (number | number[])[]) => boolean) | null,
  csiIdentifier: null as unknown,
  scrollToBottom: vi.fn(),
  buffer: { active: { type: "normal", viewportY: 0, baseY: 0 } },
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
vi.mock("@tauri-apps/plugin-clipboard-manager", () => ({ readText: vi.fn(), writeText: vi.fn() }));
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
    buffer = h.buffer;
    open(host: HTMLElement) {
      const viewport = document.createElement("div");
      viewport.className = "xterm-viewport";
      host.appendChild(viewport);
    }
    loadAddon(addon: { activate?: (t: unknown) => void }) { addon?.activate?.(this); }
    resize() {}
    write(_data: unknown, callback?: () => void) { callback?.(); }
    writeln(_data: unknown, callback?: () => void) { callback?.(); }
    parser = {
      registerCsiHandler(id: unknown, handler: (params: (number | number[])[]) => boolean) {
        h.csiIdentifier = id;
        h.csiHandler = handler;
        return { dispose() {} };
      },
    };
    onData(handler: (data: string) => void) { h.dataHandler = handler; }
    onSelectionChange() {}
    attachCustomKeyEventHandler(handler: (event: KeyboardEvent) => boolean) { h.keyHandler = handler; }
    dispose() {}
    refresh() {}
    focus() {}
    clear() {}
    getSelection() { return ""; }
    hasSelection() { return false; }
    paste() {}
    scrollToBottom() { h.scrollToBottom(); }
  },
}));
vi.mock("@xterm/addon-fit", () => ({
  FitAddon: class {
    term: { cols: number; rows: number } | null = null;
    activate(t: { cols: number; rows: number }) { this.term = t; }
    dispose() {}
    fit() {}
    proposeDimensions() { return { cols: 118, rows: 30 }; }
  },
}));
vi.mock("@xterm/addon-webgl", () => ({ WebglAddon: class { onContextLoss() {} dispose() {} } }));
vi.mock("@xterm/addon-search", () => ({
  SearchAddon: class {
    onDidChangeResults() {}
    findNext() {}
    findPrevious() {}
    clearDecorations() {}
    dispose() {}
  },
}));

class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }

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
  await wrapper.vm.$nextTick();
  return { wrapper, runtime, paneId };
}

/** A negative wheel delta is an explicit user request to review history. */
function emitWheel(wrapper: ReturnType<typeof mount>, deltaY: number): void {
  wrapper.get(".terminal").element.dispatchEvent(
    new WheelEvent("wheel", { deltaY, bubbles: true, cancelable: true }),
  );
}

function keyEvent(key: string, mods: { ctrl?: boolean } = {}): KeyboardEvent {
  return {
    type: "keydown",
    key,
    code: key === "/" ? "Slash" : "",
    ctrlKey: mods.ctrl ?? false,
    metaKey: false,
    shiftKey: false,
    altKey: false,
    preventDefault: vi.fn(),
  } as unknown as KeyboardEvent;
}

function emitStream(runtime: ReturnType<typeof useRuntimeStore>, paneId: string, bytes: Uint8Array): void {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  runtime.paneStreams[paneId] = [btoa(binary)];
  runtime.streamCursor[paneId] = 1;
}

const ALT_EXIT = new Uint8Array([0x1b, 0x5b, 0x3f, 0x31, 0x30, 0x34, 0x39, 0x6c]);

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  h.dataHandler = null;
  h.scrollHandler = null;
  h.keyHandler = null;
  h.csiHandler = null;
  h.csiIdentifier = null;
  h.buffer.active = { type: "normal", viewportY: 0, baseY: 0 };
  (globalThis as { ResizeObserver?: unknown }).ResizeObserver = ResizeObserverStub;
});

afterEach(() => { vi.useRealTimers(); });

describe("Terminal scroll ownership wiring", () => {
  it("keeps a reviewing viewport undisturbed, then typing returns it to bottom", async () => {
    vi.useFakeTimers();
    const { wrapper, runtime, paneId } = await mountRunningTerminal();

    emitWheel(wrapper, -120);
    emitStream(runtime, paneId, new TextEncoder().encode("output\n"));
    await wrapper.vm.$nextTick();
    expect(h.scrollToBottom).not.toHaveBeenCalled();

    h.dataHandler!("x");
    expect(h.writeSession).toHaveBeenCalledWith("sid-1", [120]);
    expect(h.scrollToBottom).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("does not treat xterm focus reports as user input while reviewing", async () => {
    vi.useFakeTimers();
    const { wrapper } = await mountRunningTerminal();
    emitWheel(wrapper, -120);

    // A TUI enabling focus reporting makes xterm answer with the current focus
    // state through onData; this is not a keystroke and must preserve review.
    h.dataHandler!("\u001b[I");
    h.dataHandler!("\u001b[O");
    expect(h.scrollToBottom).not.toHaveBeenCalled();

    h.dataHandler!("x");
    expect(h.scrollToBottom).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("returns a reviewed viewport to bottom for direct Ctrl+/ PTY input", async () => {
    vi.useFakeTimers();
    const { wrapper } = await mountRunningTerminal();
    emitWheel(wrapper, -120);
    h.keyHandler!(keyEvent("/", { ctrl: true }));
    expect(h.scrollToBottom).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("scrolls back after xterm restores a live alt-screen exit", async () => {
    vi.useFakeTimers();
    const { wrapper, runtime, paneId } = await mountRunningTerminal();
    emitStream(runtime, paneId, ALT_EXIT);
    await wrapper.vm.$nextTick();

    // xterm restores the saved normal-buffer position during parsing; the
    // ownership correction must run after that restore, not inside the write.
    expect(h.scrollToBottom).not.toHaveBeenCalled();
    vi.advanceTimersByTime(0);
    expect(h.scrollToBottom).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("installs the Codex ED3 guard while leaving ED0 and ED2 to xterm", async () => {
    const { wrapper } = await mountRunningTerminal();

    expect(h.csiIdentifier).toEqual({ final: "J" });
    expect(h.csiHandler!([3])).toBe(true);
    expect(h.csiHandler!([])).toBe(false);
    expect(h.csiHandler!([0])).toBe(false);
    expect(h.csiHandler!([2])).toBe(false);
    wrapper.unmount();
  });

  it("does not move the viewport after alt-screen exit while reviewing", async () => {
    vi.useFakeTimers();
    const { wrapper, runtime, paneId } = await mountRunningTerminal();
    emitWheel(wrapper, -120);
    emitStream(runtime, paneId, ALT_EXIT);
    await wrapper.vm.$nextTick();
    vi.advanceTimersByTime(0);
    expect(h.scrollToBottom).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
