<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { ExtensionsItem } from "../../lib/ipc";
import { useExtensionsStore, type ExtensionsKind } from "../../stores/extensions";
import ExtensionDetailPanel from "./ExtensionDetailPanel.vue";
import ExtensionSourceManager from "./ExtensionSourceManager.vue";
import {
  EXTENSION_RECOMMENDATION_CATEGORIES,
  EXTENSION_RECOMMENDATIONS_BY_CATEGORY,
  type CategorizedRecommendation,
  type RecommendationCategoryId,
} from "./recommendationCatalog";

type MarketTab = "recommendations" | ExtensionsKind | "sources";

const { t } = useI18n();
const store = useExtensionsStore();
const emit = defineEmits<{ close: [] }>();

const tabs: { key: MarketTab; labelKey: string }[] = [
  { key: "recommendations", labelKey: "extensions.market.tabRecommendations" },
  { key: "skills", labelKey: "extensions.tab.skills" },
  { key: "mcp", labelKey: "extensions.tab.mcp" },
  { key: "plugins", labelKey: "extensions.tab.plugins" },
  { key: "sources", labelKey: "extensions.market.tabSources" },
];
const activeTab = ref<MarketTab>("recommendations");
const activeCategory = ref<RecommendationCategoryId>("research");
const query = ref("");
const selectedRecommendation = ref<CategorizedRecommendation | null>(null);
const selectedMarketItem = ref<ExtensionsItem | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const closeRef = ref<HTMLButtonElement | null>(null);

const recommendations = computed(() =>
  EXTENSION_RECOMMENDATIONS_BY_CATEGORY[activeCategory.value],
);
const marketSkillGroups = computed(() => store.marketSkillGroups);
const marketItems = computed<ExtensionsItem[]>(() => {
  if (activeTab.value === "skills") return store.marketSkills;
  if (activeTab.value === "mcp") return store.marketMcp;
  if (activeTab.value === "plugins") return store.marketPlugins;
  return [];
});
const detailRecommendation = computed(() => {
  if (selectedRecommendation.value) return selectedRecommendation.value;
  const item = selectedMarketItem.value;
  if (!item) return undefined;
  const direct = EXTENSION_RECOMMENDATIONS_BY_CATEGORY[activeCategory.value].find(
    (entry) => entry.kind === item.kind && entry.identity === item.id,
  );
  if (direct) return direct;
  const category = (Object.keys(EXTENSION_RECOMMENDATIONS_BY_CATEGORY) as RecommendationCategoryId[])
    .find((value) => EXTENSION_RECOMMENDATIONS_BY_CATEGORY[value].some(
      (entry) => entry.kind === item.kind && entry.identity === item.id,
    ));
  return category
    ? EXTENSION_RECOMMENDATIONS_BY_CATEGORY[category].find(
      (entry) => entry.kind === item.kind && entry.identity === item.id,
    )
    : undefined;
});
const detailItem = computed<ExtensionsItem | null>(() =>
  selectedMarketItem.value ?? (selectedRecommendation.value ? {
    kind: selectedRecommendation.value.kind,
    id: selectedRecommendation.value.identity,
    name: selectedRecommendation.value.name,
    repo: selectedRecommendation.value.identity.split(":", 1)[0],
    directory: selectedRecommendation.value.identity.split(":")[1] ?? "",
    description: selectedRecommendation.value.summaryEn,
    ...(selectedRecommendation.value.heat ? { installs: selectedRecommendation.value.heat } : {}),
  } : null),
);
const locale = computed(() => (useI18n().locale.value === "en-US" ? "en-US" : "zh-CN") as "en-US" | "zh-CN");
const marketCache = computed(() => {
  if (activeTab.value === "skills") return store.marketCacheByKind.skills;
  if (activeTab.value === "mcp") return store.marketCacheByKind.mcp;
  if (activeTab.value === "plugins") return store.marketCacheByKind.plugins;
  return null;
});
function categoryLabel(category: { labelZh: string; labelEn: string }): string {
  return locale.value === "en-US" ? category.labelEn : category.labelZh;
}
function recommendationSummary(entry: { summaryZh: string; summaryEn: string }): string {
  return locale.value === "en-US" ? entry.summaryEn : entry.summaryZh;
}
function heatLabel(entry: {
  heat?: string;
  heatSource: "skills.sh" | "smithery" | "official-directory";
}): string {
  return entry.heat
    ? `${entry.heat} · ${heatSourceLabel(entry.heatSource)}`
    : heatSourceLabel(entry.heatSource);
}

