<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useWorkspaceExplorerStore } from "../../stores/workspaceExplorer";
import type { ConversationReadMessage } from "../../types";
import { readingTurns } from "./conversationReading";
import RecordContent from "./RecordContent.vue";

const { t } = useI18n();
const explorer = useWorkspaceExplorerStore();
const PAGE = 100;
const target = computed(() => explorer.conversationViewer);
const messages = ref<ConversationReadMessage[]>([]);
const turns = computed(() => readingTurns(messages.value));
const total = ref(0);
const start = ref(0);
const omitted = ref(0);
const malformed = ref(0);
const openActivities = ref(new Set<number>());
const openSteps = ref(new Set<number>());
const loading = ref(false);
const loadingEarlier = ref(false);
const error = ref("");
const bodyEl = ref<HTMLElement | null>(null);
const panel = ref<HTMLElement | null>(null);
let generation = 0;
let opener: HTMLElement | null = null;

async function loadInitial() {
  const cur = target.value;
  if (!cur || !explorer.workspace) return;
  const request = ++generation;
  loading.value = true; loadingEarlier.value = false; error.value = "";
  messages.value = []; total.value = 0; start.value = 0; omitted.value = 0; malformed.value = 0;
  openActivities.value = new Set(); openSteps.value = new Set();
  try {
    const r = await explorer.readConversationPage(cur.conversationId, cur.agent, PAGE);
    if (request !== generation) return;
    messages.value = r.messages; total.value = r.total; start.value = r.start;
    omitted.value = r.omitted_entries ?? 0; malformed.value = r.malformed_lines;
    // A snapshot opens at the beginning of the loaded page; never follows output.
    await nextTick();
    if (request === generation && bodyEl.value) bodyEl.value.scrollTop = 0;
  } catch (e) { if (request === generation) error.value = String(e); }
  finally { if (request === generation) loading.value = false; }
}

async function loadEarlier() {
  const cur = target.value;
  if (!cur || loadingEarlier.value || loading.value || start.value <= 0) return;
  const request = generation;
  loadingEarlier.value = true; error.value = "";
  const el = bodyEl.value;
  const oldHeight = el?.scrollHeight ?? 0;
  const oldTop = el?.scrollTop ?? 0;
  try {
    const r = await explorer.readConversationPage(cur.conversationId, cur.agent, PAGE, start.value);
    if (request !== generation) return;
    messages.value = [...r.messages, ...messages.value]; start.value = r.start;
    await nextTick();
    if (request === generation && el) el.scrollTop = oldTop + el.scrollHeight - oldHeight;
  } catch (e) { if (request === generation) error.value = String(e); }
  finally { if (request === generation) loadingEarlier.value = false; }
}

function close() { explorer.closeConversationViewer(); }
function time(ts?: string | null) {
  if (!ts) return "";
  const date = new Date(ts);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
}
function preview(text: string) { return text.split("\n")[0]?.slice(0, 100) ?? ""; }
function toggle(set: Set<number>, id: number, event: Event) {
  if ((event.target as HTMLDetailsElement).open) set.add(id); else set.delete(id);
}
function keydown(event: KeyboardEvent) {
  if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(); return; }
  if (event.key !== "Tab" || !panel.value) return;
  const nodes = [...panel.value.querySelectorAll<HTMLElement>("button:not([disabled]), summary, a[href], [tabindex='0']")]
    .filter(el => el.getClientRects().length > 0);
  const first = nodes[0], last = nodes[nodes.length - 1];
  if (!first || !last) return;
  if (event.shiftKey && (document.activeElement === first || document.activeElement === panel.value)) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}
watch(target, async (value, old) => {
  if (!value) {
    generation++; messages.value = []; error.value = "";
    await nextTick(); if (opener?.isConnected) opener.focus(); opener = null;
  } else {
    if (!old) opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    void loadInitial();
    await nextTick(); panel.value?.focus();
  }
}, { immediate: true });
watch(() => explorer.workspace, () => { if (target.value) close(); });
onBeforeUnmount(() => { generation++; });
</script>

