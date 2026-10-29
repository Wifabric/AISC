import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { reactive } from "vue";
import { i18n } from "../../../i18n";
import ExtensionSourceManager from "../ExtensionSourceManager.vue";

let store: ReturnType<typeof makeStore>;
function makeStore() {
  return reactive({
    canLoad: true, busy: false, sourceMaintenanceBusy: false, skillReposUnsupported: false,
    skillRepos: [
      { kind: "skill-repo", id: "owner/repo", name: "owner/repo", repo: "owner/repo", branch: "main", enabled: true },
      { kind: "skill-repo", id: "old/repo", name: "old/repo", repo: "old/repo", branch: "dev", enabled: false },
    ],
    skillReposBusy: false, skillReposError: null as string | null,
    pluginMarkets: [
      { kind: "marketplace", id: "claude-plugins-official", name: "claude-plugins-official", source: "Built in" },
      { kind: "marketplace", id: "disposable", name: "disposable", source: "https://example.git" },
    ],
    pluginMarketsBusy: false, pluginMarketsError: null as string | null,
    loadSkillRepos: vi.fn(async () => {}), loadPluginMarkets: vi.fn(async () => {}),
    addSkillRepo: vi.fn(async () => {}), removeSkillRepo: vi.fn(async () => {}),
    addPluginMarket: vi.fn(async () => {}), removePluginMarket: vi.fn(async () => {}),
  });
}
vi.mock("../../../stores/extensions", () => ({ useExtensionsStore: () => store }));

beforeEach(() => {
  store = makeStore();
  i18n.global.locale.value = "zh-CN";
});

function mountManager() {
  return mount(ExtensionSourceManager, { global: { plugins: [i18n] } });
}

