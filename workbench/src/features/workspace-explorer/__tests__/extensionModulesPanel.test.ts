import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import ExtensionModulesPanel from "../ExtensionModulesPanel.vue";
import { i18n } from "../../../i18n";
const ipc = vi.hoisted(() => ({ loadExtensionModules: vi.fn(), saveExtensionModules: vi.fn(), extensionsCall: vi.fn() }));
const extensions = vi.hoisted(() => ({ canLoad: false, marketSkills: [], marketMcp: [], marketPlugins: [], errorsByKind: {},
  searchSkills: vi.fn(), searchMcp: vi.fn(), searchPlugins: vi.fn() }));
vi.mock("../../../lib/ipc", () => ipc);
vi.mock("../../../stores/extensions", () => ({ useExtensionsStore: () => extensions }));
beforeEach(() => {
  vi.clearAllMocks(); i18n.global.locale.value = "zh-CN";
  ipc.loadExtensionModules.mockResolvedValue({ schema_version: 1, revision: 0, definitions: [], hidden_builtin_ids: [] });
  ipc.saveExtensionModules.mockImplementation(async (_revision, document) => JSON.parse(JSON.stringify({ ...document, revision: 1 })));
});
const render = () => mount(ExtensionModulesPanel, { global: { plugins: [createPinia(), i18n] } });
describe("module editor", () => {
  it("saves the installable source directories when research recommendations are selected", async () => {
    const wrapper = render(); await flushPromises();
    await wrapper.get('[data-testid="module-new"]').trigger("click");
    await wrapper.get('[data-testid="module-name"]').setValue("Research source paths");
    for (const name of ["literature-search-arxiv", "literature-search-openalex", "pubmed-database", "literature-search-europepmc"]) {
      const choice = wrapper.findAll(".module-candidates button").find(button => button.text().startsWith(name));
      expect(choice).toBeDefined();
      await choice!.trigger("click");
    }
    await wrapper.get("form").trigger("submit"); await flushPromises();
    expect(ipc.saveExtensionModules.mock.calls[0]?.[1].definitions[0].members).toEqual([
      { kind: "skills", identity: "google-deepmind/science-skills:literature_search_arxiv", name: "literature-search-arxiv", source_url: "https://github.com/google-deepmind/science-skills" },
      { kind: "skills", identity: "google-deepmind/science-skills:literature_search_openalex", name: "literature-search-openalex", source_url: "https://github.com/google-deepmind/science-skills" },
      { kind: "skills", identity: "google-deepmind/science-skills:pubmed_database", name: "pubmed-database", source_url: "https://github.com/google-deepmind/science-skills" },
      { kind: "skills", identity: "google-deepmind/science-skills:literature_search_europepmc", name: "literature-search-europepmc", source_url: "https://github.com/google-deepmind/science-skills" },
    ]);
    expect(ipc.extensionsCall).not.toHaveBeenCalled(); wrapper.unmount();
  });
  it("creates an offline mixed module, prevents duplicates, removes a member, and saves without installation", async () => {
    const wrapper = render(); await flushPromises();
    await wrapper.get('[data-testid="module-new"]').trigger("click");
    await wrapper.get('[data-testid="module-name"]').setValue("QA mixed");
    for (const kind of ["skills", "mcp", "plugins"]) {
      await wrapper.get("select").setValue(kind);
      const choice = wrapper.get(".module-candidates button");
      await choice.trigger("click");
      expect(choice.attributes("disabled")).toBeDefined();
    }
    expect(wrapper.findAll(".module-members li")).toHaveLength(3);
    await wrapper.get(".module-members button").trigger("click");
    expect(wrapper.findAll(".module-members li")).toHaveLength(2);
    await wrapper.get("form").trigger("submit"); await flushPromises();
    expect(ipc.saveExtensionModules.mock.calls[0]?.[1].definitions[0].members.map((m: any) => m.kind)).toEqual(["mcp", "plugins"]);
    expect(wrapper.find('[data-testid="module-editor"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("QA mixed");
    expect(ipc.extensionsCall).not.toHaveBeenCalled(); wrapper.unmount();
  });
  it("keeps the editable draft when persistence fails", async () => {
    const wrapper = render(); await flushPromises();
    await wrapper.get('[data-testid="module-new"]').trigger("click");
    await wrapper.get('[data-testid="module-name"]').setValue("Keep my draft");
    ipc.saveExtensionModules.mockRejectedValueOnce({ technical_detail: "revision conflict" });
    await wrapper.get("form").trigger("submit"); await flushPromises();
    expect((wrapper.get('[data-testid="module-name"]').element as HTMLInputElement).value).toBe("Keep my draft");
    expect(wrapper.get('[role="alert"]').text()).toBe("revision conflict"); wrapper.unmount();
  });
});
