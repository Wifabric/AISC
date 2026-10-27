/**
 * A7 (D-8 自研): self-update store state machine tests — check/download/
 * install transitions over mocked ipc, error paths reset to recoverable
 * states, progress events feed the counters.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { UpdateInfo, UpdateDownloadResult } from "../../lib/ipc";
import { listen } from "@tauri-apps/api/event";

const progress = vi.hoisted(() => ({ callbacks: [] as ((event: { payload: { downloaded: number; total: number; requestId: string } }) => void)[], stop: vi.fn() }));

const mockIpc = vi.hoisted(() => ({
  appCheckUpdate: vi.fn(),
  appDownloadUpdate: vi.fn(),
  appInstallUpdate: vi.fn(),
}));

vi.mock("../../lib/ipc", () => mockIpc);
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockImplementation((_event, callback) => {
    progress.callbacks.push(callback);
    return Promise.resolve(progress.stop);
  }),
}));

import { useUpdateStore } from "../update";

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  mockIpc.appCheckUpdate.mockReset();
  mockIpc.appDownloadUpdate.mockReset();
  mockIpc.appInstallUpdate.mockReset();
  progress.callbacks = [];
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue("Windows NT 10.0");
});

const available = (latest = "2.1.17"): UpdateInfo => ({
  current: "2.1.16", latest, updateAvailable: true,
  setupUrl: `https://example.test/${latest}.exe`, sha256Url: `https://example.test/${latest}.sha256`,
  releaseUrl: "https://example.test/release", note: "",
  cliCurrent: "0.1.10.dev0", cliLatest: "0.1.10.dev0",
});
const artifact = (path = "C:\\tmp\\setup.exe"): UpdateDownloadResult => ({ path, sha256: "ab".repeat(32), size: 42 });
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function ready() {
  mockIpc.appCheckUpdate.mockResolvedValue(available());
  mockIpc.appDownloadUpdate.mockResolvedValue(artifact());
  const store = useUpdateStore();
  await store.check();
  await store.download();
  return store;
}

describe("b5 explicit update state and identity", () => {
  it.each(["WB_ERR_UPDATE_NETWORK: HTTP 503", "check failed (network strategies exhausted): timeout", "bundled CLI check failed: offline"])("does not report a failed check as current: %s", async (note) => {
    mockIpc.appCheckUpdate.mockResolvedValue({ ...available(), updateAvailable: false, note });
    const s = useUpdateStore();
    expect(await s.check()).toBeNull();
    expect(s.status).toBe("idle");
    expect(s.error).toBe(note);
  });

  it("keeps an available installer with a partial-check warning", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue({ ...available(), note: "bundled CLI check failed: offline" });
    const s = useUpdateStore();
    expect((await s.check())?.updateAvailable).toBe(true);
    expect(s.status).toBe("available");
    expect(s.error).toContain("failed");
  });

  it.each(["current", "cliCurrent", "cliLatest"])("does not claim an unknown %s version is current", async field => {
    mockIpc.appCheckUpdate.mockResolvedValue({ ...available(), updateAvailable: false, [field]: null });
    const store = useUpdateStore();
    expect(await store.check()).toBeNull();
    expect(store.status).toBe("idle");
    expect(store.error).toBeTruthy();
  });

  it("does not claim an unknown latest version is current", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue({ ...available(), latest: null, updateAvailable: false });
    const s = useUpdateStore();
    expect(await s.check()).toBeNull();
    expect(s.status).toBe("idle");
    expect(s.error).toBeTruthy();
  });

  it.each([false, true])("ignores an old check's late completion (reject=%s)", async (reject) => {
    const old = deferred<UpdateInfo>();
    mockIpc.appCheckUpdate.mockReturnValueOnce(old.promise).mockResolvedValueOnce(available("2.1.18"));
    const s = useUpdateStore();
    const pending = s.check();
    await s.check();
    if (reject) old.reject(new Error("old offline")); else old.resolve(available());
    expect(await pending).toBeNull();
    expect(s.info?.latest).toBe("2.1.18");
    expect(s.status).toBe("available");
    expect(s.error).toBeNull();
  });

  it("invalidates a staged download and its progress as soon as a new check starts", async () => {
    const s = await ready();
    const oldProgress = progress.callbacks[0]!;
    const next = deferred<UpdateInfo>();
    mockIpc.appCheckUpdate.mockReturnValue(next.promise);
    const checking = s.check();
    oldProgress({ payload: { downloaded: 99, total: 100, requestId: "old" } });
    expect(s.staged).toBeNull();
    expect(s.downloaded).toBe(0);
    expect(s.total).toBe(0);
    next.resolve(available("2.1.18"));
    await checking;
  });

  it.each([false, true])("ignores an invalidated download's result/error and blocks overlapping installer writes (reject=%s)", async (reject) => {
    const old = deferred<UpdateDownloadResult>();
    mockIpc.appCheckUpdate.mockResolvedValue(available());
    mockIpc.appDownloadUpdate.mockReturnValueOnce(old.promise).mockResolvedValueOnce(artifact("B.exe"));
    const s = useUpdateStore();
    await s.check();
    const pending = s.download();
    await vi.waitFor(() => expect(mockIpc.appDownloadUpdate).toHaveBeenCalledOnce());
    mockIpc.appCheckUpdate.mockResolvedValue(available("2.1.18"));
    await s.check();
    expect(await s.download()).toBe(false);
    progress.callbacks[0]!({ payload: { downloaded: 99, total: 100, requestId: "old" } });
    expect(s.downloaded).toBe(0);
    if (reject) old.reject(new Error("old hash failure")); else old.resolve(artifact());
    expect(await pending).toBe(false);
    expect(s.staged).toBeNull();
    expect(s.status).toBe("available");
    expect(s.error).toBeNull();
    expect(progress.stop).toHaveBeenCalledOnce();
    expect(await s.download()).toBe(true);
    expect(s.staged?.path).toBe("B.exe");
  });

  it("does not start downloading if a new check invalidates pending listener setup", async () => {
    const listener = deferred<() => void>();
    vi.mocked(listen).mockReturnValueOnce(listener.promise);
    mockIpc.appCheckUpdate.mockResolvedValue(available());
    const s = useUpdateStore();
    await s.check();
    const downloading = s.download();
    mockIpc.appCheckUpdate.mockResolvedValue(available("2.1.18"));
    await s.check();
    listener.resolve(progress.stop);
    expect(await downloading).toBe(false);
    expect(mockIpc.appDownloadUpdate).not.toHaveBeenCalled();
    expect(progress.stop).toHaveBeenCalledOnce();
    expect(s.status).toBe("available");
    expect(s.info?.latest).toBe("2.1.18");
  });

  it("clears failed progress and detaches its listener before retry", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue(available());
    mockIpc.appDownloadUpdate.mockRejectedValue(new Error("bad hash"));
    const s = useUpdateStore();
    await s.check();
    await s.download();
    progress.callbacks[0]!({ payload: { downloaded: 50, total: 100, requestId: "stale" } });
    expect(s.downloaded).toBe(0);
    expect(s.total).toBe(0);
    expect(progress.stop).toHaveBeenCalledOnce();
    expect(s.staged).toBeNull();
  });

  it("only accepts progress bearing this download's unique request ID", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue(available());
    const download = deferred<UpdateDownloadResult>();
    mockIpc.appDownloadUpdate.mockReturnValueOnce(download.promise).mockResolvedValueOnce(artifact());
    const s = useUpdateStore();
    await s.check();
    const pending = s.download();
    await vi.waitFor(() => expect(mockIpc.appDownloadUpdate).toHaveBeenCalledOnce());
    const requestId = mockIpc.appDownloadUpdate.mock.calls[0]![3];
    expect(requestId).toEqual(expect.any(String));
    expect(requestId.length).toBeGreaterThan(0);
    const callback = progress.callbacks[0]!;
    callback({ payload: { downloaded: 1, total: 100, requestId: "other" } });
    callback({ payload: { downloaded: 2, total: 100 } } as Parameters<typeof callback>[0]);
    expect(s.downloaded).toBe(0);
    callback({ payload: { downloaded: 30, total: 100, requestId } });
    expect(s.downloaded).toBe(30);
    expect(s.total).toBe(100);
    download.resolve(artifact());
    await pending;
    await s.check();
    await s.download();
    expect(mockIpc.appDownloadUpdate.mock.calls[1]![3]).not.toBe(requestId);
    progress.callbacks[1]!({ payload: { downloaded: 99, total: 100, requestId } });
    expect(s.downloaded).toBe(0);
  });

  it("keeps ready throughout explicit launch, blocks duplicate actions and recovers after failure", async () => {
    const s = await ready();
    const launch = deferred<void>();
    mockIpc.appInstallUpdate.mockReturnValue(launch.promise);
    s.error = "previous failure";
    const pending = s.install();
    expect(s.status).toBe("ready");
    expect(s.error).toBeNull();
    await s.install();
    await s.check();
    await s.download();
    expect(mockIpc.appInstallUpdate).toHaveBeenCalledOnce();
    expect(mockIpc.appCheckUpdate).toHaveBeenCalledOnce();
    expect(mockIpc.appDownloadUpdate).toHaveBeenCalledOnce();
    launch.reject(new Error("Explorer launch failed"));
    await pending;
    expect(s.status).toBe("ready");
    expect(s.error).toBe("Explorer launch failed");
    expect(s.staged?.path).toBe(artifact().path);
  });

  it("keeps ready after a successful launch response, leaving app exit to Rust", async () => {
    const s = await ready();
    mockIpc.appInstallUpdate.mockResolvedValue(undefined);
    await s.install();
    expect(s.status).toBe("ready");
  });

  it("shows structured launch failure detail and retains the downloaded installer", async () => {
    const store = await ready();
    mockIpc.appInstallUpdate.mockRejectedValue({ code: "WB_ERR_USAGE", message: "参数无效",
      technical_detail: "installer shell open failed: The operation was canceled by the user. (os error 1223)" });
    await store.install();
    expect(store.status).toBe("ready");
    expect(store.error).toContain("os error 1223");
    expect(store.staged?.path).toBe(artifact().path);
  });

  it.each(["target", "path", "hash", "size", "same-target-redownload"])("rejects a confirmation snapshot after %s changes", async (change) => {
    const s = await ready();
    const snapshot = s.captureInstallation();
    if (change === "target") s.info!.latest = "2.1.18";
    if (change === "path") s.staged!.path = "B.exe";
    if (change === "hash") s.staged!.sha256 = "cd".repeat(32);
    if (change === "size") s.staged!.size++;
    if (change === "same-target-redownload") { await s.check(); await s.download(); }
    await s.install(snapshot);
    expect(mockIpc.appInstallUpdate).not.toHaveBeenCalled();
  });

  it("only downloads on Windows and with a known target", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue(available());
    const s = useUpdateStore();
    await s.check();
    vi.spyOn(navigator, "userAgent", "get").mockReturnValue("Macintosh");
    expect(await s.download()).toBe(false);
    expect(mockIpc.appDownloadUpdate).not.toHaveBeenCalled();
    vi.spyOn(navigator, "userAgent", "get").mockReturnValue("Windows NT 10.0");
    s.info!.latest = null;
    expect(await s.download()).toBe(false);
  });
});

describe("update store (A7)", () => {
  it("check: available -> available state with info", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue({
      current: "0.1.0", latest: "0.2.0", updateAvailable: true,
      setupUrl: "s", sha256Url: "h", releaseUrl: "r", note: "",
    });
    const s = useUpdateStore();
    const info = await s.check();
    expect(info?.updateAvailable).toBe(true);
    expect(s.status).toBe("available");
  });

  it("check: up to date -> none state", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue({
      current: "0.1.0", latest: "0.1.0", updateAvailable: false,
      cliCurrent: "0.1.10.dev0", cliLatest: "0.1.10.dev0",
      setupUrl: null, sha256Url: null, releaseUrl: null, note: "",
    });
    const s = useUpdateStore();
    await s.check();
    expect(s.status).toBe("none");
  });

  it("check failure -> error surfaced, back to idle", async () => {
    mockIpc.appCheckUpdate.mockRejectedValue({ message: "offline" });
    const s = useUpdateStore();
    const info = await s.check();
    expect(info).toBeNull();
    expect(s.error).toBe("offline");
    expect(s.status).toBe("idle");
  });

  it("download success -> ready with staged result", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue({
      current: "0.1.0", latest: "0.2.0", updateAvailable: true,
      setupUrl: "s", sha256Url: "h", releaseUrl: "r", note: "",
    });
    mockIpc.appDownloadUpdate.mockResolvedValue({
      path: "C:\\tmp\\setup.exe", sha256: "ab".repeat(32), size: 42,
    });
    const s = useUpdateStore();
    await s.check();
    const ok = await s.download();
    expect(ok).toBe(true);
    expect(s.status).toBe("ready");
    expect(s.staged?.size).toBe(42);
    expect(mockIpc.appDownloadUpdate).toHaveBeenCalledWith("s", "h", "0.2.0", expect.any(String));
  });

  it("download failure -> back to available (retryable)", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue({
      current: "0.1.0", latest: "0.2.0", updateAvailable: true,
      setupUrl: "s", sha256Url: "h", releaseUrl: "r", note: "",
    });
    mockIpc.appDownloadUpdate.mockRejectedValue({ message: "sha256 mismatch" });
    const s = useUpdateStore();
    await s.check();
    const ok = await s.download();
    expect(ok).toBe(false);
    expect(s.status).toBe("available");
    expect(s.error).toContain("sha256");
  });

  it("install calls the ipc with the staged path", async () => {
    mockIpc.appCheckUpdate.mockResolvedValue({
      current: "0.1.0", latest: "0.2.0", updateAvailable: true,
      setupUrl: "s", sha256Url: "h", releaseUrl: "r", note: "",
    });
    mockIpc.appDownloadUpdate.mockResolvedValue({
      path: "C:\\tmp\\setup.exe", sha256: "ab".repeat(32), size: 42,
    });
    mockIpc.appInstallUpdate.mockResolvedValue(undefined);
    const s = useUpdateStore();
    await s.check();
    await s.download();
    await s.install();
    expect(mockIpc.appInstallUpdate).toHaveBeenCalledWith("C:\\tmp\\setup.exe");
  });
});
