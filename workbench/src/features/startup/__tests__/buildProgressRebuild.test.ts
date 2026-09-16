/**
 * B1 (2.1.12): one-click rebuild from the build terminal state. The old
 * recovery path was backToSummary -> preflight -> build button (three
 * steps); BuildProgress now offers Rebuild on failed/cancelled, calling the
 * SAME store.startBuild chain with the failed tag (contract pinned in
 * b-docker-ui-and-rebuild.md: retry tag = store.buildTag).
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { useRuntimeStore } from "../../../stores/runtime";
import BuildProgress from "../BuildProgress.vue";

const mockIpc = vi.hoisted(() => ({
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  buildImage: vi.fn(),
}));
vi.mock("../../../lib/ipc", () => mockIpc);
vi.mock("@tauri-apps/plugin-dialog", () => ({
  confirm: vi.fn().mockResolvedValue(true),
  open: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ Channel: class {} }));

const win = vi.hoisted(() => {
  const w = {
    focused: true,
    minimized: false,
    getCurrentWindow: vi.fn(),
    isFocused: vi.fn(),
    isMinimized: vi.fn(),
  };
  w.getCurrentWindow.mockReturnValue(w);
  w.isFocused.mockImplementation(() => Promise.resolve(w.focused));
  w.isMinimized.mockImplementation(() => Promise.resolve(w.minimized));
  return w;
});
vi.mock("@tauri-apps/api/window", () => ({ getCurrentWindow: win.getCurrentWindow }));

const notif = vi.hoisted(() => ({
  isPermissionGranted: vi.fn(),
  requestPermission: vi.fn(),
  sendNotification: vi.fn(),
}));
vi.mock("@tauri-apps/plugin-notification", () => notif);

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  i18n.global.locale.value = "en-US";
  win.focused = true;
  notif.isPermissionGranted.mockResolvedValue(true);
  notif.requestPermission.mockResolvedValue("granted");
  notif.sendNotification.mockResolvedValue(undefined);
});

function buttonsOf(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll("button").map((b) => ({ text: b.text(), el: b }));
}

describe("BuildProgress rebuild button (B1)", () => {
  it("failed state shows Rebuild; click re-runs the same tag and can complete", async () => {
    mockIpc.buildImage
      .mockRejectedValueOnce({ code: "AISC_ERR_GENERAL" })
      .mockResolvedValueOnce(undefined);
    const s = useRuntimeStore();
    await s.startBuild("img-b1");
    expect(s.buildStatus).toBe("failed");

    const wrapper = mount(BuildProgress, { global: { plugins: [i18n] } });
    const rebuild = buttonsOf(wrapper).find((b) => b.text === "Rebuild");
    expect(rebuild, "Rebuild button rendered on failed").toBeTruthy();

    await rebuild!.el.trigger("click");
    await flushPromises();
    expect(mockIpc.buildImage).toHaveBeenCalledTimes(2);
    expect(mockIpc.buildImage).toHaveBeenNthCalledWith(2, "img-b1", expect.anything());
    expect(s.buildStatus).toBe("complete");
    // Terminal complete has no Rebuild (nothing to retry).
    expect(buttonsOf(wrapper).find((b) => b.text === "Rebuild")).toBeUndefined();
    wrapper.unmount();
  });

  it("cancelled state also offers Rebuild", async () => {
    mockIpc.buildImage
      .mockRejectedValueOnce({ code: "WB_ERR_CLI_CANCELLED" })
      .mockResolvedValueOnce(undefined);
    const s = useRuntimeStore();
    await s.startBuild("img-b1");
    expect(s.buildStatus).toBe("cancelled");

    const wrapper = mount(BuildProgress, { global: { plugins: [i18n] } });
    const rebuild = buttonsOf(wrapper).find((b) => b.text === "Rebuild");
    expect(rebuild, "Rebuild button rendered on cancelled").toBeTruthy();
    await rebuild!.el.trigger("click");
    await flushPromises();
    expect(s.buildStatus).toBe("complete");
    wrapper.unmount();
  });

  it("docker-unavailable failure keeps Start Docker primary alongside Rebuild", async () => {
    mockIpc.buildImage.mockRejectedValueOnce({ code: "AISC_ERR_DOCKER_UNAVAILABLE" });
    const s = useRuntimeStore();
    await s.startBuild("img-b1");
    const wrapper = mount(BuildProgress, { global: { plugins: [i18n] } });
    const texts = buttonsOf(wrapper).map((b) => b.text);
    expect(texts).toContain("Rebuild");
    expect(texts.some((t) => t.includes("Start Docker"))).toBe(true);
    wrapper.unmount();
  });
});
