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

export function skillUpdateSpec(item: ExtensionsItem): string {
  if (item.id.includes(":")) return item.id;
  const directory = item.directory || item.id;
  return item.repo?.includes("/") ? `${item.repo}:${directory}` : directory;
}