describe("ExtensionSourceManager", () => {
  it("lists skill repositories and plugin marketplaces with honest metadata", () => {
    const wrapper = mountManager();
    expect(wrapper.get("[data-testid='skill-source-list']").text()).toContain("owner/repo");
    expect(wrapper.get("[data-testid='skill-source-list']").text()).toContain("main");
    expect(wrapper.get("[data-testid='plugin-source-list']").text()).toContain("claude-plugins-official");
    expect(wrapper.get("[data-testid='plugin-source-list']").text()).toContain("Built in");
  });

  it("adds a skill repository and a plugin marketplace through the store", async () => {
    const wrapper = mountManager();
    const skillInput = wrapper.get("[data-testid='skill-repo-add']");
    await skillInput.setValue("https://github.com/example/skills");
    await wrapper.get("[data-testid='skill-repo-add-btn']").trigger("click");
    await flushPromises();
    expect(store.addSkillRepo).toHaveBeenCalledWith("https://github.com/example/skills");
    expect((skillInput.element as HTMLInputElement).value).toBe("");

    const marketInput = wrapper.get("[data-testid='plugin-market-add']");
    await marketInput.setValue("https://example/marketplace.git");
    await wrapper.get("[data-testid='plugin-market-add-btn']").trigger("click");
    await flushPromises();
    expect(store.addPluginMarket).toHaveBeenCalledWith("https://example/marketplace.git");
    expect((marketInput.element as HTMLInputElement).value).toBe("");
  });

  it("confirms skill repository deletion and explains installed-skill retention", async () => {
    const wrapper = mountManager();
    const row = wrapper.findAll("[data-testid^='skill-source-row-']")[0]!;
    await row.get("[data-testid='skill-repo-remove']").trigger("click");
    expect(store.removeSkillRepo).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("不会卸载已安装技能");
    await wrapper.get("[data-testid='confirm-source-remove']").trigger("click");
    expect(store.removeSkillRepo).toHaveBeenCalledWith("owner/repo");
  });

  it("confirms plugin marketplace deletion and explains discovery impact", async () => {
    const wrapper = mountManager();
    const row = wrapper.findAll("[data-testid^='plugin-source-row-']")[1]!;
    await row.get("[data-testid='plugin-market-remove']").trigger("click");
    expect(store.removePluginMarket).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("已安装插件不会被自动卸载");
    await wrapper.get("[data-testid='confirm-source-remove']").trigger("click");
    expect(store.removePluginMarket).toHaveBeenCalledWith("disposable");
  });

  it("uses aggregate source busy state across skill and plugin kinds", async () => {
    const wrapper = mountManager();
    store.sourceMaintenanceBusy = true;
    await nextTick();
    expect(wrapper.get("[data-testid='skill-repo-add-btn']").attributes("disabled")).toBeDefined();
    expect(wrapper.get("[data-testid='plugin-market-add-btn']").attributes("disabled")).toBeDefined();
    const skillRow = wrapper.findAll("[data-testid^='skill-source-row-']")[0]!;
    const pluginRow = wrapper.findAll("[data-testid^='plugin-source-row-']")[0]!;
    expect(skillRow.get("[data-testid='skill-repo-remove']").attributes("disabled")).toBeDefined();
    expect(pluginRow.get("[data-testid='plugin-market-remove']").attributes("disabled")).toBeDefined();
  });

  it("explains only a stable unsupported operation", async () => {
    store.skillReposError = "old runtime lacks skill-repos-list";
    store.skillReposUnsupported = true;
    const wrapper = mountManager();
    expect(wrapper.get("[data-testid='source-maintenance-unavailable']").text()).toContain("当前运行环境不支持来源维护");
    expect(wrapper.get("[data-testid='source-maintenance-unavailable']").text()).toContain("升级或重建镜像");
    expect(wrapper.get("[data-testid='skill-repo-add-btn']").attributes("disabled")).toBeDefined();
    expect(wrapper.get("[data-testid='plugin-market-add-btn']").attributes("disabled")).toBeDefined();
    const skillRow = wrapper.findAll("[data-testid^='skill-source-row-']")[0]!;
    expect(skillRow.get("[data-testid='skill-repo-remove']").attributes("disabled")).toBeDefined();
    expect(wrapper.findAll("[role='alert']")).toHaveLength(1);
    wrapper.unmount();
  });

  it("keeps transient listing errors retryable rather than claiming unsupported", async () => {
    store.skillReposError = "database is locked";
    const wrapper = mountManager();
    expect(wrapper.find("[data-testid='source-maintenance-unavailable']").exists()).toBe(false);
    await wrapper.get("[data-testid='skill-repo-add']").setValue("https://github.com/owner/repo");
    await wrapper.get("[data-testid='plugin-market-add']").setValue("https://example.test/market.json");
    expect((wrapper.get("[data-testid='skill-repo-add-btn']").element as HTMLButtonElement).disabled).toBe(false);
    expect((wrapper.get("[data-testid='plugin-market-add-btn']").element as HTMLButtonElement).disabled).toBe(false);
    wrapper.unmount();
  });

  it("keeps Smithery built in and directs MCP maintenance to installed servers", () => {
    const wrapper = mountManager();
    const note = wrapper.get("[data-testid='mcp-source-note']").text();
    expect(note).toContain("Smithery");
    expect(note).toContain("内置");
    expect(note).toContain("已安装 MCP");
  });

  it("shows source errors and disables add/remove during busy state", async () => {
    store.skillReposError = "repo registry unavailable";
    store.pluginMarketsError = "market registry unavailable";
    store.busy = true;
    const wrapper = mountManager();
    expect(wrapper.text()).toContain("repo registry unavailable");
    expect(wrapper.text()).toContain("market registry unavailable");
    expect(wrapper.get("[data-testid='skill-repo-add-btn']").attributes("disabled")).toBeDefined();
    expect(wrapper.get("[data-testid='plugin-market-add-btn']").attributes("disabled")).toBeDefined();
    const row = wrapper.findAll("[data-testid^='skill-source-row-']")[0]!;
    expect(row.get("[data-testid='skill-repo-remove']").attributes("disabled")).toBeDefined();
  });
});
