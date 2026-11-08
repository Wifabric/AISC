<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useExtensionsStore } from "../../stores/extensions";

const { t } = useI18n();
const store = useExtensionsStore();
const emit = defineEmits<{ dismissed: [] }>();
const latest = computed(() => store.latestFailure);
function dismiss(): void {
  if (!latest.value) return;
  store.dismissFailureNotice(latest.value.operationId);
  emit("dismissed");
}
const statusLabel = computed(() =>
  latest.value ? t(`extensions.log.status.${latest.value.status}`) : "",
);
</script>

<template>
  <section
    v-if="latest"
    class="extension-failure"
    data-testid="extension-failure"
    role="alert"
  >
    <header>
      <strong>{{ t("extensions.failure.title") }}</strong>
      <span>{{ statusLabel }}</span>
      <button type="button" class="failure-close" data-testid="extension-failure-close"
        :aria-label="t('extensions.failure.dismiss')" :title="t('extensions.failure.dismiss')"
        @click="dismiss">×</button>
    </header>
    <p>
      {{ t(`extensions.tab.${latest.kind}`) }} ·
      {{ t(`extensions.log.action.${latest.action}`) }} · {{ latest.label }}
    </p>
    <pre>{{ latest.diagnostic }}</pre>
    <footer>
      <button
        v-if="latest.status === 'failed' && store.canRetryOperation(latest.operationId)"
        type="button"
        data-testid="extension-failure-retry"
        :disabled="store.busy"
        @click="store.retryOperation(latest.operationId)"
      >{{ t("extensions.log.retry") }}</button>
      <button
        type="button"
        data-testid="extension-failure-copy"
        @click="store.copyOperationDiagnostic(latest.operationId)"
      >{{ t("extensions.log.copy") }}</button>
    </footer>
  </section>
</template>

<style scoped>
.extension-failure {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: var(--border-w) solid var(--error-border);
  border-radius: var(--radius-sm);
  background: var(--error-bg);
  color: var(--error-fg);
}
header, footer { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
header strong { flex: 1; min-width: 0; overflow-wrap: anywhere; }
header span { font-size: var(--font-xs); }
.failure-close { flex-shrink: 0; min-width: 1.75rem; min-height: 1.75rem; cursor: pointer; }
p { margin: 0; font-size: var(--font-xs); overflow-wrap: anywhere; }
pre { max-height: 6rem; margin: 0; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font-size: var(--font-xs); }
footer { justify-content: flex-end; }
</style>
