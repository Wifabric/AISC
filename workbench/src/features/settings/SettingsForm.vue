<script setup lang="ts">
/**
 * Shared settings form (Step 3 / G-01; IDEA-1 S2; IDEA-3 3d: tab-only — the
 * pre-runtime modal dialog is retired, Settings is a workspace-layer tab).
 *
 * Load/save/reset against the typed settings backend, per-field errors and
 * effective-scope markers (02 §三.4 table). Defaults and bounds live in Rust -
 * this view renders whatever `load_settings` returns. Chrome belongs to the
 * parent; the status strip (dirty/saved) renders here because the pane has no
 * header of its own.
 */
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { confirm } from "@tauri-apps/plugin-dialog";
import { useSettingsStore } from "../../stores/settings";
import { useUpdateStore } from "../../stores/update";
import { buildSearchMatcher } from "../../lib/search";
import type { TerminalSettings, UiSettings, WindowSettings } from "../../types";

const { t } = useI18n();
const store = useSettingsStore();
const update = useUpdateStore();
const emit = defineEmits<{ close: [] }>();

type EffectKind = "immediate" | "rebuild" | "restart";
interface FieldDef {
  key: string;
  labelKey: string;
  control: "select" | "number" | "text" | "checkbox" | "range";
  options?: { value: string; labelKey: string }[];
  /** Range slider bounds (control: "range"). Values match the Rust schema. */
  min?: number;
  max?: number;
  step?: number;
  effect: EffectKind;
  helpKey?: string;
}

const FIELDS: FieldDef[] = [
  { key: "ui.language", labelKey: "settings.ui.language", control: "select", options: [
    { value: "auto", labelKey: "settings.ui.language.auto" },
    { value: "zh-CN", labelKey: "settings.ui.language.zh" },
    { value: "en-US", labelKey: "settings.ui.language.en" },
  ], effect: "immediate" },
  { key: "ui.font_scale", labelKey: "settings.ui.fontScale", control: "range", min: 0.8, max: 1.5, step: 0.05, effect: "immediate" },
  { key: "ui.theme", labelKey: "settings.ui.theme", control: "select", options: [
    { value: "system", labelKey: "settings.ui.theme.system" },
    { value: "dark", labelKey: "settings.ui.theme.dark" },
    { value: "light", labelKey: "settings.ui.theme.light" },
  ], effect: "immediate" },
  { key: "ui.default_tab_agent", labelKey: "settings.ui.defaultTab", control: "select", options: [
    { value: "claude", labelKey: "tabbar.menu.claude" },
    { value: "codex", labelKey: "tabbar.menu.codex" },
    { value: "bash", labelKey: "tabbar.menu.bash" },
    { value: "cc-switch", labelKey: "tabbar.ccSwitchUi" },
  ], effect: "immediate", helpKey: "settings.ui.defaultTab.help" },
  { key: "ui.explorer_ignore", labelKey: "settings.ui.explorerIgnore", control: "text",
    effect: "immediate", helpKey: "settings.ui.explorerIgnore.help" },
  { key: "terminal.font_family", labelKey: "settings.term.fontFamily", control: "text",
    effect: "rebuild", helpKey: "settings.term.fontFamily.help" },
  { key: "terminal.font_size", labelKey: "settings.term.fontSize", control: "range", min: 10, max: 24, step: 1, effect: "immediate" },
  { key: "terminal.line_height", labelKey: "settings.term.lineHeight", control: "range", min: 1.0, max: 1.6, step: 0.05, effect: "immediate" },
  { key: "terminal.letter_spacing", labelKey: "settings.term.letterSpacing", control: "range", min: -1, max: 3, step: 1, effect: "immediate" },
  { key: "terminal.scrollback", labelKey: "settings.term.scrollback", control: "range", min: 1000, max: 50000, step: 1000, effect: "immediate" },
  { key: "terminal.renderer", labelKey: "settings.term.renderer", control: "select", options: [
    { value: "auto", labelKey: "settings.term.renderer.auto" },
    { value: "default", labelKey: "settings.term.renderer.default" },
    { value: "webgl", labelKey: "settings.term.renderer.webgl" },
  ], effect: "rebuild" },
  { key: "terminal.smooth_scroll_duration", labelKey: "settings.term.smoothScroll", control: "range", min: 0, max: 500, step: 10, effect: "immediate" },
  { key: "window.remember_geometry", labelKey: "settings.window.rememberGeometry", control: "checkbox", effect: "restart" },
  { key: "window.close_behavior", labelKey: "settings.window.closeBehavior", control: "select", options: [
    { value: "quit", labelKey: "settings.window.closeBehavior.quit" },
    { value: "minimize-to-tray", labelKey: "settings.window.closeBehavior.tray" },
  ], effect: "immediate" },
];

const EFFECT_KEY: Record<EffectKind, string> = {
  immediate: "settings.effect.immediate",
  rebuild: "settings.effect.rebuild",
  restart: "settings.effect.restart",
};

// Manual-test fix #1 (2026-09-06): P8 added 'performance' to the section
// list but not to GROUP_KEY — t(undefined) threw SyntaxError mid-render,
// breaking the App patch (settings chip switched, content stuck on the
// workspace, UI dead until restart). The Record<Group,...> typing below
// makes a future missing entry a COMPILE error, and the heading falls back
// to the raw group id instead of undefined.
const GROUPS = ["ui", "terminal", "window", "hostTools", "machines", "performance", "disk", "about"] as const;
type SettingsGroup = (typeof GROUPS)[number];
const GROUP_KEY: Record<SettingsGroup, string> = {
  ui: "settings.group.ui",
  terminal: "settings.group.terminal",
  window: "settings.group.window",
  hostTools: "settings.group.hostTools",
  machines: "settings.group.machines",
  performance: "settings.group.performance",
  disk: "settings.group.disk",
  about: "settings.group.about",
};

// --- P2-5 (手测裁决: VS Code 式左导航右内容 + 搜索) ---
/** The active nav section (no query = the pane shows exactly this one). */
const activeGroup = ref<SettingsGroup>("ui");
/** Search query — matches a group when its heading or any of its FIELDS'
 * labels match (shared matcher: substring > subsequence > /regex/). The
 * hand-rolled custom sections (hostTools/machines/performance/disk) match
 * on their heading only — their rows aren't FIELDS-driven. */
const query = ref("");
const queryText = computed(() => query.value.trim().toLowerCase());
function groupMatches(group: SettingsGroup): boolean {
  const q = queryText.value;
  if (!q) return true;
  const matcher = buildSearchMatcher(q);
  if (matcher === null) return true;
  const hay = [
    t(GROUP_KEY[group] ?? group),
    ...FIELDS.filter((f) => f.key.startsWith(`${group}.`)).map((f) => t(f.labelKey)),
  ].join(" ").toLowerCase();
  return matcher(hay) > 0;
}
const searching = computed(() => queryText.value.length > 0);
const visibleGroups = computed<SettingsGroup[]>(() => {
  if (!searching.value) return [activeGroup.value];
  return GROUPS.filter(groupMatches);
});
function pickGroup(group: SettingsGroup): void {
  activeGroup.value = group;
  query.value = ""; // picking a nav entry always leaves search mode
}

