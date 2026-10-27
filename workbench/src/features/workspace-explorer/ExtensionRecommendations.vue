<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useExtensionsStore, type ExtensionsKind } from "../../stores/extensions";
import { EXTENSION_RECOMMENDATIONS, type ExtensionRecommendation } from "./extensionRecommendations";

const { t } = useI18n();
const store = useExtensionsStore();
const emit = defineEmits<{ discover: [kind: ExtensionsKind, query: string] }>();

function discover(entry: ExtensionRecommendation): void {
  if (!store.canLoad || store.marketBusy) return;
  emit("discover", entry.kind, entry.query);
  void store.discoverRecommendation(entry.kind, entry.query);
}
</script>

<template>
  <section class="extension-recommendations" :aria-label="t('extensions.recommendations.title')">
    <h3>{{ t("extensions.recommendations.title") }}</h3>
    <p class="recommendations-hint">{{ t("extensions.recommendations.hint") }}</p>
    <p v-if="!store.canLoad" class="recommendations-hint" role="status">{{ t("extensions.recommendations.noRuntime") }}</p>
    <p v-else-if="store.marketBusy" class="recommendations-hint" role="status">{{ t("extensions.recommendations.busy") }}</p>
    <ul>
      <li v-for="entry in EXTENSION_RECOMMENDATIONS" :key="entry.identity">
        <div class="recommendation-heading">
          <strong>{{ entry.name }}</strong>
          <span class="recommendation-kind">{{ t(`extensions.tab.${entry.kind}`) }}</span>
        </div>
        <p>{{ t(entry.reasonKey) }}</p>
        <code>{{ entry.identity }}</code>
        <div class="recommendation-actions">
          <a :href="entry.sourceUrl" target="_blank" rel="noopener noreferrer">{{ t("extensions.recommendations.source") }}</a>
          <button type="button" class="ui-button" :disabled="!store.canLoad || store.marketBusy" @click="discover(entry)">
            {{ t("extensions.recommendations.search") }}
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.extension-recommendations { min-width: 0; }
h3 { margin: 0; font-size: var(--font-sm); }
.recommendations-hint { margin: var(--space-1) 0; color: var(--text-muted); font-size: var(--font-xs); }
ul { display: grid; gap: var(--space-1); list-style: none; padding: 0; margin: var(--space-2) 0; }
li { min-width: 0; padding: var(--space-2); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface-2); overflow-wrap: anywhere; }
.recommendation-heading, .recommendation-actions { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
.recommendation-kind, code, li p { font-size: var(--font-xs); color: var(--text-muted); }
li p { margin: var(--space-1) 0; }
.recommendation-actions { justify-content: space-between; margin-top: var(--space-1); }
a { color: var(--accent); font-size: var(--font-xs); }
</style>
