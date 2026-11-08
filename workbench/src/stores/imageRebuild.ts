import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { Channel } from "@tauri-apps/api/core";
import type { BuildEvent, BuildProgressData, BuildStatus, WorkbenchError } from "../types";
import * as ipc from "../lib/ipc";
import { useSettingsStore } from "./settings";
import { i18n } from "../i18n";

export const useImageRebuildStore = defineStore("imageRebuild", () => {
  const settings = useSettingsStore();
  const visible = ref(false);
  const references = ref<string[]>([]);
  const selected = ref("");
  const noCache = ref(true);
  const checking = ref(false);
  const check = ref<ipc.ImageRebuildCheck | null>(null);
  const error = ref<string | null>(null);
  const buildStatus = ref<BuildStatus>("idle");
  const buildTag = ref("");
  const buildLog = ref("");
  const buildLogPath = ref<string | null>(null);
  const buildProgress = ref<BuildProgressData | null>(null);
  const buildStartedAt = ref<number | null>(null);
  const buildDurationMs = ref<number | null>(null);
  const buildWarnings = ref<string[]>([]);
  const buildError = ref<WorkbenchError | null>(null);
  const result = ref<{new_image_id: string; old_image_action: string} | null>(null);
  const dockerStarting = ref(false);
  let epoch = 0;
  let taskId = "";
  let cancelRequested = false;
  let expected: string | undefined;
  const targetSnapshot = ref("");
  let refreshOrigin: (() => Promise<void>) | undefined;
  const targetKey = () => `${settings.target?.kind ?? "local"}:${settings.target?.machine?.name ?? ""}`;
  const targetChanged = computed(() => visible.value && targetSnapshot.value !== targetKey());
  const remote = computed(() => settings.target?.kind === "remote");
  const busy = computed(() => checking.value || buildStatus.value === "building");
  const canStart = computed(() => !!check.value && !busy.value && !targetChanged.value
    && !remote.value && check.value.running_containers.length === 0);
  const message = (e: unknown) => {
    const err = e as WorkbenchError;
    return err.technical_detail || err.message || String(e);
  };

  async function refresh() {
    if (buildStatus.value === "building") return;
    const current = ++epoch;
    checking.value = true; check.value = null; error.value = null;
    try {
      if (remote.value || targetChanged.value) throw new Error(i18n.global.t("imageRebuild.localOnly"));
      const state = await ipc.checkImageRebuild(selected.value, expected);
      if (current !== epoch || targetChanged.value) return;
      check.value = state;
    } catch (e) {
      if (current === epoch) error.value = message(e);
    } finally {
      if (current === epoch) checking.value = false;
    }
  }

  async function open(refs: string[], expectedId?: string, onRefresh?: () => Promise<void>) {
    if (busy.value) return;
    references.value = [...new Set(refs)]; selected.value = refs[0] ?? "";
    expected = expectedId; refreshOrigin = onRefresh; targetSnapshot.value = targetKey();
    noCache.value = true; visible.value = true; buildStatus.value = "idle";
    buildError.value = null; result.value = null;
    await refresh();
  }

  async function startBuild(_tag?: string) {
    if (buildStatus.value === "building" || checking.value) return;
    if (buildStatus.value !== "idle") {
      buildStatus.value = "idle"; expected = undefined;
      await refresh(); return;
    }
    if (!canStart.value || !check.value) return;
    const snapshot = check.value;
    const current = ++epoch;
    const operationId = crypto.randomUUID(); taskId = operationId;
    cancelRequested = false;
    buildStatus.value = "building"; buildTag.value = snapshot.tag;
    buildLog.value = ""; buildLogPath.value = null; buildProgress.value = null;
    buildWarnings.value = []; buildError.value = null; result.value = null;
    buildStartedAt.value = Date.now(); buildDurationMs.value = null;
    const channel = new Channel<BuildEvent>();
    channel.onmessage = event => {
      if (current !== epoch) return;
      if (event.type === "build.output" && typeof event.data?.chunk === "string")
        buildLog.value = (buildLog.value + event.data.chunk).slice(-100_000);
      if (event.type === "build.start" && typeof event.data?.log_path === "string") buildLogPath.value = event.data.log_path;
      // A very early cancellation can arrive before Rust has registered the
      // task. Once start is observed, retry that same task's cancellation.
      if (event.type === "build.start" && cancelRequested) void cancelBuild();
      if (event.type === "build.progress") buildProgress.value = event.data as unknown as BuildProgressData;
      if (event.type === "build.warning" && typeof event.data?.message === "string") buildWarnings.value.push(event.data.message);
      if ((event.type === "build.result" || event.type === "build.complete") && typeof event.data?.new_image_id === "string")
        result.value = event.data as unknown as {new_image_id: string; old_image_action: string};
    };
    try {
      await ipc.rebuildImage(snapshot.tag, snapshot.image_id, noCache.value, operationId, channel);
      if (current !== epoch) return;
      buildStatus.value = "complete";
    } catch (e) {
      if (current !== epoch) return;
      buildError.value = e as WorkbenchError;
      buildStatus.value = buildError.value.code === "WB_ERR_CLI_CANCELLED" ? "cancelled" : "failed";
    } finally {
      if (current === epoch) {
        buildDurationMs.value = Date.now() - (buildStartedAt.value ?? Date.now());
        // Refresh only the originating target, including failure/cancel where
        // a last-moment publication may already have completed.
        if (!targetChanged.value) {
          try { await refreshOrigin?.(); } catch (e) { buildWarnings.value.push(message(e)); }
        }
      }
    }
  }
  async function cancelBuild() {
    if (buildStatus.value !== "building") return;
    cancelRequested = true;
    try {
      if (!await ipc.cancelBuild(`rebuild:${taskId}`)) buildWarnings.value.push(i18n.global.t("imageRebuild.cancelMissed"));
    } catch (e) { buildWarnings.value.push(message(e)); }
  }
  function close() {
    if (buildStatus.value === "building") return;
    ++epoch; visible.value = false; checking.value = false;
  }
  async function revealBuildLog() { if (buildLogPath.value) await ipc.workspaceRevealDataFile(buildLogPath.value); }
  async function startDockerAndRepreflight() {
    dockerStarting.value = true;
    try { await ipc.startDocker(); buildStatus.value = "idle"; await refresh(); }
    finally { dockerStarting.value = false; }
  }
  return { visible, references, selected, noCache, checking, check, error, busy, canStart, targetChanged,
    buildStatus, buildTag, buildLog, buildLogPath, buildProgress, buildStartedAt, buildDurationMs,
    buildWarnings, buildError, dockerStarting, result, open, refresh, startBuild, cancelBuild,
    close, backToSummaryFromBuild: close, revealBuildLog, startDockerAndRepreflight };
});
