import { describe, it, expect, vi } from "vitest";
import { computed, defineComponent, h } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { extensionsCall } from "../../../lib/ipc";
import { useExtensionsStore } from "../../../stores/extensions";
import ExtensionItemDetail from "../ExtensionItemDetail.vue";
vi.mock("../../../lib/ipc", () => ({ extensionsCall: vi.fn() }));
vi.mock("@tauri-apps/plugin-clipboard-manager", () => ({ writeText: vi.fn() }));
describe("skill detail reactive cache", () => {
  it("does not automatically retry a failed description when the group projection changes", async () => {
    setActivePinia(createPinia()); i18n.global.locale.value = "zh-CN";
    const call=vi.mocked(extensionsCall);call.mockReset();call.mockRejectedValue(new Error('offline'));
    const store=useExtensionsStore();store.setContext('/qa','runtime');
    store.marketSkills=[{kind:'market-skill',id:'owner/repo:audit',name:'audit',repo:'owner/repo',directory:'audit'}];
    const Host=defineComponent({setup(){const item=computed(()=>store.marketSkillGroups[0].items[0]);return ()=>h(ExtensionItemDetail,{item:item.value});}});
    const wrapper=mount(Host,{global:{plugins:[i18n]}});
    for(let n=0;n<4;n++)await flushPromises();
    expect(call).toHaveBeenCalledTimes(1);expect(wrapper.text()).toContain('offline');
    const source='https://github.com/owner/repo/blob/commit/skills/nested/audit/SKILL.md';
    call.mockResolvedValueOnce({items:[{id:'owner/repo:audit',description:'Verified upstream summary',description_url:source}]});
    await wrapper.get('.detail-fetch-error button').trigger('click');await flushPromises();
    expect(call).toHaveBeenCalledTimes(2);expect(wrapper.text()).toContain('Verified upstream summary');
    expect(wrapper.get('a.detail-source-link').attributes('href')).toBe(source);wrapper.unmount();
  });
});
