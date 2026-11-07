<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useModuleOperationsStore } from "../../stores/moduleOperations";
const operations = useModuleOperationsStore();
const { t, te } = useI18n();
const reason = (value: string) => te(`modules.reason.${value}`) ? t(`modules.reason.${value}`) : value;
</script>
<template>
  <section v-if="operations.phase !== 'idle' || operations.error" class="module-progress" aria-live="polite" data-testid="module-operation-progress">
    <p v-if="operations.error" role="alert">{{ operations.error }}</p>
    <p v-if="operations.targetChanged" role="alert">{{ t("modules.targetChanged") }}</p>
    <strong>{{ operations.plan?.module_name }} · {{ t(`modules.phase.${operations.phase}`) }}</strong>
    <p v-if="operations.phase === 'running'">{{ operations.completed }} / {{ operations.plan?.rows.length }}<span v-if="operations.cancelRequested"> · {{ t("modules.stopping") }}</span></p>
    <p>{{ t("modules.executionNotice") }}</p>
    <p v-if="operations.phase === 'history'">{{ t("modules.historyNotice") }}</p>
    <ul v-if="operations.plan">
      <li v-for="row in operations.plan.rows" :key="row.key">
        <span>{{ row.member.name }} · {{ t(`extensions.tab.${row.member.kind}`) }}<small>{{ row.member.identity }}</small></span>
        <span>{{ t(`modules.action.${row.action}`) }} · {{ t(`modules.status.${row.status}`) }}<small v-if="!['installed', 'removed', 'auth_required'].includes(row.status)">{{ reason(row.reason) }}</small></span>
      </li>
    </ul>
    <div class="progress-actions">
      <button v-if="operations.phase === 'prepared'" type="button" :disabled="operations.targetChanged || !operations.plan?.rows.length" @click="operations.run">{{ t("modules.confirmRun") }}</button>
      <button v-if="operations.phase === 'running'" type="button" :disabled="operations.cancelRequested" @click="operations.cancel">{{ t("modules.stop") }}</button>
      <button v-if="operations.plan && !operations.busy && operations.phase !== 'prepared'" type="button" :disabled="operations.targetChanged" @click="operations.retry">{{ t("modules.recheck") }}</button>
    </div>
  </section>
</template>
<style scoped>
.module-progress { border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); padding: var(--space-3); min-width: 0; }
.module-progress ul { padding: 0; list-style: none; }
.module-progress li { display: flex; flex-wrap: wrap; justify-content: space-between; gap: var(--space-2); margin-bottom: var(--space-2); }
.module-progress small { display: block; color: var(--text-muted); overflow-wrap: anywhere; }
.progress-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.progress-actions button { border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface-2); color: var(--text); font: inherit; padding: var(--space-1) var(--space-2); cursor: pointer; }
.progress-actions button:focus-visible { outline: var(--focus-ring-width) solid var(--focus); }
.progress-actions button:disabled { opacity: 0.45; cursor: default; }
</style>
