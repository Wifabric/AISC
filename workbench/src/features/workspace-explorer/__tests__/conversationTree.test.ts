/**
 * b8 R3 acceptance: flat provider data becomes a parent-first tree; filter
 * matches retain their ancestor path and orphaned children become roots.
 */
import { describe, expect, it } from "vitest";
import { buildConversationTreeRows } from "../conversationTree";
import type { ConversationSummary } from "../../../types";

function conversation(
  id: string,
  parentThreadId: string | null = null,
  title = id,
): ConversationSummary {
  return {
    conversation_id: id,
    agent: "codex",
    title,
    started_at: null,
    last_at: id,
    message_count: 1,
    file_size: 10,
    resumable: true,
    parent_thread_id: parentThreadId,
  };
}

describe("conversation tree rows", () => {
  it("nests codex child sessions below their parent and counts immediate children", () => {
    const rows = buildConversationTreeRows([
      conversation("child-1", "parent"),
      conversation("parent"),
      conversation("child-2", "PARENT"),
    ]);
    expect(rows.map((row) => [row.conversation.conversation_id, row.depth, row.childCount])).toEqual([
      ["parent", 0, 2],
      ["child-1", 1, 0],
      ["child-2", 1, 0],
    ]);
  });

  it("promotes a child whose parent is absent from the loaded list", () => {
    const rows = buildConversationTreeRows([conversation("orphan", "missing")]);
    expect(rows.map((row) => [row.conversation.conversation_id, row.depth])).toEqual([["orphan", 0]]);
  });

  it("keeps a matching child under its ancestor and excludes unrelated non-matches", () => {
    const rows = buildConversationTreeRows(
      [conversation("parent", null, "root"), conversation("child", "parent", "needle"), conversation("other", null, "other")],
      (item) => item.title.includes("needle"),
    );
    expect(rows.map((row) => [row.conversation.conversation_id, row.depth])).toEqual([
      ["parent", 0],
      ["child", 1],
    ]);
  });
});
