import { computed, ref, watch } from "vue";
import { defineStore } from "pinia";
import * as ipc from "../lib/ipc";
import type { ExtensionModuleDefinition, ExtensionModuleMember } from "../lib/ipc";
import { useExtensionsStore } from "./extensions";
import { useSettingsStore } from "./settings";

export interface ModuleOperationRow {
  member: ExtensionModuleMember;
  key: string;
  action: "install" | "remove" | "retain" | "release" | "blocked";
  reason: string;
  status: "planned" | "pending" | "installed" | "removed" | "retained" | "absent" | "auth_required" | "failed" | "unknown" | "blocked";
  auth_required: boolean;
}
export interface ModuleOperationPlan {
  plan_id: string;
  module_id: string;
  module_name: string;
  runtime_id: string;
  action: "apply" | "uninstall";
  rows: ModuleOperationRow[];
}
type Phase = "idle" | "preparing" | "prepared" | "running" | "complete" | "partial" | "stopped" | "history";

export const useModuleOperationsStore = defineStore("moduleOperations", () => {
  const extensions = useExtensionsStore();
  const settings = useSettingsStore();
  const plan = ref<ModuleOperationPlan | null>(null);
  const phase = ref<Phase>("idle");
  const error = ref("");
  const cancelRequested = ref(false);
  const completed = ref(0);
  const ownerKey = ref("");
  let generation = 0;
  let definition: ExtensionModuleDefinition | null = null;
  let owner: { workspace: string; runtimeId: string } | null = null;
  const contextKey = computed(() => {
    const context = extensions.context;
    return context ? JSON.stringify([settings.target?.kind ?? "local", settings.target?.machine?.name ?? "", context.workspace, context.runtimeId]) : "";
  });
  const busy = computed(() => phase.value === "preparing" || phase.value === "running");
  const canPrepare = computed(() => !!contextKey.value && !busy.value && !Object.values(extensions.busyByKind ?? {}).some(Boolean));
  const targetChanged = computed(() => !!ownerKey.value && ownerKey.value !== contextKey.value);
  const message = (e: unknown) => {
    const err = e as { technical_detail?: string; message?: string };
    return err.technical_detail || err.message || String(e);
  };
  watch(contextKey, () => {
    if (phase.value === "running") cancelRequested.value = true;
    else { ++generation; plan.value = null; phase.value = "idle"; error.value = ""; }
  });
  async function prepare(module: ExtensionModuleDefinition, action: "apply" | "uninstall") {
    if (!canPrepare.value || !extensions.context) return;
    const current = ++generation;
    owner = { ...extensions.context }; ownerKey.value = contextKey.value;
    definition = JSON.parse(JSON.stringify(module));
    phase.value = "preparing"; error.value = ""; plan.value = null; completed.value = 0;
    try {
      const result = await ipc.extensionsCall({ ...owner, op: "module-plan", config: JSON.stringify({ definition, action }) });
      if (current !== generation || targetChanged.value) return;
      plan.value = result as unknown as ModuleOperationPlan;
      phase.value = "prepared";
    } catch (e) {
      if (current === generation) { error.value = message(e); phase.value = "idle"; }
    }
  }
  async function run() {
    if (phase.value !== "prepared" || !plan.value || !owner || targetChanged.value
      || Object.values(extensions.busyByKind ?? {}).some(Boolean)) return;
    const active = plan.value;
    const context = { ...owner };
    // Context reset replaces this record. Release only the record we reserved,
    // never a busy flag belonging to operations in the newly selected target.
    const reservedBusy = extensions.busyByKind;
    phase.value = "running"; error.value = ""; cancelRequested.value = false;
    for (const kind of ["skills", "mcp", "plugins"] as const) reservedBusy[kind] = true;
    try {
      for (let index = 0; index < active.rows.length; index++) {
        if (cancelRequested.value || targetChanged.value) break;
        const row = await ipc.extensionsCall({ ...context, op: "module-step", config: JSON.stringify({ plan_id: active.plan_id, index }) });
        active.rows[index] = row as unknown as ModuleOperationRow;
        completed.value = index + 1;
      }
      phase.value = cancelRequested.value || targetChanged.value ? "stopped"
        : active.rows.some(r => ["failed", "unknown", "blocked", "pending"].includes(r.status) || r.reason === "source_unknown") ? "partial" : "complete";
    } catch (e) {
      error.value = message(e); phase.value = "partial";
      // A transport failure can leave this member running in the container.
      // The next prepare will inspect the durable marker before any retry.
      if (active.rows[completed.value]) active.rows[completed.value]!.status = "unknown";
    } finally {
      for (const kind of ["skills", "mcp", "plugins"] as const) reservedBusy[kind] = false;
      if (!targetChanged.value) {
        try { await extensions.load(); } catch { /* operation evidence stays visible */ }
      }
    }
  }
  async function retry() {
    if (definition && plan.value) await prepare(definition, plan.value.action);
  }
  function cancel() { if (phase.value === "running") cancelRequested.value = true; }
  async function history(module: ExtensionModuleDefinition) {
    if (!canPrepare.value || !extensions.context) return;
    const current = ++generation;
    owner = { ...extensions.context }; ownerKey.value = contextKey.value;
    definition = JSON.parse(JSON.stringify(module));
    error.value = ""; phase.value = "preparing"; plan.value = null;
    try {
      const result = await ipc.extensionsCall({ ...owner, op: "module-status", config: JSON.stringify({ module_id: module.id }) });
      if (current !== generation || targetChanged.value) return;
      plan.value = result.latest as ModuleOperationPlan | null;
      phase.value = "history";
    } catch (e) { if (current === generation) { error.value = message(e); phase.value = "idle"; } }
  }
  return { plan, phase, error, busy, canPrepare, targetChanged, cancelRequested, completed, prepare, run, retry, cancel, history };
});
