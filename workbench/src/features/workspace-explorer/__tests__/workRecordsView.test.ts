/**
 * v2.1.15 b6 Task 6 — Work Records view acceptance behavior.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { confirm } from "@tauri-apps/plugin-dialog";
import {
  conversationList,
  workRecordDelete,
  workRecordList,
  workRecordRemoveMember,
} from "../../../lib/ipc";
import { useWorkspaceExplorerStore } from "../../../stores/workspaceExplorer";
import WorkRecordsView from "../WorkRecordsView.vue";
import type { WorkRecordListResult } from "../../../types";

vi.mock("../../../lib/ipc", () => ({
  conversationList: vi.fn(async () => ({ schema_version: 1, conversations: [] })),
  conversationPreflight: vi.fn(),
  conversationDelete: vi.fn(),
  conversationRename: vi.fn(),
  workspaceList: vi.fn(),
  workspaceOpen: vi.fn(),
  workspaceCreateFile: vi.fn(),
  workspaceCreateDir: vi.fn(),
  workspaceCopyEntry: vi.fn(),
  workspaceRename: vi.fn(),
  workspaceReveal: vi.fn(),
  workspaceCopyPath: vi.fn(),
  workspaceWatchStart: vi.fn(),
  workspaceWatchStop: vi.fn(),
  logUiEvent: vi.fn(),
  artifactList: vi.fn(),
  artifactInspect: vi.fn(),
  artifactRefresh: vi.fn(),
  workRecordList: vi.fn(),
  workRecordCreate: vi.fn(),
  workRecordRename: vi.fn(),
  workRecordActivate: vi.fn(),
  workRecordDeactivate: vi.fn(),
  workRecordArchive: vi.fn(),
  workRecordRestore: vi.fn(),
  workRecordAddMember: vi.fn(),
  workRecordRemoveMember: vi.fn(),
  workRecordDelete: vi.fn(),
  workRecordReconcile: vi.fn(),
}));
const runtimeMock = vi.hoisted(() => ({
  closeLiveConversationSessions: vi.fn(async () => {}),
  resolvePendingConversationAssociations: vi.fn(async () => 0),
}));

vi.mock("../../../stores/runtime", () => ({
  useRuntimeStore: () => runtimeMock,
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({ confirm: vi.fn() }));

const conversationId = "01a04ca9-d3f6-7021-b9e7-50d48d818c65";
const withParent = (parentThreadId: string | null) => ({
  ...member,
  parent_thread_id: parentThreadId,
}) as typeof member;
const member = {
  member_key: `codex:${conversationId}`,
  agent: "codex" as const,
  conversation_id: conversationId,
  runtime_id: null,
  source: "manual" as const,
  added_at: "2026-01-01T00:00:00Z",
};
const activeCollection = {
  id: "active-1",
  title: "Feature",
  status: "active" as const,
  created_at: "t",
  updated_at: "t",
  archived_at: null,
  members: [member],
};
const archivedCollection = {
  ...activeCollection,
  id: "archived-1",
  title: "Old",
  status: "archived" as const,
  archived_at: "t",
};
const provider = {
  conversation_id: conversationId,
  agent: "codex" as const,
  title: "Provider",
  started_at: null,
  last_at: null,
  message_count: 1,
  file_size: 10,
  resumable: true,
};

function listResult(): WorkRecordListResult {
  return {
    schema_version: "aisc.work-collections/v1",
    active_collection_id: "active-1",
    collections: [activeCollection, archivedCollection],
    unfiled: [provider],
  };
}

beforeEach(() => {
  setActivePinia(createPinia());
  i18n.global.locale.value = "zh-CN";
  vi.clearAllMocks();
  vi.mocked(workRecordList).mockResolvedValue(listResult());
  vi.mocked(conversationList).mockResolvedValue({ schema_version: 1, conversations: [provider] });
  vi.mocked(confirm).mockResolvedValue(true);
});

async function mountView() {
  const explorer = useWorkspaceExplorerStore();
  explorer.workspace = "/ws";
  explorer.conversations = [provider];
  const wrapper = mount(WorkRecordsView, {
    props: { workspace: "/ws" },
    global: { plugins: [i18n] },
  });
  await flushPromises();
  return { wrapper, explorer };
}

describe("WorkRecordsView", () => {
  it("hides archived collections by default and shows them with the switch", async () => {
    const { wrapper } = await mountView();
    expect(wrapper.findAll("[data-testid=collection]").map((w) => w.attributes("data-id")))
      .toEqual(["active-1"]);
    await wrapper.find("[data-testid=show-archived]").setValue(true);
    expect(wrapper.findAll("[data-testid=collection]").map((w) => w.attributes("data-id")))
      .toEqual(["active-1", "archived-1"]);
  });

  it("marks the active collection and shows unfiled rows", async () => {
    const { wrapper } = await mountView();
    expect(wrapper.find("[data-testid=collection][data-id=active-1]").attributes("data-active")).toBe("true");
    expect(wrapper.find("[data-testid=unfiled]").text()).toContain("Provider");
  });

  it("uses one ordinary confirmation containing count and permanent-delete wording", async () => {
    const { wrapper } = await mountView();
    await wrapper.find(`[data-testid=delete-${activeCollection.id}]`).trigger("click");
    await flushPromises();
    expect(confirm).toHaveBeenCalledTimes(1);
    const [message, options] = vi.mocked(confirm).mock.calls[0] as [string, { title: string; kind: string }];
    expect(message).toContain("1");
    expect(message).toContain("永久删除");
    expect(options.kind).toBe("warning");
    expect(workRecordDelete).toHaveBeenCalledWith("/ws", activeCollection.id);
  });

  it("shows partial delete failures", async () => {
    vi.mocked(workRecordDelete).mockResolvedValue({
      deleted: true,
      collection_id: activeCollection.id,
      terminated_session_ids: [],
      deleted_members: [],
      failed_members: [{ ...member, stage: "delete", reason: "locked transcript" }],
    });
    const { wrapper } = await mountView();
    await wrapper.find(`[data-testid=delete-${activeCollection.id}]`).trigger("click");
    await flushPromises();
    const failures = wrapper.find("[data-testid=delete-failures]");
    expect(failures.exists()).toBe(true);
    expect(failures.text()).toContain("locked transcript");
  });

  it("closes matching live resume sessions before deleting a collection", async () => {
    const order: string[] = [];
    runtimeMock.closeLiveConversationSessions.mockImplementation(async () => {
      order.push("close");
    });
    vi.mocked(workRecordDelete).mockImplementation(async () => {
      order.push("delete");
      return {
        deleted: true,
        collection_id: activeCollection.id,
        terminated_session_ids: [conversationId],
        deleted_members: [member],
        failed_members: [],
      };
    });

    const { wrapper } = await mountView();
    await wrapper.find(`[data-testid=delete-${activeCollection.id}]`).trigger("click");
    await flushPromises();

    expect(order).toEqual(["close", "delete"]);
    expect(runtimeMock.closeLiveConversationSessions).toHaveBeenCalledWith([conversationId]);
  });

  it("refreshes both ledger and provider conversations", async () => {
    const { wrapper } = await mountView();
    const refresh = wrapper.findAll("button").find((button) => button.attributes("title") === "刷新");
    await refresh!.trigger("click");
    await flushPromises();

    expect(workRecordList).toHaveBeenCalledTimes(2);
    expect(conversationList).toHaveBeenCalledTimes(2);
  });

  it("restores unfiled immediately after removing a member", async () => {
    const { wrapper } = await mountView();
    vi.mocked(workRecordList).mockResolvedValue({
      ...listResult(),
      collections: [{ ...activeCollection, members: [] }],
    });
    vi.mocked(workRecordRemoveMember).mockResolvedValue({ removed: true, member_key: member.member_key });
    const remove = wrapper.findAll("button").find((button) => button.attributes("title") === "移出");
    await remove!.trigger("click");
    await flushPromises();

    expect(workRecordList).toHaveBeenCalledTimes(2);
    expect(wrapper.find(`[data-testid="resume-${member.member_key}"]`).exists()).toBe(false);
    expect(wrapper.find("[data-testid=unfiled]").text()).toContain("Provider");
  });

  it("resolves pending new provider tabs after refresh", async () => {
    const { wrapper } = await mountView();
    runtimeMock.resolvePendingConversationAssociations.mockClear();
    const refresh = wrapper.findAll("button").find((button) => button.attributes("title") === "刷新");
    await refresh!.trigger("click");
    await flushPromises();

    expect(runtimeMock.resolvePendingConversationAssociations).toHaveBeenLastCalledWith([provider]);
  });

  it("opens All Sessions inside Work Records without switching to History", async () => {
    const { wrapper, explorer } = await mountView();
    explorer.activateView = vi.fn();
    await wrapper.find("[data-testid=all-sessions]").trigger("click");
    expect(wrapper.findComponent({ name: "ConversationsPane" }).exists()).toBe(true);
    expect(wrapper.find(".conversation-row").text()).toContain("Provider");
    expect(explorer.activateView).not.toHaveBeenCalled();
  });

  it("keeps a search-matched child under its parent in All Sessions", async () => {
    const explorer = useWorkspaceExplorerStore();
    explorer.workspace = "/ws";
    const parent = { ...provider, conversation_id: "parent-1", title: "Parent", parent_thread_id: null };
    const child = { ...provider, conversation_id: "child-1", title: "Child", parent_thread_id: "parent-1" };
    explorer.conversations = [parent, child];
    vi.mocked(conversationList).mockResolvedValue({ schema_version: 1, conversations: [parent, child] });
    const wrapper = mount(WorkRecordsView, {
      props: { workspace: "/ws" },
      global: { plugins: [i18n] },
    });
    await flushPromises();
    await wrapper.find("[data-testid=all-sessions]").trigger("click");
    await wrapper.find('[data-testid="conversations-search"]').setValue("Child");
    const rows = wrapper.findAll(".conversation-row");
    expect(rows).toHaveLength(2);
    expect(rows[0].text()).toContain("Parent");
    expect(rows[1].text()).toContain("Child");
    expect(rows[1].attributes("style")).toContain("padding-left: 20px");
  });

  it("folds a collection child under its parent by default", async () => {
    const childId = "child-1";
    const parent = { ...provider, conversation_id: "parent-1", title: "Parent", parent_thread_id: null };
    const child = { ...provider, conversation_id: childId, title: "Child", parent_thread_id: "parent-1" };
    const collection: WorkRecordListResult["collections"][number] = {
      ...activeCollection,
      members: [
        { ...member, member_key: "codex:parent-1", conversation_id: "parent-1" },
        { ...withParent("parent-1"), member_key: "codex:child-1", conversation_id: childId },
      ],
    };
    useWorkspaceExplorerStore().conversations = [parent, child];
    vi.mocked(workRecordList).mockResolvedValue({
      ...listResult(),
      collections: [collection],
      active_collection_id: collection.id,
      unfiled: [],
    });
    const wrapper = mount(WorkRecordsView, {
      props: { workspace: "/ws" },
      global: { plugins: [i18n] },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("Parent");
    expect(wrapper.text()).not.toContain("Child");
    await wrapper.find('[data-testid="member-toggle-codex:parent-1"]').trigger("click");
    expect(wrapper.text()).toContain("Child");
  });

  it("disables resume for a missing transcript", async () => {
    const explorer = useWorkspaceExplorerStore();
    explorer.workspace = "/ws";
    explorer.conversations = [];
    vi.mocked(conversationList).mockResolvedValue({ schema_version: 1, conversations: [] });
    const wrapper = mount(WorkRecordsView, {
      props: { workspace: "/ws" },
      global: { plugins: [i18n] },
    });
    await flushPromises();
    const button = wrapper.find(`[data-testid="resume-${member.member_key}"]`);
    expect(button.exists()).toBe(true);
    expect(button.attributes("disabled")).toBeDefined();
    expect(button.attributes("aria-label")).toContain("缺失");
  });
});
