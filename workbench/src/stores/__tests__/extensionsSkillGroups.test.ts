import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useExtensionsStore } from "../extensions";
import { extensionsCall } from "../../lib/ipc";
import type { ExtensionsItem } from "../../lib/ipc";

vi.mock("../../lib/ipc", () => ({ extensionsCall: vi.fn() }));
const call = vi.mocked(extensionsCall);

function installed(name: string, repo: string): ExtensionsItem {
  return {
    kind: "skills", id: name, name, directory: name, repo,
    enabled_claude: true, enabled_codex: false,
  };
}

beforeEach(() => {
  setActivePinia(createPinia());
  call.mockReset();
});

describe("b13 skill repository batch operations", () => {
  it("updates every child in one repository group", async () => {
    call.mockResolvedValue({ items: [] });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    store.items = [
      installed("brainstorming", "obra/superpowers"),
      installed("debugging", "obra/superpowers"),
    ];
    expect(store.installedSkillGroups).toHaveLength(1);
    await store.updateSkillGroup(store.installedSkillGroups[0]!);

    expect(call).toHaveBeenCalledWith(expect.objectContaining({
      op: "skill-install", spec: "obra/superpowers:brainstorming",
    }));
    expect(call).toHaveBeenCalledWith(expect.objectContaining({
      op: "skill-install", spec: "obra/superpowers:debugging",
    }));
  });

  it("installs a marketplace repository group with original ids", async () => {
    call.mockResolvedValue({ items: [] });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    store.marketSkills = [
      { kind: "market-skill", id: "obra/superpowers:brainstorming", name: "brainstorming", repo: "obra/superpowers", directory: "brainstorming" },
      { kind: "market-skill", id: "obra/superpowers:debugging", name: "debugging", repo: "obra/superpowers", directory: "debugging" },
    ];
    await store.installSkillGroup(store.marketSkillGroups[0]!);

    expect(call).toHaveBeenNthCalledWith(1, expect.objectContaining({
      op: "skill-install", spec: "obra/superpowers:brainstorming",
    }));
    expect(call).toHaveBeenNthCalledWith(2, expect.objectContaining({
      op: "skill-install", spec: "obra/superpowers:debugging",
    }));
  });
});
