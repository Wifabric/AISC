<script setup lang="ts">
/**
 * Work Records view (b6; b8 visual/tree refactor). Collections are actions
 * symbolically; All Sessions reuses the conversation pane; Codex child
 * sessions stay folded beneath their parent in collection member lists.
 */
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { confirm } from "@tauri-apps/plugin-dialog";
import { useWorkRecordsStore } from "../../stores/workRecords";
import { useWorkspaceExplorerStore } from "../../stores/workspaceExplorer";
import { useRuntimeStore } from "../../stores/runtime";
import ConversationsPane from "./ConversationsPane.vue";
import type { ConversationSummary } from "../../types";
import type { WorkRecordMember, WorkRecordCollection } from "../../types";

const props = defineProps<{ workspace: string | null }>();
const { t } = useI18n();
const records = useWorkRecordsStore();
const explorer = useWorkspaceExplorerStore();
const runtime = useRuntimeStore();
const view = ref<"records" | "all">("records");
const showArchived = ref(false);
const newTitle = ref("");
const selectedCollection = ref<string | null>(null);
const editTitles = ref<Record<string, string>>({});
const expandedMembers = ref(new Set<string>());

const visibleCollections = computed(() =>
  showArchived.value ? records.collections : records.collections.filter((item) => item.status === "active"),
);

