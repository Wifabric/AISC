/** b6 复测发现：扩展视图切换页签后内容整体消失——本地复现。 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { useExtensionsStore } from "../../../stores/extensions";
import { i18n } from "../../../i18n";
import ExtensionsView from "../ExtensionsView.vue";
import * as ipc from "../../../lib/ipc";

vi.mock("../../../lib/ipc", () => ({ extensionsCall: vi.fn() }));
vi.mock("../../../stores/runtime", () => ({
  useRuntimeStore: () => ({
    workspace: "/ws",
    runtimeSnapshot: { runtime_id: "rid-1" },
  }),
}));

const items = (kind: string) => [
  kind === "mcp"
    ? { kind, id: "cuse-test", name: "cuse-test", transport: "stdio", command: "echo", enabled_claude: true, enabled_codex: true }
    : kind === "skills"
      ? { kind, id: "caveman", name: "caveman", repo: "x/y", directory: "caveman", description: "Ultra-compressed agent communication", source: "standalone", enabled_claude: true, enabled_codex: true }
      : { kind, id: "p@m", name: "p", marketplace: "m", version: "1", enabled_claude: true },
];

describe("ExtensionsView tab switching (b6 retest repro)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    i18n.global.locale.value = "zh-CN";
    vi.mocked(ipc.extensionsCall).mockReset();
    vi.mocked(ipc.extensionsCall).mockImplementation(async (p: any) => ({ items: items(p.kind) }));
  });

  it("keeps rendering after switching skills -> mcp -> plugins", async () => {
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    expect(wrapper.text()).toContain("x/y");
    expect(wrapper.text()).toContain("1 个技能");
    await wrapper.find("[data-testid^=ext-skill-header-]").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("caveman");
    await wrapper.find("[data-testid=ext-tab-mcp]").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("cuse-test");
    await wrapper.find("[data-testid=ext-tab-plugins]").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("m · 1");
    expect(wrapper.find("[data-testid=ext-tab-mcp]").exists()).toBe(true);
    wrapper.unmount();
  });

  it("keeps a group open while opening and closing a child detail panel", async () => {
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    const group = wrapper.find("[data-testid^=ext-skill-group-]");
    await group.get("[data-testid^=ext-skill-header-]").trigger("click");
    await flushPromises();

    const child = wrapper.find("[data-testid=ext-skill-child-caveman]");
    expect(child.exists()).toBe(true);
    expect(wrapper.find("[data-testid='extension-detail-panel']").exists()).toBe(false);

    await child.get("[data-testid=ext-skill-child-header-caveman]").trigger("click");
    await flushPromises();
    expect(wrapper.get("[data-testid='extension-detail-panel']").text()).toContain("极简");
    expect(wrapper.get("[data-testid='extension-detail-panel']").text()).toContain("caveman");

    await child.get("[data-testid=ext-skill-child-header-caveman]").trigger("click");
    await flushPromises();
    expect(wrapper.find("[data-testid='extension-detail-panel']").exists()).toBe(false);
    expect(wrapper.text()).toContain("caveman");
    wrapper.unmount();
  });
});

describe("ExtensionsView operation button spinners (preview b3)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    i18n.global.locale.value = "zh-CN";
    vi.mocked(ipc.extensionsCall).mockReset();
    vi.mocked(ipc.extensionsCall).mockImplementation(async (p: any) => ({ items: items(p.kind) }));
  });

  it("shows a group update spinner only on the update button", async () => {
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    const store = useExtensionsStore();
    store.operationsByKind.skills = {
      kind: "skills", action: "update", id: "installed:x/y", label: "x/y",
      completed: 0, total: 1,
    };
    await nextTick();

    expect(wrapper.find('button[title="更新全部"] .spinner').exists()).toBe(true);
    expect(wrapper.find('button[title="卸载全部"] .spinner').exists()).toBe(false);
    wrapper.unmount();
  });

  it("shows a group remove spinner only on the remove button", async () => {
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    const store = useExtensionsStore();
    store.operationsByKind.skills = {
      kind: "skills", action: "remove", id: "installed:x/y", label: "x/y",
      completed: 0, total: 1,
    };
    await nextTick();

    expect(wrapper.find('button[title="更新全部"] .spinner').exists()).toBe(false);
    expect(wrapper.find('button[title="卸载全部"] .spinner').exists()).toBe(true);
    wrapper.unmount();
  });

  it("shows a child update spinner only on that child update button", async () => {
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    await wrapper.find("[data-testid^=ext-skill-header-]").trigger("click");
    await flushPromises();
    const store = useExtensionsStore();
    store.operationsByKind.skills = {
      kind: "skills", action: "update", id: "caveman", label: "caveman",
      completed: 0, total: 1,
    };
    await nextTick();

    expect(wrapper.find('button[title="更新技能"] .spinner').exists()).toBe(true);
    expect(wrapper.find('button[title="卸载/删除"] .spinner').exists()).toBe(false);
    wrapper.unmount();
  });
});

describe("v2.1.17 b2 update signals", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    i18n.global.locale.value = "zh-CN";
    vi.mocked(ipc.extensionsCall).mockReset();
    vi.mocked(ipc.extensionsCall).mockImplementation(async (p: any) => ({ items: items(p.kind) }));
  });

  it("marks reliable plugin updates and explains unsupported sources", async () => {
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    await wrapper.find("[data-testid=ext-tab-plugins]").trigger("click");
    await flushPromises();
    const store = useExtensionsStore();
    store.updateItemsByKind.plugins = {
      "p@m": {
        kind: "plugins", id: "p@m", status: "ok", update_available: true,
        current_version: "1", latest_version: "2",
      },
    };
    await nextTick();

    const row = wrapper.find('[data-testid="ext-item-p@m"]');
    expect(row.text()).toContain("可更新");
    expect(row.find(".ext-name.has-update").exists()).toBe(true);
    await row.get("[data-testid='ext-item-header-p@m']").trigger("click");
    await nextTick();
    const detail = wrapper.get("[data-testid='extension-detail-panel']");
    expect(detail.text()).toContain("当前版本");
    expect(detail.text()).toContain("1");
    expect(detail.text()).toContain("最新版本");
    expect(detail.text()).toContain("2");

    store.updateItemsByKind.plugins = {
      "p@m": {
        kind: "plugins", id: "p@m", status: "unsupported",
        update_available: false, reason: "market does not expose a comparable version field",
      },
    };
    await nextTick();
    expect(wrapper.get("[data-testid='extension-detail-panel']").text()).toContain("暂无可靠版本源");
    wrapper.unmount();
  });

  it("offers an explicit update check action", async () => {
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    const store = useExtensionsStore();
    const check = vi.spyOn(store, "checkUpdates").mockResolvedValue();
    await wrapper.find("[data-testid=ext-check-updates]").trigger("click");
    expect(check).toHaveBeenCalledOnce();
    wrapper.unmount();
  });

  it("uses native row headers and preserves real keyboard actions", async () => {
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    const store = useExtensionsStore();
    const groupSpy = vi.spyOn(store, "updateSkillGroup").mockResolvedValue();
    const group = wrapper.find("[data-testid^=ext-skill-group-]");
    const header = group.get("[data-testid^=ext-skill-header-]");
    expect(header.element.tagName).toBe("BUTTON");
    expect(header.attributes("aria-expanded")).toBe("false");
    expect(header.attributes("aria-controls")).toBe("ext-skill-children-x/y");
    await header.trigger("click");
    await flushPromises();
    expect(header.attributes("aria-expanded")).toBe("true");

    const child = wrapper.get("[data-testid=ext-skill-child-caveman]");
    expect(child.attributes("role")).toBeUndefined();
    expect(child.attributes("tabindex")).toBeUndefined();
    const childHeader = child.get("[data-testid=ext-skill-child-header-caveman]");
    expect(childHeader.element.tagName).toBe("BUTTON");
    await childHeader.trigger("keydown", { key: "Enter" });
    await flushPromises();
    expect(wrapper.find("[data-testid='extension-detail-panel']").exists()).toBe(true);

    const update = group.get("button[title='更新全部']");
    await update.trigger("keydown", { key: "Space" });
    await flushPromises();
    expect(groupSpy).toHaveBeenCalledOnce();
    expect(header.attributes("aria-expanded")).toBe("true");
    wrapper.unmount();
  });

  it("keeps one-line row actions siblings of a native identity button", async () => {
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    await wrapper.find("[data-testid=ext-tab-plugins]").trigger("click");
    await flushPromises();
    const store = useExtensionsStore();
    const update = vi.spyOn(store, "pluginAction").mockResolvedValue();
    const row = wrapper.get("[data-testid='ext-item-p@m']");
    expect(row.attributes("role")).toBeUndefined();
    const identity = row.get("[data-testid='ext-item-header-p@m']");
    expect(identity.element.tagName).toBe("BUTTON");
    const action = row.get("button[title='更新插件']");
    await action.trigger("keydown", { key: "Enter" });
    await flushPromises();
    expect(update).toHaveBeenCalledWith("plugin-update", "p@m");
    expect(update).toHaveBeenCalledOnce();
    wrapper.unmount();
  });

  it("returns focus to the toolbar button that opened the market", async () => {
    const wrapper = mount(ExtensionsView, {
      attachTo: document.body,
      global: {
        plugins: [i18n],
        stubs: {
          ExtensionMarketDialog: {
            emits: ["close"],
            template: `<button type="button" data-testid="stub-market-close" @click="$emit('close')">close</button>`,
          },
        },
      },
    });
    await flushPromises();
    const opener = wrapper.get("[data-testid='open-extension-market']");
    (opener.element as HTMLElement).focus();
    await opener.trigger("click");
    await wrapper.get("[data-testid='stub-market-close']").trigger("click");
    await flushPromises();
    expect(document.activeElement).toBe(opener.element);
    wrapper.unmount();
  });

  it("renders an empty installed list without a second market button", async () => {
    vi.mocked(ipc.extensionsCall).mockResolvedValue({ items: [] });
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    expect(wrapper.text()).toContain("暂无内容");
    expect(wrapper.find("[data-testid='open-extension-market-empty']").exists()).toBe(false);
    expect(wrapper.findAll("[data-testid='open-extension-market']")).toHaveLength(1);
    wrapper.unmount();
  });

  it("returns focus to the toolbar opener from an empty installed list", async () => {
    vi.mocked(ipc.extensionsCall).mockResolvedValue({ items: [] });
    const wrapper = mount(ExtensionsView, {
      attachTo: document.body,
      global: {
        plugins: [i18n],
        stubs: {
          ExtensionMarketDialog: {
            emits: ["close"],
            template: `<button type="button" data-testid="stub-market-close" @click="$emit('close')">close</button>`,
          },
        },
      },
    });
    await flushPromises();
    const opener = wrapper.get("[data-testid='open-extension-market']");
    await opener.trigger("click");
    await wrapper.get("[data-testid='stub-market-close']").trigger("click");
    await flushPromises();
    expect(document.activeElement).toBe(opener.element);
    wrapper.unmount();
  });

  it("keeps recommendations, discovery, and operation history out of the main view", async () => {
    const wrapper = mount(ExtensionsView, {
      global: {
        plugins: [i18n],
        stubs: {
          ExtensionMarketDialog: { template: "<div data-testid='stub-market-dialog' />" },
        },
      },
    });
    await flushPromises();
    expect(wrapper.find(".extension-recommendations").exists()).toBe(false);
    expect(wrapper.find(".extension-operation-log").exists()).toBe(false);
    expect(wrapper.find("[data-testid='ext-skill-search']").exists()).toBe(false);
    expect(wrapper.find("[data-testid='ext-mcp-search']").exists()).toBe(false);
    expect(wrapper.find("[data-testid='ext-plugin-search']").exists()).toBe(false);
    expect(wrapper.find("[data-testid='ext-market-add']").exists()).toBe(false);
    expect(wrapper.find("[data-testid='stub-market-dialog']").exists()).toBe(false);
    await wrapper.get("[data-testid='open-extension-market']").trigger("click");
    expect(wrapper.find("[data-testid='stub-market-dialog']").exists()).toBe(true);
    wrapper.unmount();
  });

  it("provides both locales for new market metadata labels", () => {
    const zh = i18n.global.getLocaleMessage("zh-CN") as Record<string, string>;
    const en = i18n.global.getLocaleMessage("en-US") as Record<string, string>;
    expect(zh["extensions.detail.marketOriginal"]).toBeTruthy();
    expect(en["extensions.detail.marketOriginal"]).toBeTruthy();
    expect(zh["extensions.detail.updatedAt"]).toBeTruthy();
    expect(en["extensions.detail.updatedAt"]).toBeTruthy();
  });
});
