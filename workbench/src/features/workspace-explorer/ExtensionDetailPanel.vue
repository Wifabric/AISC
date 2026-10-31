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
  evidenceLabel?: string;
  loading?: boolean;
  error?: string;
}>();

const emit = defineEmits<{ close: []; retry: [] }>();
const { t, locale: currentLocale } = useI18n();

const locale = computed<ExtensionSummaryLocale>(() =>
  currentLocale.value === "en-US" ? "en-US" : "zh-CN",
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
const authText = computed(() => {
  if (!props.item.auth_required) return "";
  if (props.item.auth_configured) return t("extensions.detail.authConfigured");
  const claude = props.item.auth_claude_configured;
  const codex = props.item.auth_codex_configured;
  if (claude || codex) {
    return t("extensions.detail.authPartial", {
      claude: claude ? t("extensions.detail.authConfigured") : t("extensions.detail.authMissing"),
      codex: codex ? t("extensions.detail.authConfigured") : t("extensions.detail.authMissing"),
    });
  }
  return t("extensions.detail.authRequired", {
    env: props.item.auth_env_var || "GITHUB_PAT_TOKEN",
  });
});

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

</script>

<template>
  <section
    class="extension-detail-panel"
    data-testid="extension-detail-panel"
    role="complementary"
    :aria-label="t('extensions.detail.panel')"
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
      {{ loading ? t("extensions.detail.loading") : summary.summary }}
    </p>

    <div v-if="error" class="detail-fetch-error" role="status">
      <p>{{ error }}</p><button type="button" @click="emit('retry')">{{ t("extensions.detail.retry") }}</button>
    </div>

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
      <div v-if="item.auth_required" data-testid="extension-detail-auth">
        <dt>{{ t("extensions.detail.auth") }}</dt>
        <dd>{{ authText }}</dd>
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

    <div v-if="summary.marketOriginal && summary.marketOriginal !== summary.summary" class="detail-original">
      <span>{{ evidenceLabel ?? t("extensions.detail.marketOriginal") }}</span>
      <p data-testid="extension-detail-original">{{ summary.marketOriginal }}</p>
    </div>

    <footer v-if="$slots.actions" class="detail-actions">
      <slot name="actions" />
    </footer>
  </section>
</template>

<style scoped>
.extension-detail-panel {
  display: flex;
  box-sizing: border-box;
  width: 100%;
  flex: 0 0 auto;
  overflow-wrap: anywhere;
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
.detail-header { justify-content: space-between; flex-wrap: wrap; }
.detail-heading { flex: 1 1 140px; flex-direction: column; align-items: flex-start; }
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
  grid-template-columns: repeat(auto-fit, minmax(min(120px, 100%), 1fr));
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
.detail-actions { flex-wrap: wrap; justify-content: flex-end; padding-top: var(--space-2); border-top: var(--border-w) solid var(--border); }
/* The region itself never takes focus: keep keyboard rings on real controls. */
.detail-fetch-error { display: flex; flex-wrap: wrap; gap: var(--space-2); color: var(--text-muted); font-size: var(--font-xs); }
.detail-fetch-error p { margin: 0; min-width: 0; flex: 1 1 160px; }
.detail-fetch-error button { flex: none; }
</style>
