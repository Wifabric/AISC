<script setup lang="ts">
/**
 * b8 R4/R2/R3: the provider conversation list reused by Work Records.
 * It preserves search/rename/delete/resume/read-only capabilities while
 * replacing the former standalone History tab with a compact tree.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { confirm } from "@tauri-apps/plugin-dialog";
import { errorCodeOf, useWorkspaceExplorerStore } from "../../stores/workspaceExplorer";
import { buildSearchMatcher } from "../../lib/search";
import { buildConversationTreeRows, type ConversationTreeRow } from "./conversationTree";
import type { ConversationSummary } from "../../types";

const { t } = useI18n();
const explorer = useWorkspaceExplorerStore();

type ConversationMenuTarget = {
  conversationId: string;
  agent: "claude" | "codex";
  title: string;
};

interface MenuAction {
  id: string;
  label: string;
  disabled?: boolean;
  reason?: string;
  run: () => void;
}

const menu = ref<{ target: ConversationMenuTarget; x: number; y: number } | null>(null);
const panelSearch = ref("");
const expanded = ref(new Set<string>());
const renamingConvId = ref<string | null>(null);
const convRenameValue = ref("");
const convRenameInputEl = ref<HTMLInputElement | null>(null);
const status = ref<{ key: string; tone: "ok" | "warn" } | null>(null);
let statusTimer: number | null = null;

function flash(key: string, tone: "ok" | "warn" = "ok"): void {
  status.value = { key, tone };
  if (statusTimer !== null) window.clearTimeout(statusTimer);
  statusTimer = window.setTimeout(() => { status.value = null; }, 2200);
}

function errorI18nKey(error: unknown): string {
  switch (errorCodeOf(error)) {
    case "WB_ERR_WORKSPACE_CONFLICT": return "explorer.error.conflict";
    case "WB_ERR_WORKSPACE_INVALID": return "explorer.error.invalid";
    case "WB_ERR_WORKSPACE_NOT_FOUND": return "explorer.error.notFound";
    case "WB_ERR_WORKSPACE_IO": return "explorer.error.io";
    default: return "explorer.error.default";
  }
}

const searchMatcher = computed(() => buildSearchMatcher(panelSearch.value));
const searchActive = computed(() => panelSearch.value.trim().length > 0);
type ConversationDisplayRow =
  | { kind: "header"; key: string; agent: "claude" | "codex"; label: string; count: number }
  | { kind: "conversation"; key: string; row: ConversationTreeRow; visible: boolean };

/** Group by agent only when both engines have history; within each group,
 * parent/child rows come from the shared pure tree builder. */
const conversationRows = computed<ConversationDisplayRow[]>(() => {
  // Tree search receives the full list so a child hit can retain ancestors.
  const list = explorer.conversations;
  const matcher = searchMatcher.value;
  const rowsFor = (items: ConversationSummary[]): ConversationTreeRow[] =>
    buildConversationTreeRows(
      items,
      matcher === null ? undefined : (item) => matcher(item.title.toLowerCase()) > 0,
    );
  const claude = list.filter((item) => item.agent === "claude");
  const codex = list.filter((item) => item.agent === "codex");
  const groups = claude.length && codex.length
    ? [
        { agent: "claude" as const, label: t("explorer.conversations.group.claude"), items: claude },
        { agent: "codex" as const, label: t("explorer.conversations.group.codex"), items: codex },
      ].sort((a, b) => recent(b.items) - recent(a.items))
    : [{ agent: list[0]?.agent ?? "codex", label: "", items: list }];
  const out: ConversationDisplayRow[] = [];
  for (const group of groups) {
    if (claude.length && codex.length) {
      out.push({
        kind: "header", key: `header:${group.agent}`, agent: group.agent,
        label: group.label, count: group.items.length,
      });
    }
    for (const row of rowsFor(group.items)) {
      out.push({
        kind: "conversation",
        key: `${group.agent}:${row.conversation.conversation_id}`,
        row,
        visible: searchActive.value || !parentOf(row) || expanded.value.has(parentOf(row)!),
      });
    }
  }
  return out;
});

