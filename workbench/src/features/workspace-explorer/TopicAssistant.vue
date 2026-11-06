<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { TopicCallParams } from '../../lib/ipc';
import { useTopicAssistantStore } from '../../stores/topicAssistant';

const props = defineProps<{ workspace: string; topicId: string }>();
const { locale } = useI18n();
const api = useTopicAssistantStore();
const l = (zh: string, en: string) => locale.value.startsWith('zh') ? zh : en;
interface Memory { id: string; kind: string; text: string; status: string; evidence: string }
interface Baseline { id: string; name: string; purpose: string; source: string; fingerprint: string; path: string }
interface Assistant { revision: number; enabled: boolean; mode: string; memories: Memory[]; baselines: Baseline[] }
interface Result { assistant: Assistant; profile: Assistant }
const settings = ref<Assistant>();
const profile = ref<Assistant>();
const skills = ref<Array<{ id: string; name: string; source: string }>>([]);
const selected = ref('');
const purpose = ref('');
const busy = ref(false);
const error = ref('');
const notice = ref('');
const warnings = ref<string[]>([]);
const saved = ref('');
let generation = 0;
const serialized = () => JSON.stringify([settings.value, profile.value]);
const dirty = computed(() => !!settings.value && serialized() !== saved.value);
const kinds = ['preference', 'constraint', 'experience', 'rule'];
const kindName = (kind: string) => ({preference: l('偏好','Preference'), constraint: l('条件与限制','Constraint'), experience: l('实践经验','Experience'), rule: l('协作约定','Rule')}[kind] ?? kind);
function accept(result: Result) {
  settings.value = result.assistant; profile.value = result.profile; saved.value = serialized();
}
async function load() {
  const token = ++generation;
  busy.value = true; error.value = ''; notice.value = '';
  const workspace = props.workspace, id = props.topicId;
  try {
    const result = await api.call<Result>({workspace, id, operation: 'assistant-show'});
    if (token !== generation) return;
    accept(result);
    const list = await api.call<{skills: typeof skills.value; warnings: string[]}>({workspace, operation: 'assistant-skills'});
    if (token !== generation) return;
    skills.value = list.skills; warnings.value = list.warnings;
  } catch(e) { if (token === generation) error.value = (e as Error)?.message ?? String(e); }
  finally { if (token === generation) busy.value = false; }
}
watch(() => [props.workspace, props.topicId], () => {
  settings.value = undefined; profile.value = undefined; skills.value = []; selected.value = ''; purpose.value = ''; warnings.value = [];
  void load();
}, {immediate: true});
async function mutate(operation: TopicCallParams['operation'], payload: Record<string, unknown>) {
  if (busy.value) return;
  const token = generation;
  busy.value = true; error.value = ''; notice.value = '';
  try {
    const result = await api.call<Result>({workspace: props.workspace, id: props.topicId, operation, payload});
    if (token !== generation) return;
    // A topic save must not discard unsaved shared preferences (and vice versa).
    if (operation === 'assistant-save') {
      settings.value = result.assistant;
      const prior = JSON.parse(saved.value) as [Assistant, Assistant];
      saved.value = JSON.stringify([result.assistant, prior[1]]);
    } else if (operation === 'assistant-profile-save') {
      profile.value = result.profile;
      const prior = JSON.parse(saved.value) as [Assistant, Assistant];
      saved.value = JSON.stringify([prior[0], result.profile]);
    } else accept(result);
    notice.value = l('已保存。新对话会加载这些设置；当前对话请告诉助手重新读取。','Saved. New chats load these settings; ask the current assistant to reread them.');
  } catch(e) { if (token === generation) error.value = (e as Error)?.message ?? String(e); }
  finally { if (token === generation) busy.value = false; }
}
function save(shared = false) {
  const value = shared ? profile.value : settings.value;
  if (!value) return;
  void mutate(shared ? 'assistant-profile-save' : 'assistant-save', {expected_revision: value.revision, enabled: value.enabled, mode: value.mode, memories: value.memories});
}
function addMemory(shared = false) {
  const value = shared ? profile.value : settings.value;
  value?.memories.push({id: crypto.randomUUID(), kind: 'preference', text: '', status: 'confirmed', evidence: ''});
}
function pin() {
  if (!settings.value || dirty.value) return;
  void mutate('assistant-pin', {expected_revision: settings.value.revision, skill_id: selected.value, purpose: purpose.value});
}
function unpin(id: string) {
  if (!settings.value || dirty.value) return;
  void mutate('assistant-unpin', {expected_revision: settings.value.revision, baseline_id: id});
}
</script>

