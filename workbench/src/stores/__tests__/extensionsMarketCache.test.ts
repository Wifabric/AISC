import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useExtensionsStore } from "../extensions";
import { extensionsCall } from "../../lib/ipc";

vi.mock("../../lib/ipc", () => ({ extensionsCall: vi.fn() }));
const call = vi.mocked(extensionsCall);

describe("v2.1.17 b1 market metadata cache", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    call.mockReset();
  });

  it("records cache metadata independently for each market", async () => {
    call.mockImplementation(async (p: any) => {
      if (p.op === "skill-search") {
        return {
          items: [{ kind: "market-skill", id: "demo/repo:skill", name: "skill" }],
          cache: { source: "cache", cached: true, query: "demo", fetched_at: "2026-10-26T01:00:00Z", error: "remote down" },
        };
      }
      if (p.op === "mcp-search") {
        return {
          items: [{ kind: "market-mcp", id: "example/mcp", name: "mcp" }],
          cache: { source: "remote", cached: false, query: "mcp", fetched_at: "2026-10-26T01:01:00Z" },
        };
      }
      return { items: [] };
    });

    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    await store.searchSkills("demo");
    await store.searchMcp("mcp");

    expect(store.marketCacheByKind.skills).toMatchObject({ cached: true, source: "cache" });
    expect(store.marketCacheByKind.mcp).toMatchObject({ cached: false, source: "remote" });
    expect(store.marketCacheByKind.plugins).toBeNull();
  });

  it("keeps the last successful cache metadata when a no-cache refresh fails", async () => {
    call.mockResolvedValueOnce({
      items: [{ kind: "market-plugin", id: "demo@market", name: "demo" }],
      cache: { source: "remote", cached: false, query: "demo", fetched_at: "2026-10-26T01:00:00Z" },
    }).mockRejectedValueOnce({ message: "remote down" });

    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    store.kind = "plugins";
    await store.searchPlugins("demo");
    const before = store.marketPlugins;
    await store.searchPlugins("demo");

    expect(store.marketPlugins).toBe(before);
    expect(store.marketCacheByKind.plugins).toMatchObject({ source: "remote", cached: false });
    expect(store.error).toContain("remote down");
  });

  it("clears cache metadata with results when the query becomes blank", async () => {
    const store = useExtensionsStore();
    store.marketPlugins = [{ kind: "market-plugin", id: "old@market", name: "old" }];
    store.marketCacheByKind.plugins = { source: "cache", cached: true, query: "old", fetched_at: "2026-10-26T01:00:00Z" };
    store.clearMarketResults("plugins");
    expect(store.marketPlugins).toEqual([]);
    expect(store.marketCacheByKind.plugins).toBeNull();
  });
});
