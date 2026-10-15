/**
 * v2.1.15 b6 Task 5 — Work Record Pinia store behavior.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useWorkRecordsStore } from "../workRecords";
import {
  workRecordAddMember,
  workRecordArchive,
  workRecordCreate,
  workRecordDelete,
  workRecordList,
  workRecordMoveMember,
  workRecordRemoveMember,
  workRecordRename,
  workRecordRestore,
} from "../../lib/ipc";
import type { WorkRecordListResult } from "../../types";

vi.mock("../../lib/ipc", () => ({
  workRecordList: vi.fn(),
  workRecordCreate: vi.fn(),
  workRecordRename: vi.fn(),
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

const member = {
  member_key: "codex:01a04ca9-d3f6-7021-b9e7-50d48d818c65",
  agent: "codex" as const,
  conversation_id: "01a04ca9-d3f6-7021-b9e7-50d48d818c65",
  runtime_id: null,
  source: "manual" as const,
  added_at: "2026-01-01T00:00:00Z",
};

const collection = {
  id: "collection-1",
  title: "Feature",
  status: "active" as const,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  archived_at: null,
  members: [],
};

const provider = {
  conversation_id: "01a04ca9-d3f6-7021-b9e7-50d48d818c65",
  agent: "codex" as const,
  title: "Provider",
  started_at: null,
  last_at: null,
  message_count: 1,
  file_size: 12,
  resumable: true,
};

function listResult(): WorkRecordListResult {
  return {
    schema_version: "aisc.work-collections/v1",
    active_collection_id: "collection-1",
    collections: [{ ...collection, members: [member] }],
    unfiled: [provider],
  };
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  vi.mocked(workRecordList).mockResolvedValue(listResult());
});

describe("workRecords store", () => {
  it("loads collections and joined unfiled conversations", async () => {
    const s = useWorkRecordsStore();
    await s.load("/ws");
    expect(workRecordList).toHaveBeenCalledWith("/ws");
    expect(s.workspace).toBe("/ws");
    expect(s.collections).toHaveLength(1);
    expect(s.unfiled).toEqual([provider]);
    expect(s.byId("collection-1")?.members).toEqual([member]);
    expect(s.error).toBeNull();
  });

  it("performs collection CRUD without optimistic mutation", async () => {
    const s = useWorkRecordsStore();
    await s.load("/ws");
    vi.mocked(workRecordCreate).mockResolvedValue({ collection });
    const created = await s.create("Feature");
    expect(created?.id).toBe("collection-1");
    expect(workRecordCreate).toHaveBeenCalledWith("/ws", "Feature");

    vi.mocked(workRecordRename).mockResolvedValue({
      collection: { ...collection, title: "Renamed" },
    });
    await s.rename("collection-1", "Renamed");
    expect(s.byId("collection-1")?.title).toBe("Renamed");

    vi.mocked(workRecordArchive).mockResolvedValue({
      collection: { ...collection, status: "archived", archived_at: "t" },
    });
    await s.archive("collection-1");
    expect(s.byId("collection-1")?.status).toBe("archived");

    vi.mocked(workRecordRestore).mockResolvedValue({ collection });
    await s.restore("collection-1");
    expect(s.byId("collection-1")?.status).toBe("active");
  });

  it("adds and removes members and updates unfiled", async () => {
    const s = useWorkRecordsStore();
    await s.load("/ws");
    vi.mocked(workRecordAddMember).mockResolvedValue({ member });
    const added = await s.addMember(
      "collection-1", "codex", "01a04ca9-d3f6-7021-b9e7-50d48d818c65",
    );
    expect(added?.member_key).toBe(member.member_key);
    expect(s.byId("collection-1")?.members).toContainEqual(member);
    expect(s.unfiled).toHaveLength(0);

    vi.mocked(workRecordRemoveMember).mockResolvedValue({ removed: true, member_key: member.member_key });
    await s.removeMember(
      "collection-1", "codex", "01a04ca9-d3f6-7021-b9e7-50d48d818c65",
    );
    expect(s.byId("collection-1")?.members).toHaveLength(0);
  });

  it("moves atomically and reloads the joined view", async () => {
    const s = useWorkRecordsStore();
    await s.load("/ws");
    vi.mocked(workRecordMoveMember).mockResolvedValue({
      member,
      member_key: member.member_key,
      collection_id: "collection-2",
    });
    const moved = await s.moveMember(
      "collection-1", "collection-2", "codex",
      "01a04ca9-d3f6-7021-b9e7-50d48d818c65",
      [member.member_key],
    );
    expect(moved).toBe(true);
    expect(workRecordMoveMember).toHaveBeenCalledWith(
      "/ws", "collection-1", member.member_key, "collection-2", [member.member_key],
    );
    expect(workRecordList).toHaveBeenLastCalledWith("/ws");
  });

  it("records successful and partial delete outcomes", async () => {
    const s = useWorkRecordsStore();
    await s.load("/ws");
    vi.mocked(workRecordDelete).mockResolvedValue({
      deleted: true,
      collection_id: "collection-1",
      terminated_session_ids: ["session-1"],
      deleted_members: [member],
      failed_members: [],
    });
    const result = await s.delete("collection-1");
    expect(result?.failed_members).toHaveLength(0);
    expect(s.collections).toHaveLength(0);
    expect(s.lastDeleteFailure).toBeNull();

    await s.load("/ws");
    vi.mocked(workRecordDelete).mockResolvedValue({
      deleted: true,
      collection_id: "collection-1",
      terminated_session_ids: [],
      deleted_members: [],
      failed_members: [{ ...member, stage: "delete", reason: "locked" }],
    });
    const partial = await s.delete("collection-1");
    expect(partial?.failed_members).toHaveLength(1);
    expect(s.lastDeleteFailure?.failed_members).toHaveLength(1);
    expect(s.collections).toHaveLength(0);
  });

  it("clears state when workspace changes", async () => {
    const s = useWorkRecordsStore();
    await s.load("/ws");
    s.setWorkspace("/other");
    expect(s.collections).toEqual([]);
    expect(s.unfiled).toEqual([]);
    expect(s.lastDeleteFailure).toBeNull();
  });
});
