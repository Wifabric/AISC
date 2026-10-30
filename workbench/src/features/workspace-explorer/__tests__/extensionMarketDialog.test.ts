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
    installSkill: vi.fn(async () => {}), installSkillGroup: vi.fn(async (_group: any) => {}), installMcpMarket: vi.fn(async () => {}),
    pluginAction: vi.fn(async () => {}),
    marketSkills: [] as ExtensionsItem[], marketMcp: [] as ExtensionsItem[], marketPlugins: [] as ExtensionsItem[],
    marketSkillGroups: [] as any[],
    marketCacheByKind: { skills: null, mcp: null, plugins: null } as any,
    skillRepos: [], pluginMarkets: [], error: null as string | null,
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

  it("expands recommendation details inline without a fixed right pane", async () => {
    const wrapper = mountDialog();
    const body = wrapper.get(".market-body");
    expect(body.classes()).toContain("recommendations");
    expect(wrapper.find(".market-detail").exists()).toBe(false);

    const cases = [
      { category: "research" as const, kind: "skills" as const, label: "技能" },
      { category: "education" as const, kind: "mcp" as const, label: "MCP" },
      { category: "development" as const, kind: "plugins" as const, label: "插件" },
    ];
    const chips = wrapper.findAll("[data-testid='recommendation-category']");
    for (const testCase of cases) {
      const categoryIndex = EXTENSION_RECOMMENDATION_CATEGORIES.findIndex(
        (category) => category.id === testCase.category,
      );
      await chips[categoryIndex]!.trigger("click");
      const catalog = EXTENSION_RECOMMENDATIONS_BY_CATEGORY[testCase.category];
      const entryIndex = catalog.findIndex((entry) => entry.kind === testCase.kind);
      const card = wrapper.findAll("[data-testid='recommendation-card']")[entryIndex]!;
      const entry = catalog[entryIndex]!;
      expect(card.text()).toContain(entry.name);
      expect(card.text()).toContain(entry.identity);
      expect(card.text()).toContain(entry.sourceUrl);

      const header = card.get("[data-testid='recommendation-card-header']");
      expect(header.attributes("aria-expanded")).toBe("false");
      await header.trigger("click");
      const expandedCard = wrapper.findAll("[data-testid='recommendation-card']")[entryIndex]!;
      const expandedHeader = expandedCard.get("[data-testid='recommendation-card-header']");
      expect(expandedHeader.attributes("aria-expanded")).toBe("true");
      const detail = expandedCard.get("[data-testid='extension-detail-panel']");
      expect(detail.text()).toContain(entry.summaryZh);
      expect(wrapper.findAll("[data-testid='extension-detail-panel']")).toHaveLength(1);
      expect(wrapper.find(".market-detail").exists()).toBe(false);
      expect(wrapper.text()).toContain(testCase.label);
    }
    wrapper.unmount();
  });

  it("collapses one recommendation when another opens and keeps search explicit", async () => {
    const wrapper = mountDialog();
    const headers = wrapper.findAll("[data-testid='recommendation-card-header']");
    await headers[0]!.trigger("click");
    await headers[1]!.trigger("click");
    let cards = wrapper.findAll("[data-testid='recommendation-card']");
    expect(cards[0]!.find("[data-testid='extension-detail-panel']").exists()).toBe(false);
    expect(cards[1]!.find("[data-testid='extension-detail-panel']").exists()).toBe(true);
    expect(store.searchSkills).not.toHaveBeenCalled();

    await cards[1]!.get("[data-testid='recommendation-card-header']").trigger("click");
    cards = wrapper.findAll("[data-testid='recommendation-card']");
    expect(cards[1]!.find("[data-testid='extension-detail-panel']").exists()).toBe(false);
    await cards[1]!.get("[data-testid='recommendation-card-header']").trigger("click");
    expect(wrapper.get("[data-testid='market-search-action']").exists()).toBe(true);

    await wrapper.get("[data-testid='market-search-action']").trigger("click");
    await flushPromises();
    expect(store.searchSkills).toHaveBeenCalledWith(
      EXTENSION_RECOMMENDATIONS_BY_CATEGORY.research[1]!.query,
    );
    wrapper.unmount();
  });

  it("clears recommendation state after selecting a real market result", async () => {
    const result: ExtensionsItem = {
      kind: "market-skill", id: "owner/repo:research", name: "research",
      repo: "owner/repo", directory: "research", description: "Live market copy",
    };
    store.searchSkills.mockImplementation(async () => {
      store.marketSkills = [result];
      store.marketSkillGroups = [{
        id: "owner/repo", name: "owner/repo", repo: "owner/repo",
        conflict: false, expanded: true, items: [result],
      }];
    });
    const wrapper = mountDialog();
    await wrapper.get("[data-testid='recommendation-card-header']").trigger("click");
    await wrapper.get("[data-testid='market-search-action']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-testid='market-result-owner/repo:research']").trigger("click");
    const detail = wrapper.get("[data-testid='extension-detail-panel']");
    expect(detail.text()).toContain("市场原文");
    expect(detail.text()).toContain("Live market copy");
    expect(detail.text()).not.toContain("推荐依据");
    await wrapper.get("[data-testid='market-install-action']").trigger("click");
    expect(store.installSkill).toHaveBeenCalledWith("owner/repo:research");
    wrapper.unmount();
  });

  it("opens a market result detail and runs the kind-safe install action", async () => {
    store.marketSkills = [{
      kind: "market-skill", id: "owner/repo:demo", name: "demo",
      repo: "owner/repo", directory: "demo", description: "Original copy",
    }];
    store.marketSkillGroups = [{
      id: "owner/repo", name: "owner/repo", repo: "owner/repo",
      conflict: false, expanded: true, items: store.marketSkills,
    }];
    const wrapper = mountDialog();
    await wrapper.get("[data-testid='market-tab-skills']").trigger("click");
    await wrapper.get("[data-testid^='market-result-']").trigger("click");
    expect(wrapper.get("[data-testid='extension-detail-summary']").text()).toMatch(/^这是一个/);
    await wrapper.get("[data-testid='market-install-action']").trigger("click");
    expect(store.installSkill).toHaveBeenCalledWith("owner/repo:demo");
    wrapper.unmount();
  });

  it("keeps repository-group installation available for multi-skill market results", async () => {
    store.marketSkills = [
      { kind: "market-skill", id: "owner/repo:a", name: "a", repo: "owner/repo", directory: "a" },
      { kind: "market-skill", id: "owner/repo:b", name: "b", repo: "owner/repo", directory: "b" },
    ];
    store.marketSkillGroups = [{
      id: "owner/repo", name: "owner/repo", repo: "owner/repo",
      conflict: false, expanded: true, items: store.marketSkills,
    }];
    const wrapper = mountDialog();
    await wrapper.get("[data-testid='market-tab-skills']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-testid^='market-group-']").trigger("click");
    await wrapper.get("[data-testid='market-group-install']").trigger("click");
    expect(store.installSkillGroup).toHaveBeenCalledTimes(1);
    const group = store.installSkillGroup.mock.calls[0]![0] as { items: ExtensionsItem[] };
    expect(group.items.map((item: ExtensionsItem) => item.id)).toEqual([
      "owner/repo:a", "owner/repo:b",
    ]);
    wrapper.unmount();
  });

  it("renders source management in its own tab", async () => {
    const wrapper = mountDialog();
    expect(wrapper.find("[data-testid='stub-source-manager']").exists()).toBe(false);
    await wrapper.get("[data-testid='market-tab-sources']").trigger("click");
    expect(wrapper.find("[data-testid='stub-source-manager']").exists()).toBe(true);
    expect(wrapper.find("[data-testid='extension-detail-panel']").exists()).toBe(false);
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

  it("labels each heat source once without duplicating official-directory copy", async () => {
    const wrapper = mountDialog();
    const observed = wrapper.get("[data-testid='recommendation-card']");
    expect(observed.text()).toContain("skills.sh 热榜");
    expect(observed.text().match(/skills\.sh 热榜/g)).toHaveLength(1);
    await wrapper.get("[data-testid='recommendation-category']:nth-child(2)").trigger("click");
    const officialCounts = wrapper.findAll("[data-testid='recommendation-card']")
      .map((card) => card.text().match(/官方目录/g)?.length ?? 0);
    expect(officialCounts.some((count) => count > 0)).toBe(true);
    expect(Math.max(...officialCounts)).toBe(1);
    wrapper.unmount();
  });

  it("renders search failures separately from a genuinely empty result", async () => {
    store.kind = "mcp";
    store.error = "Smithery transport unavailable";
    const wrapper = mountDialog();
    await wrapper.get("[data-testid='market-tab-mcp']").trigger("click");
    const failure = wrapper.get("[data-testid='market-search-error']");
    expect(failure.attributes("role")).toBe("alert");
    expect(failure.text()).toContain("Smithery transport unavailable");
    expect(wrapper.find("[data-testid='market-cache']").exists()).toBe(false);
    expect(wrapper.find(".market-empty").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("暂无搜索结果");
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

  it("moves between market tabs with arrow keys", async () => {
    const wrapper = mountDialog();
    const recommendations = wrapper.get("[data-testid='market-tab-recommendations']");
    (recommendations.element as HTMLElement).focus();
    await recommendations.trigger("keydown", { key: "ArrowRight" });
    expect(wrapper.get("[data-testid='market-tab-skills']").attributes("aria-selected")).toBe("true");
    const skills = wrapper.get("[data-testid='market-tab-skills']");
    await skills.trigger("keydown", { key: "ArrowLeft" });
    expect(wrapper.get("[data-testid='market-tab-recommendations']").attributes("aria-selected")).toBe("true");
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
