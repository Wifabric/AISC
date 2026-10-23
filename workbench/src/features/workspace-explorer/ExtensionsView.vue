<script setup lang="ts">
/**
 * Extensions unified view (b10): single-line rows, expand on click, install
 * progress spinners, Smithery MCP marketplace, skill source conflict markers.
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
const expandedId = ref<string | null>(null);
const skillQuery = ref("");
const skillLink = ref("");
const mcpJson = ref("");
const mcpLink = ref("");
const mcpQuery = ref("");
const pluginId = ref("");
const pluginQuery = ref("");
const marketSrc = ref("");

onMounted(syncContext);
watch([() => runtime.workspace, runtimeId], syncContext);
function syncContext(): void {
  if (runtime.workspace && runtimeId.value) store.setContext(runtime.workspace, runtimeId.value);
  else store.setContext("", "");
  if (store.canLoad) void store.load();
}
async function onTab(target: ExtensionsKind): Promise<void> {
  expandedId.value = null;
  await store.load(target);
  if (target === "plugins") void store.loadPluginMarkets();
}
</script>

<template>
  <div class="explorer-body extensions-view" data-testid="extensions-view">
    <div class="extensions-tabs" role="tablist">
      <button v-for="tab in KIND_TABS" :key="tab.key" type="button" role="tab" :aria-selected="store.kind === tab.key" :class="{ active: store.kind === tab.key }" :data-testid="'ext-tab-' + tab.key" @click="onTab(tab.key)">{{ t(tab.labelKey) }}</button>
    </div>

    <p v-if="store.error" class="explorer-error" role="alert">{{ store.error }}</p>
    <p v-if="!store.canLoad" class="explorer-empty">{{ t("extensions.noRuntime") }}</p>
    <p v-else-if="store.loading" class="explorer-empty">{{ t("explorer.loading") }}</p>
    <p v-else-if="!store.items.length" class="explorer-empty">{{ t("extensions.empty") }}</p>

    <template v-else>
      <div v-for="item in store.items" :key="item.id" class="extensions-card one-line" :data-testid="'ext-item-' + item.id" @click="expandedId = expandedId === item.id ? null : item.id">
        <div class="ext-row">
          <span class="ext-chevron" aria-hidden="true">{{ expandedId === item.id ? "▾" : "▸" }}</span>
          <span v-if="item.conflict" class="ext-conflict" :title="t('extensions.sourceConflict')">⚠</span>
          <span class="ext-name" :title="item.id">{{ item.name }}</span>
          <span v-if="store.kind === 'plugins'" class="ext-badge">{{ item.marketplace }} · {{ item.version }}</span>
          <span v-else-if="store.kind === 'mcp'" class="ext-badge">{{ item.transport }}</span>
          <span v-else-if="item.repo" class="ext-badge">{{ item.repo }}</span>
          <span class="ext-spacer" />
          <template v-if="store.kind !== 'plugins'">
            <button v-for="agent in (['claude', 'codex'] as const)" :key="agent" type="button" class="ui-icon-button sm" :class="{ on: (agent === 'claude' ? item.enabled_claude : item.enabled_codex) === true }" :disabled="store.busy" :title="t('extensions.toggle', { agent })" @click.stop="store.toggle(item, agent, !(agent === 'claude' ? item.enabled_claude : item.enabled_codex))">{{ agent === "claude" ? "C" : "X" }}</button>
          </template>
          <button v-if="store.kind === 'plugins'" type="button" class="ui-icon-button sm" :disabled="store.busy" :title="t('extensions.pluginUpdate')" @click.stop="store.pluginAction('plugin-update', item.id)">
            <span v-if="store.opBusyId === item.id" class="spinner" />
            <span v-else>⟳</span>
          </button>
          <button type="button" class="ui-icon-button sm danger" :disabled="store.busy" :title="t('extensions.remove')" @click.stop="store.remove(item)">
            <span v-if="store.opBusyId === item.id" class="spinner" />
            <span v-else>✕</span>
          </button>
        </div>
        <p v-if="expandedId === item.id" class="ext-desc">
          {{ item.description || item.url || item.command || item.id }}
          <span v-if="item.sources" class="ext-sources"> · {{ item.source }}</span>
        </p>
      </div>
    </template>

    <!-- 商城/安装区 -->
    <div v-if="store.kind === 'skills'" class="extensions-market">
      <div class="market-row">
        <input v-model="skillQuery" type="text" :placeholder="t('extensions.marketSearch')" :aria-label="t('extensions.marketSearch')" data-testid="ext-skill-search" @keydown.enter.prevent="store.searchSkills(skillQuery.trim())" />
        <button type="button" class="ui-button" :disabled="!skillQuery.trim() || store.marketBusy" data-testid="ext-skill-search-btn" @click="store.searchSkills(skillQuery.trim())">{{ t("extensions.marketSearchBtn") }}</button>
      </div>
      <div v-for="m in store.marketSkills" :key="m.id" class="market-hit" @click="expandedId = expandedId === m.id ? null : m.id">
        <span class="ext-chevron" aria-hidden="true">{{ expandedId === m.id ? "▾" : "▸" }}</span>
        <span class="mh-name" :title="m.id">{{ m.name }}</span>
        <span class="mh-meta">{{ m.repo }} · ⬇ {{ m.installs }}</span>
        <span class="ext-spacer" />
        <button type="button" class="ui-icon-button sm" :disabled="store.busy" :title="t('extensions.install')" @click.stop="store.installSkill(m.id)">
          <span v-if="store.opBusyId === m.id" class="spinner" />
          <span v-else>＋</span>
        </button>
        <p v-if="expandedId === m.id" class="mh-detail">{{ m.id }} · {{ m.repo }}:{{ m.directory }}</p>
      </div>
      <div class="market-row">
        <input v-model="skillLink" type="text" :placeholder="t('extensions.skillLink')" :aria-label="t('extensions.skillLink')" data-testid="ext-skill-repo" @keydown.enter.prevent="void store.addSkillRepo(skillLink.trim()).then(() => (skillLink = ''))" />
        <button type="button" class="ui-icon-button sm" :disabled="!skillLink.trim() || store.busy" :title="t('extensions.install')" @click="store.addSkillRepo(skillLink.trim()).then(() => (skillLink = ''))">＋</button>
      </div>
    </div>

    <div v-else-if="store.kind === 'mcp'" class="extensions-market">
      <div class="market-row">
        <input v-model="mcpQuery" type="text" :placeholder="t('extensions.mcpMarketSearch')" :aria-label="t('extensions.mcpMarketSearch')" data-testid="ext-mcp-search" @keydown.enter.prevent="store.searchMcp(mcpQuery.trim())" />
        <button type="button" class="ui-button" :disabled="!mcpQuery.trim() || store.marketBusy" data-testid="ext-mcp-search-btn" @click="store.searchMcp(mcpQuery.trim())">{{ t("extensions.marketSearchBtn") }}</button>
      </div>
      <div v-for="m in store.marketMcp" :key="m.id" class="market-hit" @click="expandedId = expandedId === m.id ? null : m.id">
        <span class="ext-chevron" aria-hidden="true">{{ expandedId === m.id ? "▾" : "▸" }}</span>
        <span class="mh-name" :title="m.id">{{ m.name }}</span>
        <span class="mh-meta">{{ m.repo }} · ⬇ {{ m.installs }}</span>
        <span class="ext-spacer" />
        <button type="button" class="ui-icon-button sm" :disabled="store.busy" :title="t('extensions.install')" @click.stop="store.installMcpMarket(m.id)">
          <span v-if="store.opBusyId === m.id" class="spinner" />
          <span v-else>＋</span>
        </button>
        <p v-if="expandedId === m.id" class="mh-detail">{{ m.description }}</p>
      </div>
      <div class="market-row">
        <input v-model="mcpLink" type="text" :placeholder="t('extensions.mcpLink')" :aria-label="t('extensions.mcpLink')" data-testid="ext-mcp-link" @keydown.enter.prevent="void store.importDeeplink(mcpLink.trim()).then(() => (mcpLink = ''))" />
        <button type="button" class="ui-button" :disabled="!mcpLink.trim() || store.busy" data-testid="ext-mcp-link-btn" @click="store.importDeeplink(mcpLink.trim()).then(() => (mcpLink = ''))">{{ t("extensions.mcpLinkBtn") }}</button>
      </div>
      <textarea v-model="mcpJson" rows="3" :placeholder="t('extensions.mcpPlaceholder')" :aria-label="t('extensions.mcpPlaceholder')" data-testid="ext-mcp-json" />
      <button type="button" class="ui-button" :disabled="!mcpJson.trim() || store.busy" data-testid="ext-mcp-add" @click="store.addMcp(mcpJson.trim(), 'claude,codex').then(() => (mcpJson = ''))">{{ t("extensions.mcpAdd") }}</button>
    </div>

    <div v-else class="extensions-market">
      <div class="market-row">
        <input v-model="pluginQuery" type="text" :placeholder="t('extensions.pluginMarketSearch')" :aria-label="t('extensions.pluginMarketSearch')" data-testid="ext-plugin-search" @keydown.enter.prevent="store.searchPlugins(pluginQuery.trim())" />
        <button type="button" class="ui-button" :disabled="!pluginQuery.trim() || store.marketBusy" data-testid="ext-plugin-search-btn" @click="store.searchPlugins(pluginQuery.trim())">{{ t("extensions.marketSearchBtn") }}</button>
      </div>
      <div v-for="m in store.marketPlugins" :key="m.id" class="market-hit" @click="expandedId = expandedId === m.id ? null : m.id">
        <span class="ext-chevron" aria-hidden="true">{{ expandedId === m.id ? "▾" : "▸" }}</span>
        <span class="mh-name" :title="m.id">{{ m.name }}</span>
        <span class="mh-meta">{{ m.marketplace }} · ⬇ {{ m.installs }}</span>
        <span class="ext-spacer" />
        <button type="button" class="ui-icon-button sm" :disabled="store.busy" :title="t('extensions.install')" @click.stop="store.pluginAction('plugin-install', m.id)">
          <span v-if="store.opBusyId === m.id" class="spinner" />
          <span v-else>＋</span>
        </button>
        <p v-if="expandedId === m.id" class="mh-detail">{{ m.description }}{{ m.repo ? ` · ${m.repo}` : "" }}</p>
      </div>
      <div class="market-row">
        <input v-model="pluginId" type="text" :placeholder="t('extensions.pluginSpec')" :aria-label="t('extensions.pluginSpec')" data-testid="ext-plugin-id" @keydown.enter.prevent="void store.pluginAction('plugin-install', pluginId.trim()).then(() => (pluginId = ''))" />
        <button type="button" class="ui-icon-button sm" :disabled="!pluginId.trim() || store.busy" :title="t('extensions.install')" @click="store.pluginAction('plugin-install', pluginId.trim()).then(() => (pluginId = ''))">
          <span v-if="store.opBusyId === pluginId" class="spinner" />
          <span v-else>＋</span>
        </button>
      </div>
      <div class="market-row">
        <input v-model="marketSrc" type="text" :placeholder="t('extensions.pluginMarketLink')" :aria-label="t('extensions.pluginMarketLink')" data-testid="ext-market-add" @keydown.enter.prevent="void store.addPluginMarket(marketSrc.trim()).then(() => (marketSrc = ''))" />
        <button type="button" class="ui-button" :disabled="!marketSrc.trim() || store.busy" data-testid="ext-market-add-btn" @click="store.addPluginMarket(marketSrc.trim()).then(() => (marketSrc = ''))">{{ t("extensions.pluginMarketAdd") }}</button>
      </div>
      <div v-for="m in store.pluginMarkets" :key="m.id" class="market-hit" @click="expandedId = expandedId === m.id ? null : m.id">
        <span class="ext-chevron" aria-hidden="true">{{ expandedId === m.id ? "▾" : "▸" }}</span>
        <span class="mh-name">{{ m.name }}</span>
        <span class="ext-spacer" />
        <p v-if="expandedId === m.id" class="mh-detail">{{ m.source }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.extensions-view { display: grid; gap: var(--space-2); overflow: auto; align-content: start; }
.extensions-tabs { display: flex; gap: var(--space-1); }
.extensions-tabs button { flex: 1; padding: 4px 8px; border: var(--border-w) solid var(--border); border-radius: var(--radius-sm); background: var(--surface-2); color: var(--text-2); cursor: pointer; }
.extensions-tabs button.active { border-color: var(--accent); color: var(--text); background: var(--surface-3); }
.extensions-card { padding: 2px var(--space-2); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface); }
.extensions-card.one-line { padding: 2px var(--space-2); }
.ext-row { display: flex; align-items: center; gap: 6px; min-height: 28px; cursor: pointer; }
.ext-chevron { flex: 0 0 auto; color: var(--text-faint); font-size: 10px; }
.ext-conflict { flex: 0 0 auto; color: var(--warn); font-size: 14px; }
.ext-name { flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.ext-badge { flex: 0 0 auto; font-size: var(--font-xs); color: var(--text-faint); border: var(--border-w) solid var(--border-2); border-radius: 999px; padding: 0 6px; white-space: nowrap; }
.ext-spacer { flex: 1; }
.ext-row .ui-icon-button.on { color: var(--accent); border-color: var(--accent); }
.ext-desc { margin: 2px 0 4px 18px; font-size: var(--font-xs); color: var(--text-muted); overflow-wrap: anywhere; }
.ext-sources { color: var(--text-faint); }
.extensions-market { display: grid; gap: var(--space-1); padding-top: var(--space-2); border-top: var(--border-w) solid var(--border); }
.market-row { display: flex; gap: var(--space-1); }
.market-row input, .extensions-market textarea { width: 100%; box-sizing: border-box; flex: 1; min-width: 0; }
.market-hit { position: relative; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 4px var(--space-1); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface-2); cursor: pointer; }
.mh-name { font-size: var(--font-sm); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mh-meta { flex: 1; font-size: var(--font-xs); color: var(--text-faint); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mh-detail { flex-basis: 100%; margin: 2px 0 0 14px; font-size: var(--font-xs); color: var(--text-faint); overflow-wrap: anywhere; }
.spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
