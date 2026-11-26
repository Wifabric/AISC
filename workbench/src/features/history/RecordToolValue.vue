<script setup lang="ts">
import { computed } from "vue";
import RecordContent from "./RecordContent.vue";

const props = withDefaults(defineProps<{ value: unknown; workspace: string; depth?: number; commandWrapper?: boolean }>(), { depth: 0 });
const data = computed(() => {
  if (props.commandWrapper && typeof props.value === "string") {
    const call = props.value.trim().match(/^text\(\s*await\s+tools\.exec_command\(\s*(\{[\s\S]*\})\s*\)\s*\)\s*;?$/);
    if (call) {
      // Preserve quoted command contents. Only normalize literal property names.
      const literal = call[1].replace(/"(?:\\.|[^"\\])*"|([A-Za-z_]\w*)\s*:/g,
        (match, key) => key ? JSON.stringify(key) + ":" : match);
      try { return JSON.parse(literal); } catch { /* Show arbitrary scripts verbatim below. */ }
    }
  }
  if (props.depth === 0 && typeof props.value === "string" && /^[\s]*[[{]/.test(props.value)) {
    try { return JSON.parse(props.value); } catch { /* Partial tool output is still readable as text. */ }
  }
  return props.value;
});
const fields = computed(() => data.value && typeof data.value === "object" ? Object.entries(data.value) : null);
</script>

<template>
  <dl v-if="fields?.length && depth < 8" class="tool-fields">
    <template v-for="[key, child] in fields" :key="key">
      <dt>{{ Array.isArray(data) ? Number(key) + 1 : key }}</dt>
      <dd><RecordToolValue :value="child" :workspace="workspace" :depth="depth + 1" /></dd>
    </template>
  </dl>
  <pre v-else-if="fields">{{ JSON.stringify(data, null, 2) }}</pre>
  <pre v-else-if="commandWrapper">{{ data }}</pre>
  <RecordContent v-else :text="String(data ?? '')" :workspace="workspace" />
</template>

<style scoped>
.tool-fields { display: grid; grid-template-columns: fit-content(30%) minmax(0, 1fr); gap: 6px 16px; margin: 8px 0; }
dt { color: var(--text-muted); overflow-wrap: anywhere; }
dd { margin: 0; min-width: 0; }
</style>
