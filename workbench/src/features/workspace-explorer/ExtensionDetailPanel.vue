<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { ExtensionsItem } from "../../lib/ipc";
import type { ExtensionUpdateItem } from "../../stores/extensions";
import type { CategorizedRecommendation } from "./recommendationCatalog";
import { extensionSummary, type ExtensionSummaryLocale } from "./extensionSummaries";

const props = defineProps<{
  item: ExtensionsItem;
  recommendation?: CategorizedRecommendation;
  update?: ExtensionUpdateItem;
}>();

const emit = defineEmits<{ close: [] }>();
const { t } = useI18n();

const locale = computed<ExtensionSummaryLocale>(() =>
  i18nLocaleValue() === "en-US" ? "en-US" : "zh-CN",
);
const summary = computed(() => extensionSummary(props.item, locale.value));
const kindLabel = computed(() => {
  if (props.item.kind === "mcp" || props.item.kind === "market-mcp") return t("extensions.tab.mcp");
  if (props.item.kind === "plugins" || props.item.kind === "market-plugin") return t("extensions.tab.plugins");
  return t("extensions.tab.skills");
});
const sourceText = computed(() =>
  props.item.marketplace?.trim() ||
  props.item.repo?.trim() ||
  props.recommendation?.sourceUrl ||
  props.item.id,
);
const currentVersion = computed(() =>
  props.update?.current_version?.trim() || props.item.version?.trim() || "",
);
const latestVersion = computed(() =>
  props.update?.update_available ? (props.update.latest_version?.trim() || "") : "",
);
const sourceUrl = computed(() => {
  const explicit = props.recommendation?.sourceUrl ?? "";
  if (explicit) return explicit;
  const repo = props.item.repo?.trim() ?? "";
  if (/^https:\/\//i.test(repo)) return repo;
  if (repo && /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)) {
    return `https://github.com/${repo}`;
  }
  return "";
});

function i18nLocaleValue(): string {
  return useI18n().locale.value;
}
</script>

<template>
  <section
    class="extension-detail-panel"
    data-testid="extension-detail-panel"
    role="complementary"
    :aria-label="t('extensions.detail.panel')"
    tabindex="-1"
    @keydown.escape.stop="emit('close')"
  >
    <header class="detail-header">
      <div class="detail-heading">
        <h3>{{ item.name }}</h3>
        <span class="detail-kind">{{ kindLabel }}</span>
      </div>
      <a
        v-if="sourceUrl"
        class="detail-source-link"
        :href="sourceUrl"
        target="_blank"
        rel="noopener noreferrer"
      >{{ t("extensions.detail.openSource") }}</a>
    </header>

    <p class="detail-summary" data-testid="extension-detail-summary">
      {{ summary.summary }}
    </p>

    <p
      v-if="update?.status === 'unsupported'"
      class="detail-unsupported"
      data-testid="extension-detail-unsupported"
    >{{ t("extensions.noComparableVersion") }}</p>

    <dl class="detail-metadata" data-testid="extension-detail-metadata">
      <div>
        <dt>{{ t("extensions.detail.kind") }}</dt>
        <dd>{{ kindLabel }}</dd>
      </div>
      <div>
        <dt>{{ t("extensions.detail.source") }}</dt>
        <dd>{{ sourceText }}</dd>
      </div>
      <div v-if="item.installs">
        <dt>{{ t("extensions.detail.installs") }}</dt>
        <dd>{{ item.installs }}</dd>
      </div>
      <div v-if="item.updated_at">
        <dt>{{ t("extensions.detail.updatedAt") }}</dt>
        <dd>{{ item.updated_at }}</dd>
      </div>
      <div v-if="currentVersion">
        <dt>{{ t("extensions.detail.currentVersion") }}</dt>
        <dd>{{ currentVersion }}</dd>
      </div>
      <div v-if="latestVersion">
        <dt>{{ t("extensions.detail.latestVersion") }}</dt>
        <dd>{{ latestVersion }}</dd>
      </div>
    </dl>

    <div v-if="summary.marketOriginal || item.description" class="detail-original">
      <span>{{ t("extensions.detail.marketOriginal") }}</span>
      <p data-testid="extension-detail-original">{{ summary.marketOriginal || item.description }}</p>
    </div>

    <footer v-if="$slots.actions" class="detail-actions">
      <slot name="actions" />
    </footer>
  </section>
</template>

<style scoped>
.extension-detail-panel {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  border: var(--border-w) solid var(--border-2);
  border-radius: var(--radius-md);
  background: var(--surface);
}
.extension-detail-panel:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus);
  outline-offset: calc(-1 * var(--focus-ring-width));
}
.detail-header, .detail-heading, .detail-actions {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: var(--space-2);
}
.detail-header { justify-content: space-between; }
.detail-heading { flex: 1 1 auto; flex-direction: column; align-items: flex-start; }
h3 { margin: 0; color: var(--text); font-size: var(--font-lg); line-height: var(--leading-tight); overflow-wrap: anywhere; }
.detail-kind, .detail-original span {
  color: var(--text-muted);
  font-size: var(--font-xs);
}
.detail-source-link { color: var(--info); font-size: var(--font-xs); text-decoration: none; flex: 0 0 auto; }
.detail-source-link:hover, .detail-source-link:focus-visible { text-decoration: underline; }
.detail-summary { margin: 0; color: var(--text-2); font-size: var(--font-md); line-height: var(--leading-relaxed); }
.detail-unsupported { margin: 0; color: var(--text-muted); font-size: var(--font-xs); }
.detail-metadata {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--space-2);
  margin: 0;
  padding-top: var(--space-2);
  border-top: var(--border-w) solid var(--border);
}
.detail-metadata div { min-width: 0; }
dt { color: var(--text-faint); font-size: var(--font-xs); }
dd { margin: 2px 0 0; color: var(--text-2); font-size: var(--font-sm); overflow-wrap: anywhere; }
.detail-original {
  padding-top: var(--space-2);
  border-top: var(--border-w) solid var(--border);
}
.detail-original p { margin: 2px 0 0; color: var(--text-muted); font-size: var(--font-xs); line-height: var(--leading-normal); }
.detail-actions { justify-content: flex-end; padding-top: var(--space-2); border-top: var(--border-w) solid var(--border); }
</style>
