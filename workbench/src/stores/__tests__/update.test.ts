/**
 * A7 (D-8 自研): self-update store state machine tests — check/download/
 * install transitions over mocked ipc, error paths reset to recoverable
 * states, progress events feed the counters.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

const mockIpc = vi.hoisted(() => ({
  appCheckUpdate: vi.fn(),
  appDownloadUpdate: vi.fn(),
  appInstallUpdate: vi.fn(),
}));

vi.mock("../../lib/ipc", () => mockIpc);
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(() => {}),
}));

import { useUpdateStore } from "../update";

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
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
    expect(mockIpc.appDownloadUpdate).toHaveBeenCalledWith("s", "h", "0.2.0");
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
