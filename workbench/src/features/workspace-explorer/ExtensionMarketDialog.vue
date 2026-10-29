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
    description: "",
    ...(selectedRecommendation.value.heat ? { installs: selectedRecommendation.value.heat } : {}),
  } : null),
);
const searchPlaceholder = computed(() => {
  if (activeTab.value === "skills") return t("extensions.market.searchSkills");
  if (activeTab.value === "mcp") return t("extensions.mcpMarketSearch");
  if (activeTab.value === "plugins") return t("extensions.pluginMarketSearch");
  return t("extensions.market.searchRecommendations");
});

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

        <div class="market-tabs" role="tablist" :aria-label="t('extensions.market.title')">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.key"
            :class="{ active: activeTab === tab.key }"
            :data-testid="'market-tab-' + tab.key"
            @click="selectTab(tab.key)"
          >{{ t(tab.labelKey) }}</button>
        </div>

        <div class="market-body">
          <div v-if="activeTab === 'recommendations'" class="recommendation-pane">
            <div class="category-chips" role="group" :aria-label="t('extensions.market.categories')">
              <button
                v-for="category in EXTENSION_RECOMMENDATION_CATEGORIES"
                :key="category.id"
                type="button"
                :class="{ active: activeCategory === category.id }"
                data-testid="recommendation-category"
                @click="activeCategory = category.id; selectedRecommendation = null"
              >{{ category.labelZh }}</button>
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
                <p>{{ entry.summaryZh }}</p>
                <footer>
                  <span>{{ entry.heat ?? t("extensions.market.officialDirectory") }}</span>
                  <span>{{ entry.heatSource }}</span>
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
            <div class="market-results">
              <button
                v-for="item in marketItems"
                :key="item.id"
                type="button"
                class="market-result"
                :data-testid="'market-result-' + item.id"
                @click="selectedMarketItem = item"
              >
                <strong>{{ item.name }}</strong>
                <span>{{ item.repo || item.marketplace || item.id }}</span>
                <span v-if="item.installs">{{ t("extensions.detail.installs") }} {{ item.installs }}</span>
              </button>
              <p v-if="!marketItems.length" class="market-empty">{{ t("extensions.market.noResults") }}</p>
            </div>
          </div>

          <ExtensionSourceManager v-else />

          <ExtensionDetailPanel
            v-if="detailItem"
            class="market-detail"
            :item="detailItem"
            :recommendation="detailRecommendation"
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
.market-result strong { color: var(--text); }
.market-result span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.market-empty { margin: var(--space-3); color: var(--text-muted); }
.market-detail { overflow: auto; }
@media (max-width: 720px) {
  .market-body { grid-template-columns: 1fr; overflow: auto; }
  .market-detail { max-height: 45vh; }
}
</style>
