import { describe, expect, it } from "vitest";
import type { ExtensionsItem } from "../../../lib/ipc";
import { groupSkillItems, splitSkillSubgroups } from "../skillGroups";

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

  it("nests a repo's skills by the first directory segment (b16)", () => {
    const items = [
      { id: "m/s:engineering/grill-with-docs", name: "grill-with-docs", repo: "m/s", directory: "engineering/grill-with-docs" } as ExtensionsItem,
      { id: "m/s:engineering/domain-modeling", name: "domain-modeling", repo: "m/s", directory: "engineering/domain-modeling" } as ExtensionsItem,
      { id: "m/s:productivity/ask-matt", name: "ask-matt", repo: "m/s", directory: "productivity/ask-matt" } as ExtensionsItem,
      { id: "m/s:standalone", name: "standalone", repo: "m/s", directory: "standalone" } as ExtensionsItem,
    ];
    const split = splitSkillSubgroups(items)!;
    expect(split.roots.map((i) => i.name)).toEqual(["standalone"]);
    expect(split.subgroups.map((sg) => sg.key)).toEqual(["engineering", "productivity"]);
    expect(split.subgroups[0]!.items).toHaveLength(2);
    expect(split.subgroups[1]!.items).toHaveLength(1);
  });

  it("returns null when a repo has no nested directories (b16)", () => {
    const items = [
      { id: "m/s:a", name: "a", repo: "m/s", directory: "a" } as ExtensionsItem,
      { id: "m/s:b", name: "b", repo: "m/s", directory: "b" } as ExtensionsItem,
    ];
    expect(splitSkillSubgroups(items)).toBeNull();
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
