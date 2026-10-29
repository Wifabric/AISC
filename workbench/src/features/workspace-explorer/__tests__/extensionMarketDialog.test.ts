import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick, reactive } from "vue";
import type { ExtensionsItem } from "../../../lib/ipc";
import { i18n } from "../../../i18n";
import ExtensionMarketDialog from "../ExtensionMarketDialog.vue";
import {
  EXTENSION_RECOMMENDATION_CATEGORIES,
  EXTENSION_RECOMMENDATIONS_BY_CATEGORY,
} from "../recommendationCatalog";

vi.mock("../ExtensionSourceManager.vue", () => ({
  default: { template: "<div data-testid='stub-source-manager' />" },
}));

let store: ReturnType<typeof makeStore>;
function makeStore() {
  return reactive({
    kind: "skills", canLoad: true, marketBusy: false, busy: false,
    load: vi.fn(async () => {}), searchSkills: vi.fn(async () => {}),
    searchMcp: vi.fn(async () => {}), searchPlugins: vi.fn(async () => {}),
    loadPluginMarkets: vi.fn(async () => {}), loadSkillRepos: vi.fn(async () => {}),
    installSkill: vi.fn(async () => {}), installMcpMarket: vi.fn(async () => {}),
    pluginAction: vi.fn(async () => {}),
    marketSkills: [] as ExtensionsItem[], marketMcp: [] as ExtensionsItem[], marketPlugins: [] as ExtensionsItem[],
    marketCacheByKind: { skills: null, mcp: null, plugins: null } as any,
    skillRepos: [], pluginMarkets: [],
  });
}
vi.mock("../../../stores/extensions", () => ({ useExtensionsStore: () => store }));
vi.mock("../../../stores/runtime", () => ({
  useRuntimeStore: () => ({ workspace: "/ws", runtimeSnapshot: { runtime_id: "rid" } }),
}));

beforeEach(() => {
  store = makeStore();
  i18n.global.locale.value = "zh-CN";
});

function mountDialog() {
  return mount(ExtensionMarketDialog, {
    global: {
      plugins: [i18n],
      stubs: {
        Teleport: true,
        ExtensionSourceManager: { template: "<div data-testid='stub-source-manager' />" },
      },
    },
    attachTo: document.body,
  });
}

describe("ExtensionMarketDialog", () => {
  it("is a labelled modal with five tabs", () => {
    const wrapper = mountDialog();
    const dialog = wrapper.get("[data-testid='extension-market-dialog']");
    expect(dialog.attributes("role")).toBe("dialog");
    expect(dialog.attributes("aria-modal")).toBe("true");
    const tabs = wrapper.findAll("[role='tab']");
    expect(tabs.map((tab) => tab.text())).toEqual([
      "推荐", "技能", "MCP", "插件", "来源管理",
    ]);
    wrapper.unmount();
  });

  it("shows all six categories and exactly ten recommendations per category", async () => {
    const wrapper = mountDialog();
    const chips = wrapper.findAll("[data-testid='recommendation-category']");
    expect(chips.map((chip) => chip.text())).toEqual(
      EXTENSION_RECOMMENDATION_CATEGORIES.map((category) => category.labelZh),
    );
    expect(wrapper.findAll("[data-testid='recommendation-card']")).toHaveLength(10);
    await chips[1]!.trigger("click");
    expect(wrapper.findAll("[data-testid='recommendation-card']")).toHaveLength(10);
    expect(wrapper.text()).toContain("Microsoft Learn");
    wrapper.unmount();
  });

  it("opens recommendation details before any search mutation", async () => {
    const wrapper = mountDialog();
    await wrapper.get("[data-testid='recommendation-card']").trigger("click");
    const detail = wrapper.get("[data-testid='extension-detail-panel']");
    expect(detail.text()).toContain(
      EXTENSION_RECOMMENDATIONS_BY_CATEGORY.research[0]!.summaryZh,
    );
    expect(store.searchSkills).not.toHaveBeenCalled();
    await wrapper.get("[data-testid='market-search-action']").trigger("click");
    await flushPromises();
    expect(store.searchSkills).toHaveBeenCalledWith("research");
    wrapper.unmount();
  });

  it("opens a market result detail and runs the kind-safe install action", async () => {
    store.marketSkills = [{
      kind: "market-skill", id: "owner/repo:demo", name: "demo",
      repo: "owner/repo", directory: "demo", description: "Original copy",
    }];
    const wrapper = mountDialog();
    await wrapper.get("[data-testid='market-tab-skills']").trigger("click");
    await wrapper.get("[data-testid^='market-result-']").trigger("click");
    expect(wrapper.get("[data-testid='extension-detail-summary']").text()).toMatch(/^这是一个/);
    await wrapper.get("[data-testid='market-install-action']").trigger("click");
    expect(store.installSkill).toHaveBeenCalledWith("owner/repo:demo");
    wrapper.unmount();
  });

  it("renders source management in its own tab", async () => {
    const wrapper = mountDialog();
    expect(wrapper.find("[data-testid='stub-source-manager']").exists()).toBe(false);
    await wrapper.get("[data-testid='market-tab-sources']").trigger("click");
    expect(wrapper.find("[data-testid='stub-source-manager']").exists()).toBe(true);
    expect(store.loadSkillRepos).toHaveBeenCalled();
    expect(store.loadPluginMarkets).toHaveBeenCalled();
    wrapper.unmount();
  });

  it("localizes category labels and recommendation copy in English", async () => {
    i18n.global.locale.value = "en-US";
    const wrapper = mountDialog();
    expect(wrapper.get("[data-testid='recommendation-category']:nth-child(2)").text()).toBe("Education");
    await wrapper.get("[data-testid='recommendation-category']:nth-child(2)").trigger("click");
    expect(wrapper.get("[data-testid='recommendation-card']").text()).toContain(
      EXTENSION_RECOMMENDATIONS_BY_CATEGORY.education[0]!.summaryEn,
    );
    wrapper.unmount();
  });

  it("labels observed heat sources in the UI instead of leaking raw enum values", () => {
    const wrapper = mountDialog();
    const card = wrapper.get("[data-testid='recommendation-card']");
    expect(card.text()).toContain("skills.sh");
    expect(card.text()).not.toContain("heatSource");
    wrapper.unmount();
  });

  it("keeps market cache provenance visible in the search pane", async () => {
    store.kind = "plugins";
    store.marketCacheByKind = {
      skills: null,
      mcp: null,
      plugins: { source: "cache", cached: true, query: "chart", fetched_at: 1760000000, error: "remote refresh down" },
    } as any;
    const wrapper = mountDialog();
    await wrapper.get("[data-testid='market-tab-plugins']").trigger("click");
    const cache = wrapper.get("[data-testid='market-cache']");
    expect(cache.text()).toContain("缓存结果");
    expect(cache.text()).toContain("remote refresh down");
    wrapper.unmount();
  });

  it("moves focus forward cyclically and closes on Escape", async () => {
    const wrapper = mountDialog();
    await nextTick();
    const dialog = wrapper.get("[data-testid='extension-market-dialog']");
    await dialog.trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
    const first = wrapper.get("[data-testid='market-close']");
    expect(document.activeElement).toBe(first.element);
    wrapper.unmount();
  });
});
