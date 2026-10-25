import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useExtensionsStore } from "../extensions";
import { extensionsCall } from "../../lib/ipc";

vi.mock("../../lib/ipc", () => ({
  extensionsCall: vi.fn(),
}));

const extensionsCallMock = vi.mocked(extensionsCall);

beforeEach(() => {
  setActivePinia(createPinia());
  extensionsCallMock.mockReset();
});

describe("extensions plugin marketplace", () => {
  it("searches the configured Claude plugin marketplaces", async () => {
    extensionsCallMock.mockResolvedValue({
      items: [{ kind: "market-plugin", id: "skill-creator@claude-plugins-official", name: "skill-creator" }],
    });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    await store.searchPlugins("skill creator");

    expect(store.marketPlugins).toHaveLength(1);
    expect(store.marketPlugins[0]?.id).toBe("skill-creator@claude-plugins-official");
    expect(extensionsCallMock).toHaveBeenCalledWith({
      workspace: "e:/projects",
      runtimeId: "00000000-0000-4000-8000-000000000000",
      op: "plugin-search",
      query: "skill creator",
    });
  });

  it("tracks operation progress with completed and total counts", async () => {
    let releaseOperation: (() => void) | undefined;
    const operation = new Promise<Record<string, unknown>>((resolve) => {
      releaseOperation = () => resolve({ items: [] });
    });
    extensionsCallMock.mockImplementationOnce(() => operation).mockResolvedValue({ items: [] });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    store.kind = "plugins";
    const pending = store.pluginAction("plugin-install", "skill-creator@claude-plugins-official");
    expect(store.opBusyId).toBe("skill-creator@claude-plugins-official");
    expect(store.activeOperation).toMatchObject({
      kind: "plugins",
      action: "install",
      completed: 0,
      total: 1,
    });
    releaseOperation?.();
    await pending;
    expect(store.opBusyId).toBeNull();
    expect(store.activeOperation).toBeNull();
  });
});


describe("v2.1.16 preview b1 extension isolation", () => {
  it("keeps skill installation state independent from the MCP panel", async () => {
    let letResolve: (() => void) | undefined;
    const first = new Promise<Record<string, unknown>>((resolve) => {
      letResolve = () => resolve({ items: [] });
    });
    let releaseSecond: (() => void) | undefined;
    const second = new Promise<Record<string, unknown>>((resolve) => {
      releaseSecond = () => resolve({ items: [] });
    });
    extensionsCallMock.mockImplementation(async (p: any) => {
      if (p.op === "skill-install") return first;
      if (p.op === "mcp-market-install") return second;
      return { items: [] };
    });

    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    const skillInstall = store.installSkill("obra/superpowers:brainstorming");
    expect(store.busy).toBe(true);

    await store.load("mcp");
    expect(store.kind).toBe("mcp");
    expect(store.busy).toBe(false);
    expect(store.activeOperation).toBeNull();
    expect(store.operationsByKind.skills?.kind).toBe("skills");

    releaseSecond?.();
    const mcpInstall = store.installMcpMarket("example/mcp");
    expect(store.busy).toBe(true);
    expect(store.activeOperation?.kind).toBe("mcp");

    letResolve?.();
    await Promise.all([skillInstall, mcpInstall]);
    expect(store.busy).toBe(false);
    expect(store.activeOperation).toBeNull();
  });

  it("clears market results when the query becomes blank", async () => {
    extensionsCallMock.mockResolvedValue({ items: [] });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    store.marketPlugins = [{ kind: "market-plugin", id: "old@market", name: "old" }];
    store.clearMarketResults("plugins");
    expect(store.marketPlugins).toEqual([]);
  });
});
