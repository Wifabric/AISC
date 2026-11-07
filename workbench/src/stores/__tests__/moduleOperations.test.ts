import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { nextTick, reactive } from "vue";
import { useModuleOperationsStore } from "../moduleOperations";
import type { ModuleOperationPlan } from "../moduleOperations";
const ipc = vi.hoisted(() => ({ extensionsCall: vi.fn() }));
vi.mock("../../lib/ipc", () => ipc);
let extensions: any;
let settings: any;
vi.mock("../extensions", () => ({ useExtensionsStore: () => extensions }));
vi.mock("../settings", () => ({ useSettingsStore: () => settings }));
const member = { kind: "skills" as const, identity: "owner/repo:qa", name: "QA", source_url: "https://github.com/owner/repo" };
const definition = { id: "qa", name: "QA", members: [member] };
const prepared: ModuleOperationPlan = { plan_id: "plan", module_id: "qa", module_name: "QA", runtime_id: "runtime-a", action: "apply",
  rows: [0, 1].map(i => ({ key: String(i), member, action: "install", status: "planned", reason: "missing", auth_required: false })) };
beforeEach(() => {
  setActivePinia(createPinia()); vi.clearAllMocks();
  extensions = reactive({ context: { workspace: "/a", runtimeId: "runtime-a" },
    busyByKind: { skills: false, mcp: false, plugins: false }, load: vi.fn(async () => {}) });
  settings = reactive({ target: { kind: "local", machine: null } });
  ipc.extensionsCall.mockImplementation(async (p: any) => p.op === "module-plan" ? structuredClone(prepared)
    : { ...structuredClone(prepared.rows[JSON.parse(p.config).index]), status: "installed" });
});
describe("module operation orchestration", () => {
  it("requires confirmation, prevents double execution, and preserves partial failure", async () => {
    const store = useModuleOperationsStore(); await store.prepare(definition, "apply");
    expect(ipc.extensionsCall).toHaveBeenCalledTimes(1);
    ipc.extensionsCall.mockImplementationOnce(async () => ({ ...prepared.rows[0], status: "failed" }));
    const running = store.run(); await store.run(); await running;
    expect(ipc.extensionsCall).toHaveBeenCalledTimes(3);
    expect(store.phase).toBe("partial");
    expect(extensions.busyByKind.skills).toBe(false);
    await store.retry();
    expect(store.phase).toBe("prepared");
    expect(ipc.extensionsCall.mock.calls[ipc.extensionsCall.mock.calls.length - 1]?.[0].op).toBe("module-plan");
  });
  it("stops after the current item, retaining its actual result", async () => {
    const store = useModuleOperationsStore(); await store.prepare(definition, "apply");
    let finish!: (value: unknown) => void;
    ipc.extensionsCall.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    const running = store.run(); store.cancel();
    expect(store.phase).toBe("running");
    finish({ ...prepared.rows[0], status: "installed" }); await running;
    expect(store.phase).toBe("stopped"); expect(store.completed).toBe(1);
    expect(ipc.extensionsCall).toHaveBeenCalledTimes(2);
  });
  it("does not dispatch or refresh into a newly selected target", async () => {
    const store = useModuleOperationsStore(); await store.prepare(definition, "apply");
    let finish!: (value: unknown) => void;
    ipc.extensionsCall.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    const running = store.run();
    extensions.context = { workspace: "/b", runtimeId: "runtime-b" };
    extensions.busyByKind = { skills: true, mcp: false, plugins: false };
    await nextTick(); finish({ ...prepared.rows[0], status: "installed" }); await running;
    expect(store.phase).toBe("stopped"); expect(store.targetChanged).toBe(true);
    expect(extensions.load).not.toHaveBeenCalled();
    expect(extensions.busyByKind.skills).toBe(true);
    expect(ipc.extensionsCall).toHaveBeenCalledTimes(2);
  });
  it("releases its reservation when only the machine changes", async () => {
    const store = useModuleOperationsStore(); await store.prepare(definition, "apply");
    let finish!: (value: unknown) => void;
    ipc.extensionsCall.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    const running = store.run(); settings.target = { kind: "remote", machine: { name: "remote" } };
    await nextTick(); finish({ ...prepared.rows[0], status: "installed" }); await running;
    expect(extensions.busyByKind.skills).toBe(false);
    expect(store.phase).toBe("stopped");
  });
  it("labels transport failures unknown and never automatically replays", async () => {
    const store = useModuleOperationsStore(); await store.prepare(definition, "apply");
    ipc.extensionsCall.mockRejectedValueOnce({ technical_detail: "transport disconnected" });
    await store.run();
    expect(store.plan?.rows[0]?.status).toBe("unknown");
    expect(store.phase).toBe("partial");
    expect(ipc.extensionsCall).toHaveBeenCalledTimes(2);
  });
  it("discards preparation responses after a workspace switch", async () => {
    const store = useModuleOperationsStore();
    let finish!: (value: unknown) => void;
    ipc.extensionsCall.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    const pending = store.prepare(definition, "apply");
    extensions.context = null; await nextTick(); finish(prepared); await pending;
    expect(store.plan).toBeNull(); expect(store.phase).toBe("idle");
  });
});