// Explicit non-null section models (rendered only under `v-if="store.doc"`);
// the `?? {}` casts never render - defaults come from the backend.
const ui = computed<UiSettings>(() => store.doc?.ui ?? ({} as UiSettings));
const terminal = computed<TerminalSettings>(() => store.doc?.terminal ?? ({} as TerminalSettings));
const windowS = computed<WindowSettings>(() => store.doc?.window ?? ({} as WindowSettings));
/** F2: the host-tools whitelist working copy (mutated in place; rows with an
 * empty name/program are dropped server-side by the sanitizer). */
const hostTools = ref<import("../../types").HostToolEntry[]>(
  (store.doc?.hostTools ?? []).map((e) => ({ readOnlyPreset: "", ...e })));
/** Reload the working copy whenever the backend doc is re-applied (load,
 * cancel, reset). */
watch(
  () => store.doc,
  (d) => {
    hostTools.value = (d?.hostTools ?? []).map((e) => ({ readOnlyPreset: "", ...e }));
  },
);
/** Edit -> doc sync (dirty + save both read the doc; empty rows are
 * filtered here, the Rust sanitizer is the second gate). */
watch(hostTools, (rows) => {
  if (!store.doc) return;
  store.doc.hostTools = rows
    .filter((r) => r.name.trim() && r.program.trim())
    .map((r) => ({
      name: r.name,
      program: r.program,
      ...(r.readOnlyPreset ? { readOnlyPreset: r.readOnlyPreset } : {}),
    }));
}, { deep: true });

/** R4b: remote machine profiles working copy — same flow as hostTools. */
const machines = ref<import("../../types").RemoteMachine[]>(
  (store.doc?.remoteMachines ?? []).map((m) => ({ ...m })));
watch(
  () => store.doc,
  (d) => {
    machines.value = (d?.remoteMachines ?? []).map((m) => ({ ...m }));
  },
);
watch(machines, (rows) => {
  if (!store.doc) return;
  store.doc.remoteMachines = rows
    .filter((r) => r.name.trim() && r.host.trim())
    .map((r) => ({
      name: r.name,
      host: r.host,
      user: r.user || undefined,
      port: r.port || undefined,
      keyPath: r.keyPath || undefined,
    }));
}, { deep: true });

