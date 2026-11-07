import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useImageRebuildStore } from "../imageRebuild";
import { useSettingsStore } from "../settings";

const ipc = vi.hoisted(() => ({
  checkImageRebuild: vi.fn(), rebuildImage: vi.fn(), cancelBuild: vi.fn(),
  targetSet: vi.fn(), remoteCliVersion: vi.fn(), targetGet: vi.fn().mockResolvedValue({ kind: "local", machine: null }),
  workspaceRevealDataFile: vi.fn(), startDocker: vi.fn(),
}));
vi.mock("../../lib/ipc", () => ipc);
vi.mock("@tauri-apps/api/core", () => ({ Channel: class { onmessage?: (event: unknown) => void; } }));
const check = { tag: "super-claude:qa", image_id: "sha256:old", exists: true, containers: [], running_containers: [] };
beforeEach(() => {
  setActivePinia(createPinia()); vi.clearAllMocks();
  ipc.checkImageRebuild.mockResolvedValue(check);
});

describe("selected image rebuild", () => {
  it("prechecks the selected identity and blocks running containers", async () => {
    ipc.checkImageRebuild.mockResolvedValue({ ...check, running_containers: ["working"] });
    const store = useImageRebuildStore();
    await store.open([check.tag], "sha256:old");
    expect(ipc.checkImageRebuild).toHaveBeenCalledWith(check.tag, "sha256:old");
    expect(store.canStart).toBe(false);
    await store.startBuild();
    expect(ipc.rebuildImage).not.toHaveBeenCalled();
  });

  it("passes cache choice and stable identity, streams progress, and settles once", async () => {
    let finish!: () => void;
    ipc.rebuildImage.mockImplementation((_tag, _id, _cache, _task, events) => {
      events.onmessage({ type: "build.progress", data: { phase: "steps", percent: 25, progress_kind: "determinate" } });
      events.onmessage({ type: "build.output", data: { chunk: "real build output" } });
      events.onmessage({ type: "build.complete", data: { new_image_id: "sha256:new", old_image_action: "kept_tagged" } });
      return new Promise<void>(resolve => { finish = resolve; });
    });
    const store = useImageRebuildStore(); const refreshed = vi.fn().mockResolvedValue(undefined);
    await store.open([check.tag], undefined, refreshed); store.noCache = false;
    const pending = store.startBuild(); await store.startBuild();
    expect(ipc.rebuildImage).toHaveBeenCalledTimes(1);
    expect(ipc.rebuildImage.mock.calls[0]!.slice(0, 3)).toEqual([check.tag, check.image_id, false]);
    expect(store.buildProgress?.percent).toBe(25);
    expect(store.buildLog).toContain("real build output");
    expect(store.buildStatus).toBe("building"); // terminal event alone is not authoritative
    finish(); await pending;
    expect(store.buildStatus).toBe("complete");
    expect(refreshed).toHaveBeenCalledOnce();
    expect(store.result?.new_image_id).toBe("sha256:new");
  });

  it("cancels only its task and retries through fresh confirmation", async () => {
    let reject!: (error: unknown) => void;
    ipc.rebuildImage.mockImplementation(() => new Promise((_resolve, fail) => { reject = fail; }));
    ipc.cancelBuild.mockResolvedValue(true);
    const store = useImageRebuildStore(); await store.open([check.tag]);
    const pending = store.startBuild();
    const task = ipc.rebuildImage.mock.calls[0]![3];
    await store.cancelBuild();
    expect(ipc.cancelBuild).toHaveBeenCalledWith(`rebuild:${task}`);
    reject({ code: "WB_ERR_CLI_CANCELLED", message: "cancelled" }); await pending;
    expect(store.buildStatus).toBe("cancelled");
    await store.startBuild();
    expect(store.buildStatus).toBe("idle");
    expect(ipc.rebuildImage).toHaveBeenCalledTimes(1);
    expect(ipc.checkImageRebuild).toHaveBeenCalledTimes(2);
  });

  it("does not start or refresh a different target", async () => {
    const store = useImageRebuildStore(); await store.open([check.tag]);
    ipc.targetSet.mockResolvedValue({ kind: "remote", machine: { name: "qa" } });
    await useSettingsStore().switchTarget("qa", "/qa");
    expect(store.targetChanged).toBe(true); expect(store.canStart).toBe(false);
    await store.startBuild();
    expect(ipc.rebuildImage).not.toHaveBeenCalled();
    store.close();
    await store.open([check.tag]);
    expect(store.canStart).toBe(false);
    expect(ipc.checkImageRebuild).toHaveBeenCalledTimes(1);
  });

  it("keeps a finished task attached to its original target without refreshing the new one", async () => {
    let finish!: () => void;
    ipc.rebuildImage.mockImplementation(() => new Promise<void>(resolve => { finish = resolve; }));
    const refreshed = vi.fn().mockResolvedValue(undefined);
    const store = useImageRebuildStore(); await store.open([check.tag], undefined, refreshed);
    const pending = store.startBuild();
    ipc.targetSet.mockResolvedValue({ kind: "remote", machine: { name: "qa" } });
    await useSettingsStore().switchTarget("qa", "/qa");
    finish(); await pending;
    expect(store.targetChanged).toBe(true);
    expect(store.buildTag).toBe(check.tag);
    expect(refreshed).not.toHaveBeenCalled();
  });

  it("reissues an early missed cancel when that task starts", async () => {
    let fail!: (error: unknown) => void;
    let events!: { onmessage: (event: unknown) => void };
    ipc.rebuildImage.mockImplementation((_tag, _id, _cache, _task, channel) => {
      events = channel; return new Promise((_resolve, reject) => { fail = reject; });
    });
    ipc.cancelBuild.mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    const store = useImageRebuildStore(); await store.open([check.tag]);
    const pending = store.startBuild(); await store.cancelBuild();
    events.onmessage({ type: "build.start", data: {} });
    await Promise.resolve();
    expect(ipc.cancelBuild).toHaveBeenCalledTimes(2);
    expect(ipc.cancelBuild.mock.calls[0]).toEqual(ipc.cancelBuild.mock.calls[1]);
    fail({ code: "WB_ERR_CLI_CANCELLED", message: "cancelled" }); await pending;
    expect(store.buildStatus).toBe("cancelled");
  });
});
