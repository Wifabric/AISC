/**
 * LaunchSummary image-missing build button (G-14 bugfix, 2026-08-10).
 *
 * Root cause: the build button was gated on `imageMissing = image fail && action
 * !== reuse`, so a workspace with a matching existing runtime (recommended
 * action "reuse") hid the button while the gate still showed 镜像失败 - a dead
 * end. The button is now driven by `imageNotFound` = image check fail with
 * `AISC_ERR_IMAGE_NOT_FOUND` (genuinely missing tag), independent of action,
 * and the Docker-unreachable case (DOCKER_UNAVAILABLE) stays button-free.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { useUsageStore } from "../../../stores/usage";
import * as ipc from "../../../lib/ipc";
import { i18n } from "../../../i18n";
import { useRuntimeStore } from "../../../stores/runtime";
import LaunchSummary from "../LaunchSummary.vue";
import type { PreflightReport, RecommendedAction } from "../../../types";

vi.mock("../../../lib/ipc", () => ({
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  buildImage: vi.fn(),
  negotiateCapabilities: vi.fn(),
  networkSubscriptionShow: vi.fn(),
  networkSubscriptionImportFile: vi.fn(),
  networkSubscriptionClear: vi.fn(),
}));
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

function preflight(action: RecommendedAction, imageError: string | null): PreflightReport {
  return {
    spec: {},
    checks: [
      { id: "docker", status: "pass", error_code: null, detail: null },
      { id: "workspace", status: "pass", error_code: null, detail: null },
      {
        id: "image",
        status: imageError ? "fail" : "pass",
        error_code: imageError,
        detail: imageError ? "Image not found" : null,
      },
      { id: "network", status: "pass", error_code: null, detail: null },
      { id: "runtime_conflict", status: "pass", error_code: null, detail: null },
    ],
    can_start: !imageError,
    recommended_action: action,
    matching_runtime_id: action === "reuse" || action === "restart" ? "rid" : null,
    conflicts: {},
    observed_at: "t",
  };
}

function setup(action: RecommendedAction, imageError: string | null) {
  const s = useRuntimeStore();
  s.preflight = preflight(action, imageError);
  s.launch.image = "super-claude:latest";
  return s;
}

function buildBtn(wrapper: ReturnType<typeof mount>): boolean {
  return wrapper.text().includes("构建镜像") || wrapper.text().includes("Build image");
}

beforeEach(() => {
  setActivePinia(createPinia());
  i18n.global.locale.value = "zh-CN";
});

describe("build button visibility (G-14 bugfix)", () => {
  it("reuse action + missing image shows the build button and message", () => {
    const s = setup("reuse", "AISC_ERR_IMAGE_NOT_FOUND");
    const wrapper = mount(LaunchSummary, { global: { plugins: [i18n] } });
    expect(buildBtn(wrapper)).toBe(true);
    expect(wrapper.find(".gate-msg.config").exists()).toBe(true);
    void s;
  });

  it("start action + missing image shows the build button", () => {
    const s = setup("start", "AISC_ERR_IMAGE_NOT_FOUND");
    const wrapper = mount(LaunchSummary, { global: { plugins: [i18n] } });
    expect(buildBtn(wrapper)).toBe(true);
    void s;
  });

  it("reuse action + Docker-unreachable image check shows no build button", () => {
    const s = setup("reuse", "AISC_ERR_DOCKER_UNAVAILABLE");
    const wrapper = mount(LaunchSummary, { global: { plugins: [i18n] } });
    expect(buildBtn(wrapper)).toBe(false);
    void s;
  });

  it("image present shows no build button", () => {
    const s = setup("start", null);
    const wrapper = mount(LaunchSummary, { global: { plugins: [i18n] } });
    expect(buildBtn(wrapper)).toBe(false);
    void s;
  });
});

it("updates the proxy warning after import and clear while the summary stays open", async () => {
  const status = { configured: false, source: null, url_masked: null, fetched_at: null,
    config_sha256: null, has_config_file: false, userinfo: null };
  vi.mocked(ipc.networkSubscriptionShow).mockResolvedValue(status);
  vi.mocked(ipc.networkSubscriptionImportFile).mockResolvedValue({
    ...status, configured: true, source: "manual", has_config_file: true,
  });
  const runtime = setup("start", null);
  runtime.launch.network = "proxy";
  runtime.showAdvanced = true;
  const wrapper = mount(LaunchSummary, { global: { plugins: [i18n] } });
  await flushPromises();
  expect(wrapper.find(".sub-hint").exists()).toBe(true);
  const usage = useUsageStore();
  expect(await usage.importContent("rules: []")).toBe(true);
  await nextTick();
  expect(wrapper.find(".sub-hint").exists()).toBe(false);
  expect(await usage.clearSubscription()).toBe(true);
  await nextTick();
  expect(wrapper.find(".sub-hint").exists()).toBe(true);
  wrapper.unmount();
});