<template>
  <section class="assistant" data-testid="topic-assistant">
    <header><h3>{{ l('让助手逐步适应你','An assistant that adapts to you') }}</h3>
      <p>{{ l('直接在对话中说目标、偏好和反馈。这里可以核对、修改记忆，并选择做事的方法。','Share goals, preferences and feedback in chat. Review memories and choose methods here.') }}</p>
    </header>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-for="warning in warnings" :key="warning" class="error">{{ warning }}</p>
    <button class="ui-button sm" :disabled="busy" @click="load">{{ dirty ? l('放弃未保存修改并刷新','Discard edits and reload') : l('刷新','Refresh') }}</button>
    <p v-if="busy" role="status">{{ l('正在处理…','Working…') }}</p>
    <template v-if="settings && profile">
      <fieldset :disabled="busy">
        <legend>{{ l('合作方式','Working together') }}</legend>
        <label class="inline"><input v-model="settings.enabled" type="checkbox" data-testid="assistant-enabled" />{{ l('为这个主题启用助手记忆与方法基线','Enable assistant memories and methods for this topic') }}</label>
        <p v-if="!settings.enabled">{{ l('原主题手册和 skill 保持不变。启用后才会加载下面的记忆与方法。','Existing topic files and skill are preserved. Enable to load the memories and methods below.') }}</p>
        <label>{{ l('协作节奏','Working style') }}<select v-model="settings.mode" data-testid="assistant-mode">
          <option value="collaborate">{{ l('一起做：讨论关键选择，推进成果','Collaborate: discuss choices and produce results') }}</option>
          <option value="coach">{{ l('带我学：示范、试做、复盘，学会自己改进','Coach: demonstrate, practice and reflect') }}</option>
          <option value="deliver">{{ l('直接做：优先交付，说明必要检查','Deliver: focus on the result and essential checks') }}</option>
        </select></label>
        <p>{{ l('每轮明确目标、成果和检查方式；先由助手检查，再指导你试用。','Each task has a goal, a deliverable and checks. The assistant checks first, then guides your trial.') }}</p>
      </fieldset>
      <fieldset :disabled="busy">
        <legend>{{ l('这个主题的记忆','Memories for this topic') }}</legend>
        <p>{{ l('只用于本主题。待验证的经验不会当作已经有效的方法；不保存密码或密钥。','Used only for this topic. Provisional experience is not a proven method. Do not store credentials.') }}</p>
        <article v-for="(memory, index) in settings.memories" :key="memory.id" class="memory">
          <div class="row"><select v-model="memory.kind" :aria-label="l('记忆类型','Memory type')"><option v-for="kind in kinds" :key="kind" :value="kind">{{ kindName(kind) }}</option></select>
            <select v-model="memory.status" :aria-label="l('确认状态','Status')"><option value="confirmed">{{ l('已确认','Confirmed') }}</option><option value="provisional">{{ l('待确认或待验证','Provisional') }}</option></select>
            <button class="ui-button sm" @click="settings.memories.splice(index, 1)">{{ l('移除','Remove') }}</button></div>
          <textarea v-model="memory.text" rows="2" maxlength="2000" :aria-label="l('记忆内容','Memory content')" :placeholder="l('例如：我每周只能投入两小时，希望先看具体示例。','Example: I have two hours per week and prefer concrete examples.')" />
          <input v-model="memory.evidence" maxlength="1000" :aria-label="l('来源与适用条件','Source and conditions')" :placeholder="l('来源与适用条件；已确认的实践经验必填','Source and conditions; required for confirmed experience')" />
        </article>
        <button class="ui-button sm" :disabled="settings.memories.length >= 40" @click="addMemory()">{{ l('添加主题记忆','Add topic memory') }}</button>
        <button class="ui-button" data-testid="assistant-save" @click="save()">{{ l('保存主题设置与记忆','Save topic settings and memories') }}</button>
      </fieldset>
      <fieldset :disabled="busy">
        <legend>{{ l('本工作区共享偏好','Shared workspace preferences') }}</legend>
        <label class="inline"><input v-model="profile.enabled" type="checkbox" />{{ l('允许本工作区已启用助手的主题使用这些偏好','Use these preferences in enabled assistant topics in this workspace') }}</label>
        <article v-for="(memory, index) in profile.memories" :key="memory.id" class="memory row">
          <textarea v-model="memory.text" rows="2" maxlength="2000" :aria-label="l('共享偏好','Shared preference')" />
          <button class="ui-button sm" @click="profile.memories.splice(index, 1)">{{ l('移除','Remove') }}</button>
        </article>
        <button class="ui-button sm" :disabled="profile.memories.length >= 40" @click="addMemory(true)">{{ l('添加共享偏好','Add shared preference') }}</button>
        <button class="ui-button" @click="save(true)">{{ l('保存共享偏好','Save shared preferences') }}</button>
        <p>{{ l('移除并保存后，不再作为助手记忆使用。原始聊天记录不会因此删除。','Removed memories stop being used after saving. Original chat records are not deleted.') }}</p>
      </fieldset>
      <fieldset :disabled="busy || dirty">
        <legend>{{ l('我的方法：市场 Skill 基线','My methods: marketplace skill baselines') }}</legend>
        <p>{{ l('从扩展市场安装技能后，在此选择用途。保存完整副本，市场更新不会自动改变当前方法。','Install skills from the extension market, then select their purpose here. Full snapshots stay fixed when the market updates.') }}</p>
        <p v-if="dirty">{{ l('请先保存上方修改，再调整方法基线。','Save the edits above before changing baselines.') }}</p>
        <article v-for="baseline in settings.baselines" :key="baseline.id" class="memory">
          <strong>{{ baseline.name }}</strong><p>{{ baseline.purpose }}</p>
          <small>{{ l('固定副本','Pinned snapshot') }} · {{ baseline.fingerprint.slice(0,12) }}</small>
          <button class="ui-button sm" @click="unpin(baseline.id)">{{ l('停止使用','Stop using') }}</button>
        </article>
        <p v-if="!skills.length">{{ l('没有找到已安装技能。先在扩展市场安装，再刷新这里；也可以不选基线直接开始。','No installed skills found. Install in the extension market and refresh, or begin without a baseline.') }}</p>
        <label>{{ l('已安装技能','Installed skill') }}<select v-model="selected" data-testid="assistant-baseline"><option value="">{{ l('请选择','Select a skill') }}</option><option v-for="skill in skills" :key="skill.id" :value="skill.id">{{ skill.name }}</option></select></label>
        <label>{{ l('在本主题中负责什么','Purpose in this topic') }}<input v-model="purpose" maxlength="2000" :placeholder="l('例如：组织视频故事结构，保留我的口语风格','Example: structure video stories while preserving my conversational style')" /></label>
        <button class="ui-button" :disabled="!selected || !purpose.trim() || settings.baselines.length >= 8" @click="pin">{{ l('固定为主题基线','Pin as a topic baseline') }}</button>
        <p>{{ l('停止使用不会删除历史副本或已安装技能。要采用新版，请停止使用后重新选择。','Stopping use preserves historical snapshots and installed skills. Select again to adopt a newer version.') }}</p>
      </fieldset>
    </template>
  </section>
</template>

<style scoped>
.assistant { display:grid; gap:16px; min-width:0; }
h3 { margin:0; font-size:20px; }
p { color:var(--text-2); line-height:1.6; margin:8px 0; }
fieldset { min-width:0; border:1px solid var(--border-2); border-radius:var(--radius-sm); padding:16px; display:grid; gap:12px; }
legend { font-weight:600; padding:0 6px; }
label { display:grid; gap:6px; }
label.inline { display:flex; align-items:center; gap:8px; }
.row { display:flex; gap:8px; align-items:start; flex-wrap:wrap; }
.row > select, .row > textarea { flex:1; min-width:140px; }
input:not([type=checkbox]), textarea, select { width:100%; box-sizing:border-box; background:var(--surface-2); color:var(--text); border:1px solid var(--border); border-radius:var(--radius-sm); padding:8px; font:inherit; }
textarea { resize:vertical; }
.memory { display:grid; gap:8px; border-top:1px solid var(--border-2); padding-top:12px; }
.memory.row { display:flex; }
button { justify-self:start; }
.error { color:var(--error); overflow-wrap:anywhere; }
small { overflow-wrap:anywhere; color:var(--text-2); }
:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
</style>
