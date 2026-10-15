/**
 * b8 R3: build presentation rows for provider conversations while keeping
 * the source data flat. Codex subagents are separate conversations and carry
 * `parent_thread_id`; Claude sidechains live inside one transcript. Missing
 * parents are promoted to roots so collection/filter views remain useful.
 */
import type { ConversationSummary } from "../../types";

export interface ConversationTreeRow {
  conversation: ConversationSummary;
  depth: number;
  /** Immediate child count (not the whole subtree). */
  childCount: number;
}

const keyOf = (conversation: ConversationSummary): string =>
  conversation.conversation_id.toLowerCase();

export function buildConversationTreeRows(
  items: ConversationSummary[],
  matches?: (conversation: ConversationSummary) => boolean,
): ConversationTreeRow[] {
  const byId = new Map(items.map((item) => [keyOf(item), item] as const));
  const children = new Map<string, ConversationSummary[]>();
  for (const item of items) {
    const parent: ConversationSummary | undefined = item.parent_thread_id ? byId.get(item.parent_thread_id.toLowerCase()) : undefined;
    const key = parent ? keyOf(parent) : "";
    const bucket = children.get(key) ?? [];
    bucket.push(item);
    children.set(key, bucket);
  }

  // Search keeps the ancestor path visible: a child hit must not become an
  // orphan merely because its parent title did not match.
  let visible: Set<ConversationSummary> | null = null;
  if (matches) {
    visible = new Set();
    const addAncestors = (item: ConversationSummary): void => {
      const seen = new Set<string>();
      let cursor: ConversationSummary | undefined = item;
      while (cursor && !seen.has(keyOf(cursor))) {
        seen.add(keyOf(cursor));
        visible!.add(cursor);
        const parent: ConversationSummary | undefined = cursor.parent_thread_id
          ? byId.get(cursor.parent_thread_id.toLowerCase())
          : undefined;
        cursor = parent;
      }
    };
    for (const item of items) if (matches(item)) addAncestors(item);
  }

  const selected = (item: ConversationSummary): boolean => visible?.has(item) ?? true;
  const rows: ConversationTreeRow[] = [];
  const visit = (parentKey: string, depth: number, stack: Set<string>): void => {
    for (const item of children.get(parentKey) ?? []) {
      if (!selected(item) || stack.has(keyOf(item))) continue;
      const childItems = children.get(keyOf(item)) ?? [];
      rows.push({ conversation: item, depth, childCount: childItems.length });
      visit(keyOf(item), depth + 1, new Set([...stack, keyOf(item)]));
    }
  };
  visit("", 0, new Set());
  return rows;
}
