import type { ConversationReadMessage } from "../../types";

export interface ReadingTurn {
  id: number;
  questions: ConversationReadMessage[];
  activity: ConversationReadMessage[];
  answers: ConversationReadMessage[];
}

/** One evidence disclosure per user turn. Older transcripts lack phase:
 * assistant text before the last tool is progress, text after it is answer. */
export function readingTurns(messages: ConversationReadMessage[]): ReadingTurn[] {
  const turns: ReadingTurn[] = [];
  let turn: ReadingTurn | undefined;
  let response: ConversationReadMessage[] = [];
  function finish() {
    if (!turn) return;
    const lastAction = response.reduce((last, m, i) => m.kind !== "message" ? i : last, -1);
    response.forEach((m, i) => {
      if (m.kind !== "message" || m.phase === "commentary" || (i < lastAction && m.phase !== "final_answer")) turn!.activity.push(m);
      else turn!.answers.push(m);
    });
    response = [];
  }
  for (const m of messages) {
    if (m.role === "user" && m.kind === "message") {
      if (!turn || response.length) {
        finish();
        turn = { id: m.ordinal, questions: [], activity: [], answers: [] };
        turns.push(turn);
      }
      turn.questions.push(m);
    } else {
      if (!turn) { turn = { id: m.ordinal, questions: [], activity: [], answers: [] }; turns.push(turn); }
      response.push(m);
    }
  }
  finish();
  return turns;
}

export type RecordLink = { kind: "web"; url: string } | { kind: "file"; path: string } | { kind: "anchor"; id: string };

/** Normalize presentation paths; the backend still owns symlink containment. */
export function recordLink(raw: string, workspace: string): RecordLink | null {
  if (/^https?:\/\//i.test(raw)) {
    try { const url = new URL(raw); return url.username || url.password ? null : { kind: "web", url: url.href }; } catch { return null; }
  }
  if (raw.startsWith("#")) return { kind: "anchor", id: raw.slice(1) };
  let path: string;
  try { path = decodeURIComponent(raw); } catch { return null; }
  if (/^file:\/\//i.test(path)) {
    if (!/^file:\/\/\//i.test(path)) return null;
    path = path.replace(/^file:\/\/\//i, "/").replace(/^\/([a-z]:\/)/i, "$1");
  }
  path = path.replace(/\\/g, "/").replace(/(?::\d+(?::\d+)?|#L\d+(?:C\d+)?)$/, "");
  const root = workspace.replace(/\\/g, "/").replace(/\/$/, "");
  const compare = /^[a-z]:/i.test(root) ? path.toLowerCase() : path;
  const rootCompare = /^[a-z]:/i.test(root) ? root.toLowerCase() : root;
  if (root && compare.startsWith(rootCompare + "/")) path = path.slice(root.length + 1);
  else if (path.startsWith("/root/app/")) path = path.slice(10);
  else if (path.startsWith("/app/")) path = path.slice(5);
  path = path.replace(/^\.\//, "");
  if (!path || /[\x00-\x1f\x7f:?#]/.test(path) || path.startsWith("/") || path.split("/").some(p => p === ".." || p === "")) return null;
  return { kind: "file", path };
}
