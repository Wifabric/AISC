<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRuntimeStore } from "../../stores/runtime";
import { useTopicsStore } from "../../stores/topics";
import { writeSession } from "../../lib/ipc";

const runtime = useRuntimeStore();
const topics = useTopicsStore();
watch([() => runtime.workspace, () => runtime.id], ([workspace, id]) => {
  topics.setContext(workspace ?? "", id);
  void topics.syncConversations();
}, { immediate: true });
const timer = window.setInterval(() => { void topics.syncConversations(); }, 5000);
onBeforeUnmount(() => window.clearInterval(timer));
const tab = computed(() => runtime.tabs.find(t => t.tabId === runtime.activeTabId));
const pane = computed(() => tab.value?.panes[tab.value.activePaneId]);
const status = computed(() => topics.conversationStatus.find(s => s.session_id === pane.value?.sessionId));
const topicId = computed(() => status.value?.topic_id ?? pane.value?.topicId);
const title = computed(() => status.value?.topic_title ?? pane.value?.topicTitle ?? "当前主题");
const message = computed(() => {
  if (status.value?.state === "error") return "这段对话暂时无法继续同步，已保存的记录保留。";
  if (status.value?.state === "completed") return "记录已停止，历史保留";
  if (status.value?.captured) return "记录已保存";
  return "等待对话记录";
});
const dismissed = ref<string[]>([]);
const diagnosticKey = computed(() => JSON.stringify([runtime.workspace, runtime.id, pane.value?.sessionId, status.value?.diagnostic, topics.syncError]));
const hasIssue = computed(() => status.value?.state === "error" || !!topics.syncError);
const showIssue = computed(() => hasIssue.value && !dismissed.value.includes(diagnosticKey.value));
const localError = ref("");
const filling = ref(false);
watch(() => pane.value?.sessionId, () => { localError.value = ""; });
function viewTopic(): void {
  const id = topicId.value;
  runtime.openTopicsTab();
  if (id) void topics.select(id);
}
async function fillOpening(): Promise<void> {
  const target = pane.value;
  if (!target?.sessionId || !target.openingPrompt || target.sessionState !== "running" || filling.value) return;
  const prompt = target.openingPrompt;
  if (prompt.length > 8192 || /[\x00-\x1f\x7f-\x9f]/.test(prompt)) {
    localError.value = "请使用不含换行或控制字符的简短开场问题。"; return;
  }
  filling.value = true; localError.value = "";
  try {
    await writeSession(target.sessionId, Array.from(new TextEncoder().encode(`\x1b[200~${prompt}\x1b[201~`)));
    target.openingPrompt = "";
  } catch { localError.value = "填入未完成，请确认会话已就绪后重试。"; }
  finally { filling.value = false; }
}
</script>

<template>
  <section v-if="pane && topicId" class="topic-conversation-banner" data-testid="topic-conversation-banner">
    <div class="status-line">
      <button type="button" @click="viewTopic">主题：{{ title }}</button>
      <span v-if="!hasIssue">{{ message }}</span>
      <span v-else-if="showIssue" role="status">这段对话暂时无法继续同步，已保存的记录保留。</span>
      <button v-if="showIssue" type="button" aria-label="关闭当前同步提示" @click="dismissed.push(diagnosticKey)">×</button>
      <details>
        <summary>更多</summary>
        <button type="button" @click="viewTopic">查看成果与相关对话</button>
        <button type="button" @click="runtime.createTab(tab?.agent === 'claude' ? 'claude' : 'codex')">新开普通对话</button>
        <p>普通新对话不关联主题；已启用的回答偏好仍独立生效。</p>
        <button v-if="status && status.state !== 'completed'" type="button" :disabled="topics.busy" @click="topics.sessionAction(status.topic_id, status.session_id, 'stop')">停止记录本次对话</button>
        <p>停止只影响后续记录，保留历史；已经带入本对话的主题背景不会撤回。</p>
        <button v-if="status?.state === 'error'" type="button" :disabled="topics.busy" @click="topics.sessionAction(status.topic_id, status.session_id, 'retry')">重试同步</button>
        <details v-if="hasIssue"><summary>诊断详情</summary><pre>{{ status?.diagnostic || topics.syncError }}</pre></details>
        <p v-if="topics.error" role="alert">{{ topics.error }}</p>
      </details>
    </div>
    <details v-if="pane.openingPrompt" open class="opening">
      <summary>建议的开场问题 · 可以修改</summary>
      <input v-model="pane.openingPrompt" aria-label="开场问题" maxlength="8192" />
      <button type="button" :disabled="pane.sessionState !== 'running' || filling" @click="fillOpening">填入对话，由我发送</button>
      <small>确认下方 AI 输入框已就绪再填入；检查后按回车发送。也可以直接提出自己的问题。</small>
    </details>
    <p v-if="localError" role="alert">{{ localError }}</p>
  </section>
</template>

<style scoped>
.topic-conversation-banner { padding: 8px 12px; background: var(--surface-2); color: var(--text-2); font-size: var(--font-xs); border-bottom: var(--border-w) solid var(--border); }
.status-line { display:flex; align-items:center; flex-wrap:wrap; gap:12px; }
button { border:0; background:transparent; color:var(--accent); cursor:pointer; font:inherit; padding:4px; }
button:disabled { opacity:.5; cursor:default; }
summary { cursor:pointer; }
.status-line > details { position:relative; margin-left:auto; }
.status-line > details[open] { flex-basis:100%; }
p { margin:6px 0; }
pre { white-space:pre-wrap; max-height:140px; overflow:auto; }
.opening { margin-top:8px; }
.opening input { width: min(100%, 720px); display:block; margin:8px 0; padding:6px; color:var(--text); background:var(--surface); border:1px solid var(--border); }
small { display:block; }
button:focus-visible,summary:focus-visible { outline:2px solid var(--accent); }
</style>
