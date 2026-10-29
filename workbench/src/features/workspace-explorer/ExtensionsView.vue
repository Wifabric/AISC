<script setup lang="ts">
/**
 * R2: the main Extensions view owns installed assets. Discovery, categorized
 * recommendations, and source maintenance live in ExtensionMarketDialog.
 */
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useExtensionsStore, type ExtensionAction, type ExtensionsKind } from "../../stores/extensions";
import { useRuntimeStore } from "../../stores/runtime";
import type { ExtensionsItem } from "../../lib/ipc";
import ExtensionDetailPanel from "./ExtensionDetailPanel.vue";
import ExtensionFailureNotice from "./ExtensionFailureNotice.vue";
import ExtensionMarketDialog from "./ExtensionMarketDialog.vue";

const { t } = useI18n();
const store = useExtensionsStore();
const runtime = useRuntimeStore();

const KIND_TABS: { key: ExtensionsKind; labelKey: string }[] = [
  { key: "skills", labelKey: "extensions.tab.skills" },
  { key: "mcp", labelKey: "extensions.tab.mcp" },
  { key: "plugins", labelKey: "extensions.tab.plugins" },
];

const runtimeId = computed(() => runtime.runtimeSnapshot?.runtime_id ?? "");
const expandedGroupId = ref<string | null>(null);
const marketOpen = ref(false);
const selected = ref<ExtensionsItem | null>(null);

onMounted(syncContext);
watch([() => runtime.workspace, runtimeId], syncContext);
function syncContext(): void {
  if (runtime.workspace && runtimeId.value) store.setContext(runtime.workspace, runtimeId.value);
  else store.setContext("", "");
  if (store.canLoad) void store.load();
}
async function onTab(target: ExtensionsKind): Promise<void> {
  selected.value = null;
  expandedGroupId.value = null;
  await store.load(target);
}
function opBusy(action: ExtensionAction, id: string): boolean {
  const operation = store.activeOperation;
  return operation?.action === action && operation.id === id;
}
function select(item: ExtensionsItem): void {
  selected.value = selected.value?.id === item.id ? null : item;
}
function updateFor(id: string) {
  return store.updateItems[id];
}
function isUpdateAvailable(id: string): boolean {
  return updateFor(id)?.update_available === true;
}
function updateCount(ids: string[]): number {
  return ids.filter((id) => isUpdateAvailable(id)).length;
}
async function updateSelected(): Promise<void> {
  const item = selected.value;
  if (!item || store.busy) return;
  if (store.kind === "skills") await store.updateSkill(item);
  else if (store.kind === "plugins") await store.pluginAction("plugin-update", item.id);
}
</script>