function recent(items: ConversationSummary[]): number {
  return Math.max(0, ...items.map((item) => Date.parse(item.last_at ?? "") || 0));
}

function parentOf(row: ConversationTreeRow): string | null {
  return row.conversation.parent_thread_id?.toLowerCase() ?? null;
}

function toggleTree(row: ConversationTreeRow): void {
  const parentKey = row.conversation.conversation_id.toLowerCase();
  const next = new Set(expanded.value);
  if (!next.delete(parentKey)) next.add(parentKey);
  expanded.value = next;
}

async function resume(item: ConversationSummary, fork = false): Promise<void> {
  await explorer.resumeConversation(item, fork);
}

function beginRename(item: ConversationSummary): void {
  menu.value = null;
  renamingConvId.value = item.conversation_id;
  convRenameValue.value = item.title;
  void nextTick(() => convRenameInputEl.value?.focus());
}

function cancelRename(): void {
  renamingConvId.value = null;
  convRenameValue.value = "";
}

async function commitRename(item: ConversationSummary): Promise<void> {
  const title = convRenameValue.value.trim();
  const id = renamingConvId.value;
  cancelRename();
  if (!title || id !== item.conversation_id) return;
  try {
    await explorer.renameConversation(item, title);
    flash("explorer.conversations.renamed");
  } catch (error) {
    flash(errorI18nKey(error), "warn");
  }
}

async function deleteConversation(target: ConversationMenuTarget): Promise<void> {
  menu.value = null;
  const ok = await confirm(
    t("explorer.conversations.deleteConfirm", { title: target.title }),
    { kind: "warning", title: t("explorer.conversations.deleteTitle") },
  );
  if (!ok) return;
  try {
    await explorer.deleteConversation({
      conversation_id: target.conversationId,
      agent: target.agent,
    } as ConversationSummary);
    flash("explorer.conversations.deleted");
  } catch (error) {
    flash(errorI18nKey(error), "warn");
  }
}

function menuItemsFor(target: ConversationMenuTarget): MenuAction[] {
  return [
    {
      id: "view",
      label: t("history.viewMenu"),
      run: () => {
        menu.value = null;
        explorer.openConversationViewer(target.agent, target.conversationId, target.title);
      },
    },
    {
      id: "resume",
      label: t("workRecords.resume"),
      run: () => {
        menu.value = null;
        const item = explorer.conversations.find((c) => c.conversation_id === target.conversationId);
        if (item) void resume(item);
      },
    },
    {
      id: "rename",
      label: t("explorer.menu.rename"),
      run: () => beginRename({ conversation_id: target.conversationId, agent: target.agent, title: target.title } as ConversationSummary),
    },
    {
      id: "fork",
      label: t("explorer.conversations.menuFork"),
      disabled: target.agent === "codex",
      reason: target.agent === "codex" ? t("explorer.conversations.reason.codexNoFork") : undefined,
      run: () => {
        menu.value = null;
        const item = explorer.conversations.find((c) => c.conversation_id === target.conversationId);
        if (item?.agent === "claude") void resume(item, true);
      },
    },
    { id: "delete", label: t("explorer.conversations.menuDelete"), run: () => void deleteConversation(target) },
  ];
}

const menuItems = computed(() => menu.value ? menuItemsFor(menu.value.target) : []);

function appZoom(): number {
  const app = document.querySelector<HTMLElement>(".app");
  if (!app) return 1;
  const width = app.offsetWidth || 0;
  return width > 0 ? app.getBoundingClientRect().width / width : 1;
}

function openMenu(item: ConversationSummary, clientX: number, clientY: number): void {
  const items = menuItemsFor({ conversationId: item.conversation_id, agent: item.agent, title: item.title });
  const zoom = appZoom();
  menu.value = {
    target: { conversationId: item.conversation_id, agent: item.agent, title: item.title },
    x: Math.max(4, Math.min(clientX / zoom, window.innerWidth / zoom - 180)),
    y: Math.max(4, Math.min(clientY / zoom, window.innerHeight / zoom - (12 + items.length * 26))),
  };
}

function reasonText(reason?: string): string {
  if (reason === "file_too_large") return t("explorer.conversations.reason.fileTooLarge");
  if (reason === "malformed") return t("explorer.conversations.reason.malformed");
  return t("explorer.conversations.reason.unknown");
}

