<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRuntimeStore } from "../../stores/runtime";
import { useTopicsStore } from "../../stores/topics";
import type { TopicAction } from "../../lib/ipc";
import TopicDocument from './TopicDocument.vue';
import PersonalCapabilitiesPanel from './PersonalCapabilitiesPanel.vue';

const { t } = useI18n();
const runtime = useRuntimeStore();
const store = useTopicsStore();
const showNew = ref(false);
const entry = ref<"home" | "preferences" | "topics">("home");
const firstAgent = ref<"claude" | "codex">("claude");
const moreSections = ref(false);
const related = computed(() => store.conversationStatus.filter(s => s.topic_id === store.detail?.id));
const goalText = computed(() => store.detail?.events.find(e => e.data.coverage === "主题创建表单")?.data.text as string | undefined);
const sectionLabel = (key: string) => ({ guide: "总结与手册", files: "成果文件", records: "对话与过程", iterations: "修订历史", state: "详细进度" }[key] ?? key);
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
    entry.value = "topics";
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
    await store.startConversation(firstAgent.value);
  }
}
async function prepare(): Promise<void> {
  if (await store.prepare(action.value, feedback.value)) feedback.value = "";
}
</script>

<template>
  <div class="topics-view" data-testid="topics-view">
    <h2>个人能力与主题</h2>
    <p>你想让 AI 更符合你的习惯，还是围绕一件事持续推进？两者可以独立使用。</p>
    <nav class="entry-choices" aria-label="选择使用方式">
      <button class="topic-card" :aria-pressed="entry === 'preferences'" @click="entry = 'preferences'"><strong>设置我的回答偏好</strong><span>例如先给结论、回答简洁。用于新对话，不会自动关联主题。</span></button>
      <button class="topic-card" :aria-pressed="entry === 'topics'" @click="entry = 'topics'"><strong>围绕一个主题持续做事</strong><span>例如学习 Python、制作短视频。集中保存相关对话和成果。</span></button>
    </nav>
    <PersonalCapabilitiesPanel v-show="entry === 'preferences'" />
    <template v-if="entry === 'topics'">
    <h2>我的主题</h2>
    <p class="topic-intro">选一个已有主题继续，或创建新主题。只有从这里开始的对话才会关联主题。</p>
    <p v-if="store.error" class="topic-error" role="alert">{{ store.error }}</p>
    <details v-if="store.warnings.length"><summary>部分主题需要检查</summary><p v-for="warning in store.warnings" :key="warning">{{ warning }}</p></details>
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
          <span>{{ topic.title }}</span>
        </button>
      </nav>

      <form v-if="creating" class="topic-card topic-form" data-testid="topic-create-form" @submit.prevent="createTopic">
        <strong>{{ t("topics.new") }}</strong>
        <label>{{ t("topics.name") }}<input v-model="title" required maxlength="120" data-testid="topic-title" :placeholder="t('topics.nameExample')" /></label>
        <label>{{ t("topics.goal") }}<textarea v-model="goal" required rows="4" maxlength="12000" data-testid="topic-goal" :placeholder="t('topics.goalExample')" /></label>
        <details><summary>添加参考资料（可选）</summary><label>{{ t("topics.sources") }}<textarea v-model="sources" rows="2" data-testid="topic-sources" :placeholder="t('topics.sourcesExample')" /></label></details>
        <label>用哪个 AI 开始<select v-model="firstAgent"><option value="claude">Claude</option><option value="codex">Codex</option></select></label>
        <p class="topic-note">创建后打开一段主题对话，开场问题由你检查后发送。其他新对话不受影响。</p>
        <button type="submit" class="ui-button" data-testid="topic-create" :disabled="store.busy || store.inserting || !title.trim() || !goal.trim()">创建并开始主题对话</button>
      </form>

      <template v-if="store.detail && !creating">
        <div class="topic-workspace">
        <aside class="topic-controls">
        <div class="topic-heading">
          <strong>{{ store.detail.title }}</strong>
          <p v-if="goalText" class="goal-text">{{ goalText }}</p>
        </div>

        <div class="topic-card topic-form" data-testid="topic-conversation-mode">
          <strong>继续做这件事</strong>
          <p>从这里新开的对话只属于“{{ store.detail.title }}”。也可以在下方返回已有对话。</p>
          <div class="topic-toolbar">
            <button type="button" class="ui-button" :disabled="store.busy" data-testid="topic-chat-claude" @click="store.startConversation('claude')">用 Claude 新开主题对话</button>
            <button type="button" class="ui-button" :disabled="store.busy" data-testid="topic-chat-codex" @click="store.startConversation('codex')">用 Codex 新开主题对话</button>
          </div>
          <strong>相关对话</strong>
          <p v-if="!related.length">还没有主题对话。点击上方按钮开始。</p>
          <div v-for="(item, index) in related" :key="item.session_id" class="related-session">
            <span>{{ item.agent === 'claude' ? 'Claude' : 'Codex' }} 对话 {{ index + 1 }} · {{ item.state === 'error' ? '同步需处理，历史保留' : item.state === 'completed' ? '记录已停止' : item.captured ? '记录已保存' : '等待对话记录' }}</span>
            <button v-if="store.sessions.some(s => s.sessionId === item.session_id)" class="ui-button sm" @click="store.resumeSession(item.session_id)">返回对话</button>
            <small v-else>当前未打开；可从工作记录查看或继续原会话。</small>
          </div>
        </div>
        <details class="topic-card" data-testid="topic-advanced">
          <summary>更多：整理、历史与诊断</summary>
          <p>记录保存不代表总结已经整理。需要更新总结时，在下方选择“整理主题手册”，准备后交给 AI。</p>
          <details v-if="store.syncError || store.syncWarnings.length || store.detail.warnings.length"><summary>同步诊断</summary><pre>{{ store.syncError }}</pre><p v-for="warning in [...store.detail.warnings, ...store.syncWarnings]" :key="warning">{{ warning }}</p></details>
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

          <p class="topic-note">新开普通对话请使用标签栏 ＋。停止记录入口在对应主题对话顶部的“更多”中。</p>
        </details>

        </aside>
        <div class="topic-reading">
        <div class="topic-sections" role="tablist" :aria-label="t('topics.contents')">
          <button v-for="item in (moreSections ? sections : sections.filter(s => ['guide', 'files'].includes(s)))" :key="item" type="button" role="tab" :aria-selected="section === item" :class="{ active: section === item }" :data-testid="'topic-section-' + item" @click="section = item">{{ sectionLabel(item) }}</button>
          <button @click="moreSections = !moreSections">{{ moreSections ? "收起更多" : "更多记录" }}</button>
        </div>
        <div class="topic-content" role="tabpanel">
          <div v-if="section === 'iterations'" class="topic-toolbar topic-log-actions">
            <button type="button" class="ui-button sm" data-testid="topic-open-log" :disabled="!store.detail.iteration_log" @click="store.accessIterationLog()">{{ t('topics.openLog') }}</button>
            <button type="button" class="ui-button sm" data-testid="topic-reveal-log" :disabled="!store.detail.iteration_log" @click="store.accessIterationLog(true)">{{ t('topics.revealLog') }}</button>
          </div>
          <TopicDocument v-if="section === 'guide'" :text="store.detail.guide || t('topics.emptyGuide')" @open="store.openReference" />
          <TopicDocument v-else-if="section === 'iterations'" data-testid="topic-iteration-log" :text="store.detail.iteration_log || t('topics.emptyIterations')" @open="store.openReference" />
          <TopicDocument v-else-if="section === 'state'" :text="store.detail.state || t('topics.emptyState')" @open="store.openReference" />
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
              <TopicDocument :text="eventBody(event.data) || event.summary" @open="store.openReference" />
              <details><summary>原始记录与技术详情</summary><small>{{ event.id }} · {{ event.type }}</small><pre>{{ JSON.stringify(event.data, null, 2) }}</pre></details>
            </article>
          </div>
        </div>
        <details class="topic-card"><summary>检查记录完整性（进阶）</summary>
          <button type="button" class="ui-button sm" data-testid="topic-check" :disabled="store.busy" @click="store.check()">{{ t("topics.check") }}</button>
          <p class="topic-note">{{ t("topics.checkScope") }}</p>
          <div v-if="store.checkResult" role="status">
            <p>{{ t('topics.check.' + (store.checkResult.status === 'passed' ? 'passed' : 'failed'), { count: store.checkResult.checked_events }) }}</p>
            <p v-for="message in store.checkResult.errors" :key="message" class="topic-error">{{ message }}</p>
            <p v-for="message in store.checkResult.warnings" :key="message" class="topic-note">{{ message }}</p>
          </div>
        </details>
        </div>
        </div>
      </template>
    </template>
    </template>
  </div>