const conversationBy = computed(() => {
  const out = new Map<string, ConversationSummary>();
  for (const item of explorer.conversations) {
    out.set(`${item.agent}:${item.conversation_id.toLowerCase()}`, item);
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
    newTitle.value = "";
    selectedCollection.value = created.id;
  }
}

async function renameCollection(id: string) {
  const title = (editTitles.value[id] ?? "").trim();
  if (!title) return;
  const updated = await records.rename(id, title);
  if (updated) editTitles.value[id] = "";
}

async function removeCollection(id: string, title: string) {
  const memberCount = records.byId(id)?.members.length ?? 0;
  const message = t("workRecords.deleteConfirm", { title, count: memberCount });
  const ok = await confirm(message, { title: t("workRecords.deleteTitle"), kind: "warning" });
  if (!ok) return;
  await explorer.loadConversations(true);
  await runtime.resolvePendingConversationAssociations(explorer.conversations);
  // Known live resume sessions close before CLI cascade deletion; tabs without
  // a safe conversation identity remain untouched (b6 behavior).
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

async function addUnfiled(item: ConversationSummary) {
  const target = selectedCollection.value ?? records.activeCollectionId;
  if (!target) return;
  await records.addMember(target, item.agent, item.conversation_id);
}

async function resumeMember(memberKey: string) {
  const item = memberConversation(memberKey);
  if (item?.resumable) await explorer.resumeConversation(item);
}

interface MemberTreeRow {
  member: WorkRecordMember;
  depth: number;
  childCount: number;
}

/** Collection members are provider identities; build a local tree without
 * relying on runtime ids. A missing parent is promoted, never dropped. */
function memberTree(collection: WorkRecordCollection): MemberTreeRow[] {
  const byId = new Map(collection.members.map((member) => [member.conversation_id.toLowerCase(), member]));
  const children = new Map<string, WorkRecordMember[]>();
  for (const member of collection.members) {
    const conversation = conversationBy.value.get(`${member.agent}:${member.conversation_id.toLowerCase()}`);
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
      rows.push({ member, depth, childCount: (children.get(key) ?? []).length });
      visit(key, depth + 1, new Set([...stack, key]));
    }
  };
  visit("", 0, new Set());
  return rows;
}

function memberVisible(collection: WorkRecordCollection, row: MemberTreeRow): boolean {
  const parentId = (row.member as WorkRecordMember & { parent_thread_id?: string | null }).parent_thread_id?.toLowerCase();
  if (!parentId || !collection.members.some((member) => member.conversation_id.toLowerCase() === parentId)) return true;
  return expandedMembers.value.has(parentId);
}

function toggleMember(member: WorkRecordMember): void {
  const key = member.conversation_id.toLowerCase();
  const next = new Set(expandedMembers.value);
  if (!next.delete(key)) next.add(key);
  expandedMembers.value = next;
}

onMounted(async () => {
  if (props.workspace) {
    await Promise.all([records.load(props.workspace), explorer.loadConversations(true)]);
    await runtime.resolvePendingConversationAssociations(explorer.conversations);
  }
});

watch(() => props.workspace, async (workspace) => {
  records.setWorkspace(workspace);
  if (workspace) {
    await Promise.all([records.load(workspace), explorer.loadConversations(true)]);
  }
});
</script>

<template>
  <div class="explorer-body work-records-panel">
    <div class="work-record-switches">
      <button
        class="ui-button sm"
        :class="{ active: view === 'records' }"
        type="button"
        data-testid="work-records-tab"
        @click="view = 'records'"
      >{{ t("workRecords.title") }}</button>
      <button
        class="ui-button sm"
        :class="{ active: view === 'all' }"
        type="button"
        data-testid="all-sessions"
        @click="view = 'all'"
      >{{ t("workRecords.allSessions") }}</button>
      <template v-if="view === 'records'">
        <label class="work-record-checkbox">
          <input v-model="showArchived" type="checkbox" data-testid="show-archived" />
          {{ t("workRecords.showArchived") }}
        </label>
        <button class="ui-icon-button sm" type="button" :title="t('workRecords.refresh')" :aria-label="t('workRecords.refresh')" @click="refreshWorkRecords()">⟳</button>
      </template>
    </div>

    <ConversationsPane v-if="view === 'all'" />

    <template v-else>
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
        :data-active="collection.id === records.activeCollectionId ? 'true' : 'false'"
      >
        <header class="work-record-head">
          <h4>{{ collection.title }}</h4>
          <span v-if="collection.id === records.activeCollectionId" class="work-record-active">{{ t("workRecords.active") }}</span>
          <span v-else-if="collection.status === 'archived'" class="work-record-archived">{{ t("workRecords.archived") }}</span>
        </header>

        <div class="work-record-actions">
          <input
            v-model="editTitles[collection.id]"
            type="text"
            :placeholder="t('workRecords.newTitle')"
            :aria-label="t('workRecords.rename')"
          />
          <button
            class="ui-icon-button sm"
            type="button"
            :disabled="!(editTitles[collection.id] ?? '').trim()"
            :title="t('workRecords.rename')"
            :aria-label="t('workRecords.rename')"
            @click="renameCollection(collection.id)"
          >✎</button>
          <button
            v-if="collection.id !== records.activeCollectionId && collection.status === 'active'"
            class="ui-icon-button sm"
            type="button"
            :title="t('workRecords.activate')"
            :aria-label="t('workRecords.activate')"
            @click="records.activate(collection.id)"
          >◎</button>
          <button
            v-if="collection.id === records.activeCollectionId"
            class="ui-icon-button sm"
            type="button"
            :title="t('workRecords.deactivate')"
            :aria-label="t('workRecords.deactivate')"
            @click="records.deactivate()"
          >○</button>
          <button
            v-if="collection.status === 'active'"
            class="ui-icon-button sm"
            type="button"
            :title="t('workRecords.archive')"
            :aria-label="t('workRecords.archive')"
            @click="records.archive(collection.id)"
          >🗄</button>
          <button
            v-else
            class="ui-icon-button sm"
            type="button"
            :title="t('workRecords.restore')"
            :aria-label="t('workRecords.restore')"
            @click="records.restore(collection.id)"
          >♻</button>
          <button
            class="ui-icon-button sm danger"
            type="button"
            :title="t('workRecords.delete')"
            :aria-label="t('workRecords.delete')"
            :data-testid="`delete-${collection.id}`"
            @click="removeCollection(collection.id, collection.title)"
          >✕</button>
        </div>

        <ul class="work-record-members">
          <template v-for="row in memberTree(collection)" :key="row.member.member_key">
            <li v-if="memberVisible(collection, row)" :style="{ paddingLeft: `${row.depth * 14}px` }">
              <button
                v-if="row.childCount"
                class="conversation-twisty"
                type="button"
                :aria-expanded="expandedMembers.has(row.member.conversation_id.toLowerCase())"
                :aria-label="t('workRecords.tree.toggle')"
                :data-testid="`member-toggle-${row.member.member_key}`"
                @click="toggleMember(row.member)"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
                  <path :d="expandedMembers.has(row.member.conversation_id.toLowerCase()) ? 'M3 4.5 6 8l3-3.5' : 'M4.5 2.5 8 6l-3.5 3.5'" />
                </svg>
                <span class="conversation-child-count">{{ row.childCount }}</span>
              </button>
              <span v-else class="conversation-twisty spacer" aria-hidden="true" />
              <span class="member-title">
                {{ memberConversation(row.member.member_key)?.title || t("workRecords.missing") }}
              </span>
              <span class="member-agent">{{ row.member.agent }}</span>
              <button
                class="ui-icon-button sm"
                type="button"
                :data-testid="`resume-${row.member.member_key}`"
                :disabled="!memberConversation(row.member.member_key)?.resumable"
                :title="memberConversation(row.member.member_key)?.resumable ? t('workRecords.resume') : t('workRecords.missing')"
                :aria-label="memberConversation(row.member.member_key)?.resumable ? t('workRecords.resume') : t('workRecords.missing')"
                @click="resumeMember(row.member.member_key)"
              >{{ memberConversation(row.member.member_key)?.resumable ? "▶" : "🚫" }}</button>
              <button
                class="ui-icon-button sm danger"
                type="button"
                :title="t('workRecords.remove')"
                :aria-label="t('workRecords.remove')"
                @click="removeMember(collection.id, row.member.agent, row.member.conversation_id)"
              >✕</button>
            </li>
          </template>
        </ul>
        <p v-if="!collection.members.length" class="work-record-no-members">{{ t("workRecords.noMembers") }}</p>
      </article>

      <section v-if="records.unfiled.length" class="work-record-unfiled">
        <h4>{{ t("workRecords.unfiled") }}</h4>
        <div
          v-for="item in records.unfiled"
          :key="`${item.agent}:${item.conversation_id}`"
          class="explorer-row artifact-row"
          data-testid="unfiled"
        >
          <span class="explorer-name">{{ item.title }}</span>
          <select v-model="selectedCollection" :aria-label="t('workRecords.selectCollection')">
            <option :value="records.activeCollectionId">{{ t("workRecords.activeCollection") }}</option>
            <option v-for="collection in records.activeCollections" :key="collection.id" :value="collection.id">
              {{ collection.title }}
            </option>
          </select>
          <button
            class="ui-icon-button sm"
            type="button"
            :title="t('workRecords.add')"
            :aria-label="t('workRecords.add')"
            @click="addUnfiled(item)"
          >＋</button>
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
    </template>
  </div>
</template>

<style scoped>
.work-records-panel { gap: var(--space-2); overflow: auto; }
.work-record-switches { display:flex; align-items:center; gap:var(--space-1); flex-wrap:wrap; }
.work-record-checkbox { display:inline-flex; gap:4px; align-items:center; font-size:var(--font-sm); }
.work-record-create { display:flex; gap:var(--space-1); }
.work-record-create input, .work-record-actions input, .work-record-unfiled select { min-width:0; }
.work-record { border:var(--border-w) solid var(--border); border-radius:var(--radius-sm); padding:var(--space-2); }
.work-record-head { display:flex; align-items:center; gap:var(--space-1); }
.work-record-head h4 { margin:0; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.work-record-active, .work-record-archived { font-size:var(--font-xs); color:var(--text-faint); border:var(--border-w) solid var(--border-2); border-radius:999px; padding:0 6px; }
.work-record-actions { display:flex; gap:var(--space-1); margin-top:var(--space-1); flex-wrap:wrap; align-items:center; }
.work-record-actions input { flex:1; min-width:80px; }
.work-record-members, .work-record-failures ul { margin:var(--space-1) 0 0; padding-left:0; list-style:none; display:grid; gap:4px; }
.work-record-members li { display:flex; align-items:center; gap:var(--space-1); }
.member-title { min-width:0; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.member-agent { color:var(--text-faint); font-size:var(--font-xs); }
.conversation-twisty { display:inline-flex; align-items:center; gap:3px; flex:0 0 auto; height:20px; padding:0 3px; background:none; border:none; color:var(--text-muted); border-radius:var(--radius-sm); cursor:pointer; }
.conversation-twisty:hover { color:var(--text); background:var(--surface-hover); }
.conversation-twisty.spacer { width:14px; padding:0; }
.conversation-child-count { font-size:10px; }
.work-record-no-members { color:var(--text-faint); font-size:var(--font-xs); }
.work-record-unfiled, .work-record-failures { margin-top:var(--space-2); border-top:var(--border-w) solid var(--border); padding-top:var(--space-1); }
.work-record-unfiled h4, .work-record-failures h4 { margin:0 0 var(--space-1); }
.work-record-failures { color:var(--error); }
.ui-icon-button.danger { color:var(--error); }
</style>
