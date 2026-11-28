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
import type { LaunchAgent } from "../../types";
import SessionLaunchMenu from "../workspace/SessionLaunchMenu.vue";
import { memberRows, type MemberTreeRow } from './workRecordLayout';
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
const sessionLaunchError = ref<string | null>(null);
const sessionMenu = ref<{ anchor: HTMLElement; collectionId: string } | null>(null);
watch(() => props.workspace, () => { sessionMenu.value = null; });
const deleteDialog = ref<HTMLDialogElement | null>(null);
const pendingDelete = ref<{
  kind: "collection" | "conversation";
  message: string;
  collectionId?: string;
  conversation?: ConversationSummary;
  /** b2 (反馈 #11): same-agent + same-title conversations to cascade-delete. */
  conversations?: ConversationSummary[];
} | null>(null);
/** 2.2.0 b5 / U-1: unsubscribe handle for the runtime's session push. */
let stopSessionPush: (() => void) | null = null;

const contextMenu = ref<{
  x: number;
  y: number;
  collectionId: string | null;
  memberKey: string;
  collectionOnly: boolean;
} | null>(null);

const visibleCollections = computed(() =>
  showArchived.value ? records.collections : records.collections.filter((item) => item.status === "active"),
);
const conversationBy = computed(() => {
  const out = new Map<string, ConversationSummary>();
  for (const item of [...records.conversations, ...explorer.conversations]) {
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
    records.byId(id)?.members ?? [],
  );
  await records.delete(id);
  await explorer.loadConversations(true);
}


async function refreshWorkRecords() {
  await Promise.all([records.reload(), explorer.loadConversations(true)]);
  await runtime.resolvePendingConversationAssociations(explorer.conversations);
}

/** b17 (T5): import a local Markdown work record as a new unfiled
 *  conversation. The file dialog lives in the Rust command; a cancel is a
 *  no-op. */
async function importMarkdown() {
  if (!props.workspace) return;
  await records.importMarkdown(props.workspace);
}

async function removeMember(id: string, agent: "claude" | "codex", conversationId: string) {
  const removed = await records.removeMember(id, agent, conversationId);
  if (removed) await records.reload();
}

async function resumeMember(memberKey: string) {
  const item = memberConversation(memberKey);
  if (item?.resumable) await explorer.resumeConversation(item);
}

// b2 (反馈 #11) 左键预览: open the read-only transcript viewer. This is
// viewing only — resume stays an explicit per-row action.
function previewConversation(item: ConversationSummary | null): void {
  if (item) explorer.openConversationViewer(item.agent, item.conversation_id, item.title);
}
function previewMember(memberKey: string): void {
  previewConversation(memberConversation(memberKey));
}

async function exportFromMenu() {
  const item = menuConversation();
  closeMenu();
  if (!item) return;
  try { await explorer.exportConversation(item.agent, item.conversation_id, item.title); }
  catch (cause) { sessionLaunchError.value = (cause as Error)?.message || String(cause); }
}

watch(pendingDelete, async (pending) => {
  if (pending) {
    await nextTick();
    deleteDialog.value?.showModal?.();
  }
});
watch(() => props.workspace, () => { pendingDelete.value = null; });
// b2 (反馈 #11): while the provider conversation list is loading, a member row
// must show a loading placeholder — never flash "missing reference" before the
// lookup data has actually arrived.
function memberTitle(memberKey: string): string {
  if (explorer.conversationsLoading) return t("explorer.loading");
  return memberConversation(memberKey)?.title || t("workRecords.missing");
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
  // b2 (反馈 #11): deleting a session deletes every same-titled session of the
  // same agent — including rows currently folded away or filtered out. A
  // cross-agent title collision must NOT be cascaded.
  const title = (item.title || "").trim();
  const matches = explorer.conversations.filter(
    (candidate) => candidate.agent === item.agent && (candidate.title || "").trim() === title,
  );
  const conversations = matches.some((candidate) => candidate.conversation_id === item.conversation_id)
    ? matches
    : [...matches, item];
  const ids = new Set(conversations.map(c => c.conversation_id.toLowerCase()));
  const children = new Map<string, ConversationSummary[]>();
  for (const c of explorer.conversations) {
    if (c.agent !== item.agent || !c.parent_thread_id) continue;
    const parent = c.parent_thread_id.toLowerCase();
    if (!children.has(parent)) children.set(parent, []);
    children.get(parent)!.push(c);
  }
  for (const c of conversations) {
    for (const child of children.get(c.conversation_id.toLowerCase()) ?? []) {
      const id = child.conversation_id.toLowerCase();
      if (!ids.has(id)) {
        ids.add(id);
        conversations.push(child);
      }
    }
  }
  pendingDelete.value = {
    kind: "conversation",
    collectionId: collectionId ?? undefined,
    conversation: item,
    conversations,
    message: t("workRecords.deleteConversationConfirm", { title: item.title, count: conversations.length }),
  };
}

async function performConversationDelete(conversations: ConversationSummary[]) {
  for (const item of conversations) {
    await explorer.deleteConversation(item);
    const id = item.conversation_id.toLowerCase();
    for (const collection of records.collections) {
      if (collection.members.some((m) => m.agent === item.agent && m.conversation_id.toLowerCase() === id)) {
        await records.removeMember(collection.id, item.agent, item.conversation_id);
      }
    }
  }
  await records.reload();
}

async function confirmQuietDelete() {
  const pending = pendingDelete.value;
  pendingDelete.value = null;
  if (!pending) return;
  if (pending.kind === "collection" && pending.collectionId) {
    sessionLaunchError.value = null;
    try { await performCollectionDelete(pending.collectionId); }
    catch (e) { sessionLaunchError.value = (e as Error)?.message || String(e); }
  } else if (pending.conversation) {
    await performConversationDelete(pending.conversations ?? [pending.conversation]);
  }
}


function memberTree(collection: WorkRecordCollection) {
  return memberRows(collection, conversationBy.value);
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

interface DragMemberEntry {
  memberKey: string;
  agent: "claude" | "codex";
  conversationId: string;
}
interface DragMemberPayload extends DragMemberEntry {
  collectionId: string | null;
  /** b2 (反馈 #11): dragged subtree in source order (the dragged row first). */
  subtree: DragMemberEntry[];
}
function setMemberDrag(event: DragEvent, payload: DragMemberPayload) {
  event.dataTransfer?.setData("application/x-aisc-work-record-member", JSON.stringify(payload));
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
}
/** Contiguous rows strictly deeper than the dragged row form its subtree. */
function subtreeKeysFrom<T extends { depth: number }>(rows: T[], keyOf: (row: T) => string, draggedKey: string): string[] {
  const startIndex = rows.findIndex((row) => keyOf(row) === draggedKey);
  if (startIndex < 0) return [draggedKey];
  const startDepth = rows[startIndex].depth;
  const keys = [draggedKey];
  for (let index = startIndex + 1; index < rows.length; index++) {
    if (rows[index].depth <= startDepth) break;
    keys.push(keyOf(rows[index]));
  }
  return keys;
}
function buildMemberDragSubtree(collectionId: string, memberKey: string): string[] {
  const collection = records.byId(collectionId);
  return collection ? subtreeKeysFrom(memberTree(collection), (row) => row.member.member_key, memberKey) : [memberKey];
}
function collectionEntries(collection: WorkRecordCollection, keys: string[]): DragMemberEntry[] {
  const byKey = new Map(collection.members.map((member) => [member.member_key, member] as const));
  return keys.flatMap((key) => {
    const member = byKey.get(key);
    return member ? [{ memberKey: key, agent: member.agent, conversationId: member.conversation_id }] : [];
  });
}
function memberDragStart(event: DragEvent, collectionId: string, member: WorkRecordMember) {
  const collection = records.byId(collectionId);
  const keys = buildMemberDragSubtree(collectionId, member.member_key);
  const subtree = collection
    ? collectionEntries(collection, keys)
    : [{ memberKey: member.member_key, agent: member.agent, conversationId: member.conversation_id }];
  setMemberDrag(event, { collectionId, memberKey: member.member_key, agent: member.agent, conversationId: member.conversation_id, subtree });
}
function unfiledDragStart(event: DragEvent, item: ConversationSummary) {
  const key = unfiledKey(item);
  const keys = subtreeKeysFrom(unfiledTreeRows.value, (row) => unfiledKey(row.conversation), key);
  const byKey = new Map(records.unfiled.map((entry) => [unfiledKey(entry), entry] as const));
  const subtree: DragMemberEntry[] = keys.flatMap((entryKey) => {
    const entry = byKey.get(entryKey);
    return entry ? [{ memberKey: entryKey, agent: entry.agent, conversationId: entry.conversation_id }] : [];
  });
  setMemberDrag(event, { collectionId: null, memberKey: key, agent: item.agent, conversationId: item.conversation_id, subtree });
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
async function dropMember(event: DragEvent, targetCollectionId: string | null, targetMemberKey?: string) {
  event.preventDefault();
  event.stopPropagation();
  const source = draggedMember(event);
  if (source) await moveSubtree(source, targetCollectionId, targetMemberKey);
}
async function moveSubtree(source: DragMemberPayload, targetCollectionId: string | null, targetMemberKey?: string) {
  // b2 (反馈 #11): moving a parent moves its whole subtree, in source order.
  const moving = source.subtree?.length
    ? source.subtree
    : [{ memberKey: source.memberKey, agent: source.agent, conversationId: source.conversationId }];
  const movingKeys = moving.map((entry) => entry.memberKey);
  // Dropping onto a member of the dragged subtree is a no-op (the anchor would
  // disappear with the move itself).
  if (targetMemberKey && targetMemberKey !== source.memberKey && movingKeys.includes(targetMemberKey)) return;
  const original = areaKeys(targetCollectionId);
  const area = original.filter((key) => !movingKeys.includes(key));
  const anchor = targetMemberKey && targetMemberKey !== source.memberKey ? targetMemberKey : null;
  // Drop-on-row keeps the historical orderWithKey semantics: the dragged
  // subtree takes the target's ORIGINAL slot (the target shifts after it).
  const anchorIndex = anchor ? original.indexOf(anchor) : original.length;
  area.splice(Math.min(anchorIndex, area.length), 0, ...movingKeys);
  if (source.collectionId === targetCollectionId) {
    if (targetCollectionId === null) await records.reorderUnfiled(area);
    else await records.reorderMembers(targetCollectionId, area);
    return;
  }
  for (const entry of moving) {
    if (source.collectionId === null) {
      if (!await records.addMember(targetCollectionId!, entry.agent, entry.conversationId)) return;
    } else {
      const order = moving.length === 1 ? area : undefined;
      if (!await records.moveMember(source.collectionId, targetCollectionId, entry.agent, entry.conversationId, order)) return;
    }
  }
  if (targetCollectionId === null) await records.reorderUnfiled(area);
  else await records.reorderMembers(targetCollectionId, area);
}
function collectionDragStart(event: DragEvent, collection: WorkRecordCollection) {
  event.dataTransfer?.setData("application/x-aisc-work-record-collection", collection.id);
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
}
async function dropCollection(event: DragEvent, targetId: string) {
  event.preventDefault();
  event.stopPropagation();
  const sourceId = event.dataTransfer?.getData("application/x-aisc-work-record-collection");
  if (!sourceId) {
    await dropMember(event, targetId);
    return;
  }
  if (sourceId === targetId) return;
  const ids = records.collections.map((item) => item.id);
  const from = ids.indexOf(sourceId);
  const to = ids.indexOf(targetId);
  if (from < 0 || to < 0) return;
  ids.splice(to, 0, ...ids.splice(from, 1));
  await records.reorderCollections(ids);
}
const menuEl = ref<HTMLElement | null>(null);
const submenuEl = ref<HTMLElement | null>(null);
const submenuTrigger = ref<HTMLButtonElement | null>(null);
const menuPosition = ref({ x: 0, y: 0 });
const submenuPosition = ref({ x: 0, y: 0 });
const submenuWidth = ref<number | null>(null);
let submenuSide: "left" | "right" = "right";
const menuReady = ref(false);
const submenuReady = ref(false);
const moveSubOpen = ref(false);
let menuOrigin: HTMLElement | null = null;
let menuResizeObserver: ResizeObserver | undefined;
const viewport = ref(readMenuViewport());

function readMenuViewport() {
  const view = window.visualViewport;
  return { x: view?.offsetLeft ?? 0, y: view?.offsetTop ?? 0,
    width: view?.width ?? window.innerWidth, height: view?.height ?? window.innerHeight };
}
const menuLimits = computed(() => ({
  minWidth: `${Math.min(160, Math.max(0, viewport.value.width - 16))}px`,
  maxWidth: `${Math.max(0, viewport.value.width - 16)}px`,
  maxHeight: `${Math.max(0, viewport.value.height - 16)}px`,
}));
const submenuLimits = computed(() => ({
  ...menuLimits.value,
  ...(submenuWidth.value === null ? {} : {
    minWidth: `${Math.min(160, submenuWidth.value)}px`,
    maxWidth: `${submenuWidth.value}px`,
  }),
}));
function boundedPosition(x: number, y: number, width: number, height: number) {
  const view = viewport.value;
  const left = view.x + 8, top = view.y + 8;
  return {
    x: Math.max(left, Math.min(x, view.x + view.width - 8 - width)),
    y: Math.max(top, Math.min(y, view.y + view.height - 8 - height)),
  };
}
function measuredSize(el: HTMLElement) {
  const rect = el.getBoundingClientRect();
  return { width: Math.min(rect.width, Math.max(0, viewport.value.width - 16)),
    height: Math.min(rect.height, Math.max(0, viewport.value.height - 16)) };
}
function placeMenus() {
  const menu = contextMenu.value;
  if (!menu || !menuEl.value) return;
  // Both menus are teleported outside .app's CSS zoom: all measurements and
  // pointer coordinates are viewport CSS pixels, with no appZoom division.
  const view = viewport.value;
  const { width, height } = measuredSize(menuEl.value);
  menuPosition.value = boundedPosition(
    menu.x + width > view.x + view.width - 8 ? menu.x - width : menu.x,
    menu.y + height > view.y + view.height - 8 ? menu.y - height : menu.y,
    width, height,
  );
  menuReady.value = true;
  if (moveSubOpen.value) void nextTick(placeSubmenu);
}
async function placeSubmenu() {
  if (!contextMenu.value || !moveSubOpen.value || !submenuEl.value || !submenuTrigger.value) return;
  const menu = contextMenu.value;
  const anchor = submenuTrigger.value.getBoundingClientRect();
  const view = viewport.value;
  const rightSpace = Math.max(0, view.x + view.width - 8 - anchor.right);
  const leftSpace = Math.max(0, anchor.left - view.x - 8);
  if (submenuWidth.value === null) {
    const naturalWidth = measuredSize(submenuEl.value).width;
    submenuSide = naturalWidth <= rightSpace ? "right" : naturalWidth <= leftSpace ? "left"
      : rightSpace >= leftSpace ? "right" : "left";
  }
  // Never cover the trigger on hover: that can turn the subsequent click
  // into a move to whichever destination appeared under the pointer.
  submenuWidth.value = submenuSide === "right" ? rightSpace : leftSpace;
  await nextTick();
  if (contextMenu.value !== menu || !moveSubOpen.value || !submenuEl.value) return;
  const { width, height } = measuredSize(submenuEl.value);
  submenuPosition.value = boundedPosition(
    submenuSide === "right" ? anchor.right : anchor.left - width,
    anchor.top, width, height,
  );
  submenuReady.value = true;
}
async function openMoveSubmenu(focus = false) {
  const menu = contextMenu.value;
  if (!menu) return;
  moveSubOpen.value = true;
  submenuReady.value = false;
  submenuWidth.value = null;
  await nextTick();
  if (contextMenu.value !== menu || !moveSubOpen.value) return;
  await placeSubmenu();
  // Focus only after Vue has applied the visible, measured placement.
  await nextTick();
  if (contextMenu.value !== menu || !moveSubOpen.value) return;
  if (focus) submenuEl.value?.querySelector<HTMLButtonElement>("button:not(:disabled)")?.focus();
}
function leaveMoveSubmenu(event: MouseEvent) {
  const target = event.relatedTarget;
  if (target instanceof Node && (submenuEl.value?.contains(target) || submenuTrigger.value?.contains(target))) return;
  moveSubOpen.value = false;
}
async function openMemberMenu(event: MouseEvent | KeyboardEvent, collectionId: string | null, member: WorkRecordMember | null, item: ConversationSummary | null, collectionOnly = false) {
  event.preventDefault();
  if (!item && !collectionOnly) { closeMenu(); return; }
  menuOrigin = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
  const anchor = menuOrigin?.getBoundingClientRect();
  moveSubOpen.value = false;
  menuReady.value = false;
  viewport.value = readMenuViewport();
  contextMenu.value = {
    x: "clientX" in event ? event.clientX : anchor?.left ?? 8,
    y: "clientY" in event ? event.clientY : anchor?.bottom ?? 8,
    collectionId,
    memberKey: member?.member_key ?? (item ? unfiledKey(item) : ""),
    collectionOnly,
  };
  const menu = contextMenu.value;
  await nextTick();
  if (contextMenu.value !== menu) return;
  placeMenus();
  await nextTick();
  if (contextMenu.value !== menu) return;
  menuEl.value?.querySelector<HTMLButtonElement>("button:not(:disabled)")?.focus({ preventScroll: true });
}
function closeMenu(restoreFocus = false) {
  const origin = menuOrigin;
  contextMenu.value = null;
  moveSubOpen.value = false;
  menuOrigin = null;
  if (restoreFocus && origin?.isConnected) origin.focus({ preventScroll: true });
}
function deleteMenuCollection() {
  const id = contextMenu.value?.collectionId;
  const collection = id && records.byId(id);
  closeMenu(true);
  if (collection) requestCollectionDelete(collection.id, collection.title);
}
function isMenuTarget(target: EventTarget | null) {
  return target instanceof Node && !!(menuEl.value?.contains(target) || submenuEl.value?.contains(target));
}
function onOutsideMenu(event: Event) {
  if (contextMenu.value && !isMenuTarget(event.target)) closeMenu();
}
function onMenuViewportChange() {
  if (contextMenu.value) closeMenu(isMenuTarget(document.activeElement));
}
function onMenuScroll(event: Event) {
  if (!contextMenu.value) return;
  if (isMenuTarget(event.target)) {
    if (event.target instanceof Node && menuEl.value?.contains(event.target)) {
      if (submenuEl.value?.contains(document.activeElement)) submenuTrigger.value?.focus({ preventScroll: true });
      moveSubOpen.value = false;
    }
    return;
  }
  onMenuViewportChange();
}
function onMenuKeydown(event: KeyboardEvent) {
  if (!contextMenu.value) return;
  if (event.key === "Escape") {
    event.preventDefault(); event.stopPropagation(); closeMenu(true); return;
  }
  if (!isMenuTarget(event.target)) return;
  if (event.key === "Tab") { closeMenu(true); return; }
  if (event.key === "ArrowRight" && event.target === submenuTrigger.value) {
    event.preventDefault(); void openMoveSubmenu(true); return;
  }
  if (event.key === "ArrowLeft" && moveSubOpen.value) {
    event.preventDefault(); moveSubOpen.value = false; submenuTrigger.value?.focus(); return;
  }
  if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
  const parent = submenuEl.value?.contains(event.target as Node) ? submenuEl.value : menuEl.value;
  const buttons = Array.from(parent?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)") ?? []);
  if (!buttons.length) return;
  event.preventDefault();
  const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
  const next = event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1
    : (index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length;
  buttons[next]?.focus();
}
function onMemberMenuKey(event: KeyboardEvent, collectionId: string | null, member: WorkRecordMember | null, item: ConversationSummary | null) {
  if (event.key === "ContextMenu" || (event.key === "F10" && event.shiftKey)) {
    event.stopPropagation(); void openMemberMenu(event, collectionId, member, item);
  }
}
function menuConversation(): ConversationSummary | null {
  return contextMenu.value ? memberConversation(contextMenu.value.memberKey) : null;
}
// b5 (反馈 #7/#8): a Work Record launch is tracked; launch failure closes only
// the new label and preserves the readable error for recovery.
async function createSessionInRecord(agent: LaunchAgent | "topics", directory: string): Promise<void> {
  const menu = sessionMenu.value;
  sessionMenu.value = null;
  if (!menu || !records.byId(menu.collectionId)) return;
  if (agent === "topics") { runtime.openTopicsTab({ collectionId: menu.collectionId, directory }); return; }
  sessionLaunchError.value = null;
  const result = await runtime.createTrackedTab(agent, menu.collectionId, directory || undefined);
  if (result.error) {
    sessionLaunchError.value = result.error === "tab-limit"
      ? t("history.viewer.tabLimit")
      : result.error === "provider-not-configured"
        ? t("workRecords.providerNotConfigured")
        : result.error;
  }
  await refreshWorkRecords();
}

// b5 (反馈 #7): context-menu /new remains scoped to the same Work Record.
async function forkSessionFromMenu(): Promise<void> {
  const item = menuConversation();
  closeMenu();
  if (!item) return;
  sessionLaunchError.value = null;
  const created = await explorer.resumeConversation(item, true);
  if (!created) return;
  const result = await runtime.waitForTabSession(runtime.lastCreatedTabId ?? null);
  if (result.error && result.tabId) {
    sessionLaunchError.value = result.error;
    await runtime.removeTab(result.tabId);
  }
  await refreshWorkRecords();
}
defineExpose({ buildMemberDragSubtree });
watch(() => records.revealKey, async key => {
  if (!key) return;
  const collection = records.collections.find(c => c.members.some(m => m.member_key === key));
  if (collection?.status === "archived") showArchived.value = true;
  if (collection) collapsedCollections.value.delete(collection.id);
  else unfiledExpanded.value = true;
  const expanded = collection ? expandedMembers.value : expandedUnfiled.value;
  const visited = new Set<string>();
  let c = conversationBy.value.get(key) ?? records.unfiled.find(c => unfiledKey(c) === key);
  while (c?.parent_thread_id && !visited.has(c.parent_thread_id)) {
    visited.add(c.parent_thread_id);
    expanded.add(c.parent_thread_id.toLowerCase());
    c = conversationBy.value.get(c.agent + ":" + c.parent_thread_id.toLowerCase());
  }
  await nextTick();
  const row = document.querySelector<HTMLElement>(`[data-record-key="${CSS.escape(key)}"]`);
  row?.focus();
  row?.scrollIntoView?.({ block: "nearest" });
  records.revealKey = "";
}, { immediate: true });
async function moveFromMenu(targetId: string | null) {
  const menu = contextMenu.value;
  if (!menu) return;
  const collection = menu.collectionId ? records.byId(menu.collectionId) : null;
  const keys = collection ? buildMemberDragSubtree(collection.id, menu.memberKey)
    : subtreeKeysFrom(unfiledTreeRows.value, row => unfiledKey(row.conversation), menu.memberKey);
  const subtree = collection ? collectionEntries(collection, keys) : keys.flatMap(key => {
    const c = records.unfiled.find(item => unfiledKey(item) === key);
    return c ? [{ memberKey: key, agent: c.agent, conversationId: c.conversation_id }] : [];
  });
  const source = subtree.find(entry => entry.memberKey === menu.memberKey);
  if (source) await moveSubtree({ ...source, collectionId: menu.collectionId, subtree }, targetId);
  if (contextMenu.value === menu) closeMenu();
}

watch(() => explorer.conversations, async (current, old) => {
  if (current.length === old.length && current.every((c, i) =>
    c.conversation_id === old[i].conversation_id && c.agent === old[i].agent)) return;
  await records.reconcile();
  if (records.workspace === props.workspace) await runtime.resolvePendingConversationAssociations(current);
});
onMounted(async () => {
  // 2.2.0 b5 / U-1: real-time push — the runtime announces provider terminal
  // activity; a conversation created in another tab refreshes this panel
  // without the user clicking refresh.
  stopSessionPush = records.onSessionActivity((workspace) => {
    if (workspace === props.workspace) void refreshWorkRecords();
  });
  window.addEventListener("click", onOutsideMenu);
  window.addEventListener("focusin", onOutsideMenu);
  window.addEventListener("keydown", onMenuKeydown);
  window.addEventListener("resize", onMenuViewportChange);
  window.addEventListener("scroll", onMenuScroll, true);
  window.visualViewport?.addEventListener("resize", onMenuViewportChange);
  window.visualViewport?.addEventListener("scroll", onMenuViewportChange);
  if (typeof ResizeObserver !== "undefined") menuResizeObserver = new ResizeObserver(placeMenus);
  if (props.workspace) {
    await Promise.all([records.load(props.workspace), explorer.loadConversations(true)]);
    await runtime.resolvePendingConversationAssociations(explorer.conversations);
  }
});
watch([menuEl, submenuEl], () => {
  menuResizeObserver?.disconnect();
  if (menuEl.value) menuResizeObserver?.observe(menuEl.value);
  if (submenuEl.value) menuResizeObserver?.observe(submenuEl.value);
});
onBeforeUnmount(() => {
  stopSessionPush?.();
  stopSessionPush = null;
  menuResizeObserver?.disconnect();
  window.removeEventListener("click", onOutsideMenu);
  window.removeEventListener("focusin", onOutsideMenu);
  window.removeEventListener("keydown", onMenuKeydown);
  window.removeEventListener("resize", onMenuViewportChange);
  window.removeEventListener("scroll", onMenuScroll, true);
  window.visualViewport?.removeEventListener("resize", onMenuViewportChange);
  window.visualViewport?.removeEventListener("scroll", onMenuViewportChange);
});
watch(() => props.workspace, async (workspace) => {
  closeMenu();
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
    </div>

      <p v-if="records.error" class="explorer-error" role="alert">{{ records.error }}</p>
    <p v-if="sessionLaunchError" class="explorer-error" role="alert" data-testid="work-record-session-error">{{ sessionLaunchError }}</p>

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
        <button
          class="ui-button sm"
          type="button"
          data-testid="import-markdown"
          :title="t('workRecords.importMarkdown')"
          :aria-label="t('workRecords.importMarkdown')"
          @click="importMarkdown"
        >{{ t("workRecords.importMarkdown") }}</button>
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
        <header class="work-record-head" @contextmenu.prevent="openMemberMenu($event, collection.id, null, null, true)"
          @keydown.shift.f10.prevent="openMemberMenu($event, collection.id, null, null, true)">
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
          <h4 v-else class="collection-title" @dblclick="beginCollectionRename(collection)">{{ records.numbers.get(collection.id) }} {{ collection.title }}</h4>
          <span v-if="collection.status === 'archived'" class="work-record-archived">{{ t("workRecords.archived") }}</span>
          <span class="head-actions">
            <button v-if="collection.status === 'active'" class="ui-icon-button sm" type="button" :title="t('workRecords.newSession')" :aria-label="t('workRecords.newSession')" aria-haspopup="menu" :aria-expanded="sessionMenu?.collectionId === collection.id" :data-testid="'new-session-' + collection.id" @click.stop="sessionMenu = sessionMenu?.collectionId === collection.id ? null : { anchor: $event.currentTarget as HTMLElement, collectionId: collection.id }">＋</button>
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
              tabindex="0"
              :data-testid="'member-' + row.member.member_key"
              :data-record-key="row.member.member_key"
              @dragstart="memberDragStart($event, collection.id, row.member)"
              @dragover.prevent
              @drop.stop="dropMember($event, collection.id, row.member.member_key)"
              @click="previewMember(row.member.member_key)"
              @contextmenu.prevent="openMemberMenu($event, collection.id, row.member, memberConversation(row.member.member_key)!)"
              @keydown="onMemberMenuKey($event, collection.id, row.member, memberConversation(row.member.member_key))"
            >
              <span class="member-tree-indent" :class="{ branch: row.depth > 0 }" :style="{ width: (row.depth * 14) + 'px' }" />
              <button v-if="row.childCount" class="conversation-twisty" type="button" :aria-expanded="expandedMembers.has(row.member.conversation_id.toLowerCase())" :aria-label="t('workRecords.tree.toggle')" :data-testid="'member-toggle-' + row.member.member_key" @click.stop="toggleMember(row.member)">
                <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path :d="expandedMembers.has(row.member.conversation_id.toLowerCase()) ? 'M3 4.5 6 8l3-3.5' : 'M4.5 2.5 8 6l-3.5 3.5'" /></svg>
                <span class="conversation-child-count">{{ row.childCount }}</span>
              </button>
              <span v-else class="conversation-twisty spacer" aria-hidden="true" />
              <input v-if="renamingConversationKey === row.member.member_key" v-model="renameValue" class="title-input member-title-input" type="text" data-testid="conversation-rename-input" @click.stop @keydown.enter.prevent="commitConversationRename(memberConversation(row.member.member_key)!)" @keydown.esc.prevent="renamingConversationKey = null" @blur="commitConversationRename(memberConversation(row.member.member_key)!)">
              <span v-else class="member-title">{{ records.numbers.get(row.member.member_key) }} {{ memberTitle(row.member.member_key) }}</span>
              <span class="member-agent">{{ row.member.agent }}</span>
              <button class="ui-icon-button sm" type="button" :data-testid="'resume-' + row.member.member_key" :disabled="!memberConversation(row.member.member_key)?.resumable" :title="t('workRecords.resume')" :aria-label="t('workRecords.resume')" @click.stop="resumeMember(row.member.member_key)">▶</button>
              <button class="ui-icon-button sm" type="button" :title="t('workRecords.rename')" :aria-label="t('workRecords.rename')" @click.stop="beginConversationRename(row.member.member_key)">✎</button>
              <button class="ui-icon-button sm danger" type="button" :title="t('workRecords.remove')" :aria-label="t('workRecords.remove')" @click.stop="removeMember(collection.id, row.member.agent, row.member.conversation_id)">✕</button>
            </li>
            <li v-if="memberVisible(row) && explorer.resumeErrors[row.member.conversation_id]" class="record-resume-error" role="alert">{{ explorer.resumeErrors[row.member.conversation_id] }}</li>
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
          C0 {{ t("workRecords.unfiled") }}
        </h4>
        <div v-if="unfiledExpanded" class="work-record-members">
          <template v-for="row in unfiledTreeRows" :key="unfiledKey(row.conversation)">
            <div
              v-if="unfiledVisible(row)"
              class="unfiled-row"
              draggable="true"
              :data-testid="'unfiled-' + unfiledKey(row.conversation)"
              :data-record-key="unfiledKey(row.conversation)"
              @dragstart="unfiledDragStart($event, row.conversation)"
              @dragover.prevent
              @drop.stop="dropMember($event, null, unfiledKey(row.conversation))"
              @click="previewConversation(row.conversation)"
              @contextmenu.prevent="openMemberMenu($event, null, null, row.conversation)"
              tabindex="0"
              @keydown="onMemberMenuKey($event, null, null, row.conversation)"
            >
              <span class="member-tree-indent" :class="{ branch: row.depth > 0 }" :style="{ width: (row.depth * 14) + 'px' }" />
              <button v-if="row.childCount" class="conversation-twisty" type="button" :aria-expanded="expandedUnfiled.has(row.conversation.conversation_id.toLowerCase())" :aria-label="t('workRecords.tree.toggle')" :data-testid="'unfiled-toggle-' + row.conversation.agent + ':' + row.conversation.conversation_id" @click.stop="toggleUnfiled(row.conversation.conversation_id)">
                <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path :d="expandedUnfiled.has(row.conversation.conversation_id.toLowerCase()) ? 'M3 4.5 6 8l3-3.5' : 'M4.5 2.5 8 6l-3.5 3.5'" /></svg>
                <span class="conversation-child-count">{{ row.childCount }}</span>
              </button>
              <span v-else class="conversation-twisty spacer" aria-hidden="true" />
              <input v-if="renamingConversationKey === unfiledKey(row.conversation)" v-model="renameValue" class="title-input member-title-input" type="text" data-testid="conversation-rename-input" @click.stop @keydown.enter.prevent="commitConversationRename(row.conversation)" @keydown.esc.prevent="renamingConversationKey = null" @blur="commitConversationRename(row.conversation)">
              <span v-else class="member-title">{{ records.numbers.get(unfiledKey(row.conversation)) }} {{ row.conversation.title }}</span>
              <span class="member-agent">{{ row.conversation.agent }}</span>
              <button class="ui-icon-button sm" type="button" :disabled="!row.conversation.resumable" :title="t('workRecords.resume')" :aria-label="t('workRecords.resume')" :data-testid="'resume-' + unfiledKey(row.conversation)" @click.stop="explorer.resumeConversation(row.conversation)">▶</button>
              <button class="ui-icon-button sm" type="button" :title="t('workRecords.rename')" :aria-label="t('workRecords.rename')" @click.stop="beginConversationRename(unfiledKey(row.conversation))">✎</button>
            </div>
            <p v-if="unfiledVisible(row) && explorer.resumeErrors[row.conversation.conversation_id]" class="record-resume-error" role="alert">{{ explorer.resumeErrors[row.conversation.conversation_id] }}</p>
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
    <dialog v-if="pendingDelete" ref="deleteDialog" class="quiet-delete" aria-modal="true" :aria-label="t('workRecords.deleteTitle')" data-testid="quiet-delete-dialog" @cancel.prevent="pendingDelete = null">
        <h3>{{ t("workRecords.deleteTitle") }}</h3>
        <p>{{ pendingDelete.message }}</p>
        <div class="quiet-delete-actions">
          <button autofocus type="button" data-testid="quiet-delete-cancel" @click="pendingDelete = null">{{ t("workRecords.cancel") }}</button>
          <button type="button" class="danger" data-testid="quiet-delete-confirm" @click="confirmQuietDelete">{{ t("workRecords.delete") }}</button>
        </div>
    </dialog>
    <SessionLaunchMenu v-if="sessionMenu" :key="sessionMenu.collectionId" :anchor="sessionMenu.anchor" @close="sessionMenu = null" @choose="createSessionInRecord" />
    <Teleport to="body">
      <div v-if="contextMenu" ref="menuEl" class="work-record-menu" role="menu" :aria-label="t('workRecords.title')" :style="{ ...menuLimits, left: menuPosition.x + 'px', top: menuPosition.y + 'px', visibility: menuReady ? 'visible' : 'hidden' }" data-testid="work-record-context-menu" @click.stop>
        <button v-if="contextMenu.collectionOnly" role="menuitem" type="button" @click="deleteMenuCollection">{{ t("workRecords.delete") }}</button>
        <template v-else>
        <button role="menuitem" type="button" @click="resumeMember(contextMenu.memberKey); closeMenu()">{{ t("workRecords.resume") }}</button>
        <button role="menuitem" v-if="menuConversation()" type="button" @click="previewConversation(menuConversation()); closeMenu()">{{ t("workRecords.preview") }}</button>
        <button role="menuitem" v-if="menuConversation()" type="button" @click="exportFromMenu">{{ t("workRecords.exportMarkdown") }}</button>
        <button role="menuitem" v-if="menuConversation()" type="button" @click="forkSessionFromMenu()">{{ t("workRecords.forkSession") }}</button>
        <button role="menuitem" type="button" @click="beginConversationRename(contextMenu.memberKey); closeMenu()">{{ t("workRecords.rename") }}</button>
        <button role="menuitem" type="button" @click="requestConversationDelete(memberConversation(contextMenu.memberKey)!, contextMenu.collectionId); closeMenu()">{{ t("workRecords.delete") }}</button>
        <button role="menuitem" v-if="contextMenu.collectionId" type="button" @click="moveFromMenu(null)">{{ t("workRecords.moveOut") }}</button>
        <!-- b9 手测 #4: 扁平「移入 测试 / 移入 Test …」收敛为单个子菜单入口 -->
        <div v-if="records.unarchivedCollections.some((c) => c.id !== (contextMenu?.collectionId ?? ''))" class="menu-sub" @mouseenter="openMoveSubmenu()" @mouseleave="leaveMoveSubmenu">
          <button role="menuitem" ref="submenuTrigger" type="button" class="submenu-trigger" aria-haspopup="menu" :aria-expanded="moveSubOpen" @click="openMoveSubmenu(true)">{{ t("workRecords.moveToMenu") }} <span class="arrow">▸</span></button>
          <Teleport to="body">
          <div v-show="moveSubOpen" ref="submenuEl" class="submenu" role="menu" :aria-label="t('workRecords.moveToMenu')" :style="{ ...submenuLimits, left: submenuPosition.x + 'px', top: submenuPosition.y + 'px', visibility: submenuReady ? 'visible' : 'hidden' }" @click.stop @mouseleave="leaveMoveSubmenu">
            <template v-for="collection in records.unarchivedCollections" :key="collection.id">
              <button role="menuitem" v-if="collection.id !== contextMenu.collectionId" type="button" @click="moveFromMenu(collection.id)">{{ collection.title }}</button>
            </template>
          </div>
          </Teleport>
        </div>
        </template>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.work-records-panel { gap: var(--space-2); overflow: auto; width:100%; max-width:100%; min-width:0; overflow-x:hidden; }
.record-resume-error { color: var(--error, var(--text-2)); white-space: normal !important; overflow-wrap: anywhere; font-size: var(--font-sm); padding: 6px; }
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
.work-record-members li, .unfiled-row { display:flex; align-items:center; gap:var(--space-1); min-height:26px; padding:0 var(--space-1); border-radius:var(--radius-sm); background:var(--surface-2); color:var(--text-2); white-space:nowrap; box-sizing:border-box; width:100%; max-width:100%; min-width:0; cursor:pointer; }
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
.work-record-menu, .submenu { position:fixed; z-index:1000; display:flex; flex-direction:column; width:max-content; min-width:min(160px, calc(100vw - 16px)); box-sizing:border-box; overflow:auto; overscroll-behavior:contain; padding:4px; border:var(--border-w) solid var(--border); border-radius:var(--radius-sm); background:var(--surface); box-shadow:var(--shadow-menu); }
.work-record-menu > *, .submenu > button { flex-shrink:0; }
.work-record-menu button, .submenu button { justify-content:flex-start; padding:5px 8px; border:none; background:none; color:var(--text); text-align:left; border-radius:var(--radius-sm); cursor:pointer; white-space:normal; overflow-wrap:anywhere; }
.work-record-menu button:hover, .submenu button:hover { background:var(--surface-hover); }
.work-record-menu button:focus-visible, .submenu button:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }
.menu-sub { position: relative; }
.submenu-trigger { display: flex; width: 100%; justify-content: space-between; align-items: center; }
.submenu { z-index:1001; }

</style>

.quiet-delete::backdrop { background: var(--scrim); }
.quiet-delete h3 { margin: 0 0 var(--space-3); color: var(--text); }
.quiet-delete { width:min(420px,90vw); padding:var(--space-3); background:var(--surface); border:var(--border-w) solid var(--border-strong); border-radius:var(--radius-md); box-shadow:var(--shadow-menu); }
.quiet-delete p { margin:0 0 var(--space-3); color:var(--text); }
.quiet-delete-actions { display:flex; justify-content:flex-end; gap:var(--space-2); }
