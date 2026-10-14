/**
 * v2.1.15 b6 — Work Record / Collection state.
 *
 * The CLI already joins unfiled provider summaries with Collections. This
 * store keeps explicit command outcomes (especially partial delete failures),
 * does not optimistically commit manual mutations, and is workspace-scoped.
 */
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import type {
  ConversationSummary,
  WorkRecordCollection,
  WorkRecordDeleteFailure,
  WorkRecordDeleteResult,
  WorkRecordMember,
} from "../types";
import * as ipc from "../lib/ipc";

function messageOf(error: unknown): string {
  return (error as { message?: string })?.message ?? String(error);
}

export const useWorkRecordsStore = defineStore("workRecords", () => {
  const workspace = ref<string | null>(null);
  const schemaVersion = ref<string>("");
  const activeCollectionId = ref<string | null>(null);
  const collections = ref<WorkRecordCollection[]>([]);
  const unfiled = ref<ConversationSummary[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastDeleteFailure = ref<WorkRecordDeleteResult | null>(null);

  const activeCollection = computed(
    () => collections.value.find((c) => c.id === activeCollectionId.value) ?? null,
  );
  const activeCollections = computed(() =>
    collections.value.filter((c) => c.status === "active"),
  );
  const archivedCollections = computed(() =>
    collections.value.filter((c) => c.status === "archived"),
  );

  function byId(id: string): WorkRecordCollection | null {
    return collections.value.find((c) => c.id === id) ?? null;
  }

  function replaceCollection(next: WorkRecordCollection): void {
    collections.value = collections.value.some((c) => c.id === next.id)
      ? collections.value.map((c) => (c.id === next.id ? next : c))
      : [...collections.value, next];
  }

  function clear(): void {
    workspace.value = null;
    schemaVersion.value = "";
    activeCollectionId.value = null;
    collections.value = [];
    unfiled.value = [];
    error.value = null;
    lastDeleteFailure.value = null;
  }

  function setWorkspace(next: string | null): void {
    if (workspace.value === next) return;
    clear();
    workspace.value = next;
  }

  async function load(target: string): Promise<void> {
    setWorkspace(target);
    loading.value = true;
    error.value = null;
    try {
      const result = await ipc.workRecordList(target);
      schemaVersion.value = result.schema_version;
      activeCollectionId.value = result.active_collection_id;
      collections.value = result.collections;
      unfiled.value = result.unfiled;
    } catch (e) {
      error.value = messageOf(e);
    } finally {
      loading.value = false;
    }
  }

  async function create(title: string): Promise<WorkRecordCollection | null> {
    if (!workspace.value) return null;
    error.value = null;
    try {
      const result = await ipc.workRecordCreate(workspace.value, title);
      if (result.collection) replaceCollection(result.collection);
      return result.collection;
    } catch (e) {
      error.value = messageOf(e);
      return null;
    }
  }

  async function rename(id: string, title: string): Promise<WorkRecordCollection | null> {
    if (!workspace.value) return null;
    error.value = null;
    try {
      const result = await ipc.workRecordRename(workspace.value, id, title);
      if (result.collection) replaceCollection(result.collection);
      return result.collection;
    } catch (e) {
      error.value = messageOf(e);
      return null;
    }
  }

  async function activate(id: string): Promise<void> {
    if (!workspace.value) return;
    error.value = null;
    try {
      const result = await ipc.workRecordActivate(workspace.value, id);
      activeCollectionId.value = result.active_collection_id;
    } catch (e) {
      error.value = messageOf(e);
    }
  }

  async function deactivate(): Promise<void> {
    if (!workspace.value) return;
    error.value = null;
    try {
      const result = await ipc.workRecordDeactivate(workspace.value);
      activeCollectionId.value = result.active_collection_id;
    } catch (e) {
      error.value = messageOf(e);
    }
  }

  async function archive(id: string): Promise<WorkRecordCollection | null> {
    if (!workspace.value) return null;
    error.value = null;
    try {
      const result = await ipc.workRecordArchive(workspace.value, id);
      if (result.collection) replaceCollection(result.collection);
      if (activeCollectionId.value === id) activeCollectionId.value = null;
      return result.collection;
    } catch (e) {
      error.value = messageOf(e);
      return null;
    }
  }

  async function restore(id: string): Promise<WorkRecordCollection | null> {
    if (!workspace.value) return null;
    error.value = null;
    try {
      const result = await ipc.workRecordRestore(workspace.value, id);
      if (result.collection) replaceCollection(result.collection);
      return result.collection;
    } catch (e) {
      error.value = messageOf(e);
      return null;
    }
  }

  function removeLocalMember(id: string, memberKey: string): void {
    collections.value = collections.value.map((c) =>
      c.id === id ? { ...c, members: c.members.filter((m) => m.member_key !== memberKey) } : c,
    );
  }

  async function addMember(
    id: string,
    agent: "claude" | "codex",
    conversationId: string,
    runtimeId?: string | null,
  ): Promise<WorkRecordMember | null> {
    if (!workspace.value) return null;
    error.value = null;
    try {
      const result = await ipc.workRecordAddMember(
        workspace.value,
        id,
        agent,
        conversationId,
        runtimeId,
      );
      if (result.member) {
        const member = result.member;
        const current = byId(id);
        if (current && !current.members.some((m) => m.member_key === member.member_key)) {
          replaceCollection({ ...current, members: [...current.members, member] });
        }
        unfiled.value = unfiled.value.filter(
          (item) => !(item.agent === member.agent && item.conversation_id === member.conversation_id),
        );
      }
      return result.member;
    } catch (e) {
      error.value = messageOf(e);
      return null;
    }
  }

  async function removeMember(
    id: string,
    agent: "claude" | "codex",
    conversationId: string,
  ): Promise<boolean> {
    if (!workspace.value) return false;
    error.value = null;
    try {
      const result = await ipc.workRecordRemoveMember(
        workspace.value,
        id,
        agent,
        conversationId,
      );
      const memberKey = `${agent}:${conversationId.toLowerCase()}`;
      removeLocalMember(id, result.member_key ?? memberKey);
      return result.removed;
    } catch (e) {
      error.value = messageOf(e);
      return false;
    }
  }

  async function reorderCollections(ids: string[]): Promise<boolean> {
    if (!workspace.value) return false;
    error.value = null;
    try {
      const result = await ipc.workRecordReorderCollections(workspace.value, ids);
      collections.value = result.collections;
      return true;
    } catch (e) {
      error.value = messageOf(e);
      return false;
    }
  }

  async function reorderMembers(
    id: string,
    memberKeys: string[],
  ): Promise<WorkRecordCollection | null> {
    if (!workspace.value) return null;
    error.value = null;
    try {
      const result = await ipc.workRecordReorderMembers(workspace.value, id, memberKeys);
      if (result.collection) replaceCollection(result.collection);
      return result.collection;
    } catch (e) {
      error.value = messageOf(e);
      return null;
    }
  }

  async function reorderUnfiled(memberKeys: string[]): Promise<boolean> {
    if (!workspace.value) return false;
    error.value = null;
    try {
      const result = await ipc.workRecordReorderUnfiled(workspace.value, memberKeys);
      unfiled.value = result.unfiled;
      return true;
    } catch (e) {
      error.value = messageOf(e);
      return false;
    }
  }

  async function moveMember(
    fromId: string,
    toId: string | null,
    agent: "claude" | "codex",
    conversationId: string,
    destinationOrder?: string[],
  ): Promise<boolean> {
    if (!workspace.value) return false;
    error.value = null;
    const memberKey = `${agent}:${conversationId.toLowerCase()}`;
    try {
      await ipc.workRecordMoveMember(
        workspace.value,
        fromId,
        memberKey,
        toId,
        destinationOrder,
      );
      await load(workspace.value);
      return true;
    } catch (e) {
      error.value = messageOf(e);
      await reload();
      return false;
    }
  }

  async function deleteCollection(id: string): Promise<WorkRecordDeleteResult | null> {
    if (!workspace.value) return null;
    error.value = null;
    try {
      const result = await ipc.workRecordDelete(workspace.value, id);
      lastDeleteFailure.value = result.failed_members.length ? result : null;
      collections.value = collections.value.filter((c) => c.id !== id);
      if (activeCollectionId.value === id) activeCollectionId.value = null;
      return result;
    } catch (e) {
      error.value = messageOf(e);
      return null;
    }
  }

  async function reconcile(): Promise<void> {
    if (!workspace.value) return;
    await ipc.workRecordReconcile(workspace.value);
    await load(workspace.value);
  }

  async function reload(): Promise<void> {
    if (workspace.value) await load(workspace.value);
  }

  function failures(): WorkRecordDeleteFailure[] {
    return lastDeleteFailure.value?.failed_members ?? [];
  }

  return {
    workspace,
    schemaVersion,
    activeCollectionId,
    activeCollection,
    activeCollections,
    archivedCollections,
    collections,
    unfiled,
    loading,
    error,
    lastDeleteFailure,
    byId,
    setWorkspace,
    load,
    reload,
    create,
    rename,
    activate,
    deactivate,
    archive,
    restore,
    addMember,
    removeMember,
    moveMember,
    reorderCollections,
    reorderMembers,
    reorderUnfiled,
    delete: deleteCollection,
    reconcile,
    failures,
  };
});