/** Explorer ignore names as a comma-separated string for the text input. */
const explorerIgnoreText = computed<string>({
  get: () => (ui.value.explorer_ignore ?? []).join(", "),
  set: (v: string) => {
    ui.value.explorer_ignore = v
      .split(/[,，]/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  },
});

const issuesByField = computed(() => {
  const m: Record<string, string> = {};
  for (const i of store.doc?.issues ?? []) m[i.field] = i.reason;
  return m;
});

const saving = computed(() => store.saveState === "saving");
const savedFlash = ref(false);

// --- v2.1.13 remote CLI pairing (soft hint; hard gate unchanged) ---
const upgradeCmd = "pip install -U aisc-cli";
function onCheckVersion(name: string): void {
  void store.checkRemoteCliVersion(name);
}
async function onCopyUpgradeCmd(): Promise<void> {
  try {
    await navigator.clipboard.writeText(upgradeCmd);
  } catch {
    /* clipboard denied — the command text is visible next to the button */
  }
}

// --- v2.1.13 (docker-scan-fidelity): per-item inspection presentation ---
function formatBytes(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  const units = ["B", "kB", "MB", "GB", "TB"];
  let v = n;
  let u = 0;
  while (v >= 1000 && u < units.length - 1) {
    v /= 1000;
    u += 1;
  }
  return `${v >= 100 ? Math.round(v) : v.toFixed(1)} ${units[u]}`;
}
/** v2.1.13 D-9b: category order is PINNED (the Rust side returns a HashMap
 *  whose iteration order reshuffled on every scan - hand-test #3). */
const INSPECT_ORDER = ['images', 'containers', 'volumes', 'build_cache', 'networks'] as const;
const INSPECT_PREVIEW = 30;
const inspectShowAll = ref(new Set<string>());
const orderedInspect = computed(() => {
  const cats = store.inspectReport?.categories ?? {};
  return INSPECT_ORDER.filter((k) => cats[k]).map((k) => [k, cats[k]] as const);
});
function sortedInspectRows(key: string, rows: import("../../lib/ipc").CacheInspectRow[]) {
  const size = (r: import("../../lib/ipc").CacheInspectRow) =>
    r.reclaimable_bytes ?? r.size_bytes ?? 0;
  const sorted = [...rows].sort((a, b) => size(b) - size(a));
  if (inspectShowAll.value.has(key)) return sorted;
  return sorted.slice(0, INSPECT_PREVIEW);
}
function inspectDisplayName(row: import("../../lib/ipc").CacheInspectRow): string {
  if (row.name && row.name !== row.id) return row.name;
  const kind = row.kind ? row.kind + " \u00b7 " : "";
  return kind + String(row.id).slice(0, 12);
}
const inspectTotals = computed(() => {
  const cats = store.inspectReport?.categories ?? {};
  let reclaimable = 0;
  let items = 0;
  for (const cat of Object.values(cats)) {
    reclaimable += cat?.summary.reclaimable_bytes ?? 0;
    items += cat?.summary.count ?? 0;
  }
  return { reclaimable, items };
});

/** PERF P8 (D-13): performance working copy (load/edit/save like hostTools;
 *  defaults mirror the Rust sanitizer). */
const perf = computed(() => store.doc?.performance);
const perfLowSpec = computed({
  get: () => perf.value?.lowSpec ?? false,
  set: (v: boolean) => {
    if (!store.doc) return;
    store.doc.performance = {
      lowSpec: v,
      containerMemory: perf.value?.containerMemory ?? "3g",
      containerCpus: perf.value?.containerCpus ?? 1.5,
    };
  },
});
const perfMemory = computed({
  get: () => perf.value?.containerMemory ?? "3g",
  set: (v: string) => {
    if (store.doc?.performance) store.doc.performance.containerMemory = v;
  },
});
const perfCpus = computed({
  get: () => perf.value?.containerCpus ?? 1.5,
  set: (v: number) => {
    if (store.doc?.performance) store.doc.performance.containerCpus = v;
  },
});
const lowSpecRamText = ref("");
const wslMsg = ref("");
async function onWslconfig() {
  const { confirm } = await import("@tauri-apps/plugin-dialog");
  const ok = await confirm(t("settings.perf.wslConfirm"));
  if (!ok) return;
  const { wslconfigMerge } = await import("../../lib/ipc");
  const changed = await wslconfigMerge(
    perfMemory.value || "3g",
    4,
    false, // auto mode: only ADD missing keys, never overwrite user values
  );
  wslMsg.value = changed
    ? t("settings.perf.wslWritten")
    : t("settings.perf.wslNoop");
}

onMounted(async () => {
  if (!store.loaded) await store.load();
  // O7 (D-11): fill the disk & cache card (read-only df summary).
  void store.loadCacheUsage();
  // P8: show the machine's RAM band (advisory only).
  try {
    const { lowSpecStatus } = await import("../../lib/ipc");
    const st = await lowSpecStatus();
    if (st.totalRam) {
      const gb = (st.totalRam / 1024 ** 3).toFixed(1);
      lowSpecRamText.value = st.lowSpec
        ? t("settings.perf.ramLow", { gb })
        : t("settings.perf.ramOk", { gb });
    }
  } catch {
    /* advisory only */
  }
});

async function onSave() {
  const outcome = await store.save();
  if (!outcome) return; // error banner shows the reason
  savedFlash.value = true;
  window.setTimeout(() => (savedFlash.value = false), 2000);
}

/** O7 (D-11): destructive-ish op — confirm, then the until-filtered prune. */
async function onCacheCleanup() {
  const { confirm } = await import("@tauri-apps/plugin-dialog");
  const ok = await confirm(t("settings.disk.cleanupConfirm"));
  if (!ok) return;
  await store.runCacheCleanup(24);
}

// --- B3 (2.1.12): docker resource admin (scan preview -> confirm -> act) ---
function dockerActionableCount(b: { owned: unknown[]; legacy_owned: unknown[] }): number {
  return b.owned.length + b.legacy_owned.length;
}

/** Compact preview rows: one per actionable/unverified bucket, names capped. */
const dockerPreviewRows = computed(() => {
  const r = store.dockerReport;
  if (!r) return [];
  const names = (list: { name: string }[]) =>
    list.length === 0
      ? "—"
      : list.map((e) => e.name).slice(0, 6).join("、") + (list.length > 6 ? ` …（${list.length}）` : "");
  return [
    { label: t("settings.docker.rowContainers"), value: names([...r.containers.owned, ...r.containers.legacy_owned]) },
    { label: t("settings.docker.rowUnverifiedContainers"), value: names(r.containers.unverified) },
    { label: t("settings.docker.rowImages"), value: names([...r.images.owned, ...r.images.legacy_owned]) },
    { label: t("settings.docker.rowUnverifiedImages"), value: names(r.images.unverified) },
  ];
});

async function onDockerCleanup() {
  const { confirm } = await import("@tauri-apps/plugin-dialog");
  const ok = await confirm(t("settings.docker.cleanupConfirm"));
  if (!ok) return;
  await store.runDockerCleanup();
}

async function onDockerRebuild() {
  const { confirm } = await import("@tauri-apps/plugin-dialog");
  const ok = await confirm(t("settings.docker.rebuildConfirm"));
  if (!ok) return;
  await store.runDockerRebuild();
}

// --- v2.1.13 D-12: owned-resource management actions ------------------------
// Every action double-gates: a confirm dialog naming the resource, then the
// CLI's in-lock ownership re-verification (unverified refuses server-side).
const managementBusyLocal = ref(false);
type ManageRow = { id: string; name: string; state?: string; ownership: string };

function manageRows(): ManageRow[] {
  const r = store.dockerReport;
  if (!r || !r.dockerAvailable) return [];
  const out: ManageRow[] = [];
  for (const row of [...r.containers.owned, ...r.containers.legacy_owned]) {
    out.push({ id: row.id, name: row.name, state: row.status, ownership: row.ownership });
  }
  for (const row of [...r.images.owned, ...r.images.legacy_owned]) {
    out.push({ id: row.id, name: row.name, ownership: row.ownership });
  }
  return out;
}
const manageRowsRef = computed(() => manageRows());

async function onContainerAction(name: string, action: "start" | "stop" | "rm"): Promise<void> {
  if (managementBusyLocal.value) return;
  const key = action === "rm" ? "settings.docker.manage.rmConfirm" : "settings.docker.manage.stopConfirm";
  const ok = await confirm(t(key, { name }));
  if (!ok) return;
  managementBusyLocal.value = true;
  try {
    await store.containerAction(name, action);
  } finally {
    managementBusyLocal.value = false;
  }
}
async function onImageRm(id: string, name: string): Promise<void> {
  if (managementBusyLocal.value) return;
  const ok = await confirm(t("settings.docker.manage.imageRmConfirm", { name }));
  if (!ok) return;
  managementBusyLocal.value = true;
  try {
    await store.imageRm(id);
  } finally {
    managementBusyLocal.value = false;
  }
}
async function onImageTag(id: string, name: string): Promise<void> {
  if (managementBusyLocal.value) return;
  // retag-only v1: the new tag derives from the old name (see plan doc).
  const parts = name.split(":");
  const repo = parts[0] ?? name;
  const oldTag = parts[1] ?? "latest";
  const newTag = `${oldTag}-renamed`;
  const ok = await confirm(t("settings.docker.manage.imageTagConfirm", { name, newTag }));
  if (!ok) return;
  managementBusyLocal.value = true;
  try {
    await store.imageTag(id, repo, newTag);
  } finally {
    managementBusyLocal.value = false;
  }
}

/** A7: destructive-ish (app exits) — confirm before the silent install. */
async function onInstallUpdate() {
  const { confirm } = await import("@tauri-apps/plugin-dialog");
  const ok = await confirm(t("settings.about.installConfirm"));
  if (!ok) return;
  await update.install();
}

async function onReset() {
  const ok = await confirm(t("settings.resetConfirm"));
  if (!ok) return;
  await store.reset();
}

/** Stage 5 (A-ONB07): reopen the setup wizard. Marks onboarding in_progress
 *  at the environment step; the App.vue gate re-shows the overlay. */
async function reopenOnboarding() {
  const { useOnboardingStore } = await import("../../stores/onboarding");
  const onboarding = useOnboardingStore();
  // Resume at the environment step (the wizard's own step machine reads
  // this) and RAISE the manual overlay (v2.1.7 S3: the status patch alone
  // no longer opens anything).
  await onboarding.patch({ status: "in_progress", currentStep: "environment" });
  onboarding.openWizard();
  emit("close");
}
</script>

<template>
  <div class="settings-form">
    <!-- No header of its own, so the dirty/saved state lives here. -->
    <div class="tab-strip">
      <span class="spacer" />
      <span v-if="store.dirty" class="chip dirty">{{ t("settings.dirty") }}</span>
      <span v-if="savedFlash" class="chip saved">{{ t("settings.saved") }}</span>
    </div>

    <p v-if="store.corrupted" class="banner warn">
      {{ t("settings.corrupted") }}
    </p>
    <p v-if="store.readOnly" class="banner warn">
      {{ t("settings.readOnly") }}
    </p>
    <p v-if="store.error" class="banner err">
      {{ store.error }}
      <button class="link" :disabled="saving" @click="store.save()">{{ t("settings.retry") }}</button>
    </p>

    <!-- P2-5: VS Code-style — left nav (sections; dimmed when a search
         misses them) + right pane (the active section, or every matching
         section while searching). -->
    <div v-if="store.doc" class="settings-cols">
      <nav class="settings-nav" :aria-label="t('settings.navLabel')">
        <input
          v-model="query"
          class="nav-search"
          type="text"
          :placeholder="t('settings.searchPlaceholder')"
          aria-label="t('settings.searchPlaceholder')"
        />
        <button
          v-for="g in GROUPS"
          :key="g"
          type="button"
          class="nav-item"
          :class="{
            active: !searching && activeGroup === g,
            dim: searching && !groupMatches(g),
          }"
          @click="pickGroup(g)"
        >{{ t(GROUP_KEY[g] ?? g) }}</button>
      </nav>
      <div class="settings-pane">
      <template v-for="group in visibleGroups" :key="group">
        <h3 class="group">{{ t(GROUP_KEY[group] ?? group) }}</h3>

        <!-- ui section -->
        <template v-if="group === 'ui'">
          <div v-for="f in FIELDS.filter((x) => x.key.startsWith('ui.'))" :key="f.key" class="field">
            <label :for="f.key" class="label">{{ t(f.labelKey) }}</label>
            <select v-if="f.key === 'ui.language'" :id="f.key" v-model="ui.language" :disabled="store.readOnly">
              <option v-for="o in f.options" :key="o.value" :value="o.value">{{ t(o.labelKey) }}</option>
            </select>
            <input v-else-if="f.key === 'ui.font_scale'" :id="f.key" v-model.number="ui.font_scale"
              type="range" :min="f.min" :max="f.max" :step="f.step" :disabled="store.readOnly" />
            <span v-if="f.control === 'range'" class="val">{{ f.key === 'ui.font_scale' ? ui.font_scale.toFixed(2) : '' }}</span>
            <select v-else-if="f.key === 'ui.theme'" :id="f.key" v-model="ui.theme" :disabled="store.readOnly">
              <option v-for="o in f.options" :key="o.value" :value="o.value">{{ t(o.labelKey) }}</option>
            </select>
            <select v-else-if="f.key === 'ui.default_tab_agent'" :id="f.key" v-model="ui.default_tab_agent" :disabled="store.readOnly">
              <option v-for="o in f.options" :key="o.value" :value="o.value">{{ t(o.labelKey) }}</option>
            </select>
            <input v-else-if="f.key === 'ui.explorer_ignore'" :id="f.key" v-model="explorerIgnoreText"
              type="text" :disabled="store.readOnly" />
            <span class="effect">{{ t(EFFECT_KEY[f.effect]) }}</span>
            <span v-if="f.helpKey" class="help">{{ t(f.helpKey) }}</span>
            <span v-if="issuesByField[f.key]" class="err-text">{{ issuesByField[f.key] }}</span>
          </div>
        </template>

        <!-- terminal section -->
        <template v-else-if="group === 'terminal'">
          <div v-for="f in FIELDS.filter((x) => x.key.startsWith('terminal.'))" :key="f.key" class="field">
            <label :for="f.key" class="label">{{ t(f.labelKey) }}</label>
            <input v-if="f.control === 'text'" :id="f.key" v-model="terminal.font_family" type="text" :disabled="store.readOnly" />
            <input v-else-if="f.key === 'terminal.font_size'" :id="f.key" v-model.number="terminal.font_size"
              type="range" :min="f.min" :max="f.max" :step="f.step" :disabled="store.readOnly" />
            <input v-else-if="f.key === 'terminal.line_height'" :id="f.key" v-model.number="terminal.line_height"
              type="range" :min="f.min" :max="f.max" :step="f.step" :disabled="store.readOnly" />
            <input v-else-if="f.key === 'terminal.letter_spacing'" :id="f.key" v-model.number="terminal.letter_spacing"
              type="range" :min="f.min" :max="f.max" :step="f.step" :disabled="store.readOnly" />
            <input v-else-if="f.key === 'terminal.scrollback'" :id="f.key" v-model.number="terminal.scrollback"
              type="range" :min="f.min" :max="f.max" :step="f.step" :disabled="store.readOnly" />
            <select v-else-if="f.key === 'terminal.renderer'" :id="f.key" v-model="terminal.renderer" :disabled="store.readOnly">
              <option v-for="o in f.options" :key="o.value" :value="o.value">{{ t(o.labelKey) }}</option>
            </select>
            <input v-else-if="f.key === 'terminal.smooth_scroll_duration'" :id="f.key" v-model.number="terminal.smooth_scroll_duration"
              type="range" :min="f.min" :max="f.max" :step="f.step" :disabled="store.readOnly" />
            <span v-if="f.control === 'range'" class="val">{{
              f.key === 'terminal.font_size' ? terminal.font_size + 'px'
              : f.key === 'terminal.line_height' ? terminal.line_height.toFixed(2)
              : f.key === 'terminal.letter_spacing' ? terminal.letter_spacing
              : f.key === 'terminal.scrollback' ? terminal.scrollback
              : f.key === 'terminal.smooth_scroll_duration' ? terminal.smooth_scroll_duration + 'ms'
              : ''
            }}</span>
            <span class="effect">{{ t(EFFECT_KEY[f.effect]) }}</span>
            <span v-if="f.helpKey" class="help">{{ t(f.helpKey) }}</span>
            <span v-if="issuesByField[f.key]" class="err-text">{{ issuesByField[f.key] }}</span>
          </div>
        </template>

        <!-- window section -->
        <template v-else-if="group === 'window'">
          <div v-for="f in FIELDS.filter((x) => x.key.startsWith('window.'))" :key="f.key" class="field">
            <label :for="f.key" class="label">{{ t(f.labelKey) }}</label>
            <input v-if="f.key === 'window.remember_geometry'" :id="f.key" v-model="windowS.remember_geometry" type="checkbox" :disabled="store.readOnly" />
            <select v-else-if="f.key === 'window.close_behavior'" :id="f.key" v-model="windowS.close_behavior" :disabled="store.readOnly">
              <option v-for="o in f.options" :key="o.value" :value="o.value">{{ t(o.labelKey) }}</option>
            </select>
            <span class="effect">{{ t(EFFECT_KEY[f.effect]) }}</span>
            <span v-if="issuesByField[f.key]" class="err-text">{{ issuesByField[f.key] }}</span>
          </div>
          <p v-if="store.doc.window.geometry" class="note">
            {{ t("settings.window.geometryNote", { x: store.doc.window.geometry.x, y: store.doc.window.geometry.y, w: store.doc.window.geometry.width, h: store.doc.window.geometry.height, max: store.doc.window.geometry.maximized ? t("settings.window.geometryMaximized") : "" }) }}
            {{ store.doc.window.geometry.width }}×{{ store.doc.window.geometry.height }}
            {{ store.doc.window.geometry.maximized ? "" : "" }}
          </p>
        </template>

        <!-- F2 (D-10): host-tools whitelist card. Default EMPTY = the feature
             is off (every container host_exec call is refused). -->
        <template v-else-if="group === 'hostTools'">
          <p class="help">{{ t("settings.hostTools.hint") }}</p>
          <div v-for="(row, i) in hostTools" :key="i" class="field ht-row">
            <input v-model.trim="row.name" class="ht-name" :placeholder="t('settings.hostTools.namePh')" :disabled="store.readOnly" />
            <input v-model.trim="row.program" class="ht-program" :placeholder="t('settings.hostTools.programPh')" :disabled="store.readOnly" />
            <select v-model="row.readOnlyPreset" :disabled="store.readOnly" :title="t('settings.hostTools.presetHint')">
              <option value="">{{ t("settings.hostTools.presetNone") }}</option>
              <option value="git-ro">{{ t("settings.hostTools.presetGitRo") }}</option>
            </select>
            <button class="ht-del" :disabled="store.readOnly" :title="t('settings.hostTools.remove')" @click="hostTools.splice(i, 1)">×</button>
          </div>
          <div class="field">
            <button :disabled="store.readOnly" @click="hostTools.push({ name: '', program: '', readOnlyPreset: '' })">
              ＋ {{ t("settings.hostTools.add") }}
            </button>
          </div>
          <p class="note">{{ t("settings.hostTools.note") }}</p>
        </template>

        <!-- R4b: remote machines — the targets the Workbench can drive. -->
        <template v-else-if="group === 'machines'">
          <p class="help">{{ t("settings.machines.hint") }}</p>
          <!-- Column header: placeholders vanish once a row is filled, so the
               fields need standing labels (the port column has no placeholder
               at all when empty — hand-test 2026-09-15: "第4个空是什么?"). -->
          <div v-if="machines.length" class="machine-head">
            <span>{{ t("settings.machines.colName") }}</span>
            <span>{{ t("settings.machines.colHost") }}</span>
            <span>{{ t("settings.machines.colUser") }}</span>
            <span>{{ t("settings.machines.colPort") }}</span>
            <span>{{ t("settings.machines.colKey") }}</span>
          </div>
          <div v-for="(row, i) in machines" :key="i" class="field machine-row">
            <input v-model.trim="row.name" class="m-name" :placeholder="t('settings.machines.namePh')" :disabled="store.readOnly" />
            <input v-model.trim="row.host" class="m-host" :placeholder="t('settings.machines.hostPh')" :disabled="store.readOnly" />
            <input v-model.trim="row.user" class="m-user" :placeholder="t('settings.machines.userPh')" :disabled="store.readOnly" />
            <input v-model.number="row.port" type="number" min="1" max="65535" class="m-port" :placeholder="t('settings.machines.portPh')" :disabled="store.readOnly" />
            <input v-model.trim="row.keyPath" class="m-key mono-input" :placeholder="t('settings.machines.keyPh')" :disabled="store.readOnly" />
            <button class="ht-del" :disabled="store.readOnly" :title="t('settings.machines.remove')" @click="machines.splice(i, 1)">×</button>
          </div>
          <div class="field">
            <button :disabled="store.readOnly" @click="machines.push({ name: '', host: '' })">
              ＋ {{ t("settings.machines.add") }}
            </button>
          </div>
          <p class="note">{{ t("settings.machines.note") }}</p>
          <!-- Key-auth-only is a hard ruling (D-7, BatchMode=yes): without
               this note a password-auth user just sees "Permission denied"
               with no clue why no prompt ever appeared. -->
          <p class="note">{{ t("settings.machines.authNote") }}</p>
          <!-- v2.1.13 remote CLI pairing: per-machine soft version probe.
               Compares the remote serve banner's cli_version against the
               local pinned CLI (never the Workbench version). -->
          <div v-if="store.doc?.remoteMachines?.length" class="machine-versions">
            <p class="help">{{ t("settings.machines.versionTitle") }}</p>
            <div
              v-for="m in store.doc.remoteMachines"
              :key="'mv-' + m.name"
              class="field machine-version-row"
            >
              <span class="mv-name">{{ m.name }}</span>
              <span v-if="store.remoteVersions[m.name]" class="mv-detail">
                {{ t("settings.machines.versionDetail", {
                  remote: store.remoteVersions[m.name].remoteVersion || "?",
                  local: store.remoteVersions[m.name].localVersion || "?",
                }) }}
                <b v-if="store.remoteVersions[m.name].verdict === 'behind'" class="mv-behind">
                  {{ t("settings.machines.needsUpdate") }}
                </b>
                <span v-else-if="store.remoteVersions[m.name].verdict === 'equal'">
                  {{ t("settings.machines.upToDate") }}
                </span>
                <span v-else-if="store.remoteVersions[m.name].verdict === 'ahead'">
                  {{ t("settings.machines.ahead") }}
                </span>
                <span v-else>{{ t("settings.machines.versionUnknown") }}</span>
              </span>
              <span v-else class="mv-detail mv-muted">{{ t("settings.machines.notChecked") }}</span>
              <button
                class="ui-button"
                :disabled="!!store.versionBusy[m.name]"
                @click="onCheckVersion(m.name)"
              >{{ t("settings.machines.check") }}</button>
              <template v-if="store.remoteVersions[m.name]?.verdict === 'behind'">
                <code class="mv-cmd">{{ upgradeCmd }}</code>
                <button class="ui-button" @click="onCopyUpgradeCmd()">
                  {{ t("settings.machines.copyCmd") }}
                </button>
              </template>
            </div>
          </div>
        </template>

        <!-- PERF P8 (D-13): performance / low-spec mode. lowSpec gates the
             container --memory/--cpus budget (new containers only); the
             .wslconfig merge keeps user keys and only runs on confirmation. -->
        <template v-else-if="group === 'performance'">
          <p class="help">{{ t("settings.perf.hint") }}</p>
          <p v-if="lowSpecRamText" class="note">{{ lowSpecRamText }}</p>
          <div class="field">
            <label class="check-row">
              <input
                v-model="perfLowSpec"
                type="checkbox"
                :disabled="store.readOnly"
              />
              <span>{{ t("settings.perf.lowSpec") }}</span>
            </label>
          </div>
          <template v-if="perfLowSpec">
            <div class="field">
              <label class="label">{{ t("settings.perf.memory") }}</label>
              <input v-model.trim="perfMemory" class="mono-input" :disabled="store.readOnly" />
            </div>
            <div class="field">
              <label class="label">{{ t("settings.perf.cpus") }}</label>
              <input
                v-model.number="perfCpus"
                type="number"
                min="0.5"
                max="8"
                step="0.5"
                :disabled="store.readOnly"
              />
            </div>
            <div class="field">
              <button :disabled="store.readOnly" @click="onWslconfig">
                {{ t("settings.perf.wslBtn") }}
              </button>
            </div>
            <p class="note">{{ t("settings.perf.wslNote") }}</p>
            <p v-if="wslMsg" class="note">{{ wslMsg }}</p>
          </template>
          <p class="note">{{ t("settings.perf.note") }}</p>
        </template>

        <!-- O7 (D-11): disk & cache card — df summary + until-filtered prune.
             NOT a settings document field: live ops via the settings store. -->
        <template v-else-if="group === 'disk'">
          <p class="help">{{ t("settings.disk.hint") }}</p>
          <p v-if="store.cacheError" class="err-text">{{ store.cacheError }}</p>
          <template v-if="store.cacheUsage?.dockerAvailable">
            <div v-for="row in store.cacheUsage.rows" :key="row.kind" class="field disk-row">
              <span class="label">{{ row.kind }}</span>
              <span class="val">{{ row.size }}</span>
              <span class="effect">{{ t("settings.disk.reclaimable", { n: row.reclaimable, c: row.total_count }) }}</span>
            </div>
          </template>
          <p v-else-if="!store.cacheError" class="note">{{ t("settings.disk.unavailable") }}</p>
          <div class="field">
            <button :disabled="store.cacheBusy" :title="t('settings.disk.refreshTip')" @click="store.loadCacheUsage()">{{ t("settings.disk.refresh") }}</button>
            <button class="primary" :disabled="store.cacheBusy" :title="t('settings.disk.cleanupTip')" @click="onCacheCleanup">{{ t("settings.disk.cleanup") }}</button>
          </div>
          <p v-for="(line, i) in store.cacheLog" :key="i" class="note">{{ line }}</p>

          <!-- v2.1.13 (docker-scan-fidelity): read-only per-item inspection.
               Detect finer + report accurately; NO cleanup here, NO auto
               trigger — the user presses the button every single time (D-2).
               will_be_cleaned mirrors what the CURRENT manual cleanup would
               hit; the disclaimer carries the shared-layer caveat. -->
          <p class="group">{{ t("settings.disk.inspect.group") }}</p>
          <div class="field">
            <button :disabled="store.inspectBusy" @click="store.loadDockerInspect()">
              {{ store.inspectBusy ? t("settings.disk.inspect.busy") : t("settings.disk.inspect.open") }}
            </button>
            <span v-if="store.inspectReport" class="effect">
              {{ t("settings.disk.inspect.totals", {
                items: inspectTotals.items,
                reclaimable: formatBytes(inspectTotals.reclaimable) }) }}
            </span>
          </div>
          <p v-if="store.inspectError" class="err-text">{{ store.inspectError }}</p>
          <div v-if="store.inspectReport" class="inspect-groups">
            <p class="note">{{ t("settings.disk.inspect.disclaimer") }}</p>
            <details
              v-for="[key, cat] in orderedInspect"
              :key="key"
              class="inspect-cat"
            >
              <summary>
                {{ t("settings.disk.inspect.cat." + key) }}
                <span class="effect">
                  {{ cat?.summary.count ?? 0 }} · {{ formatBytes(cat?.summary.reclaimable_bytes ?? null) }}
                </span>
              </summary>
              <div class="inspect-thead">
                <span>{{ t("settings.disk.inspect.colName") }}</span>
                <span>{{ t("settings.disk.inspect.colSize") }}</span>
                <span>{{ t("settings.disk.inspect.colStatus") }}</span>
              </div>
              <div
                v-for="row in sortedInspectRows(key, cat?.rows ?? [])"
                :key="String(row.id) + String(row.name)"
                class="inspect-row"
              >
                <span class="ir-name" :title="String(row.id)">{{ inspectDisplayName(row) }}</span>
                <span class="ir-size">{{ row.size ?? row.unique_size ?? formatBytes(row.size_bytes) }}</span>
                <span class="ir-status" :title="row.will_be_cleaned ? t('settings.disk.inspect.willClean') : undefined">
                  <template v-if="row.will_be_cleaned">{{ t("settings.disk.inspect.willClean") }}</template>
                  <template v-else-if="row.dangling">{{ t("settings.disk.inspect.dangling") }}</template>
                  <template v-else-if="row.in_use">{{ t("settings.disk.inspect.inUse") }}</template>
                  <template v-else>—</template>
                </span>
              </div>
              <button
                v-if="(cat?.rows.length ?? 0) > 30 && !inspectShowAll.has(key)"
                class="inspect-more"
                @click="inspectShowAll.add(key)"
              >
                {{ t("settings.disk.inspect.showAll", { n: cat?.rows.length }) }}
              </button>
              <p v-if="!(cat?.rows ?? []).length" class="note">{{ t("settings.disk.inspect.empty") }}</p>
            </details>
          </div>

          <!-- B3 (2.1.12): docker resource admin — scan preview -> confirm ->
               act. Rebuild is LOCAL-only (remote machines manage their own
               bundle; A-chain update orchestration owns that later). -->
          <p class="group">{{ t("settings.docker.group") }}</p>
          <p class="help">{{ t("settings.docker.hint") }}</p>
          <div class="field">
            <button :disabled="store.dockerBusy" :title="t('settings.docker.scanTip')" @click="store.loadDockerScan()">{{ t("settings.docker.scan") }}</button>
            <!-- Scan-first gate (user ruling 2026-09-16): cleanup/rebuild stay
                 disabled until a scan has classified what's there — the
                 preview IS the confirmation basis; acting blind is how the
                 wrong mental model (cleanup deletes my files?) forms. -->
            <button class="danger" :disabled="store.dockerBusy || !store.dockerReport" :title="t('settings.docker.cleanupTip')" @click="onDockerCleanup">{{ t("settings.docker.cleanup") }}</button>
            <button :disabled="store.dockerRebuilding || !store.dockerReport" :title="t('settings.docker.rebuildTip')" @click="onDockerRebuild">
              {{ store.dockerRebuilding ? t("settings.docker.rebuilding") : t("settings.docker.rebuild") }}
            </button>
          </div>
          <template v-if="store.dockerReport">
            <p v-if="!store.dockerReport.dockerAvailable" class="note">{{ t("settings.docker.unavailable") }}</p>
            <template v-else>
              <p class="note">{{ t("settings.docker.summary", { c: dockerActionableCount(store.dockerReport.containers), i: dockerActionableCount(store.dockerReport.images), d: store.dockerReport.danglingOwned.length }) }}</p>
              <div v-for="row in dockerPreviewRows" :key="row.label" class="field disk-row">
                <span class="label">{{ row.label }}</span>
                <span class="val">{{ row.value }}</span>
              </div>

              <!-- v2.1.13 D-12: per-resource management (aisc-owned only;
                   unverified rows stay view-only). Buttons follow the
                   container state; confirms name the resource. -->
              <div v-if="manageRowsRef.length" class="manage-list">
                <div class="manage-thead">
                  <span>{{ t("settings.docker.manage.colResource") }}</span>
                  <span>{{ t("settings.docker.manage.colState") }}</span>
                  <span>{{ t("settings.docker.manage.colActions") }}</span>
                </div>
                <div v-for="row in manageRowsRef" :key="row.id + row.name" class="manage-row">
                  <span class="mr-name" :title="row.id">{{ row.name }}</span>
                  <span class="mr-state">{{ row.state ?? "—" }}</span>
                  <span class="mr-actions">
                    <template v-if="row.state === 'running'">
                      <button class="ui-button" :disabled="store.managementBusy !== null" @click="onContainerAction(row.name, 'stop')">{{ t("settings.docker.manage.stop") }}</button>
                    </template>
                    <template v-else>
                      <button class="ui-button" :disabled="store.managementBusy !== null" @click="onContainerAction(row.name, 'start')">{{ t("settings.docker.manage.start") }}</button>
                      <button class="danger" :disabled="store.managementBusy !== null" @click="onContainerAction(row.name, 'rm')">{{ t("settings.docker.manage.rm") }}</button>
                    </template>
                    <template v-if="!row.state">
                      <button class="danger" :disabled="store.managementBusy !== null" @click="onImageRm(row.id, row.name)">{{ t("settings.docker.manage.rm") }}</button>
                      <button class="ui-button" :disabled="store.managementBusy !== null" @click="onImageTag(row.id, row.name)">{{ t("settings.docker.manage.retag") }}</button>
                    </template>
                  </span>
                </div>
              </div>
            </template>
          </template>
          <p v-if="store.dockerError" class="err-text">{{ store.dockerError }}</p>
          <p v-for="(line, i) in store.dockerLog" :key="i" class="note">{{ line }}</p>
          <p class="note">{{ t("settings.docker.rebuildNote") }}</p>
        </template>

        <!-- A7 (0.1.0, D-8 自研): about + self-update. -->
        <template v-else-if="group === 'about'">
          <p class="help">{{ t("settings.about.hint") }}</p>
          <div class="field disk-row">
            <span class="label">{{ t("settings.about.current") }}</span>
            <span class="val">{{ update.info?.current ?? t("settings.about.unknown") }}</span>
          </div>
          <p v-if="update.error" class="err-text">{{ update.error }}</p>
          <template v-if="update.info">
            <div v-if="update.info.latest" class="field disk-row">
              <span class="label">{{ t("settings.about.latest") }}</span>
              <span class="val">{{ update.info.latest }}</span>
            </div>
            <p v-if="update.info.note" class="note">{{ update.info.note }}</p>
            <p v-if="update.status === 'none'" class="note">{{ t("settings.about.upToDate") }}</p>
            <template v-if="update.status === 'available' || update.status === 'downloading'">
              <div class="field">
                <button class="primary" :disabled="update.status === 'downloading'" @click="update.download()">
                  {{ update.status === "downloading" ? t("settings.about.downloading") : t("settings.about.download") }}
                </button>
              </div>
              <div v-if="update.status === 'downloading'" class="bar note">
                {{ update.downloaded }} / {{ update.total || "?" }} bytes
              </div>
            </template>
            <template v-if="update.status === 'ready'">
              <p class="note">{{ t("settings.about.ready", { sha: update.staged?.sha256.slice(0, 16) ?? "" }) }}</p>
              <div class="field">
                <button class="danger" @click="onInstallUpdate">{{ t("settings.about.install") }}</button>
              </div>
            </template>
          </template>
          <div v-else class="field">
            <button class="primary" :disabled="update.status === 'checking'" @click="update.check()">
              {{ update.status === "checking" ? t("settings.about.checking") : t("settings.about.check") }}
            </button>
          </div>
          <p class="note">{{ t("settings.about.sidecarNote") }}</p>
        </template>
      </template>
      </div>
    </div>
    <div v-else class="body">
      <p class="loading">{{ t("settings.loading") }}</p>
    </div>

    <footer class="foot">
      <button class="primary" :disabled="saving || store.readOnly || !store.loaded" @click="onSave">
        {{ saving ? t("settings.saving") : t("settings.save") }}
      </button>
      <button :disabled="saving || store.readOnly || !store.loaded" @click="onReset">{{ t("settings.reset") }}</button>
      <button :disabled="saving" @click="reopenOnboarding">{{ t("settings.reopenOnboarding") }}</button>
      <!-- Closing happens via the strip chip × / Ctrl+, (both revert unsaved
           edits) — no in-form Close button. -->
    </footer>
  </div>
