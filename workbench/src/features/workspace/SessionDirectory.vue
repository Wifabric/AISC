<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useWorkspaceExplorerStore } from "../../stores/workspaceExplorer";
const directory = defineModel<string>({ required: true });
const explorer = useWorkspaceExplorerStore();
const { t } = useI18n();
const directories = computed(() => Object.values(explorer.tree).flat()
  .filter(n => n.kind === "dir").map(n => n.relative_path).sort());
onMounted(() => { if (explorer.workspace) void explorer.loadDir(""); });
</script>
<template>
  <label>{{ t("tabbar.directory") }}
    <select v-model="directory" @keydown.stop @change="explorer.loadDir(directory)">
      <option value="">~/app</option>
      <option v-for="dir in directories" :key="dir" :value="dir">~/app/{{ dir }}</option>
    </select>
  </label>
</template>
