<script setup lang="ts">
/**
 * b5 (2.1.16, 需求 #2 + D-1..D-4): Extensions unified view — skills / MCP /
 * plugins. Renders inside the left dock rail view (never a terminal tab).
 */
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useExtensionsStore, type ExtensionsKind } from "../../stores/extensions";
import { useRuntimeStore } from "../../stores/runtime";

const { t } = useI18n();
const store = useExtensionsStore();
const runtime = useRuntimeStore();

const KIND_TABS: { key: ExtensionsKind; labelKey: string }[] = [
  { key: "skills", labelKey: "extensions.tab.skills" },
  { key: "mcp", labelKey: "extensions.tab.mcp" },
  { key: "plugins", labelKey: "extensions.tab.plugins" },
];

const runtimeId = computed(() => runtime.runtimeSnapshot?.runtime_id ?? "");
onMounted(syncContext);
watch([() => runtime.workspace, runtimeId], syncContext);
function syncContext(): void {
  if (runtime.workspace && runtimeId.value) store.setContext(runtime.workspace, runtimeId.value);
  else store.setContext("", "");
  if (store.canLoad) void store.load();
}

const skillSpec = ref("");
const mcpJson = ref("");
const pluginId = ref("");

async function onTab(target: ExtensionsKind): Promise<void> {
  await store.load(target);
}
</script>

<template>
  <div class="explorer-body extensions-view" data-testid="extensions-view">
    <div class="extensions-tabs" role="tablist">
      <button
        v-for="tab in KIND_TABS"
        :key="tab.key"
        type="button"
        role="tab"
        :aria-selected="store.kind === tab.key"
        :class="{ active: store.kind === tab.key }"
        :data-testid="'ext-tab-' + tab.key"
        @click="onTab(tab.key)"
      >{{ t(tab.labelKey) }}</button>
    </div>

    <p v-if="store.error" class="explorer-error" role="alert">{{ store.error }}</p>
    <p v-if="!store.canLoad" class="explorer-empty">{{ t("extensions.noRuntime") }}</p>
    <p v-else-if="store.loading" class="explorer-empty">{{ t("explorer.loading") }}</p>
    <p v-else-if="!store.items.length" class="explorer-empty">{{ t("extensions.empty") }}</p>

    <template v-else>
      <div v-for="item in store.items" :key="item.id" class="extensions-card" :data-testid="'ext-item-' + item.id">
        <div class="ext-head">
          <span class="ext-name" :title="item.id">{{ item.name }}</span>
          <span v-if="store.kind === 'plugins'" class="ext-badge">{{ item.marketplace }} · {{ item.version }}</span>
          <span v-else-if="store.kind === 'mcp'" class="ext-badge">{{ item.transport }}</span>
          <span v-else-if="item.repo" class="ext-badge">{{ item.repo }}</span>
        </div>
        <p class="ext-desc">{{ item.description || item.url || item.command || "" }}</p>
        <div class="ext-actions">
          <template v-if="store.kind !== 'plugins'">
            <button
              v-for="agent in (['claude', 'codex'] as const)"
              :key="agent"
              type="button"
              class="ui-icon-button sm"
              :class="{ on: item.enabled_claude === true && agent === 'claude' || item.enabled_codex === true && agent === 'codex' }"
              :disabled="store.busy"
              :title="t('extensions.toggle', { agent })"
              @click="store.toggle(item, agent, !(agent === 'claude' ? item.enabled_claude : item.enabled_codex))"
            >{{ agent === "claude" ? "C" : "X" }}</button>
          </template>
          <button
            v-if="store.kind === 'plugins'"
            type="button"
            class="ui-icon-button sm"
            :disabled="store.busy"
            :title="t('extensions.pluginUpdate')"
            @click="store.pluginAction('plugin-update', item.id)"
          >⟳</button>
          <button
            type="button"
            class="ui-icon-button sm danger"
            :disabled="store.busy"
            :title="t('extensions.remove')"
            @click="store.remove(item)"
          >✕</button>
        </div>
      </div>
    </template>

    <!-- 安装/新增区（D-3/D-4 裁定：P1 直接可装卸 + MCP 可新增） -->
    <div class="extensions-add">
      <template v-if="store.kind === 'skills'">
        <input v-model="skillSpec" type="text" :placeholder="t('extensions.skillSpec')" :aria-label="t('extensions.skillSpec')" data-testid="ext-skill-spec" @keydown.enter.prevent="void store.installSkill(skillSpec.trim()).then(() => (skillSpec = ''))" />
      </template>
      <template v-else-if="store.kind === 'mcp'">
        <textarea v-model="mcpJson" rows="3" :placeholder="t('extensions.mcpPlaceholder')" :aria-label="t('extensions.mcpPlaceholder')" data-testid="ext-mcp-json" />
        <button type="button" class="ui-button" :disabled="!mcpJson.trim() || store.busy" data-testid="ext-mcp-add" @click="store.addMcp(mcpJson.trim(), 'claude,codex').then(() => (mcpJson = ''))">{{ t("extensions.mcpAdd") }}</button>
      </template>
      <template v-else>
        <input v-model="pluginId" type="text" :placeholder="t('extensions.pluginSpec')" :aria-label="t('extensions.pluginSpec')" data-testid="ext-plugin-id" @keydown.enter.prevent="void store.pluginAction('plugin-install', pluginId.trim()).then(() => (pluginId = ''))" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.extensions-view { display: grid; gap: var(--space-2); overflow: auto; }
.extensions-tabs { display: flex; gap: var(--space-1); }
.extensions-tabs button { flex: 1; padding: 4px 8px; border: var(--border-w) solid var(--border); border-radius: var(--radius-sm); background: var(--surface-2); color: var(--text-2); cursor: pointer; }
.extensions-tabs button.active { border-color: var(--accent); color: var(--text); background: var(--surface-3); }
.extensions-card { display: grid; gap: 4px; padding: var(--space-2); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface); }
.ext-head { display: flex; align-items: center; gap: var(--space-1); min-width: 0; }
.ext-name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ext-badge { font-size: var(--font-xs); color: var(--text-faint); border: var(--border-w) solid var(--border-2); border-radius: 999px; padding: 0 6px; white-space: nowrap; }
.ext-desc { margin: 0; font-size: var(--font-xs); color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ext-actions { display: flex; gap: 4px; }
.ext-actions .on { color: var(--accent); border-color: var(--accent); }
.extensions-add { display: grid; gap: var(--space-1); padding-top: var(--space-2); border-top: var(--border-w) solid var(--border); }
.extensions-add input, .extensions-add textarea { width: 100%; box-sizing: border-box; }
</style>
