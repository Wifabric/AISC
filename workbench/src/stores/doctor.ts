/**
 * One-click diagnosis store (G-13, Step 12; 02 §五 F-4, A-G13-3).
 *
 * Standalone: opening/closing the diagnosis never touches the runtime/settings
 * stores (A-G13-3 "返回/关闭诊断不改变 startup state"). All entry points
 * (blocked / error / ready sidebar) drive the SAME `run_doctor` command through
 * `run()`, which is guarded so an in-flight run cannot be started twice.
 */
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as ipc from "../lib/ipc";
import type { DoctorReport, LogEvent, OpTrace, WorkbenchError } from "../types";

export type DoctorRunState = "idle" | "running" | "done" | "error";

export const useDoctorStore = defineStore("doctor", () => {
  /** Dialog visibility (owned here so blocked/error/ready views share it). */
  const open = ref(false);
  const status = ref<DoctorRunState>("idle");
  const report = ref<DoctorReport | null>(null);
  const error = ref<WorkbenchError | null>(null);
  /** Stage 6 (REL-01): recent operation traces (Doctor dialog dev layer). */
  const traces = ref<OpTrace[]>([]);
  /** lifecycle-logging (P3): recent tail of the shared JSONL timeline. */
  const logs = ref<LogEvent[]>([]);
  const updateHealth = ref<ipc.UpdateHealth | null>(null);
  let contextKey = "";
  let contextGeneration = 0;
  let runGeneration = 0;
  let healthGeneration = 0;

  const running = computed(() => status.value === "running");
  /** Non-zero failed checks / any warning - drives the summary styling. */
  const hasFailures = computed(() => (report.value?.summary.failures ?? 0) > 0);
  const hasWarnings = computed(() => (report.value?.summary.warnings ?? 0) > 0);

  function setContext(key: string): void {
    if (contextKey === key) return;
    contextKey = key;
    contextGeneration += 1;
    runGeneration += 1;
    healthGeneration += 1;
    updateHealth.value = null;
    report.value = null;
    error.value = null;
    status.value = "idle";
    if (open.value) {
      void run();
      void loadUpdateHealth();
    }
  }

  /** Run `aisc doctor --format json`. A-G13-3: never starts a second doctor
   * while one is in flight; repeated clicks are no-ops. */
  async function run(): Promise<void> {
    if (status.value === "running") return;
    const context = contextGeneration;
    const generation = ++runGeneration;
    status.value = "running";
    error.value = null;
    report.value = null;
    try {
      const result = await ipc.runDoctor();
      if (context !== contextGeneration || generation !== runGeneration) return;
      report.value = result;
      status.value = "done";
      void ipc.logUiEvent?.("doctor_run", "ok");
    } catch (e) {
      if (context !== contextGeneration || generation !== runGeneration) return;
      error.value = (e as WorkbenchError) ?? {
        code: "WB_ERR_UNKNOWN",
        message: String(e),
        technical_detail: null,
        retryable: true,
        action: "retry",
      };
      status.value = "error";
      void ipc.logUiEvent?.("doctor_run", "error", error.value?.code ?? undefined);
    }
  }

  /** Open the dialog and start a fresh diagnosis. */
  function openDialog(): void {
    open.value = true;
    void run();
  }

  /** Close the dialog. Does not alter startup state (A-G13-3). */
  function closeDialog(): void {
    open.value = false;
    runGeneration += 1;
    healthGeneration += 1;
    updateHealth.value = null;
    if (status.value === "running") status.value = "idle";
  }

  /** Stage 6 (REL-01): refresh the recent-operation trace ring. */
  async function loadTraces(): Promise<void> {
    traces.value = await ipc.opTraces().catch(() => []);
  }

  /** lifecycle-logging (P3): refresh the recent log tail (100 events). */
  async function loadLogs(): Promise<void> {
    logs.value = await ipc.logsTail(100).then((r) => r.lines).catch(() => []);
  }

  async function loadUpdateHealth(): Promise<void> {
    const context = contextGeneration;
    const generation = ++healthGeneration;
    const current = () => context === contextGeneration && generation === healthGeneration;
    updateHealth.value = null;
    try {
      const snapshot = await ipc.appUpdateHealth();
      if (current()) updateHealth.value = snapshot;
    } catch { if (current()) updateHealth.value = null; }
  }

  /** Stage 6 (REL-01): export the redacted diagnostic bundle to `path`.
   *  Returns the final path (null on failure); the UI builds the message. */
  async function exportDiagnostic(path: string): Promise<string | null> {
    try {
      const bundle = await ipc.diagnosticBundle(path);
      void ipc.logUiEvent?.("export_diagnostics", "ok");
      return bundle.path;
    } catch (e) {
      void ipc.logUiEvent?.("export_diagnostics", "error",
        (e as WorkbenchError)?.code ?? undefined);
      return null;
    }
  }

  return {
    open,
    updateHealth,
    status,
    report,
    error,
    traces,
    logs,
    running,
    hasFailures,
    hasWarnings,
    run,
    setContext,
    openDialog,
    closeDialog,
    loadTraces,
    loadLogs,
    loadUpdateHealth,
    exportDiagnostic,
  };
});
