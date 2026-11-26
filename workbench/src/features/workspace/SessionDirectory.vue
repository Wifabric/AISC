<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useWorkspaceExplorerStore } from "../../stores/workspaceExplorer";
const directory = defineModel<string>({ required: true });
const explorer = useWorkspaceExplorerStore();
const { t } = useI18n();
const listId = useId();
const folders = ref<string[]>([]);
const draft = ref(directory.value);
const relative = computed(() => draft.value.replace(/\\/g, "/").replace(/^(?:~\/app|\/root\/app)(?:\/|$)/, ""));
watch(relative, path => { directory.value = path.replace(/\/+$/, ""); }, { flush: "sync" });
watch(directory, path => { if (path !== relative.value.replace(/\/+$/, "")) draft.value = path; });
const parent = computed(() => relative.value.slice(0, relative.value.lastIndexOf("/") + 1).replace(/\/$/, ""));
const matches = computed(() => folders.value.filter(path => path.toLowerCase().startsWith(relative.value.toLowerCase())));
watch(() => [explorer.workspace, parent.value] as const, async ([workspace, folder], _, onCleanup) => {
  let current = true;
  onCleanup(() => { current = false; });
  folders.value = [];
  if (!workspace || folder.split("/").includes("..")) return;
  try {
    const paths = await explorer.sessionDirectories(workspace, folder);
    if (current) folders.value = paths;
  } catch { /* A path can still be entered while a directory listing is unavailable. */ }
}, { immediate: true });
</script>
<template>
  <label>{{ t("tabbar.directory") }}
    <span class="directory-input"><span>~/app/</span><input v-model="draft" :list="listId" autocomplete="off"
      :aria-label="t('tabbar.directory')" @keydown="($event.key !== 'Escape' && $event.key !== 'Tab') && $event.stopPropagation()" /></span>
    <datalist :id="listId"><option v-for="dir in matches" :key="dir" :value="dir + '/'" /></datalist>
  </label>
</template>
<style scoped>
.directory-input { display: flex; align-items: center; gap: 2px; min-width: 0; }
input { min-width: 0; flex: 1; font: inherit; }
</style>