function heatSourceLabel(source: "skills.sh" | "smithery" | "official-directory"): string {
  if (source === "skills.sh") return t("extensions.market.skillsHeatSource");
  if (source === "smithery") return t("extensions.market.smitheryHeatSource");
  return t("extensions.market.officialDirectory");
}
function formatCacheTime(value?: number | string): string {
  if (value === undefined || value === null || value === "") return "";
  const numeric = typeof value === "number" ? value : Number(value);
  const date = Number.isFinite(numeric) && numeric > 0
    ? new Date(numeric < 1_000_000_000_000 ? numeric * 1000 : numeric)
    : new Date(String(value));
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString(locale.value);
}

const searchPlaceholder = computed(() => {
  if (activeTab.value === "skills") return t("extensions.market.searchSkills");
  if (activeTab.value === "mcp") return t("extensions.mcpMarketSearch");
  if (activeTab.value === "plugins") return t("extensions.pluginMarketSearch");
  return t("extensions.market.searchRecommendations");
});

function onTabArrow(direction: 1 | -1): void {
  const buttons = [...panelRef.value?.querySelectorAll<HTMLElement>("[data-testid^='market-tab-']") ?? []];
  if (buttons.length === 0) return;
  const current = buttons.findIndex((button) => button === document.activeElement);
  const next = buttons[(current === -1 ? 0 : current + direction + buttons.length) % buttons.length];
  next?.focus();
  next?.click();
}

async function selectTab(target: MarketTab): Promise<void> {
  activeTab.value = target;
  selectedMarketItem.value = null;
  if (target === "sources") {
    await Promise.all([store.loadSkillRepos(), store.loadPluginMarkets()]);
    return;
  }
  if (target === "recommendations") return;
  store.kind = target;
  await store.load(target);
}

function selectRecommendation(entry: CategorizedRecommendation): void {
  selectedRecommendation.value = entry;
  selectedMarketItem.value = null;
}

function selectMarketItem(item: ExtensionsItem | null): void {
  selectedRecommendation.value = null;
  selectedMarketItem.value = item;
}

async function searchSelectedRecommendation(): Promise<void> {
  const entry = selectedRecommendation.value;
  if (!entry || !store.canLoad || store.marketBusy) return;
  await selectTab(entry.kind);
  query.value = entry.query;
  if (entry.kind === "skills") await store.searchSkills(entry.query);
  else if (entry.kind === "mcp") await store.searchMcp(entry.query);
  else await store.searchPlugins(entry.query);
}

async function searchActiveKind(): Promise<void> {
  const value = query.value.trim();
  if (!value || !store.canLoad || store.marketBusy) return;
  if (activeTab.value === "skills") await store.searchSkills(value);
  else if (activeTab.value === "mcp") await store.searchMcp(value);
  else if (activeTab.value === "plugins") await store.searchPlugins(value);
}

async function installDetail(): Promise<void> {
  const item = selectedMarketItem.value;
  if (!item || store.busy) return;
  if (item.kind === "market-skill" || item.kind === "skills") {
    await store.installSkill(item.id);
  } else if (item.kind === "market-mcp" || item.kind === "mcp") {
    await store.installMcpMarket(item.id);
  } else if (item.kind === "market-plugin" || item.kind === "plugins") {
    await store.pluginAction("plugin-install", item.id);
  }
}

function focusables(): HTMLElement[] {
  if (!panelRef.value) return [];
  return [...panelRef.value.querySelectorAll<HTMLElement>(
    "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])",
  )].filter((element) => element.offsetParent !== null || element === document.activeElement);
}

async function onTabKey(event: KeyboardEvent): Promise<void> {
  const items = focusables();
  if (items.length === 0) return;
  const index = items.indexOf(document.activeElement as HTMLElement);
  const nextIndex = event.shiftKey
    ? (index <= 0 ? items.length - 1 : index - 1)
    : (index === -1 || index === items.length - 1 ? 0 : index + 1);
  items[nextIndex]?.focus();
}

onMounted(async () => {
  await nextTick();
  closeRef.value?.focus();
});
</script>

