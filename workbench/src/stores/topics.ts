/** Topic files and explicit Agent handoff; the selected workspace owns all data. */
import { computed, ref } from "vue";
import { defineStore } from "pinia";
import * as ipc from "../lib/ipc";
import type { TopicAction, TopicCheck, TopicDetail, TopicRequest, TopicSummary } from "../lib/ipc";
import { useRuntimeStore } from "./runtime";
import { listLeaves } from "./paneTree";
import { i18n } from "../i18n";

function describeError(value: unknown): string {
  const error = value as { message?: string; technical_detail?: string };
  const message = error?.message ?? String(value);
  return error?.technical_detail && error.technical_detail !== message
    ? `${message}: ${error.technical_detail}` : message;
}

export const useTopicsStore = defineStore("topics", () => {
  const runtime = useRuntimeStore();
  const workspace = ref("");
  const instanceId = ref("");
  const topics = ref<TopicSummary[]>([]);
  const detail = ref<TopicDetail | null>(null);
  const request = ref<TopicRequest | null>(null);
  const checkResult = ref<TopicCheck | null>(null);
  const warnings = ref<string[]>([]);
  const error = ref<string | null>(null);
  const loading = ref(false);
  const busy = ref(false);
  const inserting = ref(false);
  const inserted = ref(false);
  const activeTopic = ref<TopicSummary | null>(null);
  const conversationStatus = ref<Array<{ topic_id: string; session_id: string; agent: string; captured: number; state: string; guide_pending: boolean }>>([]);
  const syncError = ref<string | null>(null);
  const syncing = ref(false);
  let syncingEpoch = -1;
  let modeGeneration = 0;
  let epoch = 0;
  let selection = 0;
  let listing = 0;

  // An instance id also distinguishes identical paths on different machines.
  const activeContext = () => !!workspace.value && runtime.workspace === workspace.value
    && runtime.id === instanceId.value;
  const current = (token: number) => token === epoch && activeContext();
  const sessions = computed(() => {
    if (!activeContext()) return [];
    return runtime.tabs.flatMap(tab => listLeaves(tab.tree).flatMap(leaf => {
      const pane = tab.panes[leaf.paneId];
      if ((leaf.sessionType !== "claude" && leaf.sessionType !== "codex")
        || !pane || pane.sessionState !== "running" || !pane.sessionId) return [];
      return [{ sessionId: pane.sessionId, tabId: tab.tabId, paneId: leaf.paneId,
        agent: leaf.sessionType, label: `${tab.title} · ${pane.sessionId.slice(0, 8)}` }];
    }));
  });

  function setContext(path: string, id: string): void {
    if (workspace.value === path && instanceId.value === id) return;
    epoch++; selection++; listing++;
    workspace.value = path;
    instanceId.value = id;
    topics.value = []; detail.value = null; request.value = null;
    checkResult.value = null; warnings.value = []; error.value = null;
    loading.value = false; busy.value = false; inserting.value = false; inserted.value = false;
    activeTopic.value = null; conversationStatus.value = []; syncError.value = null; syncing.value = false;
  }

  async function load(): Promise<void> {
    if (!activeContext()) return;
    const token = epoch, turn = ++listing;
    loading.value = true;
    error.value = null;
    try {
      const result = await ipc.topicCall<{ topics: TopicSummary[]; warnings: string[] }>({
        workspace: workspace.value, operation: "list",
      });
      if (!current(token) || turn !== listing) return;
      topics.value = result.topics;
      warnings.value = result.warnings ?? [];
    } catch (e) {
      if (current(token) && turn === listing) error.value = describeError(e);
    } finally {
      if (current(token) && turn === listing) loading.value = false;
    }
  }

  async function select(id: string): Promise<void> {
    if (!activeContext() || busy.value || inserting.value) return;
    const token = epoch, turn = ++selection;
    detail.value = null; request.value = null; checkResult.value = null;
    inserted.value = false; error.value = null;
    try {
      const result = await ipc.topicCall<{ topic: TopicDetail }>({
        workspace: workspace.value, operation: "show", id,
      });
      if (!current(token) || turn !== selection) return;
      detail.value = result.topic;
      request.value = result.topic.requests?.[0] ?? null;
    } catch (e) {
      if (current(token) && turn === selection) error.value = describeError(e);
    }
  }

  async function refresh(): Promise<void> {
    const id = detail.value?.id;
    const token = epoch, turn = selection;
    await load();
    if (id && current(token) && turn === selection) await select(id);
  }

  async function create(title: string, text: string, sources: string[]): Promise<boolean> {
    if (!activeContext() || busy.value || inserting.value || !title.trim() || !text.trim()) return false;
    const token = epoch;
    ++selection;
    ++listing;
    loading.value = false;
    busy.value = true; error.value = null;
    try {
      const result = await ipc.topicCall<{ topic: TopicDetail }>({
        workspace: workspace.value, operation: "create", title: title.trim(), text, sources,
      });
      if (!current(token)) return false;
      // Invalidate even a refresh started while create was in flight: its
      // directory snapshot may predate this newly persisted topic.
      ++listing;
      loading.value = false;
      detail.value = result.topic;
      request.value = result.topic.requests?.[0] ?? null;
      checkResult.value = null; inserted.value = false;
      topics.value = [result.topic, ...topics.value.filter(item => item.id !== result.topic.id)];
      try {
        ++modeGeneration;
        const mode = await ipc.topicCall<{ active: TopicSummary }>({ workspace: workspace.value, operation: "activate", id: result.topic.id });
        if (current(token)) activeTopic.value = mode.active ?? null;
      } catch (e) { if (current(token)) error.value = describeError(e); }
      return true;
    } catch (e) {
      if (current(token)) error.value = describeError(e);
      return false;
    } finally {
      if (current(token)) busy.value = false;
    }
  }

  async function prepare(action: TopicAction, text: string): Promise<boolean> {
    if (!activeContext() || !detail.value || busy.value || inserting.value) return false;
    if (action === "feedback" && !text.trim()) return false;
    const token = epoch, id = detail.value.id;
    busy.value = true; error.value = null;
    try {
      const result = await ipc.topicCall<{ request: TopicRequest }>({
        workspace: workspace.value, operation: "prepare", id, action, text,
      });
      if (!current(token) || detail.value?.id !== id) return false;
      request.value = result.request; inserted.value = false;
      detail.value.requests = [result.request, ...detail.value.requests.filter(r => r.id !== result.request.id)];
      return true;
    } catch (e) {
      if (current(token)) error.value = describeError(e);
      return false;
    } finally {
      if (current(token)) busy.value = false;
    }
  }

  function chooseRequest(id: string): void {
    if (busy.value || inserting.value) return;
    request.value = detail.value?.requests.find(item => item.id === id) ?? null;
    inserted.value = false;
  }

  function openAgent(agent: "claude" | "codex"): void {
    if (!activeContext()) return;
    error.value = null;
    if (!runtime.createTab(agent)) error.value = i18n.global.t("topics.sessionLimit");
  }

  async function enableConversation(): Promise<boolean> {
    if (!activeContext() || !detail.value || busy.value) return false;
    const token = epoch, id = detail.value.id;
    busy.value = true; error.value = null;
    ++modeGeneration;
    try {
      const result = await ipc.topicCall<{ active: TopicSummary }>({ workspace: workspace.value, operation: "activate", id });
      if (!current(token)) return false;
      activeTopic.value = result.active;
      return true;
    } catch (e) { if (current(token)) error.value = describeError(e); return false; }
    finally { if (current(token)) busy.value = false; }
  }

  async function startConversation(agent: "claude" | "codex"): Promise<void> {
    const token = epoch;
    if (await enableConversation() && current(token)) openAgent(agent);
  }

  async function disableConversation(): Promise<void> {
    if (!activeContext() || busy.value) return;
    const token = epoch;
    busy.value = true;
    ++modeGeneration;
    try {
      await ipc.topicCall({ workspace: workspace.value, operation: "deactivate" });
      if (current(token)) activeTopic.value = null;
    } catch (e) { if (current(token)) syncError.value = describeError(e); }
    finally { if (current(token)) busy.value = false; }
  }

  async function syncConversations(): Promise<void> {
    if (!activeContext() || busy.value || syncingEpoch === epoch) return;
    const token = epoch, chosen = selection, mode = modeGeneration;
    syncingEpoch = token; syncing.value = true;
    try {
      const result = await ipc.topicCall<{ active: TopicSummary | null; sessions: typeof conversationStatus.value; warnings: string[] }>({
        workspace: workspace.value, operation: "sync",
      });
      if (!current(token)) return;
      if (mode === modeGeneration) activeTopic.value = result.active;
      conversationStatus.value = result.sessions ?? [];
      syncError.value = result.warnings?.length ? result.warnings.join("\n") : null;
      const id = detail.value?.id;
      if (id && !busy.value && chosen === selection) {
        const latest = await ipc.topicCall<{ topic: TopicDetail }>({ workspace: workspace.value, operation: "show", id });
        if (current(token) && chosen === selection && detail.value?.id === id && !busy.value) detail.value = latest.topic;
      }
    } catch (e) { if (current(token)) syncError.value = describeError(e); }
    finally { if (syncingEpoch === token) syncingEpoch = -1; if (current(token)) syncing.value = false; }
  }

  async function insert(sessionId: string): Promise<boolean> {
    if (!activeContext() || !request.value || busy.value || inserting.value || inserted.value) return false;
    const session = sessions.value.find(item => item.sessionId === sessionId);
    if (!session) {
      error.value = i18n.global.t("topics.noAgentSession");
      return false;
    }
    const prompt = request.value.prompt;
    // The backend emits a short single-line file-reading instruction. Never
    // allow terminal controls or a forged closing bracketed-paste sequence.
    if (!prompt.trim() || prompt.length > 8192 || /[\x00-\x1f\x7f-\x9f]/.test(prompt)) {
      error.value = i18n.global.t("topics.invalidPrompt");
      return false;
    }
    const token = epoch;
    inserting.value = true; error.value = null;
    try {
      // No Enter: the user waits for the Agent input, inspects and submits.
      await ipc.writeSession(session.sessionId,
        Array.from(new TextEncoder().encode(`\x1b[200~${prompt}\x1b[201~`)));
      if (!current(token)) return false;
      inserted.value = true;
      runtime.activateTab(session.tabId);
      runtime.setActivePane(session.tabId, session.paneId);
      return true;
    } catch (e) {
      if (current(token)) error.value = describeError(e);
      return false;
    } finally {
      if (current(token)) inserting.value = false;
    }
  }

  async function check(): Promise<void> {
    if (!activeContext() || !detail.value || busy.value) return;
    const token = epoch, id = detail.value.id;
    busy.value = true; error.value = null;
    try {
      const result = await ipc.topicCall<TopicCheck>({ workspace: workspace.value, operation: "check", id });
      if (current(token) && detail.value?.id === id) checkResult.value = result;
    } catch (e) {
      if (current(token)) error.value = describeError(e);
    } finally {
      if (current(token)) busy.value = false;
    }
  }

  async function openFile(path: string): Promise<void> {
    if (!activeContext() || !detail.value || !detail.value.files.includes(path)) return;
    const token = epoch;
    try { await ipc.workspaceOpen(workspace.value, path); }
    catch (e) { if (current(token)) error.value = describeError(e); }
  }

  async function accessIterationLog(reveal = false): Promise<void> {
    if (!activeContext() || !detail.value?.iteration_log) return;
    const token = epoch;
    try {
      await (reveal ? ipc.workspaceReveal : ipc.workspaceOpen)(workspace.value, `${detail.value.relative_path}/ITERATION_LOG.md`);
    } catch (e) { if (current(token)) error.value = describeError(e); }
  }

  return { workspace, topics, detail, request, checkResult, warnings, error,
    loading, busy, inserting, inserted, sessions, activeTopic, conversationStatus, syncError, syncing,
    enableConversation, startConversation, disableConversation, syncConversations,
    setContext, load, refresh, select, create, prepare, chooseRequest, openAgent, insert, check, openFile, accessIterationLog };
});
