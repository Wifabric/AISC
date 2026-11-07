import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useExtensionsStore } from "../extensions";
import { extensionsCall } from "../../lib/ipc";
import { writeText } from "@tauri-apps/plugin-clipboard-manager";
vi.mock("../../lib/ipc", () => ({ extensionsCall: vi.fn() }));
vi.mock("@tauri-apps/plugin-clipboard-manager", () => ({ writeText: vi.fn() }));
beforeEach(() => {
  setActivePinia(createPinia()); vi.clearAllMocks();
  vi.mocked(extensionsCall).mockImplementation(async p => {
    if (p.op === "plugin-install") throw new Error("install rejected");
    return { items: [] };
  });
});
describe("failure dismissal lifecycle", () => {
  it("dismisses through the latest result, retains history and retries, and shows new failures", async () => {
    const store = useExtensionsStore(); store.setContext("/a", "r1"); store.kind = "plugins";
    await store.pluginAction("plugin-install", "one@market");
    const first = store.latestFailure!.operationId;
    await store.pluginAction("plugin-install", "two@market");
    const latest = store.latestFailure!.operationId;
    const history = JSON.stringify(store.operationLog);
    store.dismissFailureNotice(first); expect(store.latestFailure!.operationId).toBe(latest);
    store.dismissFailureNotice(latest);
    expect(store.latestFailure).toBeNull(); expect(store.error).toBeNull();
    expect(JSON.stringify(store.operationLog)).toBe(history);
    expect(store.canRetryOperation(latest)).toBe(true);
    await store.copyOperationDiagnostic(latest);
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('"status": "failed"'));
    await store.retryOperation(latest);
    expect(store.latestFailure!.operationId).not.toBe(latest);
    expect(store.latestFailure!.attempt).toBe(2);
    expect(store.error).toBe("install rejected");
  });
  it("does not hide a later independent read error or carry dismissal across targets", async () => {
    const store = useExtensionsStore(); store.setContext("/a", "r1"); store.kind = "plugins";
    await store.pluginAction("plugin-install", "one@market");
    store.dismissFailureNotice(store.latestFailure!.operationId);
    vi.mocked(extensionsCall).mockRejectedValue(new Error("install rejected"));
    await store.load(); expect(store.error).toBe("install rejected");
    store.setContext("/b", "r2"); expect(store.operationLog).toEqual([]); expect(store.latestFailure).toBeNull();
    await store.pluginAction("plugin-install", "one@market"); expect(store.latestFailure).not.toBeNull();
    expect(store.latestFailure!.workspace).toBe("/b");
  });
  it("dismisses unknown status without granting retry permission", async () => {
    const store = useExtensionsStore(); store.setContext("/a", "r1");
    vi.mocked(extensionsCall).mockImplementation(async p => {
      if (p.op === "plugin-install") throw { code: "WB_ERR_CLI_TIMEOUT", message: "timeout" };
      return { items: [], mutation_running: true };
    });
    await store.pluginAction("plugin-install", "one@market");
    const id = store.latestFailure!.operationId;
    store.dismissFailureNotice(id);
    expect(store.operationLog[0]!.status).toBe("unknown"); expect(store.canRetryOperation(id)).toBe(false);
  });
});
