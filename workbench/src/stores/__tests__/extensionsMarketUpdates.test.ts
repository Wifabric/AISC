import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useExtensionsStore } from "../extensions";
import { extensionsCall } from "../../lib/ipc";

vi.mock("../../lib/ipc", () => ({ extensionsCall: vi.fn() }));
const call = vi.mocked(extensionsCall);

beforeEach(() => {
  setActivePinia(createPinia());
  call.mockReset();
});

describe("v2.1.17 b2 market metadata and updates", () => {
  it("keeps market cache metadata per asset kind", async () => {
    call.mockResolvedValueOnce({
      items: [{ kind: "market-skill", id: "owner/repo:skill", name: "skill" }],
      cache: {
        source: "cache", cached: true, query: "skill",
        fetched_at: 123, error: "remote refresh down",
      },
    }).mockResolvedValue({ items: [] });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    await store.searchSkills("skill");

    expect(store.marketCacheByKind.skills).toMatchObject({
      cached: true, query: "skill", error: "remote refresh down",
    });
    await store.searchSkills("   ");
    expect(store.marketCacheByKind.skills).toBeNull();
  });

  it("checks updates and indexes reliable update signals by kind", async () => {
    call.mockResolvedValueOnce({
      op: "updates-check",
      items: [
        { kind: "plugins", id: "chart@official", update_available: true,
          latest_version: "1.1.0" },
        { kind: "skills", id: "caveman", update_available: false,
          status: "unsupported" },
      ],
    }).mockResolvedValue({ items: [] });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    await store.checkUpdates();

    expect(call).toHaveBeenCalledWith(expect.objectContaining({
      op: "updates-check",
    }));
    expect(store.updateItemsByKind.plugins["chart@official"]).toMatchObject({
      update_available: true, latest_version: "1.1.0",
    });
    expect(store.updateItemsByKind.skills.caveman?.status).toBe("unsupported");
    expect(store.updateItemsByKind.skills["chart@official"]).toBeUndefined();
    expect(store.updateItemsByKind.plugins.caveman).toBeUndefined();
    expect(store.updatesError).toBeNull();
  });

  it("clears stale update signal after a successful plugin update", async () => {
    call.mockResolvedValue({ items: [] });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    store.updateItemsByKind.plugins = {
      "p@m": { kind: "plugins", id: "p@m", status: "ok", update_available: true },
      "q@m": { kind: "plugins", id: "q@m", status: "ok", update_available: true },
    };
    await store.pluginAction("plugin-update", "p@m");

    expect(store.updateItemsByKind.plugins["p@m"]).toBeUndefined();
    expect(store.updateItemsByKind.plugins["q@m"]?.update_available).toBe(true);
  });

  it("isolates market cache and update state when runtime context changes", () => {
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    store.marketSkills = [{ kind: "market-skill", id: "s", name: "s" }];
    store.marketCacheByKind.skills = {
      source: "cache", cached: true, query: "s", fetched_at: 123,
    };
    store.updateItemsByKind.plugins = {
      "p@m": { kind: "plugins", id: "p@m", status: "ok", update_available: true },
    };
    store.setContext("e:/projects", "rid-2");

    expect(store.marketSkills).toEqual([]);
    expect(store.marketCacheByKind.skills).toBeNull();
    expect(store.updateItemsByKind.plugins).toEqual({});
    expect(store.updatesError).toBeNull();
  });

  it("drops an old runtime search response that resolves after context switch", async () => {
    let resolveSearch: (value: any) => void = () => {};
    call.mockImplementation(({ op }: any) => new Promise((resolve) => {
      if (op === "plugin-search") resolveSearch = resolve;
    }));
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    const pending = store.searchPlugins("old");
    store.setContext("e:/projects", "rid-2");
    resolveSearch({ items: [{ kind: "market-plugin", id: "old" }], cache: { cached: true } });
    await pending;

    expect(store.marketPlugins).toEqual([]);
    expect(store.marketCacheByKind.plugins).toBeNull();
  });

  it("clears previous query results when a new query has no cache fallback", async () => {
    call.mockResolvedValueOnce({
      items: [{ kind: "market-plugin", id: "a" }],
      cache: { source: "remote", cached: false },
    }).mockRejectedValueOnce(new Error("remote refresh down"));
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    await store.searchPlugins("a");
    await store.searchPlugins("b");

    expect(store.marketPlugins).toEqual([]);
    expect(store.marketCacheByKind.plugins).toBeNull();
    store.kind = "plugins";
    expect(store.error).toContain("remote refresh down");
  });

  it("clears stale update badges when a new check fails", async () => {
    call.mockRejectedValueOnce(new Error("remote refresh down"));
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    store.updateItemsByKind.plugins = {
      "p@m": { kind: "plugins", id: "p@m", status: "ok", update_available: true },
    };
    await store.checkUpdates();

    expect(store.updateItemsByKind.plugins).toEqual({});
    expect(store.updatesError).toContain("remote refresh down");
  });

  it("resets update busy state when the runtime changes", async () => {
    let complete!: (value: any) => void;
    call.mockImplementation(() => new Promise((resolve) => { complete = resolve; }));
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    const pending = store.checkUpdates();
    store.setContext("e:/projects", "rid-2");
    complete({ items: [] });
    await pending;
    expect(store.updatesBusy).toBe(false);
  });

  it("drops plugin marketplace responses from the previous runtime", async () => {
    let complete!: (value: any) => void;
    call.mockImplementation(() => new Promise((resolve) => { complete = resolve; }));
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    const pending = store.loadPluginMarkets();
    store.setContext("e:/projects", "rid-2");
    complete({ items: [{ id: "old" }] });
    await pending;
    expect(store.pluginMarkets).toEqual([]);
  });
});

