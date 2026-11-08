<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { ExtensionModuleDefinition, ExtensionModuleMember, ExtensionsItem } from "../../lib/ipc";
import { copyModule, moduleMemberKey, useExtensionModulesStore } from "../../stores/extensionModules";
import { useExtensionsStore, type ExtensionsKind } from "../../stores/extensions";
import { EXTENSION_RECOMMENDATIONS_BY_CATEGORY } from "./recommendationCatalog";
import { skillUpdateSpec } from "./skillGroups";
import { useModuleOperationsStore } from "../../stores/moduleOperations";
import ModuleOperationProgress from "./ModuleOperationProgress.vue";

const { t } = useI18n();
const modules = useExtensionModulesStore();
const extensions = useExtensionsStore();
const operations = useModuleOperationsStore();
const draft = ref<ExtensionModuleDefinition | null>(null);
const memberKind = ref<ExtensionsKind>("skills");
const query = ref("");
const deleting = ref<string | null>(null);
const validation = ref("");
const persistenceAlert = ref<HTMLElement | null>(null);
const validationAlert = ref<HTMLElement | null>(null);
// The save button can be far below either alert in a short market dialog.
// Keep failed saves visible without discarding the draft or moving focus.
watch(() => modules.error, async (error) => {
  if (!error) return;
  await nextTick();
  persistenceAlert.value?.scrollIntoView({ block: "nearest", inline: "nearest" });
});
const searching = ref(false);
const searchError = ref("");
const searched = ref<ExtensionsKind | null>(null);
const readonly = computed(() => !!draft.value && modules.isBuiltin(draft.value.id));
const localMembers = computed(() => {
  const seen = new Set<string>();
  return Object.values(EXTENSION_RECOMMENDATIONS_BY_CATEGORY).flat()
    .filter(m => m.kind === memberKind.value && `${m.name} ${m.identity}`.toLowerCase().includes(query.value.toLowerCase()))
    .map(m => ({ kind: m.kind, identity: m.identity, name: m.name, source_url: m.sourceUrl }))
    .filter(m => { const key = moduleMemberKey(m); if (seen.has(key)) return false; seen.add(key); return true; });
});
function marketMember(item: ExtensionsItem, kind: ExtensionsKind): ExtensionModuleMember | null {
  const identity = kind === "skills" ? skillUpdateSpec(item) : item.id;
  // A local skill without repository provenance is not an installable source.
  if (!identity || (kind === "skills" && !identity.includes(":"))) return null;
  let source = item.url;
  if (kind === "skills") source = `https://github.com/${identity.split(":")[0]}`;
  if (kind === "mcp") source = `https://registry.smithery.ai/servers/${identity}`;
  if (kind === "plugins" && !source) {
    const recommendation = Object.values(EXTENSION_RECOMMENDATIONS_BY_CATEGORY).flat().find(m => m.kind === kind && m.identity === identity);
    source = recommendation?.sourceUrl;
    if (!source && /^https?:\/\//.test(item.repo ?? "")) source = item.repo;
    if (!source && /^[\w.-]+\/[\w.-]+$/.test(item.repo ?? "")) source = `https://github.com/${item.repo}`;
  }
  if (!source?.startsWith("https://") && !source?.startsWith("http://")) return null;
  return { kind, identity, name: item.name || identity, source_url: source };
}
const remoteMembers = computed(() => {
  if (searched.value !== memberKind.value) return [];
  const items = memberKind.value === "skills" ? extensions.marketSkills : memberKind.value === "mcp" ? extensions.marketMcp : extensions.marketPlugins;
  return items.map(m => marketMember(m, memberKind.value)).filter((m): m is ExtensionModuleMember => m !== null);
});
const candidates = computed(() => [...new Map([...remoteMembers.value, ...localMembers.value]
  .map(member => [moduleMemberKey(member), member])).values()]);
const unavailableSources = computed(() => {
  if (searched.value !== memberKind.value) return false;
  const items = memberKind.value === "skills" ? extensions.marketSkills : memberKind.value === "mcp" ? extensions.marketMcp : extensions.marketPlugins;
  return items.some(item => marketMember(item, memberKind.value) === null);
});
function edit(module?: ExtensionModuleDefinition, duplicate = false) {
  deleting.value = null; validation.value = "";
  draft.value = module ? copyModule(module) : { id: crypto.randomUUID(), name: "", members: [] };
  if (duplicate) { draft.value.id = crypto.randomUUID(); draft.value.name += ` ${t("modules.copySuffix")}`; }
}
function add(member: ExtensionModuleMember) {
  if (!draft.value || readonly.value || modules.busy) return;
  if (!draft.value.members.some(m => moduleMemberKey(m) === moduleMemberKey(member))) draft.value.members.push({ ...member });
}
async function save() {
  if (!draft.value) return;
  if (!draft.value.name.trim()) {
    validation.value = t("modules.nameRequired");
    await nextTick();
    validationAlert.value?.scrollIntoView({ block: "nearest", inline: "nearest" });
    return;
  }
  validation.value = "";
  if (await modules.save(draft.value)) draft.value = null;
}
async function remove(id: string) {
  if (await modules.remove(id)) { deleting.value = null; if (draft.value?.id === id) draft.value = null; }
}
async function search() {
  if (!query.value.trim() || !extensions.canLoad || searching.value) return;
  searching.value = true; searchError.value = "";
  const kind = memberKind.value;
  try {
    if (kind === "skills") await extensions.searchSkills(query.value.trim());
    else if (kind === "mcp") await extensions.searchMcp(query.value.trim());
    else await extensions.searchPlugins(query.value.trim());
    searched.value = kind;
    searchError.value = extensions.errorsByKind[kind] ?? "";
  } finally { searching.value = false; }
}
onMounted(() => modules.load());
</script>

<template>
  <section class="modules-panel" data-testid="modules-panel" :aria-label="t('modules.title')">
    <p>{{ t("modules.definitionOnly") }}</p>
    <div class="module-actions">
      <button type="button" :disabled="modules.busy" @click="modules.load">{{ t("modules.reload") }}</button>
      <button type="button" data-testid="module-new" :disabled="!modules.document || modules.busy" @click="edit()">{{ t("modules.create") }}</button>
      <button v-if="modules.document?.hidden_builtin_ids.length" type="button" :disabled="modules.busy" @click="modules.restoreBuiltins">{{ t("modules.restore") }}</button>
    </div>
    <p v-if="modules.error" ref="persistenceAlert" role="alert">{{ modules.error }}</p>
    <p v-if="!modules.busy && modules.document && !modules.modules.length">{{ t("modules.empty") }}</p>
    <ModuleOperationProgress />
    <article v-for="module in modules.modules" :key="module.id" class="module-card">
      <strong>{{ module.name }}</strong><span>{{ t("modules.memberCount", { count: module.members.length }) }}</span>
      <div class="module-actions">
        <button type="button" :disabled="!operations.canPrepare || modules.busy" @click="operations.prepare(module, 'apply')">{{ t("modules.apply") }}</button>
        <button type="button" :disabled="!operations.canPrepare || modules.busy" @click="operations.prepare(module, 'uninstall')">{{ t("modules.uninstall") }}</button>
        <button type="button" :disabled="!operations.canPrepare || modules.busy" @click="operations.history(module)">{{ t("modules.history") }}</button>
        <button type="button" :disabled="modules.busy" @click="edit(module)">{{ t("modules.edit") }}</button>
        <button type="button" :disabled="modules.busy" @click="edit(module, true)">{{ t("modules.copy") }}</button>
        <button type="button" :disabled="modules.busy" @click="deleting = module.id">{{ modules.isBuiltin(module.id) ? t("modules.hide") : t("modules.delete") }}</button>
      </div>
      <div v-if="deleting === module.id" class="module-actions">
        <span>{{ t("modules.deleteNotice") }}</span>
        <button type="button" :disabled="modules.busy" @click="remove(module.id)">{{ t("modules.confirmDelete") }}</button>
        <button type="button" :disabled="modules.busy" @click="deleting = null">{{ t("common.cancel") }}</button>
      </div>
    </article>
    <form v-if="draft" class="module-editor" data-testid="module-editor" @submit.prevent="save">
      <label>{{ t("modules.name") }}<input v-model="draft.name" data-testid="module-name" :disabled="readonly || modules.busy" maxlength="160"></label>
      <p v-if="readonly">{{ t("modules.builtinNotice") }}</p>
      <p v-if="validation" ref="validationAlert" role="alert">{{ validation }}</p>
      <ul class="module-members">
        <li v-for="member in draft.members" :key="moduleMemberKey(member)">
          <span>{{ member.name }} · {{ t(`extensions.tab.${member.kind}`) }}<small>{{ member.identity }} · {{ member.source_url }}</small></span>
          <button type="button" :disabled="readonly || modules.busy" :aria-label="t('modules.removeMember', { name: member.name })"
            @click="draft.members = draft.members.filter(m => moduleMemberKey(m) !== moduleMemberKey(member))">{{ t("modules.remove") }}</button>
        </li>
      </ul>
      <template v-if="!readonly">
        <div class="module-actions">
          <label>{{ t("modules.kind") }}<select v-model="memberKind"><option v-for="kind in (['skills', 'mcp', 'plugins'] as const)" :key="kind" :value="kind">{{ t(`extensions.tab.${kind}`) }}</option></select></label>
          <label>{{ t("modules.search") }}<input v-model="query" type="search" @keydown.enter.prevent="search"></label>
          <button type="button" :disabled="!extensions.canLoad || !query.trim() || searching" @click="search">{{ t("modules.searchMarket") }}</button>
        </div>
        <p v-if="searchError" role="alert">{{ searchError }}</p>
        <p v-if="unavailableSources">{{ t("modules.unavailableSources") }}</p>
        <p v-if="!extensions.canLoad">{{ t("modules.offlineSearch") }}</p>
        <div class="module-candidates">
          <button v-for="member in candidates" :key="moduleMemberKey(member)" type="button"
            :disabled="modules.busy || draft.members.some(m => moduleMemberKey(m) === moduleMemberKey(member))" @click="add(member)">
            {{ member.name }}<small>{{ member.identity }}</small>
          </button>
        </div>
      </template>
      <div class="module-actions">
        <button v-if="!readonly" type="submit" data-testid="module-save" :disabled="modules.busy || !modules.document">{{ t("modules.save") }}</button>
        <button type="button" :disabled="modules.busy" @click="draft = null">{{ t("common.cancel") }}</button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.modules-panel, .module-editor, .module-card { display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; }
.module-card, .module-editor { border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); padding: var(--space-3); }
.module-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; }
.modules-panel button, .modules-panel input, .modules-panel select { border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface-2); color: var(--text); padding: var(--space-1) var(--space-2); font: inherit; min-width: 0; }
.modules-panel button { cursor: pointer; }
.modules-panel button:disabled { cursor: default; opacity: 0.45; }
.modules-panel :focus-visible { outline: var(--focus-ring-width) solid var(--focus); }
.module-members { padding: 0; list-style: none; }
.module-members li { display: flex; justify-content: space-between; gap: var(--space-2); margin-bottom: var(--space-2); }
.module-members small, .module-candidates small { display: block; color: var(--text-muted); overflow-wrap: anywhere; }
.module-candidates { display: flex; flex-wrap: wrap; gap: var(--space-2); max-height: 240px; overflow: auto; }
.module-candidates button { text-align: left; }
</style>
