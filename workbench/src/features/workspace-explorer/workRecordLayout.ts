import type { ConversationSummary, WorkRecordCollection, WorkRecordMember } from '../../types';

export interface MemberTreeRow {
  member: WorkRecordMember;
  depth: number;
  childCount: number;
  parentKey: string | null;
}

export function memberRows(collection: WorkRecordCollection, conversations: Map<string, ConversationSummary>): MemberTreeRow[] {
  const byId = new Map(collection.members.map((member) => [member.conversation_id.toLowerCase(), member]));
  const children = new Map<string, WorkRecordMember[]>();
  for (const member of collection.members) {
    const conversation = conversations.get(member.agent + ":" + member.conversation_id.toLowerCase());
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
