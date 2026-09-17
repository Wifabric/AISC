/**
 * A7 (0.1.0, D-8 自研): Workbench self-update state machine.
 *
 * idle -> checking -> (none | available) -> downloading -> ready ->
 * installing (app exits; the NSIS installer owns everything from there).
 * The sidecar CLI updates separately via `aisc update` (no app restart —
 * the serve pool evicts on exe mtime), which the about card points out.
 */
import { defineStore } from "pinia";
import { ref } from "vue";
import { listen } from "@tauri-apps/api/event";
import {
  appCheckUpdate,
  appDownloadUpdate,
  appInstallUpdate,
  type UpdateDownloadResult,
  type UpdateInfo,
} from "../lib/ipc";

export const useUpdateStore = defineStore("workbench-update", () => {
  const status = ref<"idle" | "checking" | "none" | "available" | "downloading" | "ready">("idle");
  const info = ref<UpdateInfo | null>(null);
  const error = ref<string | null>(null);
  const downloaded = ref(0);
  const total = ref(0);
  const staged = ref<UpdateDownloadResult | null>(null);
  let unlisten: Promise<(() => void) | null> | null = null;

  async function ensureProgressListener(): Promise<void> {
    if (unlisten) return;
    unlisten = listen<{ downloaded: number; total: number }>("update://progress", (e) => {
      downloaded.value = e.payload.downloaded;
      total.value = e.payload.total;
    }).then((fn) => fn).catch(() => null);
  }

  async function check(): Promise<UpdateInfo | null> {
    status.value = "checking";
    error.value = null;
    try {
      info.value = await appCheckUpdate();
      status.value = info.value.updateAvailable ? "available" : "none";
      return info.value;
    } catch (e) {
      error.value = (e as { message?: string })?.message ?? String(e);
      status.value = "idle";
      return null;
    }
  }

  async function download(): Promise<boolean> {
    if (!info.value?.setupUrl || !info.value?.sha256Url) return false;
    status.value = "downloading";
    downloaded.value = 0;
    total.value = 0;
    error.value = null;
    await ensureProgressListener();
    try {
      staged.value = await appDownloadUpdate(info.value.setupUrl, info.value.sha256Url);
      status.value = "ready";
      return true;
    } catch (e) {
      error.value = (e as { message?: string })?.message ?? String(e);
      status.value = "available"; // back to the download button
      return false;
    }
  }

  /** The UI layer collects the confirmation BEFORE calling this. */
  async function install(): Promise<void> {
    if (!staged.value) return;
    status.value = "installing" as never; // app exits right after
    try {
      await appInstallUpdate(staged.value.path);
    } catch (e) {
      error.value = (e as { message?: string })?.message ?? String(e);
      status.value = "ready";
    }
  }

  return { status, info, error, downloaded, total, staged, check, download, install };
});
