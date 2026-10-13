<script setup lang="ts">
/**
 * Work Records view (v2.1.15 b6). Aggregates Collections over the existing
 * provider conversation layer. All Sessions remains the unchanged flat view;
 * this component only adds collection metadata and member actions.
 */
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { confirm } from "@tauri-apps/plugin-dialog";
import { useWorkRecordsStore } from "../../stores/workRecords";
import { useWorkspaceExplorerStore } from "../../stores/workspaceExplorer";
import { useRuntimeStore } from "../../stores/runtime";
import type { ConversationSummary } from "../../types";

const props = defineProps<{ workspace: string | null }>();
const emit = defineEmits<{ (event: "switch", kind: "conversations"): void }>();
const { t } = useI18n();
const records = useWorkRecordsStore();
const explorer = useWorkspaceExplorerStore();
const runtime = useRuntimeStore();
const showArchived = ref(false);
const newTitle = ref("");
const selectedCollection = ref<string | null>(null);
const editTitles = ref<Record<string, string>>({});

const visibleCollections = computed(() =>
  showArchived.value
    ? records.collections
    : records.collections.filter((c) => c.status === "active"),
);

const conversationBy = computed(() => {
  const out = new Map<string, ConversationSummary>();
  for (const item of explorer.conversations) out.set(`${item.agent}:${item.conversation_id.toLowerCase()}`, item);
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
  const ok = await confirm(message, {
    title: t("workRecords.deleteTitle"),
    kind: "warning",
  });
  if (!ok) return;
  // Terminate known live resume sessions before the CLI physically cascades
  // transcript deletion. Provider tabs opened without a resume id have no safe
  // conversation identity match here and are intentionally left alone.
  await runtime.closeLiveConversationSessions(
    (records.byId(id)?.members ?? []).map((member) => member.conversation_id),
  );
  // The store preserves the partial-failure result for explicit UI display.
  await records.delete(id);
  await explorer.loadConversations(true);
}

async function refreshWorkRecords() {
  await Promise.all([
    records.reload(),
    explorer.loadConversations(true),
  ]);
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

onMounted(async () => {
  if (props.workspace) {
    await Promise.all([
      records.load(props.workspace),
      explorer.loadConversations(true),
    ]);
  }
});

watch(() => props.workspace, async (workspace) => {
  records.setWorkspace(workspace);
  if (workspace) {
    await Promise.all([
      records.load(workspace),
      explorer.loadConversations(true),
    ]);
  }
});
</script>

<template>
  <div class="explorer-body work-records-panel">
    <div class="work-record-switches">
      <button class="ui-button sm active" type="button" data-testid="work-records-tab">
        {{ t("workRecords.title") }}
      </button>
      <button
        class="ui-button sm"
        type="button"
        data-testid="all-sessions"
        @click="emit('switch', 'conversations')"
      >{{ t("workRecords.allSessions") }}</button>
      <label class="work-record-checkbox">
        <input v-model="showArchived" type="checkbox" data-testid="show-archived" />
        {{ t("workRecords.showArchived") }}
      </label>
      <button class="ui-button sm" type="button" @click="refreshWorkRecords()">
        {{ t("workRecords.refresh") }}
      </button>
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
      <button class="ui-button sm" type="button" :disabled="!newTitle.trim()" @click="createCollection">
        {{ t("workRecords.create") }}
      </button>
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
        <span v-if="collection.id === records.activeCollectionId" class="work-record-active">
          {{ t("workRecords.active") }}
        </span>
        <span v-else-if="collection.status === 'archived'" class="work-record-archived">
          {{ t("workRecords.archived") }}
        </span>
      </header>

      <div class="work-record-actions">
        <input
          v-model="editTitles[collection.id]"
          type="text"
          :placeholder="t('workRecords.newTitle')"
          :aria-label="t('workRecords.rename')"
        />
        <button class="ui-button sm" type="button" @click="renameCollection(collection.id)">
          {{ t("workRecords.rename") }}
        </button>
        <button
          v-if="collection.id !== records.activeCollectionId && collection.status === 'active'"
          class="ui-button sm"
          type="button"
          @click="records.activate(collection.id)"
        >{{ t("workRecords.activate") }}</button>
        <button
          v-if="collection.id === records.activeCollectionId"
          class="ui-button sm"
          type="button"
          @click="records.deactivate()"
        >{{ t("workRecords.deactivate") }}</button>
        <button
          v-if="collection.status === 'active'"
          class="ui-button sm"
          type="button"
          @click="records.archive(collection.id)"
        >{{ t("workRecords.archive") }}</button>
        <button
          v-else
          class="ui-button sm"
          type="button"
          @click="records.restore(collection.id)"
        >{{ t("workRecords.restore") }}</button>
        <button
          class="ui-button sm danger"
          type="button"
          :data-testid="`delete-${collection.id}`"
          @click="removeCollection(collection.id, collection.title)"
        >{{ t("workRecords.delete") }}</button>
      </div>

      <ul class="work-record-members">
        <li v-for="member in collection.members" :key="member.member_key">
          <span class="member-title">
            {{ memberConversation(member.member_key)?.title || t("workRecords.missing") }}
          </span>
          <span class="member-agent">{{ member.agent }}</span>
          <button
            class="ui-button sm"
            type="button"
            :data-testid="`resume-${member.member_key}`"
            :disabled="!memberConversation(member.member_key)?.resumable"
            @click="resumeMember(member.member_key)"
          >
            {{ memberConversation(member.member_key)?.resumable ? t("workRecords.resume") : t("workRecords.missing") }}
          </button>
          <button
            class="ui-button sm"
            type="button"
            @click="removeMember(collection.id, member.agent, member.conversation_id)"
          >{{ t("workRecords.remove") }}</button>
        </li>
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
        <button class="ui-button sm" type="button" @click="addUnfiled(item)">
          {{ t("workRecords.add") }}
        </button>
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
  </div>
</template>

<style scoped>
.work-records-panel { gap: var(--space-2); overflow: auto; }
.work-record-switches { display: flex; align-items: center; gap: var(--space-1); flex-wrap: wrap; }
.work-record-checkbox { display: inline-flex; gap: 4px; align-items: center; font-size: var(--font-sm); }
.work-record-create { display: flex; gap: var(--space-1); }
.work-record-create input, .work-record-actions input, .work-record-unfiled select { min-width: 0; }
.work-record { border: var(--border-w) solid var(--border); border-radius: var(--radius-sm); padding: var(--space-2); }
.work-record-head { display: flex; align-items: center; gap: var(--space-1); }
.work-record-head h4 { margin: 0; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.work-record-active, .work-record-archived { font-size: var(--font-xs); color: var(--text-faint); border: var(--border-w) solid var(--border-2); border-radius: 999px; padding: 0 6px; }
.work-record-actions { display: flex; gap: var(--space-1); margin-top: var(--space-1); flex-wrap: wrap; }
.work-record-actions input { flex: 1; min-width: 80px; }
.work-record-members, .work-record-failures ul { margin: var(--space-1) 0 0; padding-left: 0; list-style: none; display: grid; gap: 4px; }
.work-record-members li { display: flex; align-items: center; gap: var(--space-1); }
.member-title { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.member-agent { color: var(--text-faint); font-size: var(--font-xs); }
.work-record-no-members { color: var(--text-faint); font-size: var(--font-xs); }
.work-record-unfiled, .work-record-failures { margin-top: var(--space-2); border-top: var(--border-w) solid var(--border); padding-top: var(--space-1); }
.work-record-unfiled h4, .work-record-failures h4 { margin: 0 0 var(--space-1); }
.work-record-failures { color: var(--error); }
.ui-button.danger { color: var(--error); }
</style>
