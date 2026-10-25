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
    await wrapper.find("[data-testid^=ext-skill-group-]").trigger("click");
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

  it("keeps a skill group open while showing and re-showing a child introduction", async () => {
    const wrapper = mount(ExtensionsView, { global: { plugins: [i18n] } });
    await flushPromises();
    const group = wrapper.find("[data-testid^=ext-skill-group-]");
    await group.trigger("click");
    await flushPromises();

    const child = wrapper.find("[data-testid=ext-skill-child-caveman]");
    expect(child.exists()).toBe(true);
    expect(wrapper.text()).not.toContain("Ultra-compressed agent communication");

    await child.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Ultra-compressed agent communication");
    expect(wrapper.text()).toContain("caveman");

    await child.trigger("click");
    await flushPromises();
    expect(wrapper.text()).not.toContain("Ultra-compressed agent communication");
    expect(wrapper.text()).toContain("caveman");

    await group.trigger("click");
    await flushPromises();
    expect(wrapper.text()).not.toContain("Ultra-compressed agent communication");
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
    await wrapper.find("[data-testid^=ext-skill-group-]").trigger("click");
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
