import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { reactive } from "vue";
import { createPinia, disposePinia, type Pinia } from "pinia";
import Panel from "../PersonalCapabilitiesPanel.vue";

const ipc = vi.hoisted(() => ({ topicCall: vi.fn() }));
vi.mock("../../../lib/ipc", () => ipc);
const runtime = reactive({ workspace: "D:/one", id: "runtime-1", createTab: vi.fn(() => true) });
vi.mock("../../../stores/runtime", () => ({ useRuntimeStore: () => runtime }));
const template = { id: "collaboration-v1", name: "通用协作", description: "Template", rules: "original rules", skill: "original skill" };
let pinia: Pinia;
afterEach(() => disposePinia(pinia));
beforeEach(() => {
  pinia = createPinia();
  vi.clearAllMocks(); runtime.workspace = "D:/one"; runtime.id = "runtime-1";
  ipc.topicCall.mockImplementation(async args => {
    if (args.operation === "personal-list") return { templates: [template], profiles: [] };
    return { profile: { id: "personal-1", template_id: template.id,
      history: [{ ...args.personal, revision: 1, created_at: "2026-11-08" }] } };
  });
});
describe("personal capability flow", () => {
  it("copies a template, edits and saves exact content with explicit enable, then opens a new agent", async () => {
    const wrapper = mount(Panel, { global: { plugins: [pinia] } }); await flushPromises();
    await wrapper.get('[data-testid="personal-template-collaboration-v1"]').trigger("click");
    await wrapper.get('[data-testid="personal-rules"]').setValue("my own rules");
    await wrapper.get('[data-testid="personal-enabled"]').setValue(true);
    await wrapper.get("form").trigger("submit"); await flushPromises();
    expect(ipc.topicCall.mock.calls[1]![0]).toMatchObject({ workspace: "D:/one", operation: "personal-save",
      personal: { rules: "my own rules", skill: "original skill", enabled: true, expected_revision: 0 } });
    expect(template.rules).toBe("original rules");
    expect(wrapper.text()).toContain("之后新建的 Claude / Codex 会话");
    await wrapper.findAll("button").find(b => b.text() === "用 Codex 验证")!.trigger("click");
    expect(runtime.createTab).toHaveBeenCalledWith("codex");
    wrapper.unmount();
  });
  it("preserves a conflicting draft and does not claim it was saved", async () => {
    const wrapper = mount(Panel, { global: { plugins: [pinia] } }); await flushPromises();
    await wrapper.get('[data-testid="personal-template-collaboration-v1"]').trigger("click");
    await wrapper.get('[data-testid="personal-rules"]').setValue("keep this draft");
    ipc.topicCall.mockRejectedValueOnce({ message: "revision conflict" });
    await wrapper.get("form").trigger("submit"); await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain("revision conflict");
    expect((wrapper.get('[data-testid="personal-rules"]').element as HTMLTextAreaElement).value).toBe("keep this draft");
    expect(wrapper.text()).not.toContain("已保存。"); wrapper.unmount();
  });
  it("discards a late save response after switching workspace", async () => {
    const wrapper = mount(Panel, { global: { plugins: [pinia] } }); await flushPromises();
    await wrapper.get('[data-testid="personal-template-collaboration-v1"]').trigger("click");
    let finish!: (result: unknown) => void;
    ipc.topicCall.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    await wrapper.get("form").trigger("submit");
    runtime.workspace = "D:/two"; runtime.id = "runtime-2"; await flushPromises();
    finish({ profile: { id: "old", template_id: template.id, history: [{ name: "wrong workspace", revision: 1 }] } });
    await flushPromises();
    expect(wrapper.text()).not.toContain("wrong workspace");
    expect(wrapper.find("form").exists()).toBe(false); wrapper.unmount();
  });
  it("restores historical content as a new draft using the current revision", async () => {
    ipc.topicCall.mockResolvedValueOnce({ templates: [template], profiles: [{ id: "p", template_id: template.id,
      history: [1, 2].map(revision => ({ revision, name: "Saved", rules: `rules ${revision}`, skill: `skill ${revision}`, reason: "reason", verification: "checked", enabled: true, created_at: "today" })) }] });
    const wrapper = mount(Panel, { global: { plugins: [pinia] } }); await flushPromises();
    await wrapper.get("nav button").trigger("click");
    await wrapper.get('[data-testid="personal-history"]').setValue(1);
    await wrapper.findAll("button").find(b => b.text() === "将此版本恢复到草稿")!.trigger("click");
    await wrapper.get("form").trigger("submit"); await flushPromises();
    expect(ipc.topicCall.mock.calls[1]![0].personal).toMatchObject({ id: "p", rules: "rules 1", skill: "skill 1", expected_revision: 2, reason: "恢复第 1 版内容" });
    wrapper.unmount();
  });
});
