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

function market(name: string): ExtensionsItem {
  return {
    kind: "market-skill", id: `obra/superpowers:${name}`, name,
    repo: "obra/superpowers", directory: name,
  } as ExtensionsItem;
}

const groupResult = {
  items: [
    { spec: "obra/superpowers:brainstorming", status: "installed", error: "" },
    { spec: "obra/superpowers:debugging", status: "installed", error: "" },
  ],
  total: 2,
  completed: 2,
};

beforeEach(() => {
  setActivePinia(createPinia());
  call.mockReset();
});

describe("v2.1.17 b1 skill repository group operations", () => {
  it("updates every child in one repository group", async () => {
    call.mockResolvedValue({ items: [] });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    store.itemsByKind.skills = [
      installed("brainstorming", "obra/superpowers"),
      installed("debugging", "obra/superpowers"),
    ];
    expect(store.installedSkillGroups).toHaveLength(1);
    await store.updateSkillGroup(store.installedSkillGroups[0]!);

    expect(call).toHaveBeenCalledWith(expect.objectContaining({
      op: "skill-update", spec: "obra/superpowers:brainstorming",
    }));
    expect(call).toHaveBeenCalledWith(expect.objectContaining({
      op: "skill-update", spec: "obra/superpowers:debugging",
    }));
  });

  it("installs a marketplace repository group as one preflighted call", async () => {
    call.mockResolvedValue(groupResult);
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    store.marketSkills = [market("brainstorming"), market("debugging")];
    await store.installSkillGroup(store.marketSkillGroups[0]!);

    const installCalls = call.mock.calls.filter(([params]) => params.op === "skill-install-group");
    expect(installCalls).toHaveLength(1);
    expect(call).toHaveBeenCalledWith(expect.objectContaining({
      op: "skill-install-group",
      specs: ["obra/superpowers:brainstorming", "obra/superpowers:debugging"],
    }));
  });

  it("surfaces itemized group failures instead of a generic CLI error", async () => {
    call.mockResolvedValue({
      items: [
        { spec: "obra/superpowers:brainstorming", status: "installed", error: "" },
        { spec: "obra/superpowers:debugging", status: "failed", error: "github unreachable after direct and mirror probes" },
      ],
      total: 2,
      completed: 1,
    });
    const store = useExtensionsStore();
    const toast = await import("../toast").then((m) => m.useToastStore());
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    store.marketSkills = [market("brainstorming"), market("debugging")];
    await store.installSkillGroup(store.marketSkillGroups[0]!);

    expect(store.error).toContain("obra/superpowers:debugging");
    expect(store.error).toContain("github unreachable after direct and mirror probes");
    expect(toast.toasts[toast.toasts.length - 1]).toMatchObject({
      kind: "error",
      message: expect.stringContaining("obra/superpowers:debugging"),
    });
  });
  it("keeps group progress stable while the group operation runs", async () => {
    call.mockResolvedValue(groupResult);
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    store.marketSkills = [market("brainstorming"), market("debugging")];
    const pending = store.installSkillGroup(store.marketSkillGroups[0]!);

    expect(store.activeOperation).toMatchObject({
      kind: "skills", action: "install", completed: 0, total: 2,
    });
    await pending;
    expect(store.activeOperation).toBeNull();
  });
});
