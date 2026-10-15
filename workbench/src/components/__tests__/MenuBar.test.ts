import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createI18n } from "vue-i18n";
import { enUS } from "../../i18n/en-US";
import MenuBar from "../MenuBar.vue";
import { useToastStore } from "../../stores/toast";

const opener = vi.hoisted(() => ({ openUrl: vi.fn().mockResolvedValue(undefined) }));
const updateState = vi.hoisted(() => ({
  check: vi.fn(),
}));
const workspacesState = vi.hoisted(() => ({
  recentWorkspaces: [],
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
vi.mock("../../lib/workspaceWindow", () => ({ openWorkspaceWindow: vi.fn() }));
vi.mock("../../stores/update", () => ({ useUpdateStore: () => updateState }));
vi.mock("../../stores/workspaces", () => ({ useWorkspacesStore: () => workspacesState }));
vi.mock("../../stores/runtime", () => ({
  useRuntimeStore: () => ({ status: "idle", dockerStarting: false }),
}));
vi.mock("../../stores/settings", () => ({
  useSettingsStore: () => ({ target: null, doc: { remoteMachines: [], ui: { font_scale: 1 } } }),
}));
vi.mock("../../stores/doctor", () => ({ useDoctorStore: () => ({ openDialog: vi.fn() }) }));

const i18n = createI18n({ legacy: false, locale: "en-US", messages: { "en-US": enUS } });

async function mountHelpMenu() {
  const wrapper = mount(MenuBar, {
    global: { plugins: [i18n], stubs: { teleport: true } },
  });
  await wrapper.findAll(".menubar-btn").at(-1)!.trigger("click");
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
    await w.findAll("[role='menuitem']").at(2)!.trigger("click");
    expect(opener.openUrl).toHaveBeenCalledOnce();
    expect(opener.openUrl).toHaveBeenCalledWith("https://github.com/Wifabric/AISC#readme");
    w.unmount();
  });

  it("shows progress while an update check is running", async () => {
    updateState.check.mockImplementation(() => new Promise(() => undefined));
    const w = await mountHelpMenu();
    await w.findAll("[role='menuitem']").at(0)!.trigger("click");
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
    await w.findAll("[role='menuitem']").at(0)!.trigger("click");
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
    await w.findAll("[role='menuitem']").at(0)!.trigger("click");
    expect(useToastStore().toasts.map((t) => t.message)).toEqual(["Update 2.1.15-preview.5 is available."]);
    expect(workspacesState.openSettingsTab).toHaveBeenCalledOnce();
    w.unmount();
  });

  it("reports a failed update check", async () => {
    updateState.check.mockRejectedValue(new Error("network unavailable"));
    const w = await mountHelpMenu();
    await w.findAll("[role='menuitem']").at(0)!.trigger("click");
    expect(useToastStore().toasts.map((t) => t.message)).toEqual(["Update check failed: network unavailable"]);
    w.unmount();
  });
});
