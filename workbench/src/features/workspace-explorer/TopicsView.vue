<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRuntimeStore } from "../../stores/runtime";
import { useTopicsStore } from "../../stores/topics";
import type { TopicAction } from "../../lib/ipc";
import { workspaceOpen } from "../../lib/ipc";
import TopicDocument from './TopicDocument.vue';

const { t } = useI18n();
const runtime = useRuntimeStore();
const store = useTopicsStore();
const showNew = ref(false);
const title = ref("");
const goal = ref("");
const sources = ref("");
const action = ref<TopicAction>("continue");
const feedback = ref("");
const selectedSession = ref("");
const section = ref("guide");
let draftTopicId = "";
const sections = ["guide", "iterations", "state", "files", "records"] as const;
const deliverables = computed(() => store.detail?.files.filter(p => !store.detail?.internal_files?.includes(p)) ?? []);
async function openReference(path: string) {
  if (!store.detail || !runtime.workspace || /^(?:[a-z]+:|[/\\])/i.test(path) || path.split(/[/\\]/).includes('..')) return;
  try { await workspaceOpen(runtime.workspace, `${store.detail.relative_path}/${path}`); }
  catch (error) { store.error = String(error); }
}
function readable(value: unknown): string {
  if (Array.isArray(value)) return value.map(readable).join('\n');
  if (value && typeof value === 'object') return Object.entries(value).map(([key, item]) => `${({ practical_use: '实际使用', record_check: '记录检查', status: '状态', warnings: '提示', errors: '错误', scope: '范围', checked_events: '检查记录数' } as Record<string,string>)[key] ?? key}：${readable(item)}`).join('\n');
  return String(value ?? '');
}
function eventBody(data: Record<string, unknown>): string {
  if (typeof data.text === 'string') return data.text;
  const labels: Record<string,string> = { trigger: '触发原因', previous: '原有做法', change: '修改内容', reason: '原因', decision: '决定', outcome: '结果', verification: '验证情况', next_steps: '下一步', description: '说明', issue: '问题', next_action: '下一步' };
  return Object.entries(labels).filter(([key]) => data[key] !== undefined).map(([key,label]) => `**${label}**：${readable(data[key])}`).join('\n\n');
}
function localTime(value?: string) { return value && !Number.isNaN(Date.parse(value)) ? new Date(value).toLocaleString() : ''; }
const actions: TopicAction[] = ["continue", "feedback", "guide", "improve"];

watch([() => runtime.workspace, () => runtime.id], ([path, id]) => {
  store.setContext(path ?? "", id);
  title.value = ""; goal.value = ""; sources.value = ""; feedback.value = "";
  showNew.value = false; selectedSession.value = "";
  draftTopicId = "";
  void store.load();
}, { immediate: true });
watch(() => store.detail?.id, (id) => {
  selectedSession.value = "";
  section.value = "guide";
  if (id && id !== draftTopicId) {
    feedback.value = "";
    action.value = "continue";
    draftTopicId = id;
  }
});
watch(() => store.sessions.map(item => item.sessionId), (ids) => {
  if (!ids.includes(selectedSession.value)) selectedSession.value = "";
});

const creating = computed(() => showNew.value || (!store.topics.length && !store.loading));
const canPrepare = computed(() => !store.busy && !store.inserting
  && (action.value !== "feedback" || !!feedback.value.trim()));

async function createTopic(): Promise<void> {
  const success = await store.create(title.value, goal.value,
    sources.value.split(/\r?\n/).map(path => path.trim()).filter(Boolean));
  if (success) {
    showNew.value = false;
    title.value = ""; goal.value = ""; sources.value = "";
  }
}
async function prepare(): Promise<void> {
  if (await store.prepare(action.value, feedback.value)) feedback.value = "";
}
</script>

