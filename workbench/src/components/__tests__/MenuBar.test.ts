import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createI18n } from "vue-i18n";
import { enUS } from "../../i18n/en-US";
import { zhCN } from "../../i18n/zh-CN";
import MenuBar from "../MenuBar.vue";
import { useToastStore } from "../../stores/toast";
import type { WorkspaceRecord } from "../../types";

const opener = vi.hoisted(() => ({ openUrl: vi.fn().mockResolvedValue(undefined) }));
const workspaceWindow = vi.hoisted(() => ({ openWorkspaceWindow: vi.fn() }));
const appApi = vi.hoisted(() => ({ getVersion: vi.fn().mockResolvedValue("2.1.15-preview.7") }));
const doctorState = vi.hoisted(() => ({ openDialog: vi.fn() }));
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
vi.mock("@tauri-apps/api/app", () => appApi);
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: vi.fn() }));
vi.mock("../../lib/workspaceWindow", () => workspaceWindow);
vi.mock("../../stores/update", () => ({ useUpdateStore: () => updateState }));
vi.mock("../../stores/workspaces", () => ({ useWorkspacesStore: () => workspacesState }));
vi.mock("../../stores/runtime", () => ({
  useRuntimeStore: () => ({
    status: "idle",
    dockerStarting: false,
    capability: {
      version_info: {
        cli_version: "0.1.8.dev0",
        bundle_version: "0.1.8.dev0",
        image_version: "2.1.15",
        claude_version: "2.1.273",
        python_version: "3.12.10",
      },
    },
  }),
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
vi.mock("../../stores/doctor", () => ({ useDoctorStore: () => doctorState }));

const i18n = createI18n({ legacy: false, locale: "en-US" as string, messages: { "en-US": enUS, "zh-CN": zhCN } });

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
  i18n.global.locale.value = "en-US";
  vi.clearAllMocks();
  workspacesState.recentWorkspaces = [];
  workspacesState.activeRuntime = null;
  workspacesState.launcher = {};
});

describe("MenuBar help actions", () => {
  it("opens the current AISC documentation through the OS/browser opener", async () => {
    const w = await mountHelpMenu();
    const items = w.findAll("[role='menuitem']");
    await items[items.length - 1]!.trigger("click");
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

  it("separates diagnostics, help docs, and the About dialog", async () => {
    const oldLocale = i18n.global.locale.value;
    i18n.global.locale.value = "zh-CN";
    const w = mount(MenuBar, { global: { plugins: [i18n], stubs: { teleport: true } } });
    await w.findAll(".menubar-btn")[2]!.trigger("click");
    const items = w.findAll("[role='menuitem']");
    expect(items.map((item) => item.text())).toContain("运行诊断");
    expect(items.map((item) => item.text())).toContain("关于 AISC Workbench");
    expect(items.map((item) => item.text())).toContain("帮助文档");

    const diagnostics = items.find((item) => item.text() === "运行诊断")!;
    await diagnostics.trigger("click");
    expect(doctorState.openDialog).toHaveBeenCalledOnce();

    const about = w.find("[data-testid='about-dialog']");
    expect(about.exists()).toBe(false);
    const aboutItem = items.find((item) => item.text() === "关于 AISC Workbench")!;
    await aboutItem.trigger("click");
    await Promise.resolve();
    expect(appApi.getVersion).toHaveBeenCalledOnce();
    expect(w.find("[data-testid='about-dialog']").exists()).toBe(true);
    const text = w.find("[data-testid='about-dialog']").text();
    i18n.global.locale.value = oldLocale;
    expect(text).toContain("2.1.15-preview.7");
    expect(text).toContain("0.1.8.dev0");
    expect(text).toContain("2.1.273");
    expect(text).toContain("3.12.10");
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
