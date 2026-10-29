<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useExtensionsStore } from "../../stores/extensions";

const { t } = useI18n();
const store = useExtensionsStore();
const latest = computed(() => {
  const rows = store.operationLog.filter((row) => row.status !== "success");
  return rows[rows.length - 1] ?? null;
});
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
header span { font-size: var(--font-xs); }
p { margin: 0; font-size: var(--font-xs); overflow-wrap: anywhere; }
pre { max-height: 6rem; margin: 0; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font-size: var(--font-xs); }
footer { justify-content: flex-end; }
</style>