<template>
  <div class="topics-view" data-testid="topics-view">
    <p class="topic-intro">{{ t("topics.intro") }}</p>
    <p v-if="store.error" class="topic-error" role="alert">{{ store.error }}</p>
    <p v-for="warning in store.warnings" :key="warning" class="topic-note">{{ warning }}</p>
    <p v-if="!runtime.workspace" class="topic-note">{{ t("topics.noWorkspace") }}</p>
    <template v-else>
      <div class="topic-toolbar">
        <button type="button" class="ui-button sm" data-testid="topic-new" :disabled="store.busy || store.inserting" @click="showNew = !showNew">{{ t("topics.new") }}</button>
        <button type="button" class="ui-button sm" :disabled="store.loading || store.busy" @click="store.refresh()">{{ t("topics.refresh") }}</button>
      </div>
      <p v-if="store.loading" class="topic-note" role="status">{{ t("topics.loading") }}</p>
      <nav v-if="store.topics.length" class="topic-list" :aria-label="t('topics.list')">
        <button v-for="topic in store.topics" :key="topic.id" type="button"
          class="topic-choice" :class="{ selected: store.detail?.id === topic.id }"
          :aria-pressed="store.detail?.id === topic.id" :disabled="store.busy || store.inserting"
          :data-testid="'topic-select-' + topic.id" @click="store.select(topic.id); showNew = false">
          <span>{{ topic.title }}</span><small>{{ topic.relative_path }}</small>
        </button>
      </nav>

      <form v-if="creating" class="topic-card topic-form" data-testid="topic-create-form" @submit.prevent="createTopic">
        <strong>{{ t("topics.new") }}</strong>
        <label>{{ t("topics.name") }}<input v-model="title" required maxlength="120" data-testid="topic-title" :placeholder="t('topics.nameExample')" /></label>
        <label>{{ t("topics.goal") }}<textarea v-model="goal" required rows="4" maxlength="12000" data-testid="topic-goal" :placeholder="t('topics.goalExample')" /></label>
        <label>{{ t("topics.sources") }}<textarea v-model="sources" rows="2" data-testid="topic-sources" :placeholder="t('topics.sourcesExample')" /></label>
        <p class="topic-note">{{ t("topics.recordingNotice") }}</p>
        <button type="submit" class="ui-button" data-testid="topic-create" :disabled="store.busy || store.inserting || !title.trim() || !goal.trim()">{{ t("topics.create") }}</button>
      </form>

      <template v-if="store.detail && !creating">
        <div class="topic-heading">
          <strong>{{ store.detail.title }}</strong>
          <small>{{ t("topics.skill") }} · {{ store.detail.skill_version }}</small>
        </div>
        <p v-for="warning in store.detail.warnings" :key="warning" class="topic-note">{{ warning }}</p>
        <div class="topic-card topic-form" data-testid="topic-conversation-mode">
          <strong>{{ t('topics.chatNormally') }}</strong>
          <p class="topic-note">{{ t('topics.conversationHelp') }}</p>
          <p v-if="store.activeTopic?.id === store.detail.id" class="topic-success">{{ t('topics.modeEnabled') }}</p>
          <button v-else type="button" class="ui-button" :disabled="store.busy" data-testid="topic-enable" @click="store.enableConversation()">{{ t('topics.enableConversation') }}</button>
          <div class="topic-toolbar">
            <button type="button" class="ui-button sm" :disabled="store.busy" data-testid="topic-chat-claude" @click="store.startConversation('claude')">{{ t('topics.chatAgent', { agent: 'Claude' }) }}</button>
            <button type="button" class="ui-button sm" :disabled="store.busy" data-testid="topic-chat-codex" @click="store.startConversation('codex')">{{ t('topics.chatAgent', { agent: 'Codex' }) }}</button>
          </div>
          <p v-for="item in store.conversationStatus.filter(s => s.topic_id === store.detail?.id)" :key="item.session_id" class="topic-note">
            {{ item.agent }} · {{ t('topics.captureState.' + item.state) }} · {{ t('topics.captured', { count: item.captured }) }}
            <span v-if="item.guide_pending"> · {{ t('topics.guidePending') }}</span>
          </p>
          <p v-if="store.syncError" class="topic-error" role="alert">{{ store.syncError }}</p>
        </div>
        <details class="topic-card" data-testid="topic-advanced">
          <summary>{{ t('topics.optionalActions') }}</summary>
        <form class="topic-card topic-form" data-testid="topic-action-form" @submit.prevent="prepare">
          <label>{{ t("topics.action") }}
            <select v-model="action" data-testid="topic-action"><option v-for="item in actions" :key="item" :value="item">{{ t('topics.action.' + item) }}</option></select>
          </label>
          <label>{{ action === 'feedback' ? t('topics.feedback') : t('topics.additional') }}
            <textarea v-model="feedback" rows="3" maxlength="12000" data-testid="topic-feedback" :required="action === 'feedback'" :placeholder="t('topics.feedbackExample')" />
          </label>
          <button type="submit" class="ui-button" data-testid="topic-prepare" :disabled="!canPrepare">{{ t("topics.prepare") }}</button>
        </form>

        <div v-if="store.request" class="topic-card topic-form" data-testid="topic-handoff">
          <strong>{{ t("topics.requestSaved") }}</strong>
          <label>{{ t("topics.savedRequests") }}
            <select :value="store.request.id" :disabled="store.busy || store.inserting" data-testid="topic-request" @change="store.chooseRequest(($event.target as HTMLSelectElement).value)">
              <option v-for="item in store.detail.requests" :key="item.id" :value="item.id">{{ t('topics.action.' + item.action) }} · {{ item.created_at }}</option>
            </select>
          </label>
          <p class="topic-note">{{ t("topics.handoffHint") }}</p>
          <div class="topic-toolbar">
            <button type="button" class="ui-button sm" @click="store.openAgent('claude')">{{ t("topics.openAgent", { agent: 'Claude' }) }}</button>
            <button type="button" class="ui-button sm" @click="store.openAgent('codex')">{{ t("topics.openAgent", { agent: 'Codex' }) }}</button>
          </div>
          <label>{{ t("topics.session") }}
            <select v-model="selectedSession" data-testid="topic-session" :disabled="store.inserting">
              <option value="">{{ t("topics.chooseSession") }}</option>
              <option v-for="session in store.sessions" :key="session.sessionId" :value="session.sessionId">{{ session.label }}</option>
            </select>
          </label>
          <details><summary>{{ t("topics.promptPreview") }}</summary><pre>{{ store.request.prompt }}</pre></details>
          <button type="button" class="ui-button" data-testid="topic-insert" :disabled="!selectedSession || store.busy || store.inserting || store.inserted" @click="store.insert(selectedSession)">{{ t("topics.insert") }}</button>
          <p v-if="store.inserted" class="topic-success" role="status">{{ t("topics.inserted") }}</p>
        </div>
          <button v-if="store.activeTopic?.id === store.detail.id" type="button" class="ui-button sm" :disabled="store.busy" @click="store.disableConversation()">{{ t('topics.disableConversation') }}</button>
          <p class="topic-note">{{ t('topics.switchScope') }}</p>
        </details>

        <div class="topic-sections" role="tablist" :aria-label="t('topics.contents')">
          <button v-for="item in sections" :key="item" type="button" role="tab" :aria-selected="section === item" :class="{ active: section === item }" :data-testid="'topic-section-' + item" @click="section = item">{{ t('topics.section.' + item) }}</button>
        </div>
        <div class="topic-content" role="tabpanel">
          <div v-if="section === 'iterations'" class="topic-toolbar topic-log-actions">
            <button type="button" class="ui-button sm" data-testid="topic-open-log" :disabled="!store.detail.iteration_log" @click="store.accessIterationLog()">{{ t('topics.openLog') }}</button>
            <button type="button" class="ui-button sm" data-testid="topic-reveal-log" :disabled="!store.detail.iteration_log" @click="store.accessIterationLog(true)">{{ t('topics.revealLog') }}</button>
          </div>
          <TopicDocument v-if="section === 'guide'" :text="store.detail.guide || t('topics.emptyGuide')" @open="openReference" />
          <TopicDocument v-else-if="section === 'iterations'" data-testid="topic-iteration-log" :text="store.detail.iteration_log || t('topics.emptyIterations')" @open="openReference" />
          <TopicDocument v-else-if="section === 'state'" :text="store.detail.state || t('topics.emptyState')" @open="openReference" />
          <div v-else-if="section === 'files'" class="topic-files">
            <p v-if="!deliverables.length" class="topic-note">尚无实际成果，完成脚本或其他作品后会显示在这里。</p>
            <button v-for="path in deliverables" :key="path" type="button" class="topic-file" @click="store.openFile(path)">{{ path.split('/').pop() }}</button>
            <details v-if="store.detail.internal_files?.length"><summary>内部辅助文件（{{ store.detail.internal_files.length }}）</summary>
              <button v-for="path in store.detail.internal_files" :key="path" class="topic-file" @click="store.openFile(path)">{{ path.split('/').pop() }}</button>
            </details>
          </div>
          <div v-else class="topic-records">
            <p class="topic-note">{{ t("topics.coverage") }}</p>
            <p v-if="!store.detail.events.length" class="topic-note">{{ t("topics.emptyRecords") }}</p>
            <article v-for="event in store.detail.events" :key="event.id" class="topic-event">
              <strong>{{ event.data.speaker === 'user' ? '你' : event.data.speaker === 'assistant' ? 'AI' : event.summary }}</strong>
              <small style="display:block">{{ localTime(event.recorded_at) }}</small>
              <TopicDocument :text="eventBody(event.data) || event.summary" @open="openReference" />
              <details><summary>原始记录与技术详情</summary><small>{{ event.id }} · {{ event.type }}</small><pre>{{ JSON.stringify(event.data, null, 2) }}</pre></details>
            </article>
          </div>
        </div>
        <div class="topic-card">
          <button type="button" class="ui-button sm" data-testid="topic-check" :disabled="store.busy" @click="store.check()">{{ t("topics.check") }}</button>
          <p class="topic-note">{{ t("topics.checkScope") }}</p>
          <div v-if="store.checkResult" role="status">
            <p>{{ t('topics.check.' + (store.checkResult.status === 'passed' ? 'passed' : 'failed'), { count: store.checkResult.checked_events }) }}</p>
            <p v-for="message in store.checkResult.errors" :key="message" class="topic-error">{{ message }}</p>
            <p v-for="message in store.checkResult.warnings" :key="message" class="topic-note">{{ message }}</p>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.topics-view { display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-2); overflow: auto; min-height: 0; }