<template>
  <div class="explorer-body extensions-view" data-testid="extensions-view">
    <div class="extensions-tabs" role="tablist">
      <button v-for="tab in KIND_TABS" :key="tab.key" type="button" role="tab" :aria-selected="store.kind === tab.key" :class="{ active: store.kind === tab.key }" :data-testid="'ext-tab-' + tab.key" @click="onTab(tab.key)">{{ t(tab.labelKey) }}</button>
    </div>

    <div class="extensions-toolbar">
      <button
        type="button"
        class="ui-button"
        data-testid="ext-check-updates"
        :disabled="!store.canLoad || store.updatesBusy"
        @click="store.checkUpdates()"
      >
        {{ store.updatesBusy ? t("extensions.updatesChecking") : t("extensions.checkUpdates") }}
      </button>
      <button
        type="button"
        class="ui-button primary"
        data-testid="open-extension-market"
        :disabled="!store.canLoad"
        @click="marketOpen = true"
      >{{ t("extensions.market.title") }}</button>
      <span v-if="store.updatesError" class="explorer-error" role="alert">
        {{ t("extensions.updatesCheckFailedWithDetail", { message: store.updatesError }) }}
      </span>
    </div>

    <div v-if="store.activeOperation" class="operation-progress" data-testid="ext-operation-progress" role="status">
      <span class="op-action">{{ t(`extensions.op.${store.activeOperation.action}`) }}</span>
      <span v-if="store.activeOperation.total > 1" class="op-count">
        {{ store.activeOperation.completed }}/{{ store.activeOperation.total }}
      </span>
      <span class="op-target">{{ store.activeOperation.label }}</span>
      <span class="op-progress-track" aria-hidden="true">
        <span :style="{ width: `${Math.round((store.activeOperation.completed / store.activeOperation.total) * 100)}%` }" class="op-progress-fill" />
      </span>
    </div>

    <ExtensionFailureNotice />
    <p v-if="store.error" class="explorer-error" role="alert">{{ store.error }}</p>
    <p v-if="!store.canLoad" class="explorer-empty">{{ t("extensions.noRuntime") }}</p>
    <p v-else-if="store.loading" class="explorer-empty">{{ t("explorer.loading") }}</p>
    <div v-else-if="!store.items.length" class="explorer-empty">
      <span>{{ t("extensions.empty") }}</span>
      <button type="button" class="ui-button" :disabled="!store.canLoad" @click="marketOpen = true">
        {{ t("extensions.market.open") }}
      </button>
    </div>

    <template v-else-if="store.kind === 'skills'">
      <div
        v-for="group in store.installedSkillGroups"
        :key="group.id"
        class="extensions-card"
        :data-testid="'ext-skill-group-' + group.id"
        @click="expandedGroupId = expandedGroupId === group.id ? null : group.id; selected = null"
      >
        <div class="ext-row">
          <span class="ext-chevron" aria-hidden="true">{{ expandedGroupId === group.id ? "▾" : "▸" }}</span>
          <span v-if="group.conflict" class="ext-conflict" :title="t('extensions.sourceConflict')">⚠</span>
          <span class="ext-name" :class="{ 'has-update': updateCount(group.items.map((item) => item.id)) > 0 }" :title="group.repo">{{ group.name }}</span>
          <span class="ext-badge">{{ t("extensions.skillGroupCount", { count: group.items.length }) }}</span>
          <span v-if="updateCount(group.items.map((item) => item.id)) > 0" class="update-badge">
            {{ t("extensions.updateCount", { count: updateCount(group.items.map((item) => item.id)) }) }}
          </span>
          <span class="ext-spacer" />
          <button
            v-for="agent in (['claude', 'codex'] as const)"
            :key="agent"
            type="button"
            class="ui-icon-button sm"
            :class="{ on: group.items.every((item) => (agent === 'claude' ? item.enabled_claude : item.enabled_codex) === true) }"
            :disabled="store.busy"
            :title="t('extensions.toggle', { agent })"
            @click.stop="store.toggleSkillGroup(group, agent, !group.items.every((item) => (agent === 'claude' ? item.enabled_claude : item.enabled_codex) === true))"
          >{{ agent === "claude" ? "C" : "X" }}</button>
          <button type="button" class="ui-icon-button sm" :disabled="store.busy" :title="t('extensions.updateAll')" @click.stop="store.updateSkillGroup(group)">
            <span v-if="opBusy('update', 'installed:' + group.id)" class="spinner" />
            <span v-else>⟳</span>
          </button>
          <button type="button" class="ui-icon-button sm danger" :disabled="store.busy" :title="t('extensions.removeAll')" @click.stop="store.removeSkillGroup(group)">
            <span v-if="opBusy('remove', 'installed:' + group.id)" class="spinner" />
            <span v-else>✕</span>
          </button>
        </div>
        <div v-if="expandedGroupId === group.id" class="skill-children">
          <div
            v-for="item in group.items"
            :key="item.id"
            class="ext-row skill-child"
            :class="{ selected: selected?.id === item.id }"
            :data-testid="'ext-skill-child-' + item.name"
            role="button"
            tabindex="0"
            @click.stop="select(item)"
            @keydown.enter.stop.prevent="select(item)"
          >
            <span class="ext-chevron" aria-hidden="true">·</span>
            <span class="ext-name" :class="{ 'has-update': isUpdateAvailable(item.id) }">{{ item.name }}</span>
            <span v-if="isUpdateAvailable(item.id)" class="update-badge">{{ t("extensions.updateAvailable") }}</span>
            <span class="ext-spacer" />
            <button
              v-for="agent in (['claude', 'codex'] as const)"
              :key="agent"
              type="button"
              class="ui-icon-button sm"
              :class="{ on: (agent === 'claude' ? item.enabled_claude : item.enabled_codex) === true }"
              :disabled="store.busy"
              :title="t('extensions.toggle', { agent })"
              @click.stop="store.toggle(item, agent, !((agent === 'claude' ? item.enabled_claude : item.enabled_codex)))"
            >{{ agent === "claude" ? "C" : "X" }}</button>
            <button type="button" class="ui-icon-button sm" :disabled="store.busy" :title="t('extensions.skillUpdate')" @click.stop="store.updateSkill(item)">
              <span v-if="opBusy('update', item.id)" class="spinner" /><span v-else>⟳</span>
            </button>
            <button type="button" class="ui-icon-button sm danger" :disabled="store.busy" :title="t('extensions.remove')" @click.stop="store.remove(item)">
              <span v-if="opBusy('remove', item.id)" class="spinner" /><span v-else>✕</span>
            </button>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div
        v-for="item in store.items"
        :key="item.id"
        class="extensions-card one-line"
        :class="{ selected: selected?.id === item.id }"
        :data-testid="'ext-item-' + item.id"
        role="button"
        tabindex="0"
        @click="select(item)"
        @keydown.enter.prevent="select(item)"
      >
        <div class="ext-row">
          <span class="ext-name" :class="{ 'has-update': isUpdateAvailable(item.id) }">{{ item.name }}</span>
          <span v-if="isUpdateAvailable(item.id)" class="update-badge">{{ t("extensions.updateAvailable") }}</span>
          <span v-else-if="updateFor(item.id)?.status === 'unsupported'" class="unsupported-badge">{{ t("extensions.noComparableVersion") }}</span>
          <span class="ext-badge">
            <template v-if="store.kind === 'mcp'">{{ item.transport }}</template>
            <template v-else>{{ item.marketplace }} · {{ item.version || "-" }}</template>
          </span>
          <span class="ext-spacer" />
          <template v-if="store.kind === 'mcp'">
            <button
              v-for="agent in (['claude', 'codex'] as const)"
              :key="agent"
              type="button"
              class="ui-icon-button sm"
              :class="{ on: (agent === 'claude' ? item.enabled_claude : item.enabled_codex) === true }"
              :disabled="store.busy"
              :title="t('extensions.toggle', { agent })"
              @click.stop="store.toggle(item, agent, !((agent === 'claude' ? item.enabled_claude : item.enabled_codex)))"
            >{{ agent === "claude" ? "C" : "X" }}</button>
          </template>
          <button v-if="store.kind === 'plugins'" type="button" class="ui-icon-button sm" :disabled="store.busy" :title="t('extensions.pluginUpdate')" @click.stop="store.pluginAction('plugin-update', item.id)">
            <span v-if="opBusy('update', item.id)" class="spinner" /><span v-else>⟳</span>
          </button>
          <button type="button" class="ui-icon-button sm danger" :disabled="store.busy" :title="t('extensions.remove')" @click.stop="store.remove(item)">
            <span v-if="opBusy('remove', item.id)" class="spinner" /><span v-else>✕</span>
          </button>
        </div>
      </div>
    </template>

    <ExtensionDetailPanel
      v-if="selected"
      class="installed-detail"
      :item="selected"
      :update="updateFor(selected.id)"
      @close="selected = null"
    >
      <template #actions>
        <button
          v-if="isUpdateAvailable(selected.id) && store.kind !== 'mcp'"
          type="button"
          :disabled="store.busy"
          @click="updateSelected"
        >{{ t("extensions.skillUpdate") }}</button>
        <button type="button" class="danger" :disabled="store.busy" @click="store.remove(selected)">
          {{ t("extensions.remove") }}
        </button>
      </template>
    </ExtensionDetailPanel>

    <ExtensionMarketDialog v-if="marketOpen" @close="marketOpen = false" />
  </div>
