<script setup lang="ts">
/**
 * R2: the main Extensions view owns installed assets. Discovery, categorized
 * recommendations, and source maintenance live in ExtensionMarketDialog.
 */
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useExtensionsStore, type ExtensionAction, type ExtensionsKind } from "../../stores/extensions";
import { useRuntimeStore } from "../../stores/runtime";
import type { ExtensionsItem } from "../../lib/ipc";
import ExtensionDetailPanel from "./ExtensionItemDetail.vue";
import { skillGroupSummary } from "./extensionSummaries";
import ExtensionFailureNotice from "./ExtensionFailureNotice.vue";
import ExtensionMarketDialog from "./ExtensionMarketDialog.vue";

const { t, locale } = useI18n();
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
const marketButtonRef = ref<HTMLButtonElement | null>(null);
const selected = ref<ExtensionsItem | null>(null);

onMounted(syncContext);
watch([() => runtime.workspace, runtimeId], syncContext);
function syncContext(): void {
  selected.value = null;
  expandedGroupId.value = null;
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
async function closeDetail(item: ExtensionsItem): Promise<void> {
  selected.value = null;
  await nextTick();
  document.getElementById(`installed-header-${item.id}`)?.focus();
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
function openMarket(): void {
  marketOpen.value = true;
}

async function closeMarket(): Promise<void> {
  marketOpen.value = false;
  await nextTick();
  marketButtonRef.value?.focus();
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
        ref="marketButtonRef"
        data-testid="open-extension-market"
        :disabled="!store.canLoad"
        @click="openMarket"
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
    <p v-else-if="!store.items.length" class="explorer-empty">
      {{ t("extensions.empty") }}
    </p>

    <template v-else-if="store.kind === 'skills'">
      <div
        v-for="group in store.installedSkillGroups"
        :key="group.id"
        class="extensions-card"
        :data-testid="'ext-skill-group-' + group.id"
      >
        <div class="ext-row">
          <button
            type="button"
            class="group-header"
            :data-testid="'ext-skill-header-' + group.id"
            :aria-expanded="expandedGroupId === group.id"
            :aria-controls="'ext-skill-children-' + group.id"
            @click="expandedGroupId = expandedGroupId === group.id ? null : group.id; selected = null"
          >
            <span class="ext-chevron" aria-hidden="true">{{ expandedGroupId === group.id ? '▾' : '▸' }}</span>
            <span v-if="group.conflict" class="ext-conflict" :title="t('extensions.sourceConflict')">⚠</span>
            <span class="ext-name" :class="{ 'has-update': updateCount(group.items.map((item) => item.id)) > 0 }" :title="group.repo">{{ group.name }}</span>
            <span class="ext-badge">{{ t("extensions.skillGroupCount", { count: group.items.length }) }}</span>
            <span v-if="updateCount(group.items.map((item) => item.id)) > 0" class="update-badge">
              {{ t("extensions.updateCount", { count: updateCount(group.items.map((item) => item.id)) }) }}
            </span>
          </button>
          <button
            v-for="agent in (['claude', 'codex'] as const)"
            :key="agent"
            type="button"
            class="ui-icon-button sm"
            :class="{ on: group.items.every((item) => (agent === 'claude' ? item.enabled_claude : item.enabled_codex) === true) }"
            :disabled="store.busy"
            :title="t('extensions.toggle', { agent })"
            @click.stop="store.toggleSkillGroup(group, agent, !group.items.every((item) => (agent === 'claude' ? item.enabled_claude : item.enabled_codex) === true))"
            @keydown.enter.prevent="store.toggleSkillGroup(group, agent, !group.items.every((item) => (agent === 'claude' ? item.enabled_claude : item.enabled_codex) === true))"
            @keydown.space.prevent="store.toggleSkillGroup(group, agent, !group.items.every((item) => (agent === 'claude' ? item.enabled_claude : item.enabled_codex) === true))"
          >{{ agent === "claude" ? "C" : "X" }}</button>
          <button type="button" class="ui-icon-button sm" :disabled="store.busy" :title="t('extensions.updateAll')" @click.stop="store.updateSkillGroup(group)"
            @keydown.enter.prevent="store.updateSkillGroup(group)"
            @keydown.space.prevent="store.updateSkillGroup(group)">
            <span v-if="opBusy('update', 'installed:' + group.id)" class="spinner" />
            <span v-else>⟳</span>
          </button>
          <button type="button" class="ui-icon-button sm danger" :disabled="store.busy" :title="t('extensions.removeAll')" @click.stop="store.removeSkillGroup(group)"
            @keydown.enter.prevent="store.removeSkillGroup(group)"
            @keydown.space.prevent="store.removeSkillGroup(group)">
            <span v-if="opBusy('remove', 'installed:' + group.id)" class="spinner" />
            <span v-else>✕</span>
          </button>
        </div>
        <div v-if="expandedGroupId === group.id" :id="'ext-skill-children-' + group.id" class="skill-children">
          <p class="group-summary" data-testid="installed-group-summary">{{ skillGroupSummary(group, locale === 'en-US' ? 'en-US' : 'zh-CN') }}</p>
          <div
            v-for="item in group.items"
            :key="item.id"
            class="skill-child"
            :class="{ selected: selected?.id === item.id }"
            :data-testid="'ext-skill-child-' + item.name"
          >
            <div class="ext-row">
            <button
              type="button"
              class="row-main"
              :data-testid="'ext-skill-child-header-' + item.name"
              :id="'installed-header-' + item.id"
              :aria-controls="selected?.id === item.id ? 'installed-detail-' + item.id : undefined"
              :aria-expanded="selected?.id === item.id"
              @click="select(item)"
              @keydown.enter.prevent="select(item)"
              @keydown.space.prevent="select(item)"
            >
              <span class="ext-chevron" aria-hidden="true">·</span>
              <span class="ext-name" :class="{ 'has-update': isUpdateAvailable(item.id) }">{{ item.name }}</span>
              <span v-if="isUpdateAvailable(item.id)" class="update-badge">{{ t("extensions.updateAvailable") }}</span>
            </button>
            <button
              v-for="agent in (['claude', 'codex'] as const)"
              :key="agent"
              type="button"
              class="ui-icon-button sm"
              :class="{ on: (agent === 'claude' ? item.enabled_claude : item.enabled_codex) === true }"
              :disabled="store.busy"
              :title="t('extensions.toggle', { agent })"
              @click.stop="store.toggle(item, agent, !((agent === 'claude' ? item.enabled_claude : item.enabled_codex)))"
              @keydown.enter.prevent="store.toggle(item, agent, !((agent === 'claude' ? item.enabled_claude : item.enabled_codex)))"
              @keydown.space.prevent="store.toggle(item, agent, !((agent === 'claude' ? item.enabled_claude : item.enabled_codex)))"
            >{{ agent === "claude" ? "C" : "X" }}</button>
            <button
              type="button"
              class="ui-icon-button sm"
              :disabled="store.busy"
              :title="t('extensions.skillUpdate')"
              @click.stop="store.updateSkill(item)"
              @keydown.enter.prevent="store.updateSkill(item)"
              @keydown.space.prevent="store.updateSkill(item)"
            >
              <span v-if="opBusy('update', item.id)" class="spinner" /><span v-else>⟳</span>
            </button>
            <button
              type="button"
              class="ui-icon-button sm danger"
              :disabled="store.busy"
              :title="t('extensions.remove')"
              @click.stop="store.remove(item)"
              @keydown.enter.prevent="store.remove(item)"
              @keydown.space.prevent="store.remove(item)"
            >
              <span v-if="opBusy('remove', item.id)" class="spinner" /><span v-else>✕</span>
            </button>
            </div>
            <ExtensionDetailPanel v-if="selected?.id === item.id" class="installed-detail"
              :id="'installed-detail-' + item.id" :item="item" :update="updateFor(item.id)" @close="closeDetail(item)" />
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
      >
        <div class="ext-row">
          <button
            type="button"
            class="row-main"
            :data-testid="'ext-item-header-' + item.id"
            :id="'installed-header-' + item.id"
            :aria-controls="selected?.id === item.id ? 'installed-detail-' + item.id : undefined"
            :aria-expanded="selected?.id === item.id"
            @click="select(item)"
            @keydown.enter.prevent="select(item)"
            @keydown.space.prevent="select(item)"
          >
            <span class="ext-name" :class="{ 'has-update': isUpdateAvailable(item.id) }">{{ item.name }}</span>
            <span v-if="isUpdateAvailable(item.id)" class="update-badge">{{ t("extensions.updateAvailable") }}</span>
            <span v-else-if="updateFor(item.id)?.status === 'unsupported'" class="unsupported-badge">{{ t("extensions.noComparableVersion") }}</span>
            <span class="ext-badge">
              <template v-if="store.kind === 'mcp'">{{ item.transport }}</template>
              <template v-else>{{ item.marketplace }} · {{ item.version || "-" }}</template>
            </span>
          </button>
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
              @keydown.enter.prevent="store.toggle(item, agent, !((agent === 'claude' ? item.enabled_claude : item.enabled_codex)))"
              @keydown.space.prevent="store.toggle(item, agent, !((agent === 'claude' ? item.enabled_claude : item.enabled_codex)))"
            >{{ agent === "claude" ? "C" : "X" }}</button>
          </template>
          <button
            v-if="store.kind === 'plugins'"
            type="button"
            class="ui-icon-button sm"
            :disabled="store.busy"
            :title="t('extensions.pluginUpdate')"
            @click.stop="store.pluginAction('plugin-update', item.id)"
            @keydown.enter.prevent="store.pluginAction('plugin-update', item.id)"
            @keydown.space.prevent="store.pluginAction('plugin-update', item.id)"
          >
            <span v-if="opBusy('update', item.id)" class="spinner" /><span v-else>⟳</span>
          </button>
          <button
            type="button"
            class="ui-icon-button sm danger"
            :disabled="store.busy"
            :title="t('extensions.remove')"
            @click.stop="store.remove(item)"
            @keydown.enter.prevent="store.remove(item)"
            @keydown.space.prevent="store.remove(item)"
          >
            <span v-if="opBusy('remove', item.id)" class="spinner" /><span v-else>✕</span>
          </button>
        </div>
        <ExtensionDetailPanel v-if="selected?.id === item.id" class="installed-detail"
          :id="'installed-detail-' + item.id" :item="item" :update="updateFor(item.id)" @close="closeDetail(item)" />
      </div>

    </template>

    <ExtensionMarketDialog v-if="marketOpen" @close="closeMarket" />
  </div>
</template>

<style scoped>
.extensions-view { display: flex; flex-direction: column; min-width: 0; width: 100%; box-sizing: border-box; gap: var(--space-2); overflow: auto; }
.extensions-tabs { display: flex; gap: var(--space-1); }
.extensions-tabs button { flex: 1; min-height: var(--control-h-sm); padding: 0 var(--space-2); border: var(--border-w) solid var(--border); border-radius: var(--radius-sm); background: var(--surface-2); color: var(--text-2); cursor: pointer; }
.extensions-tabs button.active { border-color: var(--accent); color: var(--text); background: var(--surface-3); }
.extensions-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
.extensions-toolbar > button { flex-shrink: 0; }
.extensions-toolbar .explorer-error { flex: 1 0 100%; margin: 0; overflow-wrap: anywhere; }
.extensions-toolbar .primary { margin-left: auto; }
.extensions-card { width: 100%; min-width: 0; box-sizing: border-box; padding: 2px var(--space-2); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface); }
.extensions-card.one-line { cursor: pointer; }
.extensions-card.selected { border-color: var(--accent); background: var(--surface-2); }
.ext-row { display: flex; align-items: center; gap: 6px; min-height: 30px; width: 100%; min-width: 0; box-sizing: border-box; }
.group-header {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  min-width: 0;
  gap: 6px;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.group-header:focus-visible { outline: var(--focus-ring-width) solid var(--focus); outline-offset: calc(-1 * var(--focus-ring-width)); border-radius: var(--radius-sm); }
.row-main {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  min-width: 0;
  gap: 6px;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.row-main:focus-visible { outline: var(--focus-ring-width) solid var(--focus); outline-offset: calc(-1 * var(--focus-ring-width)); border-radius: var(--radius-sm); }
.extensions-card { cursor: default; }
.ext-chevron { flex: 0 0 auto; color: var(--text-faint); font-size: 10px; }
.ext-conflict { flex: 0 0 auto; color: var(--warn); font-size: 14px; }
.ext-name { flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.ext-badge { flex: 0 0 auto; max-width: 35%; overflow: hidden; text-overflow: ellipsis; font-size: var(--font-xs); color: var(--text-faint); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-full); padding: 0 6px; white-space: nowrap; }
.ext-spacer { flex: 1; }
.ext-row .ui-icon-button.on { color: var(--accent); border-color: var(--accent); }
.skill-children { display: grid; min-width: 0; gap: 2px; margin: 2px 0 3px; }
.skill-child { min-height: 28px; border-top: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); }
.skill-child.selected { background: var(--surface-2); }
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
.installed-detail { margin: var(--space-2) 0; }
.group-summary { margin: var(--space-2) 0; color: var(--text-2); font-size: var(--font-sm); line-height: var(--leading-relaxed); overflow-wrap: anywhere; }
.extensions-view > * { flex-shrink: 0; }
.ext-row .ui-icon-button { flex-shrink: 0; }
.ext-row .ui-icon-button.sm { width: 24px; height: 26px; padding: 2px; }
</style>
