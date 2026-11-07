import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useExtensionModulesStore } from "../extensionModules";
import type { ExtensionModuleDocument } from "../../lib/ipc";
const ipc = vi.hoisted(() => ({ loadExtensionModules: vi.fn(), saveExtensionModules: vi.fn(), extensionsCall: vi.fn() }));
vi.mock("../../lib/ipc", () => ipc);
const member = { kind: "skills" as const, identity: "owner/repo:skill", name: "Skill", source_url: "https://github.com/owner/repo" };
const module = { id: "qa", name: "QA", members: [member, member] };
let disk: ExtensionModuleDocument;
beforeEach(() => {
  setActivePinia(createPinia()); vi.clearAllMocks();
  disk = { schema_version: 1, revision: 0, definitions: [], hidden_builtin_ids: [] };
  ipc.loadExtensionModules.mockImplementation(async () => structuredClone(disk));
  ipc.saveExtensionModules.mockImplementation(async (revision, document) => {
    expect(revision).toBe(disk.revision);
    disk = JSON.parse(JSON.stringify({ ...document, revision: revision + 1 }));
    return structuredClone(disk);
  });
});
describe("module definitions", () => {
  it("deduplicates, persists across store recreation, and deletes only definitions", async () => {
    let store = useExtensionModulesStore(); await store.load();
    expect(await store.save(module)).toBe(true);
    expect(store.modules[0]?.members).toHaveLength(1);
    setActivePinia(createPinia()); store = useExtensionModulesStore(); await store.load();
    expect(store.modules[0]?.name).toBe("QA");
    await store.remove("qa");
    expect(disk.definitions).toHaveLength(0);
    expect(ipc.extensionsCall).not.toHaveBeenCalled();
  });
  it("retains saved data on a conflicting save and does not silently retry overwrite", async () => {
    const store = useExtensionModulesStore(); await store.load(); await store.save(module);
    ipc.saveExtensionModules.mockRejectedValueOnce({ technical_detail: "revision conflict" });
    expect(await store.save({ ...module, name: "Draft" })).toBe(false);
    expect(store.modules[0]?.name).toBe("QA");
    expect(store.error).toBe("revision conflict");
    expect(ipc.saveExtensionModules).toHaveBeenCalledTimes(2);
  });
  it("does not replace an unreadable or unsupported document", async () => {
    ipc.loadExtensionModules.mockRejectedValueOnce(new Error("Unsupported schema"));
    const store = useExtensionModulesStore(); await store.load();
    expect(await store.save(module)).toBe(false);
    expect(ipc.saveExtensionModules).not.toHaveBeenCalled();
    expect(store.document).toBeNull();
  });
});
