import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createI18n } from "vue-i18n";
import { enUS } from "../../i18n/en-US";
import MenuBar from "../MenuBar.vue";
import { useToastStore } from "../../stores/toast";
import type { WorkspaceRecord } from "../../types";

const opener = vi.hoisted(() => ({ openUrl: vi.fn().mockResolvedValue(undefined) }));
const workspaceWindow = vi.hoisted(() => ({ openWorkspaceWindow: vi.fn() }));
const updateState = vi.hoisted(() => ({
  check: vi.fn(),
}));
const workspacesState = vi.hoisted(() => ({
  recentWorkspaces: [] as WorkspaceRecord[],
  activeRuntime: null,
  launcher: {},
  openSettingsTab: vi.fn(),
  surfaceInvalidPath: vi.fn(),
  workspacePathExists: vi.fn().mockResolvedValue(true),
  clearInvalidRecent: vi.fn(),
  exportInvalidRecent: vi.fn(),
  closeWorkspace: vi.fn(),
}));

vi.mock("@tauri-apps/plugin-opener", () => opener);
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: vi.fn() }));
vi.mock("../../lib/workspaceWindow", () => workspaceWindow);
vi.mock("../../stores/update", () => ({ useUpdateStore: () => updateState }));
vi.mock("../../stores/workspaces", () => ({ useWorkspacesStore: () => workspacesState }));
vi.mock("../../stores/runtime", () => ({
  useRuntimeStore: () => ({ status: "idle", dockerStarting: false }),
}));
vi.mock("../../stores/settings", () => ({
  useSettingsStore: () => ({
    target: null,
    doc: {
      remoteMachines: [{
        name: "win-test", host: "10.147.20.7", user: "admin", port: 22, keyPath: null,
      }],
      ui: { font_scale: 1 },
    },
  }),
}));
vi.mock("../../stores/doctor", () => ({ useDoctorStore: () => ({ openDialog: vi.fn() }) }));

const i18n = createI18n({ legacy: false, locale: "en-US", messages: { "en-US": enUS } });

async function mountHelpMenu() {
  const wrapper = mount(MenuBar, {
    global: { plugins: [i18n], stubs: { teleport: true } },
  });
  const buttons = wrapper.findAll(".menubar-btn");
  await buttons[buttons.length - 1]!.trigger("click");
  return wrapper;
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  workspacesState.recentWorkspaces = [];
  workspacesState.activeRuntime = null;
  workspacesState.launcher = {};
});

describe("MenuBar help actions", () => {
  it("opens the current AISC documentation through the OS/browser opener", async () => {
    const w = await mountHelpMenu();
    const items = w.findAll("[role='menuitem']");
    await items[2]!.trigger("click");
    expect(opener.openUrl).toHaveBeenCalledOnce();
    expect(opener.openUrl).toHaveBeenCalledWith("https://github.com/Wifabric/AISC#readme");
    w.unmount();
  });

  it("opens a machine-tagged remote recent on its recorded machine", async () => {
    workspacesState.recentWorkspaces = [{
      path: "E:\\test",
      machine_name: "win-test",
      machine_host: "10.147.20.7",
      last_used_at: "2026-10-15T00:00:00Z",
      last_agent: "bash",
      pinned: false,
      runtime: null,
      layout: null,
    }];
    const w = mount(MenuBar, { global: { plugins: [i18n], stubs: { teleport: true } } });
    await w.findAll(".menubar-btn")[0]!.trigger("click");
    const remote = w.findAll(".recent").find((row) => row.text().includes("win-test"))!;
    await remote.trigger("click");
    expect(workspaceWindow.openWorkspaceWindow).toHaveBeenCalledOnce();
    expect(workspaceWindow.openWorkspaceWindow).toHaveBeenCalledWith({
      workspace: "E:\\test",
      machine: "win-test",
    });
    expect(workspacesState.workspacePathExists).not.toHaveBeenCalled();
    w.unmount();
  });

  it("routes a legacy SSH-host recent alias to its configured machine", async () => {
    workspacesState.recentWorkspaces = [{
      path: "E:\\projects",
      machine_name: "admin@10.147.20.7",
      machine_host: "admin@10.147.20.7",
      last_used_at: "2026-10-15T00:00:00Z",
      last_agent: "bash",
      pinned: false,
      runtime: null,
      layout: null,
    }];
    const w = mount(MenuBar, { global: { plugins: [i18n], stubs: { teleport: true } } });
    await w.findAll(".menubar-btn")[0]!.trigger("click");
    await w.findAll(".recent")[0]!.trigger("click");
    expect(workspaceWindow.openWorkspaceWindow).toHaveBeenCalledWith({
      workspace: "E:\\projects",
      machine: "win-test",
    });
    w.unmount();
  });

  it("shows progress while an update check is running", async () => {
    updateState.check.mockImplementation(() => new Promise(() => undefined));
    const w = await mountHelpMenu();
    const items = w.findAll("[role='menuitem']");
    await items[0]!.trigger("click");
    expect(useToastStore().toasts.map((t) => t.message)).toEqual(["Checking for updates…"]);
    w.unmount();
  });

  it("reports an up-to-date result", async () => {
    updateState.check.mockResolvedValue({
      current: "2.1.15-preview.4",
      latest: "2.1.15-preview.4",
      updateAvailable: false,
    });
    const w = await mountHelpMenu();
    const items = w.findAll("[role='menuitem']");
    await items[0]!.trigger("click");
    expect(useToastStore().toasts.map((t) => t.message)).toEqual(["Up to date (2.1.15-preview.4)."]);
    expect(workspacesState.openSettingsTab).not.toHaveBeenCalled();
    w.unmount();
  });

  it("reports an available update and routes to the install guide", async () => {
    updateState.check.mockResolvedValue({
      current: "2.1.15-preview.4",
      latest: "2.1.15-preview.5",
      updateAvailable: true,
    });
    const w = await mountHelpMenu();
    const items = w.findAll("[role='menuitem']");
    await items[0]!.trigger("click");
    expect(useToastStore().toasts.map((t) => t.message)).toEqual(["Update 2.1.15-preview.5 is available."]);
    expect(workspacesState.openSettingsTab).toHaveBeenCalledOnce();
    w.unmount();
  });

  it("reports a failed update check", async () => {
    updateState.check.mockRejectedValue(new Error("network unavailable"));
    const w = await mountHelpMenu();
    const items = w.findAll("[role='menuitem']");
    await items[0]!.trigger("click");
    expect(useToastStore().toasts.map((t) => t.message)).toEqual(["Update check failed: network unavailable"]);
    w.unmount();
  });
});
