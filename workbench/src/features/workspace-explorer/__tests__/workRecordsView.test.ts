/**
 * v2.1.15 b6 Task 6 — Work Records view acceptance behavior.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import componentSource from "../WorkRecordsView.vue?raw";
import { i18n } from "../../../i18n";
import { confirm } from "@tauri-apps/plugin-dialog";
import {
  conversationDelete,
  conversationList,
  conversationPreflight,
  workRecordAddMember,
  workRecordDelete,
  workRecordList,
  workRecordReorderCollections,
  workRecordReorderMembers,
  workRecordRename,
  workRecordMoveMember,
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
  workRecordReorderCollections: vi.fn(),
  workRecordReorderMembers: vi.fn(),
  workRecordReorderUnfiled: vi.fn(),
  workRecordMoveMember: vi.fn(),
}));
const runtimeMock = vi.hoisted(() => ({
  tabs: [] as unknown[],
  activeTabId: null as string | null,
  activateTab: vi.fn(),
  createTab: vi.fn(() => ({ id: "tab-1" })),
  closeLiveConversationSessions: vi.fn(async () => {}),
  resolvePendingConversationAssociations: vi.fn(async () => 0),
}));

vi.mock("../../../stores/runtime", () => ({
  useRuntimeStore: () => runtimeMock,
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({ confirm: vi.fn() }));

const conversationId = "01a04ca9-d3f6-7021-b9e7-50d48d818c65";
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
    expect(wrapper.find("[data-testid^='unfiled-']").text()).toContain("Provider");
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
    expect(wrapper.find(`[data-testid=collection] [data-testid="resume-${member.member_key}"]`).exists()).toBe(false);
    expect(wrapper.find("[data-testid^='unfiled-']").text()).toContain("Provider");
  });

  it("resolves pending new provider tabs after refresh", async () => {
    const { wrapper } = await mountView();
    runtimeMock.resolvePendingConversationAssociations.mockClear();
    const refresh = wrapper.findAll("button").find((button) => button.attributes("title") === "刷新");
    await refresh!.trigger("click");
    await flushPromises();

    expect(runtimeMock.resolvePendingConversationAssociations).toHaveBeenLastCalledWith([provider]);
  });

  it("does not embed an All Sessions mode inside Work Records", async () => {
    const { wrapper } = await mountView();
    expect(wrapper.find("[data-testid=all-sessions]").exists()).toBe(false);
    expect(wrapper.findComponent({ name: "ConversationsPane" }).exists()).toBe(false);
  });



  it("folds a collection child under its parent by default", async () => {
    const childId = "child-1";
    const parent = { ...provider, conversation_id: "parent-1", title: "Parent", parent_thread_id: null };
    const child = { ...provider, conversation_id: childId, title: "Child", parent_thread_id: "parent-1" };
    const collection: WorkRecordListResult["collections"][number] = {
      ...activeCollection,
      members: [
        { ...member, member_key: "codex:parent-1", conversation_id: "parent-1" },
        { ...member, member_key: "codex:child-1", conversation_id: childId },
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

  it("uses a leading indent so deep member actions stay inside the card", async () => {
    const parent = { ...provider, conversation_id: "parent-1", title: "P".repeat(160), parent_thread_id: null };
    const child = { ...provider, conversation_id: "child-1", title: "C".repeat(160), parent_thread_id: "parent-1" };
    const collection: WorkRecordListResult["collections"][number] = {
      ...activeCollection,
      members: [
        { ...member, member_key: "codex:parent-1", conversation_id: "parent-1" },
        { ...member, member_key: "codex:child-1", conversation_id: "child-1" },
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
    await wrapper.find('[data-testid="member-toggle-codex:parent-1"]').trigger("click");
    const rows = wrapper.findAll(".work-record-members li");
    expect(rows).toHaveLength(2);
    expect(rows[1].attributes("style")).toBeUndefined();
    expect(rows[1].find(".member-tree-indent").attributes("style")).toContain("width: 14px");
  });

  it("folds unfiled child sessions under their parent", async () => {
    const parent = { ...provider, conversation_id: "parent-1", title: "Unfiled Parent", parent_thread_id: null };
    const child = { ...provider, conversation_id: "child-1", title: "Unfiled Child", parent_thread_id: "parent-1" };
    useWorkspaceExplorerStore().conversations = [parent, child];
    vi.mocked(workRecordList).mockResolvedValue({
      ...listResult(),
      collections: [{ ...activeCollection, members: [] }],
      unfiled: [parent, child],
    });
    const wrapper = mount(WorkRecordsView, {
      props: { workspace: "/ws" },
      global: { plugins: [i18n] },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("Unfiled Parent");
    expect(wrapper.text()).not.toContain("Unfiled Child");
    await wrapper.find('[data-testid="unfiled-toggle-codex:parent-1"]').trigger("click");
    expect(wrapper.text()).toContain("Unfiled Child");
  });

  it("resumes a collection member through the conversation preflight chain", async () => {
    const { wrapper } = await mountView();
    await wrapper.find(`[data-testid="resume-${member.member_key}"]`).trigger("click");
    await flushPromises();

    expect(conversationPreflight).toHaveBeenCalledWith("/ws", member.conversation_id, "codex");
    expect(runtimeMock.createTab).toHaveBeenCalledWith("codex", member.conversation_id, false);
  });

  it("renames a collection through an inline editor only after clicking rename", async () => {
    const { wrapper } = await mountView();
    expect(wrapper.find("[data-testid=collection-rename-input]").exists()).toBe(false);
    await wrapper.find("[data-testid=rename-active-1]").trigger("click");
    const input = wrapper.find("[data-testid=collection-rename-input]");
    expect(input.exists()).toBe(true);
    await input.setValue("Renamed record");
    await input.trigger("keydown.enter");
    await flushPromises();
    expect(workRecordRename).toHaveBeenCalledWith("/ws", "active-1", "Renamed record");
  });

  function fakeDataTransfer(initial: Record<string, string> = {}) {
    const data = new Map(Object.entries(initial));
    return {
      effectAllowed: "none",
      setData: vi.fn((type: string, value: string) => data.set(type, value)),
      getData: vi.fn((type: string) => data.get(type) ?? ""),
    };
  }

  it("persists member drag reorder inside a collection", async () => {
    const first = { ...member, member_key: "codex:first", conversation_id: "first" };
    const second = { ...member, member_key: "codex:second", conversation_id: "second" };
    vi.mocked(workRecordList).mockResolvedValue({
      ...listResult(),
      collections: [{ ...activeCollection, members: [first, second] }],
      unfiled: [],
    });
    vi.mocked(workRecordReorderMembers).mockResolvedValue({
      collection: { ...activeCollection, members: [second, first] },
    });
    const wrapper = mount(WorkRecordsView, { props: { workspace: "/ws" }, global: { plugins: [i18n] } });
    await flushPromises();
    const transfer = fakeDataTransfer({
      "application/x-aisc-work-record-member": JSON.stringify({
        collectionId: "active-1",
        memberKey: "codex:first",
        agent: "codex",
        conversationId: "first",
      }),
    });
    await wrapper.find("[data-testid='member-codex:second']").trigger("drop", { dataTransfer: transfer });
    await flushPromises();
    expect(workRecordReorderMembers).toHaveBeenCalledWith("/ws", "active-1", ["codex:second", "codex:first"]);
  });

  it("moves an unfiled conversation into a collection by drag", async () => {
    vi.mocked(workRecordList).mockResolvedValue({
      ...listResult(),
      collections: [{ ...activeCollection, members: [{ ...member, member_key: "codex:target", conversation_id: "target" }] }],
    });
    vi.mocked(workRecordReorderMembers).mockResolvedValue({
      collection: { ...activeCollection, members: [member] },
    });
    vi.mocked(workRecordAddMember).mockResolvedValue({ member });
    const wrapper = mount(WorkRecordsView, { attachTo: document.body, props: { workspace: "/ws" }, global: { plugins: [i18n] } });
    await flushPromises();
    const transfer = fakeDataTransfer({
      "application/x-aisc-work-record-member": JSON.stringify({
        collectionId: null,
        memberKey: member.member_key,
        agent: "codex",
        conversationId: member.conversation_id,
      }),
    });
    await wrapper.find("[data-testid='member-codex:target']").trigger("drop", { dataTransfer: transfer });
    await flushPromises();
    expect(workRecordMoveMember).not.toHaveBeenCalled();
    expect(workRecordReorderMembers).toHaveBeenCalledWith("/ws", "active-1", [member.member_key, "codex:target"]);
  });

  it("persists collection drag reorder", async () => {
    vi.mocked(workRecordReorderCollections).mockResolvedValue({
      collections: [archivedCollection, activeCollection],
    });
    const wrapper = mount(WorkRecordsView, {
      props: { workspace: "/ws" },
      global: { plugins: [i18n] },
    });
    await flushPromises();
    await wrapper.find("[data-testid=show-archived]").setValue(true);
    const transfer = fakeDataTransfer({
      "application/x-aisc-work-record-collection": "active-1",
    });
    await wrapper.find("[data-id=archived-1]").trigger("drop", { dataTransfer: transfer });
    await flushPromises();
    expect(workRecordReorderCollections).toHaveBeenCalledWith("/ws", ["archived-1", "active-1"]);
  });

  it("offers move targets from a member context menu", async () => {
    const explorer = useWorkspaceExplorerStore();
    explorer.workspace = "/ws";
    explorer.conversations = [provider];
    vi.mocked(conversationList).mockResolvedValue({ schema_version: 1, conversations: [provider] });
    const wrapper = mount(WorkRecordsView, {
      props: { workspace: "/ws" },
      global: { plugins: [i18n], stubs: { teleport: true } },
    });
    await flushPromises();
    await wrapper.find(`[data-testid="unfiled-${provider.agent}:${provider.conversation_id}"]`).trigger("contextmenu", { clientX: 20, clientY: 30 });
    await flushPromises();
    const menu = wrapper.find("[data-testid=work-record-context-menu]");
    expect(menu.exists()).toBe(true);
    expect(menu.text()).toContain("恢复");
    expect(menu.text()).toContain("移入 Feature");
  });

  it("removes the ledger member automatically after context-menu delete", async () => {
    const explorer = useWorkspaceExplorerStore();
    explorer.workspace = "/ws";
    explorer.conversations = [provider];
    const wrapper = mount(WorkRecordsView, {
      props: { workspace: "/ws" },
      global: { plugins: [i18n], stubs: { Teleport: { template: '<div><slot /></div>' } } },
    });
    await flushPromises();
    vi.mocked(conversationDelete).mockResolvedValue({ deleted: true, conversation_id: conversationId, agent: "codex" });
    await wrapper.find(`[data-testid="member-${member.member_key}"]`).trigger("contextmenu", { clientX: 10, clientY: 10 });
    await flushPromises();
    const menu = wrapper.find("[data-testid=work-record-context-menu]");
    expect(menu.exists()).toBe(true);
    const del = menu.findAll("button").find((b) => b.text() === "删除")!;
    await del.trigger("click");
    await flushPromises();
    expect(conversationDelete).toHaveBeenCalled();
    expect(workRecordRemoveMember).toHaveBeenCalledWith("/ws", "active-1", "codex", conversationId);
    expect(workRecordList).toHaveBeenCalledTimes(2); // initial load + joined refresh after member removal
  });

  it("keeps long member rows bounded by the work record card", async () => {
    const source = componentSource;
    expect(source).toContain(".work-record {");
    expect(source).toContain("max-width:100%;");
    expect(source).toContain(".work-record-members, .work-record-failures ul {");
    expect(source).toContain("grid-template-columns:minmax(0,1fr);");
    expect(source).toContain(".work-record-members li, .unfiled-row {");
    expect(source).toContain("min-width:0;");
    expect(source).toContain(".member-title {");
    expect(source).toContain("overflow:hidden;");
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
  });
});