<template>
  <Teleport to="body">
    <div class="market-backdrop" data-testid="extension-market-backdrop" @mousedown.self="emit('close')">
      <section
        ref="panelRef"
        class="extension-market-dialog"
        data-testid="extension-market-dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="t('extensions.market.title')"
        tabindex="-1"
        @keydown.escape.stop="emit('close')"
        @keydown.tab.prevent="onTabKey"
      >
        <header class="market-header">
          <div>
            <h2>{{ t("extensions.market.title") }}</h2>
            <p>{{ t("extensions.market.subtitle") }}</p>
          </div>
          <button ref="closeRef" type="button" data-testid="market-close" @click="emit('close')">
            {{ t("common.close") }}
          </button>
        </header>

        <div
          class="market-tabs"
          role="tablist"
          :aria-label="t('extensions.market.title')"
          @keydown.left.prevent="onTabArrow(-1)"
          @keydown.right.prevent="onTabArrow(1)"
        >
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.key"
            :class="{ active: activeTab === tab.key }"
            :id="'market-tab-' + tab.key"
            :aria-controls="'market-panel-' + tab.key"
            :data-testid="'market-tab-' + tab.key"
            @click="selectTab(tab.key)"
          >{{ t(tab.labelKey) }}</button>
        </div>

        <div
          :id="'market-panel-' + activeTab"
          class="market-body"
          role="tabpanel"
          :aria-labelledby="'market-tab-' + activeTab"
        >
          <div v-if="activeTab === 'recommendations'" class="recommendation-pane">
            <div class="category-chips" role="group" :aria-label="t('extensions.market.categories')">
              <button
                v-for="category in EXTENSION_RECOMMENDATION_CATEGORIES"
                :key="category.id"
                type="button"
                :class="{ active: activeCategory === category.id }"
                data-testid="recommendation-category"
                :aria-pressed="activeCategory === category.id"
                @click="activeCategory = category.id; selectedRecommendation = null"
              >{{ categoryLabel(category) }}</button>
            </div>
            <div class="recommendation-list">
              <article
                v-for="entry in recommendations"
                :key="`${entry.kind}:${entry.identity}`"
                class="recommendation-card"
                data-testid="recommendation-card"
                tabindex="0"
                role="button"
                @click="selectRecommendation(entry)"
                @keydown.enter.prevent="selectRecommendation(entry)"
                @keydown.space.prevent="selectRecommendation(entry)"
              >
                <header>
                  <strong>{{ entry.name }}</strong>
                  <span>{{ t(`extensions.tab.${entry.kind}`) }}</span>
                </header>
                <p>{{ recommendationSummary(entry) }}</p>
                <footer>
                  <span>{{ heatLabel(entry) }}</span>
                </footer>
              </article>
            </div>
          </div>

          <div v-else-if="activeTab !== 'sources'" class="search-pane">
            <form class="market-search" @submit.prevent="searchActiveKind">
              <input v-model="query" type="search" :aria-label="searchPlaceholder" :placeholder="searchPlaceholder">
              <button type="submit" :disabled="!query.trim() || !store.canLoad || store.marketBusy">
                {{ t("extensions.marketSearchBtn") }}
              </button>
            </form>
            <p
              v-if="marketCache"
              class="market-cache"
              data-testid="market-cache"
            >
              {{ marketCache.cached ? t("extensions.marketCache") : t("extensions.marketRefreshed") }}
              <span v-if="marketCache.fetched_at"> · {{ t("extensions.marketCacheAt") }}{{ formatCacheTime(marketCache.fetched_at) }}</span>
              <span v-if="marketCache.error"> · {{ marketCache.error }}</span>
            </p>

            <p
              v-if="store.error"
              class="market-search-error"
              data-testid="market-search-error"
              role="alert"
            >{{ store.error }}</p>

            <div class="market-results">
              <template v-if="activeTab === 'skills'">
                <section
                  v-for="group in marketSkillGroups"
                  :key="group.id"
                  class="market-group"
                  :data-testid="'market-group-' + group.id"
                >
                  <div class="market-group-head">
                    <button type="button" class="market-result group-parent" @click="selectMarketItem(group.items[0] ?? null)">
                      <strong>{{ group.name }}</strong>
                      <span>{{ t("extensions.skillGroupCount", { count: group.items.length }) }}</span>
                    </button>
                    <button
                      type="button"
                      class="group-install"
                      data-testid="market-group-install"
                      :disabled="store.busy"
                      @click.stop="store.installSkillGroup(group)"
                    >{{ t("extensions.installAll") }}</button>
                  </div>
                  <button
                    v-for="item in group.items"
                    :key="item.id"
                    type="button"
                    class="market-result"
                    :data-testid="'market-result-' + item.id"
                    @click="selectMarketItem(item)"
                  >
                    <strong>{{ item.name }}</strong>
                    <span>{{ item.repo || item.id }}</span>
                    <span v-if="item.installs">{{ t("extensions.detail.installs") }} {{ item.installs }}</span>
                  </button>
                </section>
              </template>
              <template v-else>
                <button
                  v-for="item in marketItems"
                  :key="item.id"
                  type="button"
                  class="market-result"
                  :data-testid="'market-result-' + item.id"
                  @click="selectMarketItem(item)"
                >
                  <strong>{{ item.name }}</strong>
                  <span>{{ item.repo || item.marketplace || item.id }}</span>
                  <span v-if="item.installs">{{ t("extensions.detail.installs") }} {{ item.installs }}</span>
                </button>
              </template>
              <p v-if="!store.error && !marketItems.length && (activeTab !== 'skills' || !marketSkillGroups.length)" class="market-empty">
                {{ t("extensions.market.noResults") }}
              </p>
            </div>
          </div>

          <ExtensionSourceManager v-else />

          <ExtensionDetailPanel
            v-if="detailItem && activeTab !== 'sources'"
            class="market-detail"
            :item="detailItem"
            :recommendation="detailRecommendation"
            :evidence-label="selectedRecommendation ? t('extensions.market.catalogEvidence') : undefined"
            @close="selectedRecommendation = null; selectedMarketItem = null"
          >
            <template #actions>
              <button
                v-if="selectedRecommendation"
                type="button"
                data-testid="market-search-action"
                :disabled="!store.canLoad || store.marketBusy"
                @click="searchSelectedRecommendation"
              >{{ t("extensions.market.searchAction") }}</button>
              <button
                v-else-if="selectedMarketItem"
                type="button"
                data-testid="market-install-action"
                :disabled="store.busy"
                @click="installDetail"
              >{{ t("extensions.install") }}</button>
            </template>
          </ExtensionDetailPanel>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.market-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-dialog);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  background: var(--scrim);
}
.extension-market-dialog {
  display: flex;
  width: min(1080px, 96vw);
  max-height: min(860px, 92vh);
  flex-direction: column;
  border: var(--border-w) solid var(--border-2);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow-2);
}
.market-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: var(--border-w) solid var(--border);
}
.market-header h2 { margin: 0; color: var(--text); font-size: var(--font-xl); }
.market-header p { margin: 2px 0 0; color: var(--text-muted); font-size: var(--font-xs); }
.market-tabs {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4) 0;
}
.market-tabs button {
  min-height: var(--control-h-sm);
  padding: 0 var(--space-3);
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}
.market-tabs button.active { background: var(--surface-active); color: var(--text); }
.market-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: var(--space-3);
  min-height: 0;
  flex: 1;
  padding: var(--space-3) var(--space-4) var(--space-4);
  overflow: hidden;
}
.recommendation-pane, .search-pane { display: flex; min-width: 0; flex-direction: column; gap: var(--space-3); overflow: auto; }
.category-chips { display: flex; flex-wrap: wrap; gap: var(--space-1); }
.category-chips button, .market-search button, .market-result, .market-detail :is(button) {
  border: var(--border-w) solid var(--border-2);
  background: var(--surface-2);
  color: var(--text-2);
}
.category-chips button { min-height: var(--control-h-sm); padding: 0 var(--space-2); border-radius: var(--radius-full); cursor: pointer; }
.category-chips button.active { border-color: var(--accent); color: var(--text); background: var(--accent-soft); }
.recommendation-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-2); align-content: start; }
.recommendation-card {
  display: flex;
  min-height: 116px;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: var(--border-w) solid var(--border-2);
  border-radius: var(--radius-md);
  background: var(--surface-2);
  color: var(--text-2);
  cursor: pointer;
}
.recommendation-card:hover, .recommendation-card:focus-visible, .market-result:hover, .market-result:focus-visible { border-color: var(--border-strong); background: var(--surface-hover); }
.recommendation-card header, .recommendation-card footer { display: flex; justify-content: space-between; gap: var(--space-2); }
.recommendation-card header span, .recommendation-card footer, .market-result span { color: var(--text-muted); font-size: var(--font-xs); }
.recommendation-card p { margin: 0; font-size: var(--font-sm); line-height: var(--leading-normal); overflow-wrap: anywhere; }
.market-search { display: flex; gap: var(--space-2); }
.market-search input { flex: 1; min-width: 0; }
.market-results { display: grid; gap: var(--space-1); overflow: auto; }
.market-result { display: flex; min-height: var(--control-h-md); align-items: center; gap: var(--space-2); padding: var(--space-1) var(--space-2); border-radius: var(--radius-sm); text-align: left; cursor: pointer; }
.market-group { display: grid; min-width: 0; gap: var(--space-1); padding: var(--space-2); border: var(--border-w) solid var(--border); border-radius: var(--radius-sm); }
.market-group-head { display: flex; align-items: center; gap: var(--space-2); }
.market-group-head .group-parent { flex: 1; }
.group-install { min-height: var(--control-h-sm); padding: 0 var(--space-3); border: var(--border-w) solid var(--accent); background: var(--accent-soft); color: var(--text); cursor: pointer; }
.market-result strong { color: var(--text); }
.market-result span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.market-empty { margin: var(--space-3); color: var(--text-muted); }
.market-cache, .market-search-error { margin: 0; color: var(--text-muted); font-size: var(--font-xs); }
.market-search-error { color: var(--error); }
.market-detail { overflow: auto; }
@media (max-width: 720px) {
  .market-body { grid-template-columns: 1fr; overflow: auto; }
  .market-detail { max-height: 45vh; }
}
</style>
