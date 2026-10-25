<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useSettingsStore } from "../../stores/settings";
import type { HostToolEntry } from "../../types";

const { t } = useI18n();
const store = useSettingsStore();
const rows = ref<HostToolEntry[]>([]);
const loadError = ref<string | null>(null);

const busy = computed(() => store.saveState === "saving");

function syncFromDoc(): void {
  rows.value = (store.doc?.hostTools ?? []).map((row) => ({
    readOnlyPreset: "",
    ...row,
  }));
}

onMounted(async () => {
  if (!store.loaded) await store.load();
  syncFromDoc();
});

watch(rows, (value) => {
  if (!store.doc) return;
  store.doc.hostTools = value
    .map(({ name, program, readOnlyPreset }) => ({ name, program, readOnlyPreset: readOnlyPreset ?? "" }))
    .filter((row) => row.name.trim() || row.program.trim() || row.readOnlyPreset.trim());
}, { deep: true });

async function save(): Promise<void> {
  loadError.value = null;
  const outcome = await store.save();
  if (!outcome) loadError.value = store.error;
}
</script>

<template>
  <section class="host-tools-service" data-testid="host-tools-service">
    <h3>{{ t("settings.group.hostTools") }}</h3>
    <p class="help">{{ t("settings.hostTools.hint") }}</p>

    <div v-for="(row, i) in rows" :key="i" class="host-tool-row">
      <input v-model.trim="row.name" type="text" :placeholder="t('settings.hostTools.namePh')" :disabled="store.readOnly" />
      <input v-model.trim="row.program" type="text" :placeholder="t('settings.hostTools.programPh')" :disabled="store.readOnly" />
      <select v-model="row.readOnlyPreset!" :disabled="store.readOnly" :title="t('settings.hostTools.presetHint')">
        <option value="">{{ t("settings.hostTools.presetNone") }}</option>
        <option value="git-ro">{{ t("settings.hostTools.presetGitRo") }}</option>
      </select>
      <button type="button" class="ui-icon-button sm danger" :disabled="store.readOnly" :title="t('settings.hostTools.remove')" @click="rows.splice(i, 1)">×</button>
    </div>

    <div class="host-tools-actions">
      <button type="button" class="ui-button" :disabled="store.readOnly" @click="rows.push({ name: '', program: '', readOnlyPreset: '' })">
        ＋ {{ t("settings.hostTools.add") }}
      </button>
      <button type="button" class="ui-button primary" :disabled="store.readOnly || busy || !store.dirty" @click="save">
        {{ busy ? t("settings.saving") : t("settings.save") }}
      </button>
    </div>

    <p v-if="loadError" class="explorer-error">{{ loadError }}</p>
    <p class="note">{{ t("settings.hostTools.note") }}</p>
  </section>
</template>

<style scoped>
.host-tools-service { display: grid; gap: var(--space-2); min-width: 0; padding-top: var(--space-3); border-top: var(--border-w) solid var(--border); }
.host-tools-service h3 { margin: 0; font-size: var(--font-md); color: var(--text); }
.host-tools-service .help,
.host-tools-service .note { margin: 0; font-size: var(--font-xs); color: var(--text-muted); }
.host-tool-row { display: grid; grid-template-columns: minmax(90px, 0.8fr) minmax(140px, 1.6fr) minmax(110px, 1fr) auto; gap: var(--space-1); min-width: 0; }
.host-tool-row input,
.host-tool-row select { min-width: 0; }
.host-tool-row input:nth-child(2) { font-family: var(--font-mono); font-size: var(--font-sm); }
.host-tools-actions { display: flex; gap: var(--space-1); }
@media (max-width: 680px) {
  .host-tool-row { grid-template-columns: 1fr 1fr; }
}
</style>