onMounted(() => { if (explorer.workspace) void explorer.loadConversations(true); });
onBeforeUnmount(() => { if (statusTimer !== null) window.clearTimeout(statusTimer); });
</script>

<template>
  <div class="explorer-body conversations-panel">
    <div class="conversation-search">
      <input
        v-model="panelSearch"
        type="search"
        data-testid="conversations-search"
        class="explorer-search-input"
        :placeholder="t('explorer.searchConversations')"
        :aria-label="t('explorer.searchConversations')"
      />
    </div>

    <p v-if="explorer.conversationsLoading" class="explorer-empty">{{ t("explorer.loading") }}</p>
    <p v-else-if="explorer.conversationsError" class="explorer-empty">{{ t("explorer.conversations.loadFailed") }}</p>
    <p v-else-if="!conversationRows.length" class="explorer-empty">{{ t("explorer.empty.conversations") }}</p>
    <template v-else>
      <template v-for="entry in conversationRows" :key="entry.key">
        <p
          v-if="entry.kind === 'header'"
          class="conversation-group-label"
          :data-agent="entry.agent"
        >{{ entry.label }} <span class="explorer-label">{{ entry.count }}</span></p>
        <div
          v-else-if="entry.kind === 'conversation' && entry.visible"
          class="explorer-row artifact-row conversation-row"
          role="button"
          :style="{ paddingLeft: `${6 + entry.row.depth * 14}px` }"
          :title="t('explorer.conversations.resumeTooltip')"
          @click="resume(entry.row.conversation)"
          @contextmenu.prevent.stop="openMenu(entry.row.conversation, $event.clientX, $event.clientY)"
        >
          <button
            v-if="entry.row.childCount"
            class="conversation-twisty"
            type="button"
            :aria-expanded="expanded.has(entry.row.conversation.conversation_id.toLowerCase())"
            :aria-label="t('workRecords.tree.toggle')"
            :data-testid="`conversation-toggle-${entry.row.conversation.conversation_id}`"
            @click.stop="toggleTree(entry.row)"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
              <path :d="expanded.has(entry.row.conversation.conversation_id.toLowerCase()) ? 'M3 4.5 6 8l3-3.5' : 'M4.5 2.5 8 6l-3.5 3.5'" />
            </svg>
            <span class="conversation-child-count">{{ entry.row.childCount }}</span>
          </button>
          <span v-else class="conversation-twisty spacer" aria-hidden="true" />

          <span
            v-if="renamingConvId === entry.row.conversation.conversation_id"
            class="name-input-row conversation-rename"
          >
            <input
              ref="convRenameInputEl"
              v-model="convRenameValue"
              type="text"
              @click.stop
              @keydown.enter.prevent="commitRename(entry.row.conversation)"
              @keydown.esc.prevent="cancelRename"
              @blur="cancelRename"
            />
          </span>
          <span v-else class="explorer-name conversation-title" :title="entry.row.conversation.title">
            {{ entry.row.conversation.title }}
          </span>
          <span v-if="entry.row.conversation.message_count !== null" class="explorer-label">
            {{ t("explorer.conversations.msgCount", { n: entry.row.conversation.message_count }) }}
          </span>
          <button
            class="conversation-icon"
            type="button"
            :title="t('history.viewTooltip')"
            :aria-label="t('history.viewMenu')"
            @click.stop="explorer.openConversationViewer(entry.row.conversation.agent, entry.row.conversation.conversation_id, entry.row.conversation.title)"
          >👁</button>
          <span
            class="explorer-badge agent-glyph conversation-pill"
            :class="entry.row.conversation.agent === 'claude' ? 'agent-claude' : 'agent-codex'"
            :title="entry.row.conversation.agent"
            aria-hidden="true"
          ><span class="glyph">{{ entry.row.conversation.agent === "claude" ? "✳" : "◈" }}</span>{{ entry.row.conversation.agent }}</span>
          <div
            v-if="explorer.resumeErrors[entry.row.conversation.conversation_id]"
            class="conversation-resume-error"
          >{{ explorer.resumeErrors[entry.row.conversation.conversation_id] }}</div>
          <div v-else-if="!entry.row.conversation.resumable" class="conversation-resume-error">
            {{ reasonText(entry.row.conversation.unavailable_reason) }}
          </div>
        </div>
      </template>
    </template>

    <Transition name="pop">
      <div
        v-if="menu"
        class="explorer-menu"
        role="menu"
        :style="{ left: `${menu.x}px`, top: `${menu.y}px` }"
        @mousedown.stop
        @contextmenu.prevent
      >
        <button
          v-for="item in menuItems"
          :key="item.id"
          role="menuitem"
          :data-action="item.id"
          :disabled="item.disabled"
          :aria-disabled="item.disabled"
          :title="item.disabled ? item.reason : ''"
          @click="item.run()"
        >{{ item.label }}</button>
      </div>
    </Transition>
    <div v-if="menu" class="explorer-menu-backdrop" @mousedown="menu = null" @contextmenu.prevent="menu = null" />

    <Transition name="pop">
      <div v-if="status" class="explorer-status" :class="{ warn: status.tone === 'warn' }">
        {{ t(status.key) }}
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.conversation-search { padding: var(--space-1) 0; border-bottom: var(--border-w) solid var(--border); }
.conversation-row { cursor: pointer; flex-wrap: wrap; }
.conversation-group-label { display:flex; align-items:baseline; gap:var(--space-1); margin:var(--space-2) 2px 2px; font-size:var(--font-xs); font-weight:700; letter-spacing:.4px; text-transform:uppercase; color:var(--text-muted); }
.conversation-pill { display:inline-flex; align-items:center; gap:var(--space-1); height:20px; padding:0 var(--space-2); font-size:var(--font-xs); line-height:1; border-radius:var(--radius-pill); white-space:nowrap; }
.agent-glyph .glyph { line-height:1; font-size:var(--font-sm); }
.conversation-twisty { display:inline-flex; align-items:center; gap:3px; flex:0 0 auto; width:auto; height:20px; padding:0 3px; background:none; border:none; color:var(--text-muted); border-radius:var(--radius-sm); cursor:pointer; }
.conversation-twisty:hover { color:var(--text); background:var(--surface-hover); }
.conversation-twisty.spacer { width:14px; padding:0; }
.conversation-child-count { font-size:10px; }
.conversation-icon { width:24px; height:20px; border:none; background:none; color:var(--text-2); cursor:pointer; border-radius:var(--radius-sm); }
.conversation-icon:hover { background:var(--surface-hover); }
.conversation-title { font-weight:500; flex:1 1 0; min-width:0; overflow:hidden; text-overflow:ellipsis; }
.conversation-resume-error { flex-basis:100%; font-size:var(--font-xs); color:var(--warn); padding-left:var(--space-2); }
.conversation-rename { flex:1 1 120px; min-width:0; }
.conversation-rename input { width:100%; font-size:var(--font-sm); }
.explorer-menu-backdrop { position:fixed; inset:0; z-index:calc(var(--z-overlay) - 1); }
.explorer-menu { position:fixed; z-index:var(--z-overlay); background:var(--surface-2); border:var(--border-w) solid var(--border-2); border-radius:var(--radius-md); box-shadow:var(--shadow-menu); padding:var(--space-1); display:flex; flex-direction:column; min-width:140px; }
.explorer-menu button { background:none; border:none; border-radius:var(--radius-sm); color:var(--text-2); text-align:left; min-height:24px; padding:0 var(--space-2); cursor:pointer; font-size:var(--font-sm); }
.explorer-menu button:hover:not(:disabled) { background:var(--surface-active); color:var(--text); }
.explorer-menu button:disabled { color:var(--text-muted); cursor:default; }
.explorer-status { position:absolute; right:var(--space-2); bottom:var(--space-2); z-index:var(--z-overlay); padding:2px var(--space-2); border-radius:var(--radius-sm); background:var(--surface-2); border:var(--border-w) solid var(--border-2); box-shadow:var(--shadow-menu); color:var(--text-muted); font-size:var(--font-xs); }
.explorer-status.warn { color:var(--warn); }
</style>