</template>

<style scoped>
.entry-choices { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; }
.entry-choices button { display:grid; gap:8px; text-align:left; color:var(--text); cursor:pointer; padding:20px; }
.entry-choices button[aria-pressed=true] { border-color:var(--accent); }
.entry-choices span { color:var(--text-muted); font-size:var(--font-xs); }
.goal-text { white-space:pre-wrap; }
.related-session { display:grid; gap:6px; border-top:1px solid var(--border); padding-top:8px; }

.topics-view { container-type: inline-size; display: flex; flex-direction: column; gap: var(--space-3); padding: 24px clamp(16px, 3vw, 48px); overflow: auto; min-height: 0; }
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

.topic-list { display: flex; flex-wrap: wrap; }
.topic-choice { min-width: 180px; max-width: 320px; }
.topic-workspace { display: grid; grid-template-columns: minmax(240px, 300px) minmax(0, 1fr); gap: 24px; align-items: start; }
.topic-controls, .topic-reading { display: grid; gap: 16px; min-width: 0; }
.topic-heading strong { font-size: 22px; font-weight: 600; }
.topic-content { padding: 24px; background: var(--surface); min-height: 360px; }
.topic-sections button { padding: 9px 12px; }
@container (max-width: 760px) { .topic-workspace { grid-template-columns: minmax(0, 1fr); } .topic-content { padding: 16px; } }
</style>
