<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { ExtensionOperation } from "../../stores/extensions";

const props = defineProps<{
  operation: ExtensionOperation;
  cancellable: boolean;
}>();
const emit = defineEmits<{ cancel: [] }>();

const { t } = useI18n();
const percent = computed(() => {
  const total = props.operation.total;
  return total > 0 ? Math.round((props.operation.completed / total) * 100) : 0;
});
</script>

<template>
  <div class="operation-progress" data-testid="market-operation-progress" role="status">
    <span class="op-action">{{ t(`extensions.op.${operation.action}`) }}</span>
    <span v-if="operation.total > 1" class="op-count">
      {{ operation.completed }}/{{ operation.total }}
    </span>
    <span class="op-target">{{ operation.label }}</span>
    <span class="op-progress-track" aria-hidden="true">
      <span :style="{ width: `${percent}%` }" class="op-progress-fill" />
    </span>
    <button
      v-if="cancellable"
      type="button"
      class="op-cancel"
      data-testid="market-operation-cancel"
      @click="emit('cancel')"
    >{{ t("extensions.cancel") }}</button>
  </div>
</template>

<style scoped>
.operation-progress { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); min-width: 0; margin: 0 var(--space-4) var(--space-2); padding: var(--space-1) var(--space-2); border: var(--border-w) solid var(--accent); border-radius: var(--radius-sm); background: var(--surface-2); color: var(--text-2); }
.op-action { flex: 0 0 auto; font-size: var(--font-sm); font-weight: 600; }
.op-count { flex: 0 0 auto; font-size: var(--font-xs); color: var(--text-muted); font-variant-numeric: tabular-nums; }
.op-target { flex: 1 1 auto; min-width: 0; overflow-wrap: anywhere; font-size: var(--font-xs); color: var(--text-faint); }
.op-progress-track { flex: 1 1 100%; height: 3px; overflow: hidden; border-radius: var(--radius-full); background: var(--surface-3); }
.op-progress-fill { display: block; height: 100%; border-radius: inherit; background: var(--accent); transition: width var(--duration-normal) var(--ease); }
.op-cancel { border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface-2); color: var(--text); cursor: pointer; }
</style>
