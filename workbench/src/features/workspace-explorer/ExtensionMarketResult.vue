<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { ExtensionsItem } from "../../lib/ipc";
import { useExtensionsStore } from "../../stores/extensions";
import { extensionSummary } from "./extensionSummaries";
import ExtensionItemDetail from "./ExtensionItemDetail.vue";
const props = defineProps<{ item: ExtensionsItem; expanded: boolean }>();
const emit = defineEmits<{ select: []; close: []; install: [] }>();
const store = useExtensionsStore();
const { t, locale } = useI18n();
const summary = computed(() => extensionSummary(store.describedItem(props.item), locale.value === "en-US" ? "en-US" : "zh-CN"));
</script>
<template>
  <article class="market-result-card" :class="{ expanded }">
    <button type="button" class="market-result" :data-testid="'market-result-' + item.id"
      :aria-expanded="expanded" @click="emit('select')">
      <span class="result-heading"><strong>{{ item.name }}</strong><span aria-hidden="true">{{ expanded ? '▾' : '▸' }}</span></span>
      <span v-if="summary.source !== 'fallback'" class="result-summary">{{ summary.summary }}</span>
      <span class="result-source">{{ item.repo || item.marketplace || item.id }}<template v-if="item.installs"> · {{ t("extensions.detail.installs") }} {{ item.installs }}</template></span>
    </button>
    <ExtensionItemDetail v-if="expanded" :item="item" class="result-detail" @close="emit('close')">
      <template #actions>
        <button type="button" @click="emit('close')">{{ t("common.close") }}</button>
        <button type="button" data-testid="market-install-action" :disabled="store.busy" @click="emit('install')">{{ t("extensions.install") }}</button>
      </template>
    </ExtensionItemDetail>
  </article>
</template>
<style scoped>
.market-result-card { min-width: 0; border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface-2); }
.market-result { display: flex; flex-direction: column; gap: var(--space-1); width: 100%; min-width: 0; padding: var(--space-2); border: none; background: transparent; color: var(--text-2); text-align: left; cursor: pointer; font: inherit; border-radius: inherit; }
.market-result:focus-visible { outline: var(--focus-ring-width) solid var(--focus); outline-offset: calc(-1 * var(--focus-ring-width)); }
.result-heading { display: flex; justify-content: space-between; gap: var(--space-2); width: 100%; overflow-wrap: anywhere; color: var(--text); }
.result-summary { font-size: var(--font-sm); line-height: var(--leading-relaxed); overflow-wrap: anywhere; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.result-source { font-size: var(--font-xs); color: var(--text-muted); overflow-wrap: anywhere; }
.result-detail { width: auto; margin: 0 var(--space-2) var(--space-2); }
</style>
