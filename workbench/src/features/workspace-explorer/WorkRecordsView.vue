<script setup lang="ts">
/**
 * v2.1.15 b11: ordered Work Records with provider-child trees, drag/drop,
 * context menus, and inline rename. Collection order is persisted in the CLI.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useWorkRecordsStore } from "../../stores/workRecords";
import { useWorkspaceExplorerStore } from "../../stores/workspaceExplorer";
import { useRuntimeStore } from "../../stores/runtime";
import { buildConversationTreeRows, type ConversationTreeRow } from "./conversationTree";
import type { ConversationSummary } from "../../types";
import type { WorkRecordMember, WorkRecordCollection } from "../../types";

const props = defineProps<{ workspace: string | null }>();
const { t } = useI18n();
const records = useWorkRecordsStore();
const explorer = useWorkspaceExplorerStore();
const runtime = useRuntimeStore();
const showArchived = ref(false);
const newTitle = ref("");
const renamingCollectionId = ref<string | null>(null);
const renamingConversationKey = ref<string | null>(null);
const renameValue = ref("");
const expandedMembers = ref(new Set<string>());
const expandedUnfiled = ref(new Set<string>());
const collapsedCollections = ref(new Set<string>());
const unfiledExpanded = ref(true);
const pendingDelete = ref<{
  kind: "collection" | "conversation";
  message: string;
  collectionId?: string;
  conversation?: ConversationSummary;
} | null>(null);
const contextMenu = ref<{
  x: number;
  y: number;
  collectionId: string | null;
  memberKey: string;
  agent: "claude" | "codex";
  conversationId: string;
} | null>(null);

const visibleCollections = computed(() =>
  showArchived.value ? records.collections : records.collections.filter((item) => item.status === "active"),
);
const conversationBy = computed(() => {
  const out = new Map<string, ConversationSummary>();
  for (const item of explorer.conversations) {
    out.set(item.agent + ":" + item.conversation_id.toLowerCase(), item);
  }
  return out;
});

function memberConversation(memberKey: string): ConversationSummary | null {
  return conversationBy.value.get(memberKey) ?? null;
}

async function createCollection() {
  const title = newTitle.value.trim();
  if (!title) return;
  const created = await records.create(title);
  if (created) {
    // b16: a new record is a container header first; the user expands it on
    // demand. Existing records keep their current expansion state.
    collapsedCollections.value = new Set([...collapsedCollections.value, created.id]);
    newTitle.value = "";
  }
}

function beginCollectionRename(collection: WorkRecordCollection) {
  renamingCollectionId.value = collection.id;
  renameValue.value = collection.title;
  void nextTick(() => {
    const input = document.querySelector<HTMLInputElement>("[data-testid='collection-rename-input']");
    input?.focus();
    input?.select();
  });
}

function toggleCollection(id: string) {
  const next = new Set(collapsedCollections.value);
  if (!next.delete(id)) next.add(id);
  collapsedCollections.value = next;
}

async function commitCollectionRename(id: string) {
  const title = renameValue.value.trim();
  const current = records.byId(id);
  renamingCollectionId.value = null;
  if (!title || !current || title === current.title) return;
  await records.rename(id, title);
  await records.reload();
}

function requestCollectionDelete(id: string, title: string) {
  const memberCount = records.byId(id)?.members.length ?? 0;
  pendingDelete.value = {
    kind: "collection",
    collectionId: id,
    message: t("workRecords.deleteConfirm", { title, count: memberCount }),
  };
}

async function performCollectionDelete(id: string) {
  await explorer.loadConversations(true);
  await runtime.resolvePendingConversationAssociations(explorer.conversations);
  await runtime.closeLiveConversationSessions(
    (records.byId(id)?.members ?? []).map((member) => member.conversation_id),
  );
  await records.delete(id);
  await explorer.loadConversations(true);
}


async function refreshWorkRecords() {
  await Promise.all([records.reload(), explorer.loadConversations(true)]);
  await runtime.resolvePendingConversationAssociations(explorer.conversations);
}

async function removeMember(id: string, agent: "claude" | "codex", conversationId: string) {
  const removed = await records.removeMember(id, agent, conversationId);
  if (removed) await records.reload();
}

async function resumeMember(memberKey: string) {
  const item = memberConversation(memberKey);
  if (item?.resumable) await explorer.resumeConversation(item);
}

function beginConversationRename(memberKey: string) {
  const item = memberConversation(memberKey);
  if (!item) return;
  renamingConversationKey.value = memberKey;
  renameValue.value = item.title;
  void nextTick(() => {
    const input = document.querySelector<HTMLInputElement>("[data-testid='conversation-rename-input']");
    input?.focus();
    input?.select();
  });
}

async function commitConversationRename(item: ConversationSummary) {
  const title = renameValue.value.trim();
  renamingConversationKey.value = null;
  if (!title || title === item.title) return;
  await explorer.renameConversation(item, title);
  await records.reload();
}

function requestConversationDelete(item: ConversationSummary, collectionId?: string | null) {
  pendingDelete.value = {
    kind: "conversation",
    collectionId: collectionId ?? undefined,
    conversation: item,
    message: t("explorer.conversations.deleteConfirm", { title: item.title }),
  };
}

async function performConversationDelete(item: ConversationSummary, collectionId?: string) {
  await explorer.deleteConversation(item);
  if (collectionId) {
    await records.removeMember(collectionId, item.agent, item.conversation_id);
  }
  await records.reload();
}

async function confirmQuietDelete() {
  const pending = pendingDelete.value;
  pendingDelete.value = null;
  if (!pending) return;
  if (pending.kind === "collection" && pending.collectionId) {
    await performCollectionDelete(pending.collectionId);
  } else if (pending.conversation) {
    await performConversationDelete(pending.conversation, pending.collectionId);
  }
}


interface MemberTreeRow {
  member: WorkRecordMember;
  depth: number;
  childCount: number;
  parentKey: string | null;
}

function memberTree(collection: WorkRecordCollection): MemberTreeRow[] {
  const byId = new Map(collection.members.map((member) => [member.conversation_id.toLowerCase(), member]));
  const children = new Map<string, WorkRecordMember[]>();
  for (const member of collection.members) {
    const conversation = conversationBy.value.get(member.agent + ":" + member.conversation_id.toLowerCase());
    const parentId = conversation?.parent_thread_id?.toLowerCase();
    const parentMember = parentId ? byId.get(parentId) : undefined;
    const key = parentMember ? parentMember.conversation_id.toLowerCase() : "";
    const bucket = children.get(key) ?? [];
    bucket.push(member);
    children.set(key, bucket);
  }
  const rows: MemberTreeRow[] = [];
  const visit = (parentKey: string, depth: number, stack: Set<string>): void => {
    for (const member of children.get(parentKey) ?? []) {
      const key = member.conversation_id.toLowerCase();
      if (stack.has(key)) continue;
      rows.push({ member, depth, childCount: (children.get(key) ?? []).length, parentKey: parentKey || null });
      visit(key, depth + 1, new Set([...stack, key]));
    }
  };
  visit("", 0, new Set());
  return rows;
}

function memberVisible(row: MemberTreeRow): boolean {
  return !row.parentKey || expandedMembers.value.has(row.parentKey);
}

function toggleMember(member: WorkRecordMember): void {
  const key = member.conversation_id.toLowerCase();
  const next = new Set(expandedMembers.value);
  if (!next.delete(key)) next.add(key);
  expandedMembers.value = next;
}

const unfiledTreeRows = computed(() => buildConversationTreeRows(records.unfiled));
function unfiledKey(item: ConversationSummary): string {
  return item.agent + ":" + item.conversation_id.toLowerCase();
}
function unfiledParentKey(row: ConversationTreeRow): string | null {
  if (row.depth === 0) return null;
  const parentId = row.conversation.parent_thread_id?.toLowerCase();
  return parentId && records.unfiled.some((item) => item.conversation_id.toLowerCase() === parentId)
    ? parentId
    : null;
}
function unfiledVisible(row: ConversationTreeRow): boolean {
  const parentKey = unfiledParentKey(row);
  return !parentKey || expandedUnfiled.value.has(parentKey);
}
function toggleUnfiled(conversationId: string): void {
  const key = conversationId.toLowerCase();
  const next = new Set(expandedUnfiled.value);
  if (!next.delete(key)) next.add(key);
  expandedUnfiled.value = next;
}

interface DragMemberPayload {
  collectionId: string | null;
  memberKey: string;
  agent: "claude" | "codex";
  conversationId: string;
}
function setMemberDrag(event: DragEvent, payload: DragMemberPayload) {
  event.dataTransfer?.setData("application/x-aisc-work-record-member", JSON.stringify(payload));
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
}
function memberDragStart(event: DragEvent, collectionId: string, member: WorkRecordMember) {
  setMemberDrag(event, { collectionId, memberKey: member.member_key, agent: member.agent, conversationId: member.conversation_id });
}
function unfiledDragStart(event: DragEvent, item: ConversationSummary) {
  setMemberDrag(event, { collectionId: null, memberKey: unfiledKey(item), agent: item.agent, conversationId: item.conversation_id });
}
function draggedMember(event: DragEvent): DragMemberPayload | null {
  const raw = event.dataTransfer?.getData("application/x-aisc-work-record-member");
  if (!raw) return null;
  try { return JSON.parse(raw) as DragMemberPayload; } catch { return null; }
}
function areaKeys(collectionId: string | null): string[] {
  if (collectionId === null) return unfiledTreeRows.value.map((row) => unfiledKey(row.conversation));
  return (records.byId(collectionId)?.members ?? []).map((member) => member.member_key);
}
function orderWithKey(keys: string[], key: string, beforeKey?: string): string[] {
  const without = keys.filter((item) => item !== key);
  const index = beforeKey ? keys.indexOf(beforeKey) : without.length;
  without.splice(index < 0 ? without.length : index, 0, key);
  return without;
}
async function dropMember(event: DragEvent, targetCollectionId: string | null, targetMemberKey?: string) {
  event.preventDefault();
  event.stopPropagation();
  const source = draggedMember(event);
  if (!source) return;
  const next = orderWithKey(areaKeys(targetCollectionId), source.memberKey, targetMemberKey);
  if (source.collectionId === targetCollectionId) {
    if (targetCollectionId === null) await records.reorderUnfiled(next);
    else await records.reorderMembers(targetCollectionId, next);
  } else if (source.collectionId === null && targetCollectionId !== null) {
    await records.addMember(targetCollectionId, source.agent, source.conversationId);
    await records.reorderMembers(targetCollectionId, next);
  } else if (source.collectionId !== null && targetCollectionId !== null) {
    await records.moveMember(source.collectionId, targetCollectionId, source.agent, source.conversationId, next);
  } else if (source.collectionId !== null) {
    await records.moveMember(source.collectionId, null, source.agent, source.conversationId, next);
  }
}
function collectionDragStart(event: DragEvent, collection: WorkRecordCollection) {
  event.dataTransfer?.setData("application/x-aisc-work-record-collection", collection.id);
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
}
async function dropCollection(event: DragEvent, targetId: string) {
  event.preventDefault();
  event.stopPropagation();
  const sourceId = event.dataTransfer?.getData("application/x-aisc-work-record-collection");
  if (!sourceId || sourceId === targetId) return;
  const ids = records.collections.map((item) => item.id);
  const from = ids.indexOf(sourceId);
  const to = ids.indexOf(targetId);
  if (from < 0 || to < 0) return;
  ids.splice(to, 0, ...ids.splice(from, 1));
  await records.reorderCollections(ids);
}
function openMemberMenu(event: MouseEvent, collectionId: string | null, member: WorkRecordMember | null, item: ConversationSummary) {
  event.preventDefault();
  contextMenu.value = {
    x: event.clientX,
    y: event.clientY,
    collectionId,
    memberKey: member?.member_key ?? unfiledKey(item),
    agent: item.agent,
    conversationId: item.conversation_id,
  };
}
function closeMenu() { contextMenu.value = null; }
async function moveFromMenu(targetId: string | null) {
  const menu = contextMenu.value;
  if (!menu) return;
  const next = orderWithKey(areaKeys(targetId), menu.memberKey);
  if (menu.collectionId) {
    await records.moveMember(menu.collectionId, targetId, menu.agent, menu.conversationId, next);
  } else if (targetId) {
    await records.addMember(targetId, menu.agent, menu.conversationId);
    await records.reorderMembers(targetId, next);
  }
  closeMenu();
}

watch(() => explorer.conversations, (_value, old) => {
  if (old.length === explorer.conversations.length) return;
  void records.reconcile();
});
onMounted(async () => {
  window.addEventListener("click", closeMenu);
  if (props.workspace) {
    await Promise.all([records.load(props.workspace), explorer.loadConversations(true)]);
    await runtime.resolvePendingConversationAssociations(explorer.conversations);
  }
});
onBeforeUnmount(() => window.removeEventListener("click", closeMenu));
watch(() => props.workspace, async (workspace) => {
  records.setWorkspace(workspace);
  if (workspace) await Promise.all([records.load(workspace), explorer.loadConversations(true)]);
});
</script>

<template>
  <div class="explorer-body work-records-panel">
    <div class="work-record-switches">
      <label class="work-record-checkbox">
        <input v-model="showArchived" type="checkbox" data-testid="show-archived" />
        {{ t("workRecords.showArchived") }}
      </label>
      <button class="ui-icon-button sm" type="button" :title="t('workRecords.refresh')" :aria-label="t('workRecords.refresh')" data-testid="refresh-work-records" @click="refreshWorkRecords()">⟳</button>
    </div>

      <p v-if="records.error" class="explorer-error" role="alert">{{ records.error }}</p>

      <div class="work-record-create">
        <input
          v-model="newTitle"
          type="text"
          data-testid="new-work-record-title"
          :placeholder="t('workRecords.newTitle')"
          :aria-label="t('workRecords.newTitle')"
          @keydown.enter.prevent="createCollection"
        />
        <button
          class="ui-icon-button sm"
          type="button"
          :disabled="!newTitle.trim()"
          :title="t('workRecords.create')"
          :aria-label="t('workRecords.create')"
          @click="createCollection"
        >＋</button>
      </div>

      <p v-if="records.loading" class="explorer-empty">{{ t("explorer.loading") }}</p>
      <p v-else-if="!visibleCollections.length" class="explorer-empty">{{ t("workRecords.empty") }}</p>

      <article
        v-for="collection in visibleCollections"
        :key="collection.id"
        class="work-record"
        data-testid="collection"
        :data-id="collection.id"
        draggable="true"
        @dragstart="collectionDragStart($event, collection)"
        @dragover.prevent
        @drop="dropCollection($event, collection.id)"
      >
        <header class="work-record-head">
          <button
            class="conversation-twisty"
            type="button"
            :aria-expanded="!collapsedCollections.has(collection.id)"
            :aria-label="t('workRecords.tree.toggleCollection')"
            :data-testid="'collection-toggle-' + collection.id"
            @click.stop="toggleCollection(collection.id)"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path :d="!collapsedCollections.has(collection.id) ? 'M3 4.5 6 8l3-3.5' : 'M4.5 2.5 8 6l-3.5 3.5'" /></svg>
            <span class="conversation-child-count">{{ collection.members.length }}</span>
          </button>
          <input
            v-if="renamingCollectionId === collection.id"
            v-model="renameValue"
            class="title-input collection-title-input"
            type="text"
            data-testid="collection-rename-input"
            @keydown.enter.prevent="commitCollectionRename(collection.id)"
            @keydown.esc.prevent="renamingCollectionId = null"
            @blur="commitCollectionRename(collection.id)"
          >
          <h4 v-else class="collection-title" @dblclick="beginCollectionRename(collection)">{{ collection.title }}</h4>
          <span v-if="collection.status === 'archived'" class="work-record-archived">{{ t("workRecords.archived") }}</span>
          <span class="head-actions">
            <button class="ui-icon-button sm" type="button" :title="t('workRecords.rename')" :aria-label="t('workRecords.rename')" :data-testid="'rename-' + collection.id" @click.stop="beginCollectionRename(collection)">✎</button>
            <button v-if="collection.status === 'active'" class="ui-icon-button sm" type="button" :title="t('workRecords.archive')" :aria-label="t('workRecords.archive')" @click.stop="records.archive(collection.id)">🗄</button>
            <button v-else class="ui-icon-button sm" type="button" :title="t('workRecords.restore')" :aria-label="t('workRecords.restore')" @click.stop="records.restore(collection.id)">♻</button>
            <button class="ui-icon-button sm danger" type="button" :title="t('workRecords.delete')" :aria-label="t('workRecords.delete')" :data-testid="'delete-' + collection.id" @click.stop="requestCollectionDelete(collection.id, collection.title)">✕</button>
          </span>
        </header>

        <ul v-if="!collapsedCollections.has(collection.id)" class="work-record-members" @dragover.prevent @drop="dropMember($event, collection.id)">
          <template v-for="row in memberTree(collection)" :key="row.member.member_key">
            <li
              v-if="memberVisible(row)"
              draggable="true"
              :data-testid="'member-' + row.member.member_key"
              @dragstart="memberDragStart($event, collection.id, row.member)"
              @dragover.prevent
              @drop.stop="dropMember($event, collection.id, row.member.member_key)"
              @contextmenu.prevent="openMemberMenu($event, collection.id, row.member, memberConversation(row.member.member_key)!)"
            >
              <span class="member-tree-indent" :class="{ branch: row.depth > 0 }" :style="{ width: (row.depth * 14) + 'px' }" />
              <button v-if="row.childCount" class="conversation-twisty" type="button" :aria-expanded="expandedMembers.has(row.member.conversation_id.toLowerCase())" :aria-label="t('workRecords.tree.toggle')" :data-testid="'member-toggle-' + row.member.member_key" @click.stop="toggleMember(row.member)">
                <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path :d="expandedMembers.has(row.member.conversation_id.toLowerCase()) ? 'M3 4.5 6 8l3-3.5' : 'M4.5 2.5 8 6l-3.5 3.5'" /></svg>
                <span class="conversation-child-count">{{ row.childCount }}</span>
              </button>
              <span v-else class="conversation-twisty spacer" aria-hidden="true" />
              <input v-if="renamingConversationKey === row.member.member_key" v-model="renameValue" class="title-input member-title-input" type="text" data-testid="conversation-rename-input" @keydown.enter.prevent="commitConversationRename(memberConversation(row.member.member_key)!)" @keydown.esc.prevent="renamingConversationKey = null" @blur="commitConversationRename(memberConversation(row.member.member_key)!)">
              <span v-else class="member-title">{{ memberConversation(row.member.member_key)?.title || t("workRecords.missing") }}</span>
              <span class="member-agent">{{ row.member.agent }}</span>
              <button class="ui-icon-button sm" type="button" :data-testid="'resume-' + row.member.member_key" :disabled="!memberConversation(row.member.member_key)?.resumable" :title="t('workRecords.resume')" :aria-label="t('workRecords.resume')" @click.stop="resumeMember(row.member.member_key)">▶</button>
              <button class="ui-icon-button sm" type="button" :title="t('workRecords.rename')" :aria-label="t('workRecords.rename')" @click.stop="beginConversationRename(row.member.member_key)">✎</button>
              <button class="ui-icon-button sm danger" type="button" :title="t('workRecords.remove')" :aria-label="t('workRecords.remove')" @click.stop="removeMember(collection.id, row.member.agent, row.member.conversation_id)">✕</button>
            </li>
          </template>
        </ul>
        <p v-if="!collapsedCollections.has(collection.id) && !collection.members.length" class="work-record-no-members">{{ t("workRecords.noMembers") }}</p>
      </article>

      <section v-if="records.unfiled.length" class="work-record work-record-unfiled" data-testid="unfiled-container" @dragover.prevent @drop="dropMember($event, null)">
        <h4>
          <button class="conversation-twisty" type="button" :aria-expanded="unfiledExpanded" :aria-label="t('workRecords.tree.toggleCollection')" data-testid="unfiled-toggle" @click.stop="unfiledExpanded = !unfiledExpanded">
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path :d="unfiledExpanded ? 'M3 4.5 6 8l3-3.5' : 'M4.5 2.5 8 6l-3.5 3.5'" /></svg>
            <span class="conversation-child-count">{{ records.unfiled.length }}</span>
          </button>
          {{ t("workRecords.unfiled") }}
        </h4>
        <div v-if="unfiledExpanded" class="work-record-members">
          <template v-for="row in unfiledTreeRows" :key="unfiledKey(row.conversation)">
            <div
              v-if="unfiledVisible(row)"
              class="unfiled-row"
              draggable="true"
              :data-testid="'unfiled-' + unfiledKey(row.conversation)"
              @dragstart="unfiledDragStart($event, row.conversation)"
              @dragover.prevent
              @drop.stop="dropMember($event, null, unfiledKey(row.conversation))"
              @contextmenu.prevent="openMemberMenu($event, null, null, row.conversation)"
            >
              <span class="member-tree-indent" :class="{ branch: row.depth > 0 }" :style="{ width: (row.depth * 14) + 'px' }" />
              <button v-if="row.childCount" class="conversation-twisty" type="button" :aria-expanded="expandedUnfiled.has(row.conversation.conversation_id.toLowerCase())" :aria-label="t('workRecords.tree.toggle')" :data-testid="'unfiled-toggle-' + row.conversation.agent + ':' + row.conversation.conversation_id" @click.stop="toggleUnfiled(row.conversation.conversation_id)">
                <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path :d="expandedUnfiled.has(row.conversation.conversation_id.toLowerCase()) ? 'M3 4.5 6 8l3-3.5' : 'M4.5 2.5 8 6l-3.5 3.5'" /></svg>
                <span class="conversation-child-count">{{ row.childCount }}</span>
              </button>
              <span v-else class="conversation-twisty spacer" aria-hidden="true" />
              <input v-if="renamingConversationKey === unfiledKey(row.conversation)" v-model="renameValue" class="title-input member-title-input" type="text" data-testid="conversation-rename-input" @keydown.enter.prevent="commitConversationRename(row.conversation)" @keydown.esc.prevent="renamingConversationKey = null" @blur="commitConversationRename(row.conversation)">
              <span v-else class="member-title">{{ row.conversation.title }}</span>
              <span class="member-agent">{{ row.conversation.agent }}</span>
              <button class="ui-icon-button sm" type="button" :disabled="!row.conversation.resumable" :title="t('workRecords.resume')" :aria-label="t('workRecords.resume')" :data-testid="'resume-' + unfiledKey(row.conversation)" @click.stop="explorer.resumeConversation(row.conversation)">▶</button>
              <button class="ui-icon-button sm" type="button" :title="t('workRecords.rename')" :aria-label="t('workRecords.rename')" @click.stop="beginConversationRename(unfiledKey(row.conversation))">✎</button>
            </div>
          </template>
        </div>
      </section>


      <section v-if="records.failures().length" class="work-record-failures" data-testid="delete-failures">
        <h4>{{ t("workRecords.failures") }}</h4>
        <ul>
          <li v-for="failure in records.failures()" :key="`${failure.member_key}:${failure.stage}`">
            {{ failure.agent }} · {{ failure.conversation_id }} · {{ failure.stage }} · {{ failure.reason }}
          </li>
        </ul>
      </section>
    <div v-if="pendingDelete" class="quiet-delete-overlay" data-testid="quiet-delete-overlay" @mousedown.stop>
      <div class="quiet-delete" role="dialog" aria-modal="true" :aria-label="t('workRecords.deleteTitle')" data-testid="quiet-delete-dialog">
        <p>{{ pendingDelete.message }}</p>
        <div class="quiet-delete-actions">
          <button type="button" data-testid="quiet-delete-cancel" @click="pendingDelete = null">{{ t("workRecords.cancel") }}</button>
          <button type="button" class="danger" data-testid="quiet-delete-confirm" @click="confirmQuietDelete">{{ t("workRecords.delete") }}</button>
        </div>
      </div>
    </div>
    <Teleport to="body">
      <div v-if="contextMenu" class="work-record-menu" :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }" data-testid="work-record-context-menu" @click.stop>
        <button type="button" @click="resumeMember(contextMenu.memberKey); closeMenu()">{{ t("workRecords.resume") }}</button>
        <button type="button" @click="beginConversationRename(contextMenu.memberKey); closeMenu()">{{ t("workRecords.rename") }}</button>
        <button type="button" @click="requestConversationDelete(memberConversation(contextMenu.memberKey)!, contextMenu.collectionId); closeMenu()">{{ t("workRecords.delete") }}</button>
        <button v-if="contextMenu.collectionId" type="button" @click="moveFromMenu(null)">{{ t("workRecords.moveOut") }}</button>
        <template v-for="collection in records.unarchivedCollections" :key="collection.id">
          <button v-if="collection.id !== contextMenu.collectionId" type="button" @click="moveFromMenu(collection.id)">{{ t("workRecords.moveTo", { title: collection.title }) }}</button>
        </template>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.work-records-panel { gap: var(--space-2); overflow: auto; width:100%; max-width:100%; min-width:0; overflow-x:hidden; }
.work-record-switches { display:flex; align-items:center; gap:var(--space-1); flex-wrap:wrap; }
.work-record-checkbox { display:inline-flex; gap:4px; align-items:center; font-size:var(--font-sm); }
.work-record-create { display:flex; gap:var(--space-1); }
.work-record-create input { min-width:0; flex:1; }
.work-record { border:var(--border-w) solid var(--border); border-radius:var(--radius-sm); padding:var(--space-2); background:var(--surface); box-sizing:border-box; width:100%; max-width:100%; min-width:0; overflow:hidden; }
.work-record-head { display:flex; align-items:center; gap:var(--space-1); min-height:28px; }
.collection-title { margin:0; min-width:80px; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.title-input { height:20px; min-width:40px; flex:1; padding:0 4px; background:var(--surface-3); color:var(--text); border:var(--border-w) solid var(--accent); border-radius:var(--radius-sm); font:inherit; outline:none; }
.head-actions { display:flex; align-items:center; gap:2px; flex:0 0 auto; }
.work-record-archived { font-size:var(--font-xs); color:var(--text-faint); border:var(--border-w) solid var(--border-2); border-radius:999px; padding:0 6px; white-space:nowrap; }
.work-record-members, .work-record-failures ul { margin:var(--space-1) 0 0; padding-left:0; list-style:none; display:grid; grid-template-columns:minmax(0,1fr); gap:4px; min-height:24px; max-width:100%; }
.work-record-members li, .unfiled-row { display:flex; align-items:center; gap:var(--space-1); min-height:26px; padding:0 var(--space-1); border-radius:var(--radius-sm); background:var(--surface-2); color:var(--text-2); white-space:nowrap; box-sizing:border-box; width:100%; max-width:100%; min-width:0; }
.work-record-members li:hover, .unfiled-row:hover { background:var(--surface-hover); }
.member-title { min-width:0; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.member-agent { color:var(--text-faint); font-size:var(--font-xs); }
.member-tree-indent { flex:0 0 auto; align-self:stretch; }
.member-tree-indent.branch { border-right:1px solid var(--border-2); margin-right:4px; }
.conversation-twisty { display:inline-flex; align-items:center; gap:3px; flex:0 0 auto; height:20px; padding:0 3px; background:none; border:none; color:var(--text-muted); border-radius:var(--radius-sm); cursor:pointer; }
.conversation-twisty:hover { color:var(--text); background:var(--surface-hover); }
.conversation-twisty.spacer { width:14px; padding:0; }
.conversation-child-count { font-size:10px; }
.work-record-no-members { color:var(--text-faint); font-size:var(--font-xs); }
.work-record-unfiled { margin-top:var(--space-2); }
.work-record-unfiled h4 { margin:0 0 var(--space-1); }
.work-record-failures { margin-top:var(--space-2); color:var(--error); }
.ui-icon-button.danger { color:var(--error); }
.work-record-menu { position:fixed; z-index:1000; display:grid; min-width:160px; padding:4px; border:var(--border-w) solid var(--border); border-radius:var(--radius-sm); background:var(--surface); box-shadow:var(--shadow-menu); }
.work-record-menu button { justify-content:flex-start; padding:5px 8px; border:none; background:none; color:var(--text); text-align:left; border-radius:var(--radius-sm); cursor:pointer; }
.work-record-menu button:hover { background:var(--surface-hover); }
</style>

.quiet-delete-overlay { position:fixed; inset:0; z-index:95; background:var(--scrim,rgba(0,0,0,.4)); display:flex; align-items:center; justify-content:center; }
.quiet-delete { width:min(420px,90vw); padding:var(--space-3); background:var(--surface); border:var(--border-w) solid var(--border-strong); border-radius:var(--radius-md); box-shadow:var(--shadow-menu); }
.quiet-delete p { margin:0 0 var(--space-3); color:var(--text); }
.quiet-delete-actions { display:flex; justify-content:flex-end; gap:var(--space-2); }
