import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useExtensionsStore } from "../extensions";
import { extensionsCall } from "../../lib/ipc";
vi.mock("../../lib/ipc", () => ({ extensionsCall: vi.fn() }));
const call = vi.mocked(extensionsCall);
const skill = { kind: "market-skill", id: "owner/repo:audit", name: "audit", repo: "owner/repo", directory: "audit" };
beforeEach(() => { setActivePinia(createPinia()); call.mockReset(); });
describe("on-demand functional descriptions", () => {
  it("loads once per identity without changing installed/search lists", async () => {
    let resolve!: (value: any) => void;
    call.mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    const store = useExtensionsStore(); store.setContext("/one", "r1");
    store.marketSkills = [skill];
    const pending = store.describeSkill(skill);
    expect(store.descriptionState(skill)?.loading).toBe(true);
    await store.describeSkill(skill);
    expect(call).toHaveBeenCalledTimes(1);
    expect(call).toHaveBeenCalledWith(expect.objectContaining({ op: "skill-describe", id: skill.id }));
    resolve({ items: [{ ...skill, description: "Audit API compatibility" }] }); await pending;
    expect(store.describedItem(skill).description).toBe("Audit API compatibility");
    expect(store.marketSkills[0]?.description).toBeUndefined();
    await store.describeSkill(skill); expect(call).toHaveBeenCalledTimes(1);
  });
  it("keeps failures local and permits a real retry", async () => {
    call.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ items: [{ ...skill, description: "Audit changes" }] });
    const store = useExtensionsStore(); store.setContext("/one", "r1");
    await store.describeSkill(skill);
    expect(store.descriptionState(skill)).toMatchObject({ loading: false, error: "offline" });
    expect(store.describedItem(skill).description).toBeUndefined();
    expect(store.error).toBeNull();
    await store.describeSkill(skill);
    expect(store.descriptionState(skill)?.error).toBeUndefined();
    expect(store.describedItem(skill).description).toBe("Audit changes");
  });
  it("discards responses and errors from a previous runtime", async () => {
    let resolve!: (value: any) => void;
    call.mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    const store = useExtensionsStore(); store.setContext("/one", "r1");
    const pending = store.describeSkill(skill); store.setContext("/two", "r2");
    resolve({ items: [{ ...skill, description: "Previous workspace data" }] }); await pending;
    expect(store.describedItem(skill).description).toBeUndefined();
    expect(store.descriptionState(skill)).toBeUndefined();
  });
  it("never replaces an existing description or queries non-skill sources", async () => {
    const store = useExtensionsStore(); store.setContext("/one", "r1");
    await store.describeSkill({ ...skill, description: "Upstream text" });
    await store.describeSkill({ ...skill, kind: "mcp" });
    await store.describeSkill({ ...skill, id: "local", repo: "" });
    expect(call).not.toHaveBeenCalled();
  });
});
