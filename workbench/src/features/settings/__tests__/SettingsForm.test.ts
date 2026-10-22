/**
 * Manual-test #1 regression (2026-09-06): P8 added the 'performance' section
 * to the section list but not to GROUP_KEY — `t(undefined)` threw SyntaxError
 * mid-render, which aborted the App patch and froze the whole UI (settings
 * chip switched, content stuck on the workspace view, dead until restart).
 *
 * This mounts the REAL form with the REAL i18n bundles: every section heading
 * must translate. A future section added to GROUPS without a GROUP_KEY entry
 * (or a missing dictionary key) fails here at test time instead of bricking
 * the app at runtime.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { useSettingsStore } from "../../../stores/settings";
import SettingsForm from "../SettingsForm.vue";
import type { SettingsDocument } from "../../../types";

const mockIpc = vi.hoisted(() => ({
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  loadSettings: vi.fn(),
  saveSettings: vi.fn(),
  resetGuiSettings: vi.fn(),
  cacheUsage: vi.fn().mockResolvedValue({ dockerAvailable: true, rows: [] }),
  cacheInspect: vi.fn(),
  cacheCleanup: vi.fn(),
  dockerScan: vi.fn(),
  dockerCleanup: vi.fn(),
  dockerRebuild: vi.fn(),
  appCheckUpdate: vi.fn(),
  appDownloadUpdate: vi.fn(),
  appInstallUpdate: vi.fn(),
  lowSpecStatus: vi.fn().mockResolvedValue({ totalRam: 16 * 1024 ** 3, lowSpec: false }),
}));

vi.mock("../../../lib/ipc", () => mockIpc);
vi.mock("@tauri-apps/plugin-dialog", () => ({ confirm: vi.fn().mockResolvedValue(true) }));

const doc: SettingsDocument = {
  schemaVersion: 1,
  revision: 3,
  aiscCliPath: "C:\\aisc.exe",
  ui: { language: "auto", font_scale: 1.0, theme: "system", explorer_ignore: [], default_new_page: "workspace", default_tab_agent: "bash" },
  terminal: {
    font_family: "Cascadia Mono, Consolas, monospace",
    font_size: 14,
    line_height: 1.2,
    letter_spacing: 0,
    scrollback: 5000,
    renderer: "auto",
    smooth_scroll_duration: 100,
  },
  window: { remember_geometry: true, close_behavior: "quit", geometry: null },
  hostTools: [],
  remoteMachines: [],
  performance: { lowSpec: false, containerMemory: "3g", containerCpus: 1.5 },
  issues: [],
  corrupted: false,
  readOnly: false,
};

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  mockIpc.loadSettings.mockResolvedValue(JSON.parse(JSON.stringify(doc)));
});

describe("SettingsForm section headings (manual-test #1)", () => {
  it("P2-5: nav carries every section; the pane shows the ACTIVE one", async () => {
    const store = useSettingsStore();
    await store.load();
    const wrapper = mount(SettingsForm, { global: { plugins: [i18n] } });

    // The nav lists all eight sections (A7 added 关于与更新); the pane
    // renders only the active one (VS Code-style — 手测裁决 2026-09-12).
    const nav = wrapper.findAll(".nav-item").map((b) => b.text());
    expect(nav).toEqual([
      i18n.global.t("settings.group.ui"),
      i18n.global.t("settings.group.terminal"),
      i18n.global.t("settings.group.window"),
      i18n.global.t("settings.group.hostTools"),
      i18n.global.t("settings.group.machines"),
      i18n.global.t("settings.group.performance"),
      i18n.global.t("settings.group.disk"),
      i18n.global.t("settings.group.about"),
    ]);
    expect(wrapper.findAll("h3.group").map((h) => h.text())).toEqual([
      i18n.global.t("settings.group.ui"),
    ]);
    // Picking a section swaps the pane and leaves search mode.
    await wrapper.findAll(".nav-item")[4]!.trigger("click");
    expect(wrapper.findAll("h3.group").map((h) => h.text())).toEqual([
      i18n.global.t("settings.group.machines"),
    ]);
  });

  it("P2-5: search dims non-matching nav entries and shows matching groups", async () => {
    const store = useSettingsStore();
    await store.load();
    const wrapper = mount(SettingsForm, { global: { plugins: [i18n] } });

    await wrapper.find(".nav-search").setValue("字体");
    // Terminal matches (字体/字号); ui does not (no such label).
    const dimmed = wrapper.findAll(".nav-item.dim").map((b) => b.text());
    expect(dimmed).not.toContain(i18n.global.t("settings.group.terminal"));
    expect(wrapper.findAll("h3.group").map((h) => h.text())).toContain(
      i18n.global.t("settings.group.terminal"),
    );
    expect(wrapper.findAll("h3.group").map((h) => h.text())).not.toContain(
      i18n.global.t("settings.group.ui"),
    );
  });

  it("reports Workbench GUI and bundled CLI versions separately", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue({
      current: "2.1.15-preview.6", latest: "2.1.15-preview.7", updateAvailable: true,
      setupUrl: "s", sha256Url: "h", releaseUrl: "r",
      cliCurrent: "0.1.7.dev0", cliLatest: "0.1.8.dev0", cliUpdateAvailable: true,
      note: "",
    });
    const store = useSettingsStore();
    await store.load();
    const wrapper = mount(SettingsForm, { global: { plugins: [i18n] } });
    await wrapper.findAll(".nav-item")[7]!.trigger("click");
    const check = wrapper.findAll("button").find((b) => b.text() === i18n.global.t("settings.about.check"))!;
    await check.trigger("click");
    await Promise.resolve();
    expect(wrapper.text()).toContain("Workbench GUI");
    expect(wrapper.text()).toContain("2.1.15-preview.6");
    expect(wrapper.text()).toContain("2.1.15-preview.7");
    expect(wrapper.text()).toContain(i18n.global.t("settings.about.cliCurrent"));
    expect(wrapper.text()).toContain("0.1.7.dev0");
    expect(wrapper.text()).toContain("0.1.8.dev0");
    wrapper.unmount();
  });

  it("keeps the update check button available after a completed check", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue({
      current: "2.1.15-preview.3", latest: "2.1.15-preview.3", updateAvailable: false,
      setupUrl: null, sha256Url: null, releaseUrl: null, note: "",
    });
    const store = useSettingsStore();
    await store.load();
    const wrapper = mount(SettingsForm, { global: { plugins: [i18n] } });
    await wrapper.findAll(".nav-item")[7]!.trigger("click");
    const check = wrapper.findAll("button").find((b) => b.text() === i18n.global.t("settings.about.check"))!;
    await check.trigger("click");
    await Promise.resolve();
    expect(mockIpc.appCheckUpdate).toHaveBeenCalledTimes(1);
    const checkAgain = wrapper.findAll("button").find((b) => b.text() === i18n.global.t("settings.about.checkAgain"));
    expect(checkAgain?.exists()).toBe(true);
  });

  it("renders the low-spec memory/cpus inputs when lowSpec is on", async () => {
    mockIpc.loadSettings.mockResolvedValue(
      JSON.parse(JSON.stringify({ ...doc, performance: { lowSpec: true, containerMemory: "2g", containerCpus: 1.0 } })),
    );
    const store = useSettingsStore();
    await store.load();
    const wrapper = mount(SettingsForm, { global: { plugins: [i18n] } });

    // P2-5: navigate to the performance section first (single-section pane).
    await wrapper.findAll(".nav-item")[5]!.trigger("click");
    const body = wrapper.text();
    expect(body).toContain(i18n.global.t("settings.perf.memory"));
    expect(body).toContain(i18n.global.t("settings.perf.cpus"));
  });
});

describe("docker admin scan-first gate (2.1.12 B3, user ruling 2026-09-16)", () => {
  async function mountDiskSection() {
    const store = useSettingsStore();
    await store.load();
    const wrapper = mount(SettingsForm, { global: { plugins: [i18n] } });
    await wrapper.findAll(".nav-item")[6]!.trigger("click"); // disk section
    return { store, wrapper };
  }

  it("groups duplicate repo tags with the same image ID into one row", async () => {
    const store = useSettingsStore();
    await store.load();
    store.dockerReport = {
      dockerAvailable: true,
      dockerReason: "ok",
      containers: { owned: [], legacy_owned: [], unverified: [] },
      images: {
        owned: [
          { id: "sha256:same", name: "docker.1ms.run/library/node:22-slim", image: "docker.1ms.run/library/node:22-slim", status: "", tag: "", ownership: "owned", state: "present", reason: "label" },
          { id: "sha256:same", name: "node:22-slim", image: "node:22-slim", status: "", tag: "", ownership: "owned", state: "present", reason: "label" },
        ],
        legacy_owned: [],
        unverified: [],
      },
      danglingOwned: [],
      warnings: [],
    };
    const wrapper = mount(SettingsForm, { global: { plugins: [i18n] } });
    await wrapper.findAll(".nav-item")[6]!.trigger("click");
    const imageRows = wrapper.findAll(".manage-row");
    expect(imageRows).toHaveLength(1);
    expect(imageRows[0]!.text()).toContain("docker.1ms.run/library/node:22-slim");
    expect(imageRows[0]!.text()).toContain("node:22-slim");
    expect(imageRows).toHaveLength(1);
    wrapper.unmount();
  });

  const inspectReport = {
    dockerAvailable: true,
    categories: {
      images: { rows: [], summary: { count: 2, reclaimable_bytes: 2_000_000_000, unknown_count: 0 } },
      containers: { rows: [], summary: { count: 2, reclaimable_bytes: 100, unknown_count: 0 } },
      volumes: { rows: [], summary: { count: 3, reclaimable_bytes: 0, unknown_count: 0 } },
      build_cache: { rows: [], summary: { count: 387, reclaimable_bytes: 9_000_000_000, unknown_count: 0 } },
      networks: { rows: [], summary: { count: 5, reclaimable_bytes: 0, unknown_count: 0 } },
    },
    capabilities: {}, warnings: [], disclaimer: "",
  };
  const scanReport = {
    dockerAvailable: true,
    dockerReason: "ok",
    containers: {
      owned: [
        { id: "c1", name: "aisc-1", image: "super-claude:latest", status: "", tag: "", ownership: "owned", reason: "label" },
        { id: "c2", name: "aisc-2", image: "super-claude:latest", status: "", tag: "", ownership: "owned", reason: "label" },
      ],
      legacy_owned: [], unverified: [],
    },
    images: {
      owned: [
        { id: "same", name: "node:22", image: "node:22", status: "", tag: "", ownership: "owned", reason: "label" },
        { id: "same", name: "mirror/node:22", image: "mirror/node:22", status: "", tag: "", ownership: "owned", reason: "label" },
      ],
      legacy_owned: [], unverified: [],
    },
    danglingOwned: [{ id: "dangling", name: "dangling", image: "dangling", status: "", tag: "", ownership: "owned", reason: "label" }],
    warnings: [],
  };

  function mockUnifiedScan() {
    mockIpc.dockerScan.mockResolvedValue(scanReport);
    mockIpc.cacheInspect.mockResolvedValue(inspectReport);
  }

  async function openDisk() {
    const store = useSettingsStore();
    await store.load();
    const wrapper = mount(SettingsForm, { global: { plugins: [i18n] } });
    await wrapper.findAll(".nav-item")[6]!.trigger("click");
    return wrapper;
  }

  it("runs one unified Docker scan and reports ownership plus inspect totals", async () => {
    mockUnifiedScan();
    const wrapper = await openDisk();
    await wrapper.findAll("button").find((b) => b.text() === i18n.global.t("settings.docker.scan"))!.trigger("click");
    await Promise.resolve();
    expect(mockIpc.dockerScan).toHaveBeenCalledWith("upgrade");
    expect(mockIpc.cacheInspect).toHaveBeenCalled();
    const summary = wrapper.find("[data-testid='docker-resource-summary']");
    expect(summary.exists()).toBe(true);
    expect(summary.text()).toContain(i18n.global.t("settings.docker.rowContainers"));
    expect(summary.text()).toContain("2");
    expect(summary.text()).toContain(i18n.global.t("settings.docker.rowImages"));
    expect(summary.text()).toContain("1");
    expect(summary.text()).toContain("387");
    expect(summary.text()).toContain("9.0 GB");
    expect(summary.text()).toContain("3");
    expect(summary.text()).toContain("5");
    wrapper.unmount();
  });

  it("one-click cleanup runs AISC resources then cache cleanup and rescans", async () => {
    mockUnifiedScan();
    const order: string[] = [];
    mockIpc.dockerCleanup.mockImplementation(async () => { order.push("resources"); return { containers: { removed: [], not_found: [], failed: [] }, images: { removed: [], not_found: [], failed: [] }, skippedUnverified: [], warnings: [] }; });
    mockIpc.cacheCleanup.mockImplementation(async () => { order.push("cache"); return { prunes: [], warnings: [], rows_after: [] }; });
    mockIpc.dockerScan.mockImplementation(async () => { order.push("scan"); return scanReport; });
    const wrapper = await openDisk();
    await wrapper.findAll("button").find((b) => b.text() === i18n.global.t("settings.docker.scan"))!.trigger("click");
    await flushPromises();
    order.length = 0;
    await wrapper.findAll("button").find((b) => b.text() === i18n.global.t("settings.docker.cleanup"))!.trigger("click");
    await flushPromises();
    expect(order).toEqual(["resources", "cache", "scan"]);
    expect(mockIpc.cacheInspect).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });

  it("cleanup/rebuild disabled before any scan, enabled after one loads", async () => {
    mockIpc.dockerScan.mockResolvedValue({
      dockerAvailable: true, dockerReason: "ok",
      containers: { owned: [], legacy_owned: [], unverified: [] },
      images: { owned: [], legacy_owned: [], unverified: [] },
      danglingOwned: [], warnings: [],
    });
    const { store, wrapper } = await mountDiskSection();
    const byText = (key: string) =>
      wrapper.findAll("button").find((b) => b.text() === i18n.global.t(key));

    const cleanup = byText("settings.docker.cleanup")!;
    const rebuild = byText("settings.docker.rebuild")!;
    expect((cleanup.element as HTMLButtonElement).disabled).toBe(true);
    expect((rebuild.element as HTMLButtonElement).disabled).toBe(true);

    await store.loadDockerScan();
    await Promise.resolve();
    expect((cleanup.element as HTMLButtonElement).disabled).toBe(false);
    expect((rebuild.element as HTMLButtonElement).disabled).toBe(false);
    wrapper.unmount();
  });

  // --- v2.1.16 b3 (feedback #9): resource cards + dedicated cache cleanup ---

  it("renders the Docker summary as cards with Chinese build cache label and totals", async () => {
    mockUnifiedScan();
    const wrapper = await openDisk();
    await wrapper.findAll("button").find((b) => b.text() === i18n.global.t("settings.docker.scan"))!.trigger("click");
    await flushPromises();
    const summary = wrapper.find("[data-testid='docker-resource-summary']");
    expect(summary.exists()).toBe(true);
    const cards = summary.findAll("[data-testid='docker-summary-card']");
    expect(cards.length).toBeGreaterThanOrEqual(6);
    expect(summary.text()).toContain("构建缓存");
    expect(summary.text()).not.toContain("Build Cache");
    // 合计卡：总条目（2+2+3+387+5）与总可回收（2GB + 9GB ≈ 11 GB）
    expect(summary.text()).toContain("合计");
    expect(summary.text()).toContain("11.0 GB");
    wrapper.unmount();
  });

  it("orders action buttons with dedicated cache cleanup before the rightmost rebuild", async () => {
    mockUnifiedScan();
    const wrapper = await openDisk();
    await wrapper.findAll("button").find((b) => b.text() === i18n.global.t("settings.docker.scan"))!.trigger("click");
    await flushPromises();
    const texts = wrapper.findAll("button").map((b) => b.text());
    const scanIdx = texts.indexOf(i18n.global.t("settings.docker.scan"));
    const cleanupIdx = texts.indexOf(i18n.global.t("settings.docker.cleanup"));
    const cacheIdx = texts.indexOf(i18n.global.t("settings.docker.cacheCleanup"));
    const rebuildIdx = texts.indexOf(i18n.global.t("settings.docker.rebuild"));
    expect(cacheIdx).toBeGreaterThan(-1);
    expect(scanIdx).toBeLessThan(cleanupIdx);
    expect(cleanupIdx).toBeLessThan(cacheIdx);
    expect(cacheIdx).toBeLessThan(rebuildIdx);
    wrapper.unmount();
  });

  it("dedicated cache cleanup prunes cache only and refreshes scan data", async () => {
    mockUnifiedScan();
    const order: string[] = [];
    mockIpc.cacheCleanup.mockImplementation(async () => { order.push("cache"); return { prunes: [{ kind: "builder", reclaimed: "1.5GB", error: null }], warnings: [], rows_after: [] }; });
    mockIpc.dockerScan.mockImplementation(async () => { order.push("scan"); return scanReport; });
    mockIpc.cacheInspect.mockClear();
    const wrapper = await openDisk();
    await wrapper.findAll("button").find((b) => b.text() === i18n.global.t("settings.docker.scan"))!.trigger("click");
    await flushPromises();
    order.length = 0;
    mockIpc.cacheCleanup.mockClear();
    mockIpc.dockerCleanup.mockClear();
    mockIpc.dockerScan.mockClear();
    mockIpc.cacheInspect.mockClear();
    await wrapper.findAll("button").find((b) => b.text() === i18n.global.t("settings.docker.cacheCleanup"))!.trigger("click");
    await flushPromises();
    expect(mockIpc.cacheCleanup).toHaveBeenCalledWith(24);
    expect(mockIpc.dockerCleanup).not.toHaveBeenCalled();
    expect(order).toEqual(["cache", "scan"]);
    expect(mockIpc.cacheInspect).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });
});