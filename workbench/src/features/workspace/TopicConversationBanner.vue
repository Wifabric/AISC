<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRuntimeStore } from "../../stores/runtime";
import { useTopicsStore } from "../../stores/topics";
import { useWorkspaceExplorerStore } from "../../stores/workspaceExplorer";
import { setExplorerCollapsed } from "../../lib/panelLayout";

const { t } = useI18n();
const runtime = useRuntimeStore();
const topics = useTopicsStore();
const explorer = useWorkspaceExplorerStore();
watch([() => runtime.workspace, () => runtime.id], ([workspace, id]) => {
  topics.setContext(workspace ?? "", id);
  void topics.syncConversations();
}, { immediate: true });
const timer = window.setInterval(() => { void topics.syncConversations(); }, 5000);
onBeforeUnmount(() => window.clearInterval(timer));
const captured = computed(() => topics.conversationStatus
  .filter(item => !topics.activeTopic || item.topic_id === topics.activeTopic.id)
  .reduce((sum, item) => sum + item.captured, 0));
function viewTopic(): void {
  explorer.activateView("topics");
  setExplorerCollapsed(false);
  if (topics.activeTopic) void topics.select(topics.activeTopic.id);
}
</script>

<template>
  <div v-if="topics.activeTopic || topics.conversationStatus.length || topics.syncError" class="topic-conversation-banner" data-testid="topic-conversation-banner">
    <button v-if="topics.activeTopic" type="button" @click="viewTopic">{{ t('topics.currentConversation', { title: topics.activeTopic.title }) }}</button>
    <span>{{ t('topics.captured', { count: captured }) }}</span>
    <span v-if="topics.syncError" role="alert">{{ t('topics.syncFailed') }} {{ topics.syncError }}</span>
    <span v-else>{{ t('topics.normalChatHint') }}</span>
  </div>
</template>

<style scoped>
.topic-conversation-banner { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); padding: var(--space-2); background: var(--surface-2); color: var(--text-2); font-size: var(--font-xs); border-bottom: var(--border-w) solid var(--border); }
button { border: 0; background: transparent; color: var(--accent); cursor: pointer; font: inherit; }
[role=alert] { color: var(--text); overflow-wrap: anywhere; }
</style>