.topic-intro, .topic-note, .topic-error, .topic-success { margin: 0; font-size: var(--font-xs); line-height: 1.5; overflow-wrap: anywhere; }
.topic-note, small { color: var(--text-muted); }
.topic-error { color: var(--error); }
.topic-success { color: var(--accent); }
.topic-toolbar, .topic-sections { display: flex; gap: var(--space-1); flex-wrap: wrap; }
.topic-log-actions { margin-bottom: var(--space-3); }
.topic-card { padding: var(--space-2); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface); }
.topic-form, .topic-list, .topic-heading, .topic-files, .topic-records { display: grid; gap: var(--space-2); }
.topic-form label { display: grid; gap: var(--space-1); font-size: var(--font-xs); }
input, textarea, select { width: 100%; box-sizing: border-box; min-width: 0; padding: var(--space-2); border: var(--border-w) solid var(--border); border-radius: var(--radius-sm); background: var(--surface-2); color: var(--text); font: inherit; }
textarea { resize: vertical; }
.topic-choice { display: grid; gap: var(--space-1); text-align: left; padding: var(--space-2); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface); color: var(--text); cursor: pointer; overflow-wrap: anywhere; }
.topic-choice.selected { border-color: var(--accent); background: var(--surface-2); }
.topic-sections button { flex: 1; border: var(--border-w) solid var(--border); border-radius: var(--radius-sm); padding: var(--space-1); color: var(--text-2); background: var(--surface); cursor: pointer; }
.topic-sections button.active { color: var(--accent); border-color: var(--accent); }
.topic-content { border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); padding: var(--space-2); }
pre { margin: var(--space-1) 0; white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; font-size: var(--font-xs); line-height: 1.6; }
.topic-file { text-align: left; border: 0; background: transparent; padding: var(--space-1); color: var(--accent); overflow-wrap: anywhere; cursor: pointer; }
summary { cursor: pointer; font-size: var(--font-xs); overflow-wrap: anywhere; }
.topic-event { border-bottom: var(--border-w) solid var(--border-2); padding-bottom: var(--space-2); }
.topic-event summary small { display: block; margin-top: var(--space-1); }
button:focus-visible, summary:focus-visible { outline: var(--focus-ring-width) solid var(--focus); outline-offset: 2px; }
button:disabled { cursor: default; opacity: .5; }
</style>
