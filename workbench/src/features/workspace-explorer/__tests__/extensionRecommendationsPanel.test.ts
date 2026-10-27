import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick, reactive, type Component } from "vue";
import { i18n } from "../../../i18n";

function makeStore() {
  return reactive({
    kind: "skills", canLoad: false, marketBusy: false,
    discoverRecommendation: vi.fn(async (_kind: string, _query: string) => {}),
    setContext: vi.fn(), load: vi.fn(async () => {}), items: [],
    marketCacheByKind: { skills: null, mcp: null, plugins: null },
    marketSkillGroups: [], marketMcp: [], marketPlugins: [], pluginMarkets: [],
    pluginMarketsError: null as string | null, error: null as string | null,
  });
}
let store: ReturnType<typeof makeStore>;
const ipc = vi.hoisted(() => ({ extensionsCall: vi.fn() }));
vi.mock("../../../stores/extensions", () => ({ useExtensionsStore: () => store }));
vi.mock("../../../lib/ipc", () => ipc);
vi.mock("../../../stores/runtime", () => ({ useRuntimeStore: () => ({ workspace: "", runtimeSnapshot: null }) }));
const modules = import.meta.glob<{ default: Component }>("../ExtensionRecommendations.vue", { eager: true });
const views = import.meta.glob<{ default: Component }>("../ExtensionsView.vue", { eager: true });
function mountPanel() {
  const component = modules["../ExtensionRecommendations.vue"];
  expect(component, "B4 must provide the recommendation panel").toBeDefined();
  return mount(component!.default, { global: { plugins: [i18n] } });
}

describe("ExtensionRecommendations", () => {
  beforeEach(() => {
    store = makeStore();
    ipc.extensionsCall.mockReset();
    i18n.global.locale.value = "zh-CN";
  });

  it("shows all three kinds and sources offline with disabled search and an explanation", async () => {
    const wrapper = mountPanel();
    expect(wrapper.findAll("li")).toHaveLength(3);
    for (const label of ["精选推荐", "技能", "MCP", "插件", "启动工作区运行时后即可搜索市场"]) expect(wrapper.text()).toContain(label);
    for (const card of wrapper.findAll("li")) {
      expect(card.get("a").attributes("href")).toMatch(/^https:\/\//);
      expect(card.get("button").text()).toBe("搜索市场");
      expect(card.get("button").attributes("disabled")).toBeDefined();
      await card.get("button").trigger("click");
    }
    expect(store.discoverRecommendation).not.toHaveBeenCalled();
    expect(wrapper.emitted("discover")).toBeUndefined();
    wrapper.unmount();
  });

  it("emits query selection before dispatching discovery once, with no direct install IPC", async () => {
    store.canLoad = true;
    const wrapper = mountPanel();
    store.discoverRecommendation.mockImplementation(async () => {
      expect(wrapper.emitted("discover")?.length).toBe(store.discoverRecommendation.mock.calls.length);
    });
    for (const button of wrapper.findAll("button")) await button.trigger("click");
    await flushPromises();
    const selections = [["skills", "caveman"], ["mcp", "context7"], ["plugins", "superpowers"]];
    expect(wrapper.emitted("discover")).toEqual(selections);
    expect(store.discoverRecommendation.mock.calls).toEqual(selections);
    expect(ipc.extensionsCall).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("disables search while busy and re-enables it reactively", async () => {
    store.canLoad = true;
    store.marketBusy = true;
    const wrapper = mountPanel();
    expect(wrapper.text()).toContain("市场搜索中，请稍候");
    for (const button of wrapper.findAll("button")) {
      expect(button.attributes("disabled")).toBeDefined();
      await button.trigger("click");
    }
    expect(store.discoverRecommendation).not.toHaveBeenCalled();
    store.marketBusy = false;
    await nextTick();
    for (const button of wrapper.findAll("button")) expect(button.attributes("disabled")).toBeUndefined();
    wrapper.unmount();
  });

  it("keeps all three cards visible independently of the active kind", async () => {
    const wrapper = mountPanel();
    store.kind = "plugins";
    await nextTick();
    expect(wrapper.findAll("li")).toHaveLength(3);
    for (const name of ["caveman", "Context7", "superpowers"]) expect(wrapper.text()).toContain(name);
    wrapper.unmount();
  });

  it("syncs each existing market search input when its recommendation selects that tab", async () => {
    store.canLoad = true;
    store.discoverRecommendation.mockImplementation(async (kind) => { store.kind = kind; });
    const wrapper = mount(views["../ExtensionsView.vue"]!.default, {
      global: { plugins: [i18n], stubs: { ExtensionOperationLog: true } },
    });
    for (const [index, kind, query] of [[0, "skills", "caveman"], [1, "mcp", "context7"], [2, "plugins", "superpowers"]] as const) {
      await wrapper.get(".extension-recommendations").findAll("button")[index]!.trigger("click");
      await flushPromises();
      expect(store.kind).toBe(kind);
      const search = wrapper.get(".extensions-market input").element as HTMLInputElement;
      expect(search.value).toBe(query);
    }
    expect(store.discoverRecommendation).toHaveBeenCalledTimes(3);
    wrapper.unmount();
  });

  it("translates reasons, search, source and the offline explanation in English", () => {
    i18n.global.locale.value = "en-US";
    const wrapper = mountPanel();
    expect(wrapper.text()).toContain("Curated recommendations");
    expect(wrapper.text()).toContain("Start a workspace runtime to search the market");
    expect(wrapper.findAll("button").map((button) => button.text())).toEqual(Array(3).fill("Search market"));
    expect(wrapper.findAll("a").map((link) => link.text())).toEqual(Array(3).fill("Source"));
    expect(wrapper.text()).not.toContain("extensions.recommendations.");
    wrapper.unmount();
  });

  it("renders marketplace-list failure separately without duplicating a search error", () => {
    store.kind = "plugins";
    store.pluginMarketsError = "Marketplace listing unavailable";
    store.error = "Market search unavailable";
    const wrapper = mount(views["../ExtensionsView.vue"]!.default, {
      global: { plugins: [i18n], stubs: { ExtensionOperationLog: true } },
    });
    const alerts = wrapper.findAll('[role="alert"]');
    expect(alerts.filter((alert) => alert.text().includes("Marketplace listing unavailable"))).toHaveLength(1);
    expect(alerts.filter((alert) => alert.text().includes("Market search unavailable"))).toHaveLength(1);
    expect(wrapper.get(".extensions-market [role='alert']").text()).toContain("Marketplace listing unavailable");
    wrapper.unmount();
  });
});
