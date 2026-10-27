/**
 * svc-4 (web services): the per-workspace services cache — refresh, the
 * ids-only open path (backend owns URL generation/validation), the degraded
 * old-CLI path, and stop/remove clearing.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useRuntimeStore } from "../runtime";
import * as ipc from "../../lib/ipc";
import type { RuntimeServicesResult } from "../../types";

vi.mock("../../lib/ipc", () => ({
  runtimeServices: vi.fn(),
  runtimeStatus: vi.fn(),
  runtimePollLight: vi.fn(),
  openRuntimeServiceUrl: vi.fn(),
  logUiEvent: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({ confirm: vi.fn(), open: vi.fn() }));
vi.mock("@tauri-apps/api/core", () => ({ Channel: class {} }));
vi.mock("@tauri-apps/api/window", () => ({ getCurrentWindow: () => ({}) }));
vi.mock("@tauri-apps/plugin-notification", () => ({
  isPermissionGranted: vi.fn(),
  requestPermission: vi.fn(),
  sendNotification: vi.fn(),
}));

const RID = "11111111-1111-4111-8111-111111111111";

const PAYLOAD: RuntimeServicesResult = {
  schema_version: "aisc.runtime-services/v1",
  runtime_id: RID,
  gateway: { state: "ready", container_port: 45871, host_port: 47831, host: "127.0.0.1" },
  services: [
    {
      port: 3000,
      protocol: "http",
      name: "docs preview",
      state: "registered",
      url: "http://p3000.localhost:47831/",
    },
  ],
  observed_at: "2026-08-25T00:00:00Z",
};

function setup() {
  const store = useRuntimeStore();
  store.runtimeId = RID;
  store.workspace = "C:\\ws";
  return store;
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.mocked(ipc.runtimeServices).mockReset();
  vi.mocked(ipc.openRuntimeServiceUrl).mockReset();
  vi.mocked(ipc.runtimeStatus).mockReset();
  vi.mocked(ipc.runtimePollLight).mockReset();
});

describe("svc-4 web services cache", () => {
  it("keeps merged services when a Windows snapshot canonicalizes workspace case", async () => {
    vi.stubGlobal("navigator", { userAgent: "Windows" });
    try {
      const store = setup();
      vi.mocked(ipc.runtimeStatus).mockResolvedValueOnce({
        snapshot: { state: "running", observed_at: "now", config: { workspace: "C:\\WS" } },
        services: PAYLOAD,
      } as Awaited<ReturnType<typeof ipc.runtimeStatus>>);
      await store.refreshRuntime(true);
      expect(store.workspace).toBe("C:\\WS");
      expect(store.webServices?.services).toEqual(PAYLOAD.services);
      expect(store.inspectInFlight).toBe(false);
      expect(store.userRefreshInFlight).toBe(false);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("treats remote POSIX case changes on Windows as a new context", async () => {
    vi.stubGlobal("navigator", { userAgent: "Windows" });
    try {
      const store = setup();
      store.workspace = "/home/ws";
      store.webServices = PAYLOAD;
      store.workspace = "/home/WS";
      expect(store.webServices).toBeNull();
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it.each(["full", "light"])("clear releases a pending %s poll and preserves the next owner's busy flag", async kind => {
    const store = setup();
    type Snapshot = Awaited<ReturnType<typeof ipc.runtimePollLight>>;
    type Merged = Awaited<ReturnType<typeof ipc.runtimeStatus>>;
    const snapshot = { state: "running", observed_at: "now" } as Snapshot;
    const result = { snapshot, services: PAYLOAD } as Merged;
    let finishOld!: () => void;
    let finishNew!: () => void;
    if (kind === "full") {
      vi.mocked(ipc.runtimeStatus)
        .mockReturnValueOnce(new Promise(yes => { finishOld = () => yes(result); }))
        .mockReturnValueOnce(new Promise(yes => { finishNew = () => yes(result); }));
    } else {
      vi.mocked(ipc.runtimePollLight)
        .mockReturnValueOnce(new Promise(yes => { finishOld = () => yes(snapshot); }))
        .mockReturnValueOnce(new Promise(yes => { finishNew = () => yes(snapshot); }));
    }
    const poll = () => kind === "full" ? store.refreshRuntime(true) : store.refreshRuntimeLight();
    const old = poll();
    store.clearWebServices();
    expect(store.inspectInFlight).toBe(false);
    expect(store.userRefreshInFlight).toBe(false);
    const current = poll();
    finishOld();
    await old;
    expect(store.inspectInFlight).toBe(true);
    finishNew();
    await current;
    expect(kind === "full" ? ipc.runtimeStatus : ipc.runtimePollLight).toHaveBeenCalledTimes(2);
    expect(store.inspectInFlight).toBe(false);
    expect(store.userRefreshInFlight).toBe(false);
  });

  it("merged polling cannot revive services or unlock a new request after A-B-A", async () => {
    const store = setup();
    let oldResult!: (value: Awaited<ReturnType<typeof ipc.runtimeStatus>>) => void;
    let newResult!: (value: Awaited<ReturnType<typeof ipc.runtimeStatus>>) => void;
    vi.mocked(ipc.runtimeStatus)
      .mockReturnValueOnce(new Promise(yes => { oldResult = yes; }))
      .mockReturnValueOnce(new Promise(yes => { newResult = yes; }));
    const first = store.refreshRuntime();
    store.workspace = "C:\\other";
    store.workspace = "C:\\ws";
    const current = store.refreshRuntime();
    const result = { snapshot: { state: "running", observed_at: "now" }, services: PAYLOAD } as Awaited<ReturnType<typeof ipc.runtimeStatus>>;
    oldResult(result);
    await first;
    expect(store.webServices).toBeNull();
    expect(store.inspectInFlight).toBe(true);
    newResult(result);
    await current;
    expect(store.webServices?.services).toEqual(PAYLOAD.services);
    expect(store.inspectInFlight).toBe(false);
  });

  it("a light poll failure after identity changes cannot issue a fallback for the new context", async () => {
    const store = setup();
    let fail!: (reason: unknown) => void;
    vi.mocked(ipc.runtimePollLight).mockReturnValueOnce(new Promise((_yes, no) => { fail = no; }));
    const first = store.refreshRuntimeLight();
    store.runtimeId = "22222222-2222-4222-8222-222222222222";
    fail(new Error("old poll unavailable"));
    expect(await first).toBe(false);
    expect(ipc.runtimeStatus).not.toHaveBeenCalled();
    expect(store.webServices).toBeNull();
  });

  it.each([false, true])("ignores a response/error from the first A after A-B-A (reject=%s)", async reject => {
    const store = setup();
    let resolve!: (value: RuntimeServicesResult) => void;
    let fail!: (reason: unknown) => void;
    vi.mocked(ipc.runtimeServices).mockReturnValueOnce(new Promise((yes, no) => { resolve = yes; fail = no; }));
    const old = store.refreshWebServices();
    store.workspace = "C:\\other";
    store.workspace = "C:\\ws";
    const latest = { ...PAYLOAD, services: [{ ...PAYLOAD.services[0]!, name: "new observation" }] };
    vi.mocked(ipc.runtimeServices).mockResolvedValueOnce(latest);
    await store.refreshWebServices();
    if (reject) fail({ message: "old error" }); else resolve(PAYLOAD);
    await old;
    expect(store.webServices?.services[0]?.name).toBe("new observation");
    expect(store.webServicesError).toBeNull();
  });

  it("does not let an old finally unlock a newer runtime request", async () => {
    const store = setup();
    let first!: (value: RuntimeServicesResult) => void;
    let second!: (value: RuntimeServicesResult) => void;
    vi.mocked(ipc.runtimeServices)
      .mockReturnValueOnce(new Promise(resolve => { first = resolve; }))
      .mockReturnValueOnce(new Promise(resolve => { second = resolve; }));
    const old = store.refreshWebServices();
    store.runtimeId = "22222222-2222-4222-8222-222222222222";
    const current = store.refreshWebServices();
    first(PAYLOAD);
    await old;
    expect(store.webServicesInFlight).toBe(true);
    expect(store.webServices).toBeNull();
    second({ ...PAYLOAD, runtime_id: store.runtimeId });
    await current;
    expect(store.webServicesInFlight).toBe(false);
  });

  it("clear invalidates an in-flight request even when runtime identity is unchanged", async () => {
    const store = setup();
    let resolve!: (value: RuntimeServicesResult) => void;
    vi.mocked(ipc.runtimeServices).mockReturnValueOnce(new Promise(yes => { resolve = yes; }));
    const old = store.refreshWebServices();
    store.clearWebServices();
    resolve(PAYLOAD);
    await old;
    expect(store.webServices).toBeNull();
  });

  it.each([false, true])("a service open finishing after a context change cannot refresh or fail the new context (reject=%s)", async reject => {
    const store = setup();
    let resolve!: (value: string) => void;
    let fail!: (reason: unknown) => void;
    vi.mocked(ipc.openRuntimeServiceUrl).mockReturnValueOnce(new Promise((yes, no) => { resolve = yes; fail = no; }));
    const old = store.openWebService(3000);
    store.runtimeId = "22222222-2222-4222-8222-222222222222";
    if (reject) fail({ message: "old open failed" }); else resolve("http://localhost/");
    await old;
    expect(ipc.runtimeServices).not.toHaveBeenCalled();
    expect(store.webServicesError).toBeNull();
  });

  it("refreshWebServices stores the payload and clears prior errors", async () => {
    const store = setup();
    vi.mocked(ipc.runtimeServices).mockResolvedValue(PAYLOAD);
    await store.refreshWebServices();
    expect(ipc.runtimeServices).toHaveBeenCalledWith("C:\\ws", RID);
    expect(store.webServices?.gateway.state).toBe("ready");
    expect(store.webServices?.services[0]?.url).toBe("http://p3000.localhost:47831/");
    expect(store.webServicesError).toBeNull();
  });

  it("openWebService passes ids only — never a URL — then refreshes", async () => {
    const store = setup();
    const calls: unknown[][] = [];
    vi.mocked(ipc.openRuntimeServiceUrl).mockImplementation(async (...args: unknown[]) => {
      calls.push(args);
      return "http://p3000.localhost:47831/";
    });
    vi.mocked(ipc.runtimeServices).mockResolvedValue(PAYLOAD);
    await store.openWebService(3000);
    expect(calls).toEqual([["C:\\ws", RID, 3000]]);
    expect(store.webServicesError).toBeNull();
  });

  it("an open failure surfaces as webServicesError without crashing", async () => {
    const store = setup();
    vi.mocked(ipc.openRuntimeServiceUrl).mockRejectedValue({
      code: "WB_ERR_AISC",
      message: "boom",
      technical_detail: null,
      retryable: false,
      action: "retry",
    });
    await store.openWebService(3000);
    expect(store.webServicesError?.message).toBe("boom");
  });

  it("an old CLI (no runtime services) keeps the last payload and records the error", async () => {
    const store = setup();
    vi.mocked(ipc.runtimeServices).mockResolvedValue(PAYLOAD);
    await store.refreshWebServices();
    vi.mocked(ipc.runtimeServices).mockRejectedValue({
      code: "WB_ERR_AISC",
      message: "unrecognized command",
      technical_detail: null,
      retryable: false,
      action: "upgrade_cli",
    });
    await store.refreshWebServices();
    // degraded, not wiped: the panel gates on capability and keeps context
    expect(store.webServices?.gateway.state).toBe("ready");
    expect(store.webServicesError?.message).toBe("unrecognized command");
  });

  it("refresh is deduped while in flight", async () => {
    const store = setup();
    let resolve!: (v: RuntimeServicesResult) => void;
    vi.mocked(ipc.runtimeServices).mockImplementation(
      () => new Promise((r) => (resolve = r)),
    );
    const first = store.refreshWebServices();
    const second = store.refreshWebServices();
    resolve(PAYLOAD);
    await Promise.all([first, second]);
    expect(ipc.runtimeServices).toHaveBeenCalledTimes(1);
  });

  it("clearWebServices empties the openable state (stop/remove path)", () => {
    const store = setup();
    store.webServices = PAYLOAD;
    store.clearWebServices();
    expect(store.webServices).toBeNull();
    expect(store.webServicesError).toBeNull();
    expect(store.webServicesInFlight).toBe(false);
  });
});
