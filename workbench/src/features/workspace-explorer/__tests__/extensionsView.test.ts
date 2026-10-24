/** b6 复测发现：扩展视图切换页签后内容整体消失——本地复现。 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
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
      ? { kind, id: "caveman", name: "caveman", repo: "x/y", enabled_claude: true, enabled_codex: true }
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
    // b13：同仓库技能先显示仓库组，展开后才显示子技能。
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
});
