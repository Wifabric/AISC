<script setup lang="ts">
/**
 * 批 2 聊天式 UI (history-worklog.md): read-only conversation viewer.
 *
 * Renders the normalized `aisc.conversation-read/v1` stream as a chat
 * transcript — user/assistant bubbles, reasoning + tool calls collapsed.
 * Strictly read-only (the plan's frozen rule: input only through the
 * container PTY;「继续对话」is the existing resume two-call, not this).
 * Pages backwards from the tail: first load returns the last PAGE entries,
 * 「加载更早的消息」prepends via --before and anchors the viewport.
 */
import { computed, nextTick, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useWorkspaceExplorerStore } from "../../stores/workspaceExplorer";
import type { ConversationReadMessage } from "../../types";

const { t } = useI18n();
const explorer = useWorkspaceExplorerStore();

const PAGE = 100;

const target = computed(() => explorer.conversationViewer);
const messages = ref<ConversationReadMessage[]>([]);
const total = ref(0);
const start = ref(0);
const loading = ref(false);
const loadingEarlier = ref(false);
const error = ref<string | null>(null);
const bodyEl = ref<HTMLDivElement | null>(null);

async function loadInitial(): Promise<void> {
  const cur = target.value;
  if (!cur || !explorer.workspace) return;
  loading.value = true;
  error.value = null;
  try {
    const r = await explorer.readConversationPage(cur.conversationId, cur.agent, PAGE);
    messages.value = r.messages;
    total.value = r.total;
    start.value = r.start;
    await nextTick();
    scrollToBottom();
  } catch (e) {
    error.value = String(e);
  } finally {
    loading.value = false;
  }
}

async function loadEarlier(): Promise<void> {
  const cur = target.value;
  if (!cur || !explorer.workspace || loadingEarlier.value || start.value <= 0) return;
  loadingEarlier.value = true;
  error.value = null;
  try {
    const el = bodyEl.value;
    const beforeHeight = el ? el.scrollHeight : 0;
    const r = await explorer.readConversationPage(
      cur.conversationId, cur.agent, PAGE, start.value,
    );
    messages.value = [...r.messages, ...messages.value];
    start.value = r.start;
    await nextTick();
    // Keep the viewport anchored on the same content the user was reading.
    if (el) el.scrollTop += el.scrollHeight - beforeHeight;
  } catch (e) {
    error.value = String(e);
  } finally {
    loadingEarlier.value = false;
  }
}

function scrollToBottom(): void {
  const el = bodyEl.value;
  if (el) el.scrollTop = el.scrollHeight;
}

function firstLine(text: string): string {
  const line = (text || "").split("\n", 1)[0] ?? "";
  return line.length > 80 ? line.slice(0, 80) + "…" : line;
}

function close(): void {
  explorer.closeConversationViewer();
}

watch(target, (v) => {
  if (v) void loadInitial();
}, { immediate: true });
</script>

