/**
 * b6: proxy-node pane —「当前节点 → 代理组 → 组内节点」hierarchy.
 * The current node is shown first (group / node / latency), the proxy group
 * is pickable, and the nodes under it are pickable with per-node latency.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { useRuntimeStore } from "../../../stores/runtime";
import type { ProxyGroups } from "../../../lib/ipc";
import ProxyNodes from "../ProxyNodes.vue";

const GROUPS: ProxyGroups = {
  Selector: { current: "HK-01", nodes: ["HK-01", "JP-02"], selectable: true },
  Auto: { current: "US-03", nodes: ["US-03", "SG-04"], selectable: false },
};

const mockIpc = vi.hoisted(() => ({
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  proxyNodes: vi.fn(),
  networkSubscriptionShow: vi.fn(),
  networkSubscriptionImport: vi.fn(),
  networkSubscriptionImportFile: vi.fn(),
  networkSubscriptionRefresh: vi.fn(),
  networkSubscriptionClear: vi.fn(),
  usageOverview: vi.fn(),
}));

vi.mock("../../../lib/ipc", () => mockIpc);
vi.mock("@tauri-apps/plugin-dialog", () => ({
  confirm: vi.fn().mockResolvedValue(true),
  open: vi.fn(),
  save: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ Channel: class {} }));
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: vi.fn(() => ({
    isFocused: vi.fn().mockResolvedValue(true),
    isMinimized: vi.fn().mockResolvedValue(false),
  })),
}));

async function mountLoaded() {
  setActivePinia(createPinia());
  const runtime = useRuntimeStore();
  runtime.workspace = "/ws";
  runtime.runtimeId = "rid";
  const tab = mount(ProxyNodes, { global: { plugins: [i18n] } });
  const load = tab.findAll("button").find((b) => b.text().includes("刷新代理节点"));
  await load!.trigger("click");
  await flushPromises();
  return tab;
}

describe("ProxyNodes (b6 hierarchy)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIpc.proxyNodes.mockImplementation(async (_ws, _rid, action) => {
      if (action === "list") return { groups: structuredClone(GROUPS) };
      if (action === "select") return { selected: "x" };
      return { delay: 123 };
    });
  });

  it("orders 当前节点 → 代理组 → 组内节点 and shows the active group's current node", async () => {
    const tab = await mountLoaded();

    // Hierarchy order in the rendered markup.
    const html = tab.html();
    expect(html.indexOf("当前节点")).toBeGreaterThanOrEqual(0);
    expect(html.indexOf("当前节点")).toBeLessThan(html.indexOf("选择代理组"));
    expect(html.indexOf("选择代理组")).toBeLessThan(html.indexOf("组内节点"));

    // Current node = first group's `now`, with its group and untested latency.
    const current = tab.find(".current-node");
    expect(current.text()).toContain("Selector");
    expect(current.text()).toContain("HK-01");
    expect(current.text()).toContain("未测");

    // Group picker lists every group; only the active group's nodes render.
    const options = tab.find(".group-pick select").findAll("option");
    expect(options.map((o) => o.text())).toEqual(["Selector", "Auto"]);
    expect(tab.find(".node-list").text()).toContain("HK-01");
    expect(tab.find(".node-list").text()).toContain("JP-02");
    expect(tab.find(".node-list").text()).not.toContain("US-03");
    tab.unmount();
  });

  it("switching the proxy group swaps the current node and the node list", async () => {
    const tab = await mountLoaded();
    await tab.find(".group-pick select").setValue("Auto");
    await flushPromises();

    expect(tab.find(".current-node").text()).toContain("Auto");
    expect(tab.find(".current-node").text()).toContain("US-03");
    expect(tab.find(".node-list").text()).toContain("SG-04");
    expect(tab.find(".node-list").text()).not.toContain("HK-01");
    // Automatic group cannot be manually selected.
    const selectBtn = tab.findAll("button").find((b) => b.text() === "使用节点");
    expect(selectBtn!.attributes("disabled")).toBeDefined();
    tab.unmount();
  });

  it("selecting a node applies it to the group and its latency shows on the current node", async () => {
    const tab = await mountLoaded();

    const jpRow = tab.findAll(".node-list li").find((li) => li.text().includes("JP-02"));
    await jpRow!.find("input[type=radio]").setValue(true);
    const useBtn = tab.findAll("button").find((b) => b.text() === "使用节点");
    await useBtn!.trigger("click");
    await flushPromises();

    expect(mockIpc.proxyNodes).toHaveBeenLastCalledWith("/ws", "rid", "select", "Selector", "JP-02");
    expect(tab.find(".current-node").text()).toContain("JP-02");

    // Per-node latency test lands on that node's row and the current node.
    await jpRow!.find("button").trigger("click");
    await flushPromises();
    expect(mockIpc.proxyNodes).toHaveBeenLastCalledWith("/ws", "rid", "delay", "Selector", "JP-02");
    expect(tab.find(".current-node").text()).toContain("123 ms");
    expect(jpRow!.text()).toContain("123 ms");
    tab.unmount();
  });
});
