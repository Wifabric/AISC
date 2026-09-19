<script setup lang="ts">
/**
 * ReasoningLevelsCombo (D-7, 2026-09-19): cc-switch-desktop-style multi
 * select for thinking levels — a read-only input showing the comma-joined
 * selection; clicking opens a checkbox dropdown with a search box.
 * v-model: string[] of canonical level ids.
 */
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const props = defineProps<{
  modelValue: string[];
  levels?: string[];
  placeholder?: string;
}>();
const emit = defineEmits<{
  (e: "update:modelValue", value: string[]): void;
}>();

const open = ref(false);
const query = ref("");
const LEVELS = props.levels ?? [
  "none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra",
];

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  return q ? LEVELS.filter((lv) => lv.includes(q)) : [...LEVELS];
});

function toggle(lv: string): void {
  const cur = props.modelValue ?? [];
  const next = cur.includes(lv)
    ? cur.filter((x) => x !== lv)
    : [...cur, lv];
  // Keep the canonical dropdown order regardless of click order.
  next.sort((a, b) => LEVELS.indexOf(a as never) - LEVELS.indexOf(b as never));
  emit("update:modelValue", next);
}

function close(): void {
  open.value = false;
  query.value = "";
}
</script>

<template>
  <div class="rl-combo">
    <button type="button" class="box" @click="open = !open">
      <span :class="{ placeholder: !(modelValue ?? []).length }">
        {{ (modelValue ?? []).join(", ") || (placeholder ?? t("ccswitch.mapping.levelsPh")) }}
      </span>
      <span class="chev" :class="{ up: open }">⌄</span>
    </button>
    <div v-if="open" class="dd">
      <input
        v-model="query"
        class="search"
        :placeholder="t('ccswitch.mapping.levelsSearch')"
        spellcheck="false"
      />
      <label v-for="lv in filtered" :key="lv" class="opt">
        <input
          type="checkbox"
          :checked="(modelValue ?? []).includes(lv)"
          @change="toggle(lv)"
        />
        <span>{{ lv }}</span>
        <span v-if="(modelValue ?? []).includes(lv)" class="check">✓</span>
      </label>
      <p v-if="!filtered.length" class="empty">{{ t("ccswitch.mapping.levelsNoMatch") }}</p>
      <button type="button" class="done" @click="close">
        {{ t("ccswitch.mapping.levelsDone") }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.rl-combo { position: relative; flex: 1; min-width: 0; }
.box {
  width: 100%; box-sizing: border-box; text-align: left; cursor: pointer;
  display: flex; align-items: center; justify-content: space-between; gap: 6px;
  background: var(--surface-3); color: var(--text);
  border: var(--border-w) solid var(--border-strong); border-radius: var(--radius-sm);
  min-height: var(--control-h-sm); padding: 0 var(--space-2); font-size: var(--font-sm);
}
.box .placeholder { color: var(--text-faint); }
.chev { color: var(--text-faint); transition: transform var(--duration-fast) var(--ease); }
.chev.up { transform: rotate(180deg); }
.dd {
  position: absolute; z-index: 30; left: 0; right: 0; top: calc(100% + 4px);
  background: var(--surface); border: var(--border-w) solid var(--border-strong);
  border-radius: var(--radius-md); box-shadow: var(--shadow-lg, 0 8px 24px rgba(0,0,0,.35));
  max-height: 280px; overflow: auto; padding: 6px;
}
.search {
  width: 100%; box-sizing: border-box; margin-bottom: 6px;
  background: var(--surface-3); color: var(--text);
  border: var(--border-w) solid var(--border-strong); border-radius: var(--radius-sm);
  min-height: var(--control-h-sm); padding: 0 var(--space-2); font-size: var(--font-sm);
}
.opt {
  display: flex; align-items: center; gap: 8px; cursor: pointer;
  padding: 4px 6px; border-radius: var(--radius-sm); font-size: var(--font-sm);
  color: var(--text);
}
.opt:hover { background: var(--surface-hover); }
.opt .check { margin-left: auto; color: var(--accent); font-weight: 700; }
.empty { font-size: var(--font-xs); color: var(--text-faint); margin: 4px 6px; }
.done {
  width: 100%; margin-top: 4px; cursor: pointer;
  background: var(--accent-soft); color: var(--accent);
  border: 1px solid var(--accent); border-radius: var(--radius-sm);
  min-height: var(--control-h-sm); font-size: var(--font-sm); font-weight: 600;
}
</style>