<template>
  <Teleport to="body">
    <div v-if="target" class="cv-backdrop" @click.self="close" @keydown="keydown">
      <section ref="panel" class="cv-panel" role="dialog" aria-modal="true" aria-labelledby="record-reader-title" tabindex="-1">
        <header class="cv-head">
          <div class="cv-heading">
            <p class="cv-context">AISC · Work Record <span>{{ target.agent === 'claude' ? 'Claude Code' : 'Codex' }}</span></p>
            <h1 id="record-reader-title" :title="target.title">{{ target.title || t('history.viewer.title') }}</h1>
          </div>
          <button type="button" class="cv-close" :aria-label="t('common.close')" @click="close">{{ t('common.close') }} <span aria-hidden="true">×</span></button>
        </header>
        <div ref="bodyEl" class="cv-body" tabindex="0" :aria-label="t('history.viewer.title')" :aria-busy="loading">
          <div class="cv-reading-column">
            <div v-if="start > 0" class="cv-earlier"><button type="button" :disabled="loadingEarlier || loading" @click="loadEarlier">{{ loadingEarlier ? t('history.viewer.loading') : t('history.viewer.loadEarlier') }}</button></div>
            <p v-if="loading" class="cv-note" role="status">{{ t('history.viewer.loading') }}</p>
            <div v-if="error" class="cv-note" role="alert"><p>{{ t('history.viewer.loadFailed') }}: {{ error }}</p><button type="button" @click="start > 0 && messages.length ? loadEarlier() : loadInitial()">{{ t('history.viewer.retry') }}</button></div>
            <p v-if="!loading && !error && !messages.length" class="cv-note">{{ t('history.viewer.empty') }}</p>
            <p v-if="omitted || malformed" class="cv-limit" role="status">{{ t('history.viewer.partial', { omitted, malformed }) }}</p>
            <article v-for="turn in turns" :key="turn.id" class="cv-turn" :data-turn="turn.id">
              <section v-if="turn.questions.length" class="cv-question" :aria-label="t('history.viewer.you')">
                <div class="cv-message-meta"><strong>{{ t('history.viewer.you') }}</strong><time>{{ time(turn.questions[0]?.ts) }}</time></div>
                <RecordContent v-for="m in turn.questions" :key="m.ordinal" :text="m.text" :attachments="m.attachments" :workspace="explorer.workspace ?? ''" />
              </section>
              <details v-if="turn.activity.length" class="cv-activity" data-testid="turn-activity" :open="openActivities.has(turn.id)" @toggle="toggle(openActivities, turn.id, $event)">
                <summary><span class="cv-chevron" aria-hidden="true">›</span><span>{{ t('history.viewer.activity') }}</span><span class="cv-activity-count">{{ t('history.viewer.steps', { count: turn.activity.length }) }}</span></summary>
                <div v-if="openActivities.has(turn.id)" class="cv-activity-list">
                  <details v-for="m in turn.activity" :key="m.ordinal" class="cv-step" :open="openSteps.has(m.ordinal)" @toggle="toggle(openSteps, m.ordinal, $event)">
                    <summary><span class="cv-chevron" aria-hidden="true">›</span><strong>{{ m.kind === 'reasoning' ? t('history.viewer.reasoning') : m.kind === 'message' ? t('history.viewer.progress') : m.name || t('history.viewer.toolResult') }}</strong><span class="cv-step-preview">{{ preview(m.text) }}</span></summary>
                    <template v-if="openSteps.has(m.ordinal)">
                      <RecordContent v-if="m.kind === 'reasoning' || m.kind === 'message'" :text="m.text" :attachments="m.attachments" :workspace="explorer.workspace ?? ''" />
                      <pre v-else>{{ m.text }}</pre>
                      <template v-if="m.result != null"><h3>{{ t('history.viewer.toolResult') }}</h3><pre>{{ m.result }}</pre></template>
                      <RecordContent v-if="m.result_attachments?.length" text="" :attachments="m.result_attachments" :workspace="explorer.workspace ?? ''" />
                    </template>
                  </details>
                </div>
              </details>
              <section v-if="turn.answers.length" class="cv-answer" :aria-label="target.agent">
                <div class="cv-message-meta"><strong>{{ target.agent === 'claude' ? 'Claude Code' : 'Codex' }}</strong><time>{{ time(turn.answers[0]?.ts) }}</time></div>
                <RecordContent v-for="m in turn.answers" :key="m.ordinal" :text="m.text" :attachments="m.attachments" :workspace="explorer.workspace ?? ''" />
              </section>
            </article>
          </div>
        </div>
        <footer class="cv-foot"><span>{{ t('history.viewer.count', { start: total ? start + 1 : 0, end: start + messages.length, total }) }}</span><span>{{ t('history.viewer.readonly') }}</span></footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.cv-backdrop { position: fixed; inset: 0; z-index: var(--z-dialog); background: var(--scrim); display: grid; place-items: center; padding: 16px; }
