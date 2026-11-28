import type { ExtensionsItem } from "../../lib/ipc";

export interface SkillGroup {
  id: string;
  name: string;
  repo: string;
  items: ExtensionsItem[];
  conflict: boolean;
  expanded: boolean;
}

const LOCAL_GROUP_NAME = "本地/未记录仓库";

export function groupSkillItems(items: ExtensionsItem[]): SkillGroup[] {
  const groups = new Map<string, SkillGroup>();
  for (const item of items) {
    const repo = item.repo?.trim() ?? "";
    const id = repo || item.id || item.name || "local";
    let group = groups.get(id);
    if (!group) {
      group = {
        id,
        name: repo || LOCAL_GROUP_NAME,
        repo,
        items: [],
        conflict: false,
        expanded: false,
      };
      groups.set(id, group);
    }
    group.items.push(item);
    group.conflict ||= item.conflict === true;
  }
  return [...groups.values()];
}

export interface SkillSubgroup {
  /** First directory segment (e.g. `engineering` in `engineering/grill-with-docs`). */
  key: string;
  name: string;
  items: ExtensionsItem[];
}

export interface SplitSkillGroups {
  subgroups: SkillSubgroup[];
  /** Items whose directory has no `/` — rendered flat, above the subgroups. */
  roots: ExtensionsItem[];
}

/** b16 (T3): nest a repo's skills by the first `directory` segment when the
 * market row carries a category path (e.g. `engineering/grill-with-docs`).
 * Returns `null` when every directory is flat, so callers keep the flat list. */
export function splitSkillSubgroups(items: ExtensionsItem[]): SplitSkillGroups | null {
  const subgroups = new Map<string, SkillSubgroup>();
  const roots: ExtensionsItem[] = [];
  let nested = 0;
  for (const item of items) {
    const dir = (item.directory || item.name || "").trim();
    const slash = dir.indexOf("/");
    if (slash < 0) { roots.push(item); continue; }
    nested++;
    const key = dir.slice(0, slash);
    const group = subgroups.get(key) ?? { key, name: key, items: [] };
    group.items.push(item);
    subgroups.set(key, group);
  }
  if (nested === 0) return null;
  return { subgroups: [...subgroups.values()], roots };
}

export function skillUpdateSpec(item: ExtensionsItem): string {
  if (item.id.includes(":")) return item.id;
  const directory = item.directory || item.id;
  return item.repo?.includes("/") ? `${item.repo}:${directory}` : directory;
}