</template>

<style scoped>
/* Fill the host (dialog panel / settings tab pane); the body grows and the
   sticky footer pins to the bottom when the content is short. */
.settings-form { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.tab-strip { display: flex; align-items: center; gap: 8px; padding: 8px 14px 0; }
.tab-strip .spacer { flex: 1; }
.chip { font-size: var(--font-xs); padding: 2px var(--space-2); border-radius: var(--radius-sm); }
.chip.dirty { background: var(--warn-bg); color: var(--warn-fg); }
.chip.saved { background: var(--success-bg); color: var(--success); }
.banner { margin: var(--space-2) var(--space-4) 0; padding: var(--space-1) var(--space-2); border-radius: var(--radius-sm); font-size: var(--font-sm); }
.banner.warn { background: var(--warn-bg); color: var(--warn-fg); }
.banner.err { background: var(--error-bg); color: var(--error-fg); }
.link { background: none; border: none; color: var(--info); padding: 0; margin-left: 8px; cursor: pointer; text-decoration: underline; }
/* P2-5: left nav + right pane. The nav rides sticky inside the floating
 * pane's scroll container so it stays reachable in long sections. */
.settings-cols { display: flex; gap: 12px; flex: 1; min-height: 0; align-items: stretch; }
.settings-nav {
  flex: none;
  width: 168px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 0;
  position: sticky;
  top: 0;
  align-self: flex-start;
  max-height: 100%;
  overflow-y: auto;
}
.nav-search {
  margin: 0 6px 6px;
  background: var(--surface-3); color: var(--text);
  border: var(--border-w) solid var(--border-strong); border-radius: var(--radius-sm);
  min-height: var(--control-h-sm); padding: 0 var(--space-2); font-size: var(--font-sm);
}
.nav-item {
  text-align: left; background: none; border: none; cursor: pointer;
  color: var(--text-2); font-size: var(--font-sm);
  padding: 6px 10px; border-radius: var(--radius-sm);
}
.nav-item:hover { background: var(--surface-hover); color: var(--text); }
.nav-item.active {
  background: none;
  color: var(--accent);
  font-weight: 600;
  box-shadow: inset 2px 0 0 var(--accent);
}
.nav-item.dim { opacity: 0.45; }
/* 手测 r2: styles.css's [role="dialog"] :focus paints the ring on plain
 * :focus (dialog keyboard-nav workaround) — clicked nav items kept a +2px
 * offset ring that OVERFLOWED the pane edge. Negative offset keeps the
 * ring (the workaround's intent) strictly inside the box. */
.settings-form :is(button, input, select):focus {
  outline-offset: -2px;
}
.settings-pane { flex: 1; min-width: 0; padding: 6px 14px 12px 0; }
.body { padding: 6px 14px 12px; flex: 1; }
.group { margin: 12px 0 4px; font-size: var(--font-sm); color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.5px; }
.field { display: flex; align-items: center; gap: 8px; margin: 6px 0; flex-wrap: wrap; }
.label { width: 150px; font-size: var(--font-md); color: var(--text-2); }
input[type="text"], input[type="number"], select {
  background: var(--surface-3); color: var(--text);
  border: var(--border-w) solid var(--border-strong); border-radius: var(--radius-sm);
  min-height: var(--control-h-sm);
  padding: var(--space-1) var(--space-2); font-size: var(--font-md); flex: 1; min-width: 120px;
  box-sizing: border-box;
}
input[type="range"] {
  flex: 1; min-width: 120px; accent-color: var(--accent); cursor: pointer;
}
input:disabled, select:disabled { opacity: 0.5; }
.val {
  font-size: var(--font-sm); color: var(--info); min-width: 46px; text-align: right;
  font-variant-numeric: tabular-nums; white-space: nowrap;
}
.effect { font-size: var(--font-xs); color: var(--text-muted); white-space: nowrap; }
.help { font-size: var(--font-xs); color: var(--text-faint); width: 100%; }
.err-text { font-size: var(--font-xs); color: var(--error); width: 100%; }
.note { font-size: var(--font-xs); color: var(--text-faint); margin-top: 8px; }
.disk-row .label { color: var(--text-2); }
/* F2: host-tools whitelist rows */
.ht-row { flex-wrap: nowrap; }
.ht-name { max-width: 160px; }
.ht-program { font-family: var(--font-mono); font-size: var(--font-sm); }
.ht-row select { max-width: 150px; }
.ht-del {
  min-width: 26px; min-height: 26px; padding: 0; flex: none;
}
.mono-input { font-family: var(--font-mono); font-size: var(--font-sm); }
/* F1: SSH profile rows. Grid (not flex) so the column header shares the
 * exact tracks — a flex header can't align with max-width'd inputs.
 * min-width:0 is required: the generic input rule's 120px min overflows
 * the 110/90/72 tracks, and there's no global border-box reset (the same
 * disease ModelMappingEditor's cat-row hit and documented). */
.machine-head { display: grid; grid-template-columns: 110px 160px 90px 72px 1fr; gap: 8px;
  align-items: center; margin: 6px 0 0; font-size: var(--font-xs); color: var(--text-faint); }
.machine-row { display: grid; grid-template-columns: 110px 160px 90px 72px 1fr 26px; gap: 8px; align-items: stretch; }
.machine-row input { box-sizing: border-box; min-width: 0; }
/* v2.1.13 remote CLI pairing rows */
.machine-versions { margin-top: 4px; }
.machine-version-row {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
  font-size: var(--font-sm); color: var(--text-2);
}
.machine-version-row .mv-name { font-weight: 600; color: var(--text); min-width: 90px; }
.machine-version-row .mv-muted { color: var(--text-muted); }
.machine-version-row .mv-behind { color: var(--warn); }
.machine-version-row .mv-cmd {
  font-family: var(--font-mono); font-size: var(--font-sm);
  background: var(--surface-2, rgba(128, 128, 128, 0.12));
  padding: 2px 6px; border-radius: var(--radius-sm, 4px);
}
.m-host { font-family: var(--font-mono); font-size: var(--font-sm); }
.loading { color: var(--text-muted); font-size: var(--font-md); }
.foot {
  display: flex; gap: 8px; padding: 10px 14px; border-top: 1px solid var(--border);
  /* Sticky bottom so Save stays reachable when the parent scrolls (dialog
     panel and settings tab both scroll their content). */
  position: sticky; bottom: 0; z-index: 2; background: var(--surface);
}
button {
  display: inline-flex; align-items: center; justify-content: center;
  min-height: var(--control-h-sm);
  background: var(--surface-3); color: var(--text-2);
  border: var(--border-w) solid var(--border); border-radius: var(--radius-sm);
  padding: 0 var(--space-3); font-size: var(--font-sm); cursor: pointer;
  transition: background-color var(--duration-normal) var(--ease), color var(--duration-normal) var(--ease);
}
button:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
button:focus-visible { outline: var(--focus-ring-width) solid var(--focus); outline-offset: var(--focus-ring-offset); }
button:disabled { opacity: 0.45; cursor: default; }
button.primary { background: var(--accent); border-color: transparent; color: var(--accent-fg); font-weight: 600; }
button.primary:hover:not(:disabled) { background: var(--accent-hover); }
/* --- v2.1.13 D-9b: aligned inspection rows (hand-test redesign) --- */
.inspect-thead,
.inspect-row {
  display: grid; grid-template-columns: minmax(0, 1fr) auto 150px;
  gap: 10px; align-items: baseline; padding: 3px 4px;
  font-size: var(--font-xs);
}
.inspect-thead { color: var(--text-muted); border-bottom: 1px solid var(--border); }
.inspect-row:nth-child(odd) { background: var(--surface-hover, rgba(128, 128, 128, 0.06)); }
.inspect-row .ir-name {
  font-family: var(--font-mono); color: var(--text-2);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.inspect-row .ir-size { text-align: right; color: var(--text); white-space: nowrap; }
.inspect-row .ir-status { text-align: right; color: var(--text-muted); }
.inspect-more { margin-top: 4px; }

/* --- v2.1.13 D-12: management rows --- */
.manage-list { margin-top: 6px; }
.manage-thead,
.manage-row {
  display: grid; grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 8px; align-items: center; padding: 3px 4px; font-size: var(--font-xs);
}
.manage-thead { color: var(--text-muted); border-bottom: 1px solid var(--border); }
.manage-row .mr-name {
  font-family: var(--font-mono); color: var(--text-2);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.manage-row .mr-state { color: var(--text-muted); white-space: nowrap; }
.manage-row .mr-actions { display: flex; gap: 4px; }
</style>