/* Single sheet: viewport - 2×16px frame; reading width <= 920px + 2×32px gutters. */
.cv-panel { width: min(1120px, 100%); height: min(94dvh, 1100px); min-width: 0; display: flex; flex-direction: column; background: var(--surface); border: 1px solid var(--border-2); border-radius: 10px; overflow: hidden; color: var(--text); }
.cv-panel:focus { outline: none; }
.cv-head { display: flex; align-items: center; gap: 16px; padding: 20px 32px; background: var(--surface-2); }
.cv-heading { flex: 1; min-width: 0; }
.cv-context { margin: 0 0 6px; color: var(--text-2); font-size: 12px; display: flex; gap: 16px; flex-wrap: wrap; }
.cv-context span { font-weight: 600; }
.cv-head h1 { font-size: 20px; font-weight: 600; line-height: 1.4; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cv-close, .cv-earlier button, .cv-note button { border: 1px solid var(--border-2); background: var(--surface); border-radius: 6px; color: var(--text); padding: 7px 12px; font: inherit; font-size: 13px; cursor: pointer; }
.cv-close { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.cv-close span { font-size: 20px; line-height: 1; }
.cv-body { flex: 1; min-height: 0; overflow: auto; padding: 28px 32px 48px; scrollbar-gutter: stable; }
.cv-reading-column { width: 100%; max-width: 920px; margin: 0 auto; }
.cv-turn { display: grid; gap: 18px; margin-bottom: 36px; min-width: 0; font-size: 16px; }
.cv-question { background: var(--surface-2); border-radius: 6px; padding: 18px 22px; min-width: 0; }
.cv-answer { padding: 0 22px; min-width: 0; }
.cv-message-meta { display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap; color: var(--text-2); margin-bottom: 12px; font-size: 12px; }
.cv-message-meta strong { color: var(--text); font-size: 13px; font-weight: 600; }
.cv-activity { margin: 0 22px; font-size: 13px; min-width: 0; }
.cv-activity > summary { color: var(--text-2); display: flex; align-items: center; gap: 8px; cursor: pointer; min-height: 32px; list-style: none; }
.cv-chevron { font-size: 20px; display: inline-block; width: 12px; flex-shrink: 0; }
details[open] > summary > .cv-chevron { transform: rotate(90deg); }
summary::-webkit-details-marker { display: none; }
.cv-activity-count { font-size: 12px; margin-left: auto; }
.cv-activity-list { border-left: 1px solid var(--border-2); margin: 6px 0 0 5px; padding: 4px 0 4px 16px; display: grid; gap: 10px; }
.cv-step { min-width: 0; }
.cv-step summary { display: flex; gap: 8px; align-items: center; cursor: pointer; list-style: none; min-height: 32px; }
.cv-step summary strong { flex-shrink: 0; font-size: 13px; font-weight: 500; }
.cv-step-preview { color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-step pre { margin: 8px 0; background: var(--surface-2); border-radius: 4px; padding: 12px; white-space: pre-wrap; overflow-wrap: anywhere; max-height: 480px; overflow: auto; font: 12px/1.65 var(--font-mono); }
.cv-step h3 { font-size: 12px; font-weight: 500; color: var(--text-2); margin: 12px 0 0; }
.cv-earlier, .cv-note { text-align: center; margin-bottom: 24px; color: var(--text-2); font-size: 14px; }
.cv-limit { background: var(--surface-2); color: var(--text-2); padding: 12px 16px; font-size: 13px; border-radius: 4px; }
.cv-foot { padding: 10px 32px; display: flex; gap: 12px; flex-wrap: wrap; justify-content: space-between; color: var(--text-2); background: var(--surface-2); font-size: 12px; }
.cv-panel :is(button, summary, a):focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (max-width: 640px) {
  .cv-backdrop { padding: 0; }
  .cv-panel { height: 100dvh; max-width: 100vw; border-radius: 0; }
  .cv-head { padding: 16px; gap: 8px; }
  .cv-head h1 { font-size: 18px; }
  .cv-body { padding: 20px 16px 32px; }
  .cv-question { padding: 14px; }
  .cv-answer { padding: 0; }
  .cv-activity { margin: 0; }
  .cv-foot { padding: 10px 16px; }
  .cv-close, .cv-earlier button { min-height: 44px; }
}
</style>