<template>
  <div v-if="target" class="cv-backdrop" @click.self="close">
    <div class="cv-panel" role="dialog" :aria-label="t('history.viewer.title')">
      <header class="cv-head">
        <span class="cv-title" :title="target.title">{{ target.title }}</span>
        <span
          class="explorer-badge agent-glyph"
          :class="target.agent === 'claude' ? 'agent-claude' : 'agent-codex'"
          aria-hidden="true"
        >{{ target.agent === "claude" ? "✳" : "◈" }} {{ target.agent }}</span>
        <button class="cv-close" :title="t('common.close')" @click="close">×</button>
      </header>

      <div ref="bodyEl" class="cv-body">
        <div v-if="start > 0" class="cv-earlier">
          <button class="cv-mini" :disabled="loadingEarlier" @click="loadEarlier">
            {{ loadingEarlier ? t("history.viewer.loading") : t("history.viewer.loadEarlier") }}
          </button>
        </div>
        <p v-if="loading && messages.length === 0" class="cv-note">{{ t("history.viewer.loading") }}</p>
        <p v-else-if="error" class="cv-note cv-error">{{ t("history.viewer.loadFailed") }}: {{ error }}</p>
        <p v-else-if="messages.length === 0" class="cv-note">{{ t("history.viewer.empty") }}</p>

        <div
          v-for="m in messages"
          :key="m.ordinal"
          class="cv-msg"
          :class="'cv-role-' + m.role"
        >
          <template v-if="m.kind === 'message'">
            <div class="cv-bubble"><span class="cv-text">{{ m.text }}</span></div>
          </template>

          <details v-else-if="m.kind === 'reasoning'" class="cv-fold cv-fold-reasoning">
            <summary>{{ t("history.viewer.reasoning") }}</summary>
            <div class="cv-fold-body">{{ m.text }}</div>
          </details>

          <details v-else-if="m.kind === 'tool_use'" class="cv-fold cv-fold-tool">
            <summary>
              <span class="cv-tool-name">⚙ {{ m.name }}</span>
              <span class="cv-tool-preview">{{ firstLine(m.text) }}</span>
            </summary>
            <div class="cv-fold-body"><pre class="cv-pre">{{ m.text }}</pre></div>
            <div v-if="m.result" class="cv-tool-result">
              <div class="cv-tool-result-head">{{ t("history.viewer.toolResult") }}</div>
              <pre class="cv-pre">{{ m.result }}</pre>
            </div>
          </details>

          <details v-else class="cv-fold cv-fold-tool">
            <summary>
              <span class="cv-tool-name">{{ t("history.viewer.toolResult") }}</span>
              <span class="cv-tool-preview">{{ firstLine(m.text) }}</span>
            </summary>
            <div class="cv-fold-body"><pre class="cv-pre">{{ m.text }}</pre></div>
          </details>
        </div>
      </div>

      <footer class="cv-foot">
        <span class="cv-count">{{ t("history.viewer.count", { start: start + 1, end: total === 0 ? 0 : start + messages.length, total }) }}</span>
        <span class="cv-readonly">{{ t("history.viewer.readonly") }}</span>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.cv-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-dialog);
  background: var(--scrim);
  display: flex;
  align-items: center;
  justify-content: center;
}
.cv-panel {
  width: min(760px, 92vw);
  height: min(80vh, 860px);
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border-2);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-2);
  overflow: hidden;
}
.cv-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border, color-mix(in srgb, currentColor 12%, transparent));
}
.cv-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  font-size: var(--font-sm);
}
.cv-close {
  border: none;
  background: transparent;
  color: var(--text-2);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}
.cv-close:hover { background: color-mix(in srgb, currentColor 10%, transparent); }

.cv-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.cv-earlier { display: flex; justify-content: center; padding-bottom: var(--space-1); }
.cv-mini {
  border: 1px solid var(--border, color-mix(in srgb, currentColor 18%, transparent));
  background: transparent;
  color: var(--text-2);
  border-radius: 999px;
  font-size: var(--font-xs);
  padding: 3px 12px;
  cursor: pointer;
}
.cv-mini:hover:not(:disabled) { background: color-mix(in srgb, currentColor 8%, transparent); }
.cv-mini:disabled { opacity: 0.55; cursor: default; }
.cv-note { color: var(--text-muted); font-size: var(--font-xs); text-align: center; }
.cv-error { color: var(--status-err, var(--warn)); }

.cv-msg { display: flex; }
.cv-role-user { justify-content: flex-end; }
.cv-role-assistant, .cv-role-tool { justify-content: flex-start; }
.cv-bubble {
  max-width: 78%;
  padding: 7px 11px;
  border-radius: 12px;
  font-size: var(--font-sm);
  line-height: 1.55;
}
.cv-role-user .cv-bubble {
  background: var(--accent-soft, color-mix(in srgb, var(--accent) 16%, transparent));
  border-bottom-right-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}
.cv-role-assistant .cv-bubble {
  background: color-mix(in srgb, currentColor 7%, transparent);
  border-bottom-left-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}

.cv-fold {
  max-width: 86%;
  border: 1px solid var(--border, color-mix(in srgb, currentColor 12%, transparent));
  border-radius: 10px;
  font-size: var(--font-xs);
  background: color-mix(in srgb, currentColor 4%, transparent);
}
.cv-fold summary {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px 10px;
  cursor: pointer;
  color: var(--text-2);
  list-style: none;
  min-width: 0;
}
.cv-fold summary::-webkit-details-marker { display: none; }
.cv-fold-reasoning summary { color: var(--text-muted); font-style: italic; }
.cv-tool-name { flex-shrink: 0; font-family: var(--font-mono); }
.cv-tool-preview {
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cv-fold-body { padding: 4px 10px 8px; white-space: pre-wrap; word-break: break-word; color: var(--text-2); }
.cv-pre {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--font-xs);
  white-space: pre-wrap;
  word-break: break-word;
}
.cv-tool-result {
  margin: 0 10px 8px;
  padding: 6px 8px;
  border-radius: 8px;
  background: color-mix(in srgb, currentColor 5%, transparent);
}
.cv-tool-result-head { color: var(--text-muted); margin-bottom: 2px; }

.cv-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-1) var(--space-3);
  border-top: 1px solid var(--border, color-mix(in srgb, currentColor 12%, transparent));
  color: var(--text-muted);
  font-size: var(--font-xs);
}
</style>
