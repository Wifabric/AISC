/**
 * D-9 review fix: the Markdown render pipeline is wired into the LIVE terminal
 * pane, not only tests. The pane gains an opt-in "MD" view that reads the same
 * buffered text stream (paneStreams) and renders it through
 * renderTerminalMarkdown/toggleCodeFold/pathLinks. The raw xterm byte stream
 * underneath stays byte-identical (TUI/ANSI passthrough).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { useWorkspacesStore } from "../../../stores/workspaces";
import { useRuntimeStore } from "../../../stores/runtime";
import { useWorkspaceExplorerStore } from "../../../stores/workspaceExplorer";
import type { LaunchAgent, Tab } from "../../../types";
import Terminal from "../Terminal.vue";

const h = vi.hoisted(() => ({
  writes: [] as Uint8Array[],
  workspaceOpen: vi.fn().mockResolvedValue(undefined),
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  resizeSession: vi.fn().mockResolvedValue(undefined),
  writeSession: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../../../lib/ipc", () => ({
  resizeSession: h.resizeSession,
  writeSession: h.writeSession,
  sessionReadSpool: vi.fn().mockResolvedValue({ start: 0, length: 0, bytes: "", eof: true }),
  workspaceOpen: h.workspaceOpen,
  workspaceUploadImage: vi.fn().mockResolvedValue({ relative_path: "" }),
  logUiEvent: h.logUiEvent,
  loadHistory: vi.fn().mockResolvedValue({ schema_version: 2, revision: 0, workspaces: [] }),
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
  readImage: vi.fn(),
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
    options: Record<string, unknown> = {};
    parser = {
      registerCsiHandler(_id: unknown, _handler: (params: (number | number[])[]) => boolean) {
        return { dispose() {} };
      },
    };
    loadAddon(addon: { activate?: (t: unknown) => void }) {
      addon?.activate?.(this);
    }
    resize(cols: number, rows: number) {
      this.cols = cols;
      this.rows = rows;
    }
    open() {}
    write(d: unknown) {
      h.writes.push(d as Uint8Array);
    }
    writeln() {}
    onData() {}
    onSelectionChange() {}
    attachCustomKeyEventHandler() {}
    dispose() {}
    refresh() {}
    focus() {}
    clear() {}
    scrollToTop() {}
    scrollToBottom() {}
    getSelection() {
      return "";
    }
    paste() {}
  },
}));
vi.mock("@xterm/addon-fit", () => ({
  FitAddon: class {
    fit() {}
    proposeDimensions() {
      return { cols: 118, rows: 30 };
    }
    dispose() {}
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

const ANSI_HEAD = "\x1b[2mHere is the plan\x1b[0m";
const RAW = [
  ANSI_HEAD,
  "```ts",
  "const x = 1;",
  "```",
  "- opened /root/project/src/file.ts:42",
  "",
].join("\n");

function bareTab(id: string, agent: LaunchAgent = "bash"): Tab {
  const paneId = id;
  return {
    tabId: id,
    agent,
    title: agent,
    sessionId: "sid-1",
    sessionState: "running",
    exit: null,
    savedTabId: null,
    tree: { kind: "pane", paneId, sessionType: agent },
    activePaneId: paneId,
    panes: { [paneId]: { sessionId: "sid-1", sessionState: "running", exit: null } },
  };
}

function writtenRaw(): string {
  return h.writes.map((w) => new TextDecoder().decode(w)).join("");
}

async function mountWithStream() {
  const ws = useWorkspacesStore();
  ws.launcher.workspace.value = "C:/ws";
  ws.launcher.runtimeId.value = "rid-1";
  await ws.launcher.initTabs([]);
  const inst = ws.runtimes[0]!;
  const tab = bareTab("t1");
  inst.tabs.value = [tab];
  const runtime = useRuntimeStore();
  runtime.activeTabId = "t1";
  // File opens go through the Explorer store (the layer contract forbids a
  // component from importing `workspaceOpen` directly).
  useWorkspaceExplorerStore().workspace = "C:/ws";
  const paneId = tab.activePaneId;
  inst.paneStreams.value[paneId] = [Buffer.from(RAW, "utf-8").toString("base64")];
  inst.streamCursor.value[paneId] = 1;
  const wrapper = mount(Terminal, {
    props: { tabId: "t1", paneId },
    global: { plugins: [i18n] },
  });
  await flushPromises();
  return { wrapper, paneId };
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  h.writes.length = 0;
  (globalThis as { ResizeObserver?: unknown }).ResizeObserver = ResizeObserverStub;
});
afterEach(() => {
  vi.useRealTimers();
});

describe("Terminal Markdown view (D-9 wiring)", () => {
  it("keeps the raw PTY bytes as passthrough before the view is opened", async () => {
    const { wrapper } = await mountWithStream();
    const raw = writtenRaw();
    expect(raw).toContain(ANSI_HEAD);
    expect(raw).toContain("const x = 1;");
    wrapper.unmount();
  });

  it("opens an MD view that renders code blocks, lists and clickable paths", async () => {
    const { wrapper } = await mountWithStream();
    const toggle = wrapper.get('[data-testid="markdown-toggle"]');
    await toggle.trigger("click");
    await flushPromises();

    const overlay = wrapper.get('[data-testid="markdown-overlay"]');
    expect(overlay.text()).toContain("Here is the plan");
    expect(overlay.text()).toContain("── ts ──");
    expect(overlay.text()).toContain("const x = 1;");
    expect(overlay.text()).toContain("• opened /root/project/src/file.ts:42");
    expect(wrapper.find('[data-testid="md-path-link"]').exists()).toBe(true);

    // live xterm bytes are still the untouched raw stream (ANSI preserved)
    expect(writtenRaw()).toContain(ANSI_HEAD);
    wrapper.unmount();
  });

  it("folds a code block via its header and restores it on a second click", async () => {
    const { wrapper } = await mountWithStream();
    await wrapper.get('[data-testid="markdown-toggle"]').trigger("click");
    await flushPromises();

    const header = wrapper.get('[data-testid="md-code-header"]');
    await header.trigger("click");
    await flushPromises();
    expect(wrapper.get('[data-testid="markdown-overlay"]').text()).not.toContain("const x = 1;");
    expect(wrapper.get('[data-testid="md-code-header"]').text()).toContain("folded");

    await wrapper.get('[data-testid="md-code-header"]').trigger("click");
    await flushPromises();
    expect(wrapper.get('[data-testid="markdown-overlay"]').text()).toContain("const x = 1;");
    wrapper.unmount();
  });

  it("opens the clicked path through workspace_open", async () => {
    const { wrapper } = await mountWithStream();
    await wrapper.get('[data-testid="markdown-toggle"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-testid="md-path-link"]').trigger("click");
    await flushPromises();
    expect(h.workspaceOpen).toHaveBeenCalledWith("C:/ws", "/root/project/src/file.ts");
    wrapper.unmount();
  });
});
