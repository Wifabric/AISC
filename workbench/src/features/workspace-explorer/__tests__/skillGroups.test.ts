import { describe, expect, it } from "vitest";
import type { ExtensionsItem } from "../../../lib/ipc";
import { groupSkillItems } from "../skillGroups";

function skill(id: string, repo: string, over: Partial<ExtensionsItem> = {}): ExtensionsItem {
  return { id, name: id, repo, ...over } as ExtensionsItem;
}

describe("b13 skill repository grouping", () => {
  it("groups installed skills by repository and preserves per-skill rows", () => {
    const groups = groupSkillItems([
      skill("brainstorming", "obra/superpowers"),
      skill("debugging", "obra/superpowers"),
      skill("pdf", "anthropics/skills"),
      skill("local", ""),
    ]);
    expect(groups.map((group) => group.id)).toEqual([
      "obra/superpowers",
      "anthropics/skills",
      "local",
    ]);
    expect(groups[0]?.items).toHaveLength(2);
    expect(groups[2]?.name).toBe("本地/未记录仓库");
    expect(groups.every((group) => group.expanded !== undefined)).toBe(true);
  });

  it("groups marketplace rows by repository and keeps install ids stable", () => {
    const groups = groupSkillItems([
      { id: "obra/superpowers:brainstorming", name: "brainstorming", repo: "obra/superpowers", directory: "brainstorming" } as ExtensionsItem,
      { id: "obra/superpowers:debugging", name: "debugging", repo: "obra/superpowers", directory: "debugging" } as ExtensionsItem,
    ]);
    expect(groups).toHaveLength(1);
    expect(groups[0]?.items.map((item) => item.id)).toEqual([
      "obra/superpowers:brainstorming",
      "obra/superpowers:debugging",
    ]);
  });
});
