<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useExtensionsStore } from "../../stores/extensions";

const { t } = useI18n();
const store = useExtensionsStore();
</script>

<template>
  <details class="extension-operation-log">
    <summary>{{ t("extensions.log.title") }}</summary>
    <p v-if="!store.operationLog.length" class="log-empty">{{ t("extensions.log.empty") }}</p>
    <ul v-else class="log-rows">
      <li v-for="row in store.operationLog" :key="row.operationId" :data-status="row.status">
        <div class="log-heading">
          <strong>{{ row.label }}</strong>
          <span>{{ t(`extensions.tab.${row.kind}`) }}</span>
          <span>{{ t(`extensions.log.action.${row.action}`) }}</span>
          <span>{{ t("extensions.log.attempt", { attempt: row.attempt }) }}</span>
          <span class="log-status">{{ t(`extensions.log.status.${row.status}`) }}</span>
        </div>
        <div class="log-times">
          <span>{{ t("extensions.log.startedAt") }} <time :datetime="row.startedAt">{{ row.startedAt }}</time></span>
          <span>{{ t("extensions.log.finishedAt") }} <time :datetime="row.finishedAt">{{ row.finishedAt }}</time></span>
        </div>
        <pre>{{ row.diagnostic }}</pre>
        <div class="log-actions">
          <button
            v-if="row.status === 'failed' && store.canRetryOperation(row.operationId)"
            type="button"
            class="ui-button"
            :disabled="store.busy"
            @click="store.retryOperation(row.operationId)"
          >{{ t("extensions.log.retry") }}</button>
          <button type="button" class="ui-button" @click="store.copyOperationDiagnostic(row.operationId)">
            {{ t("extensions.log.copy") }}
          </button>
        </div>
      </li>
    </ul>
  </details>
</template>

<style scoped>
.extension-operation-log { min-width: 0; border-top: var(--border-w) solid var(--border); padding-top: var(--space-2); }
summary { cursor: pointer; font-weight: 600; }
.log-empty, .log-times { color: var(--text-muted); font-size: var(--font-xs); }
.log-rows { display: grid; gap: var(--space-2); max-height: 28rem; overflow: auto; list-style: none; margin: var(--space-2) 0 0; padding: 0; }
li { min-width: 0; padding: var(--space-2); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface-2); }
.log-heading, .log-times, .log-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); overflow-wrap: anywhere; }
.log-heading { font-size: var(--font-xs); }
.log-heading strong { color: var(--text); }
.log-status { color: var(--text-muted); }
li[data-status="failed"] .log-status, li[data-status="unknown"] .log-status { color: var(--warn); }
pre { max-height: 10rem; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font-size: var(--font-xs); }
</style>