</template>

<style scoped>
.extensions-view { display: flex; flex-direction: column; min-width: 0; width: 100%; box-sizing: border-box; gap: var(--space-2); overflow: auto; }
.extensions-tabs { display: flex; gap: var(--space-1); }
.extensions-tabs button { flex: 1; min-height: var(--control-h-sm); padding: 0 var(--space-2); border: var(--border-w) solid var(--border); border-radius: var(--radius-sm); background: var(--surface-2); color: var(--text-2); cursor: pointer; }
.extensions-tabs button.active { border-color: var(--accent); color: var(--text); background: var(--surface-3); }
.extensions-toolbar { display: flex; align-items: center; gap: var(--space-2); }
.extensions-toolbar .primary { margin-left: auto; }
.extensions-card { width: 100%; min-width: 0; box-sizing: border-box; padding: 2px var(--space-2); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface); }
.extensions-card.one-line { cursor: pointer; }
.extensions-card.selected { border-color: var(--accent); background: var(--surface-2); }
.ext-row { display: flex; align-items: center; gap: 6px; min-height: 30px; width: 100%; min-width: 0; box-sizing: border-box; }
.extensions-card { cursor: pointer; }
.ext-chevron { flex: 0 0 auto; color: var(--text-faint); font-size: 10px; }
.ext-conflict { flex: 0 0 auto; color: var(--warn); font-size: 14px; }
.ext-name { flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.ext-badge { flex: 0 0 auto; max-width: 35%; overflow: hidden; text-overflow: ellipsis; font-size: var(--font-xs); color: var(--text-faint); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-full); padding: 0 6px; white-space: nowrap; }
.ext-spacer { flex: 1; }
.ext-row .ui-icon-button.on { color: var(--accent); border-color: var(--accent); }
.skill-children { display: grid; gap: 2px; margin: 2px 0 3px 14px; }
.skill-child { min-height: 28px; border-top: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); }
.skill-child.selected { background: var(--accent-soft); }
.operation-progress { display: flex; align-items: center; gap: var(--space-2); min-width: 0; padding: var(--space-1) var(--space-2); border: var(--border-w) solid var(--accent); border-radius: var(--radius-sm); background: var(--surface-2); color: var(--text-2); }
.op-action { flex: 0 0 auto; font-size: var(--font-sm); font-weight: 600; }
.op-count { flex: 0 0 auto; font-size: var(--font-xs); color: var(--text-muted); font-variant-numeric: tabular-nums; }
.op-target { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--font-xs); color: var(--text-faint); }
.op-progress-track { flex: 0 0 100%; height: 3px; overflow: hidden; border-radius: var(--radius-full); background: var(--surface-3); }
.op-progress-fill { display: block; height: 100%; border-radius: inherit; background: var(--accent); transition: width var(--duration-normal) var(--ease); }
.update-badge, .unsupported-badge { flex: none; font-size: var(--font-xs); border-radius: var(--radius-full); padding: 1px 6px; border: 1px solid currentColor; }
.update-badge { color: var(--warn); font-weight: 700; }
.unsupported-badge { color: var(--text-muted); }
.ext-name.has-update { font-weight: 800; }
.spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.installed-detail { position: sticky; bottom: 0; margin-top: var(--space-2); box-shadow: var(--shadow-soft); }
</style>
