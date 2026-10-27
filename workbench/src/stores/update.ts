/**
 * Workbench self-update: check -> available -> download -> ready.
 * Only a separately confirmed launch hands off to the installer. Rust owns
 * the Explorer/installer launch and app exit; failures leave this store ready.
 */
import { defineStore } from "pinia";
import { onScopeDispose, ref } from "vue";
import { listen } from "@tauri-apps/api/event";
import {
  appCheckUpdate,
  appDownloadUpdate,
  appInstallUpdate,
  type UpdateDownloadResult,
  type UpdateInfo,
} from "../lib/ipc";

interface InstallationTarget {
  readonly generation: number;
  readonly target: string;
  readonly artifact: string;
  readonly path: string;
}

export const useUpdateStore = defineStore("workbench-update", () => {
  const status = ref<"idle" | "checking" | "none" | "available" | "downloading" | "ready">("idle");
  const info = ref<UpdateInfo | null>(null);
  const error = ref<string | null>(null);
  const downloaded = ref(0);
  const total = ref(0);
  const staged = ref<UpdateDownloadResult | null>(null);
  const launchPending = ref(false);
  let generation = 0;
  let downloadRunning = false;
  let stopProgress: (() => void) | null = null;
  let stagedTarget: string | null = null;

  const supportsInstaller = () => typeof navigator !== "undefined" && /Windows/i.test(navigator.userAgent);
  const message = (e: unknown) => {
    const error = e as { message?: string; technical_detail?: string | null };
    // The update backend redacts diagnostic text before crossing IPC.
    return error?.technical_detail?.trim() || error?.message || String(e);
  };
  const targetKey = () => JSON.stringify([info.value?.latest, info.value?.setupUrl, info.value?.sha256Url]);
  const artifactKey = () => JSON.stringify([staged.value?.path, staged.value?.sha256, staged.value?.size]);

  function clearProgress() {
    stopProgress?.();
    stopProgress = null;
    downloaded.value = 0;
    total.value = 0;
  }

  function invalidate() {
    generation++;
    staged.value = null;
    stagedTarget = null;
    clearProgress();
    error.value = null;
    return generation;
  }

  onScopeDispose(invalidate);

  async function check(): Promise<UpdateInfo | null> {
    if (launchPending.value) return null;
    const token = invalidate();
    status.value = "checking";
    info.value = null;
    try {
      const result = await appCheckUpdate();
      if (token !== generation) return null;
      info.value = result;
      // A note-bearing result can indicate failure instead of a rejected IPC.
      // A partial CLI check may still offer a Workbench target, but neither a
      // warning nor an unknown version proves the installation is up to date.
      if (result.note?.trim()) error.value = result.note;
      const versionsKnown = [result.current, result.latest, result.cliCurrent, result.cliLatest]
        .every(version => typeof version === "string" && version.trim().length > 0);
      if (!result.updateAvailable && (error.value || !versionsKnown)) {
        error.value ||= "Update version is unknown.";
        status.value = "idle";
        return null;
      }
      status.value = result.updateAvailable ? "available" : "none";
      return result;
    } catch (e) {
      if (token !== generation) return null;
      error.value = message(e);
      status.value = "idle";
      return null;
    }
  }

  async function download(): Promise<boolean> {
    if (!supportsInstaller() || launchPending.value || downloadRunning || status.value !== "available"
      || !info.value?.latest || !info.value?.setupUrl || !info.value?.sha256Url) return false;
    const { setupUrl, sha256Url, latest } = info.value;
    const target = targetKey();
    const token = invalidate();
    const requestId = crypto.randomUUID();
    downloadRunning = true;
    status.value = "downloading";
    const isCurrent = () => token === generation && targetKey() === target;
    let stop: (() => void) | null = null;
    let stopCalled = false;
    const detach = () => {
      if (stop && !stopCalled) {
        stopCalled = true;
        stop();
      }
      if (stopProgress === detach) stopProgress = null;
    };
    try {
      stop = await listen<{ downloaded: number; total: number; requestId: string }>("update://progress", (event) => {
        if (!isCurrent() || status.value !== "downloading" || event.payload.requestId !== requestId) return;
        downloaded.value = event.payload.downloaded;
        total.value = event.payload.total;
      });
      if (!isCurrent()) return false;
      stopProgress = detach;
      const result = await appDownloadUpdate(setupUrl, sha256Url, latest, requestId);
      if (!isCurrent()) return false;
      staged.value = result;
      stagedTarget = target;
      status.value = "ready";
      return true;
    } catch (e) {
      if (!isCurrent()) return false;
      error.value = message(e);
      status.value = "available";
      return false;
    } finally {
      detach();
      if (token === generation) {
        downloaded.value = 0;
        total.value = 0;
      }
      downloadRunning = false;
    }
  }

  /** Capture before opening a dialog, including this download's generation. */
  function captureInstallation(): InstallationTarget | null {
    if (!supportsInstaller() || launchPending.value || status.value !== "ready" || !staged.value
      || stagedTarget !== targetKey()) return null;
    return Object.freeze({ generation, target: targetKey(), artifact: artifactKey(), path: staged.value.path });
  }

  /** UI confirms first and passes the exact captured target. No installing state. */
  async function install(expected: InstallationTarget | null = captureInstallation()): Promise<void> {
    const current = captureInstallation();
    if (!expected || !current || expected.generation !== current.generation || expected.target !== current.target
      || expected.artifact !== current.artifact || expected.path !== current.path) return;
    launchPending.value = true;
    error.value = null;
    clearProgress();
    try {
      await appInstallUpdate(expected.path);
    } catch (e) {
      error.value = message(e);
    } finally {
      launchPending.value = false;
    }
  }

  return { status, info, error, downloaded, total, staged, launchPending, supportsInstaller, captureInstallation, check, download, install };
});
