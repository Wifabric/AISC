import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useExtensionsStore } from "../extensions";
import { extensionsCall } from "../../lib/ipc";
import type { ExtensionsItem } from "../../lib/ipc";

vi.mock("../../lib/ipc", () => ({ extensionsCall: vi.fn() }));
const call = vi.mocked(extensionsCall);

const repo: ExtensionsItem = {
  kind: "skill-repo", id: "owner/repo", name: "owner/repo",
  repo: "owner/repo", branch: "main", enabled: true,
} as ExtensionsItem;

beforeEach(() => {
  setActivePinia(createPinia());
  call.mockReset();
});

describe("v2.1.17 R2 extension source maintenance", () => {
  it("loads skill repositories through the extensions data plane", async () => {
    call.mockResolvedValueOnce({ items: [repo] });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    await store.loadSkillRepos();

    expect(call).toHaveBeenCalledWith({
      workspace: "e:/projects", runtimeId: "rid-1", op: "skill-repos-list",
    });
    expect(store.skillRepos).toEqual([repo]);
    expect(store.skillReposBusy).toBe(false);
    expect(store.skillReposError).toBeNull();
  });

  it("removes a skill repository and refreshes the source list", async () => {
    call.mockImplementation(async (params: any) => {
      if (params.op === "skill-repos-list") return { items: [] };
      if (params.op === "skill-repo-remove") return {};
      throw new Error(`unexpected op ${params.op}`);
    });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    store.skillRepos = [repo];
    await store.removeSkillRepo("owner/repo");

    expect(call).toHaveBeenCalledWith(expect.objectContaining({
      op: "skill-repo-remove", id: "owner/repo",
    }));
    expect(call).toHaveBeenLastCalledWith(expect.objectContaining({
      op: "skill-repos-list",
    }));
    expect(store.skillRepos).toEqual([]);
  });

  it("records skill repository listing failures without clobbering old rows", async () => {
    call.mockRejectedValue({ message: "registry unavailable" });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    store.skillRepos = [repo];
    await store.loadSkillRepos();

    expect(store.skillReposError).toContain("registry unavailable");
    expect(store.skillRepos).toEqual([repo]);
    expect(store.skillReposBusy).toBe(false);
  });

  it("classifies only stable unsupported operations as source unavailable", async () => {
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");

    call.mockRejectedValueOnce({
      code: "WB_ERR_EXTENSIONS_UNSUPPORTED_OP",
      message: "当前运行环境不支持扩展来源维护",
      technical_detail: "old runtime lacks skill-repos-list",
    });
    await store.loadSkillRepos();
    expect(store.skillReposUnsupported).toBe(true);

    call.mockRejectedValueOnce({ message: "database is locked" });
    await store.loadSkillRepos();
    expect(store.skillReposUnsupported).toBe(false);
    expect(store.skillReposError).toContain("database is locked");
  });

  it("removes a plugin marketplace and refreshes its uninstalled plugins and sources", async () => {
    const retained = { kind: "plugins", id: "keep@official", name: "keep" } as ExtensionsItem;
    call.mockImplementation(async (params: any) => {
      if (params.op === "list" && params.kind === "plugins") return { items: [retained] };
      if (params.op === "plugin-market-list") {
        return { items: [{ kind: "marketplace", id: "official", name: "official" }] };
      }
      if (params.op === "plugin-market-remove") return {};
      throw new Error(`unexpected op ${params.op}`);
    });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    store.pluginMarkets = [
      { kind: "marketplace", id: "old", name: "old" },
      { kind: "marketplace", id: "official", name: "official" },
    ] as ExtensionsItem[];
    store.itemsByKind.plugins = [
      { kind: "plugins", id: "removed@old", name: "removed" }, retained,
    ];
    await store.removePluginMarket("old");

    expect(call).toHaveBeenCalledWith(expect.objectContaining({
      op: "plugin-market-remove", id: "old",
    }));
    expect(call).toHaveBeenLastCalledWith(expect.objectContaining({
      op: "plugin-market-list",
    }));
    expect(store.pluginMarkets).toEqual([
      { kind: "marketplace", id: "official", name: "official" },
    ]);
    expect(call).toHaveBeenCalledWith(expect.objectContaining({ op: "list", kind: "plugins" }));
    expect(store.itemsByKind.plugins).toEqual([retained]);
  });

  it("clears source state when the runtime context changes", () => {
    const store = useExtensionsStore();
    store.setContext("e:/projects", "rid-1");
    store.skillRepos = [repo];
    store.skillReposError = "old";
    store.pluginMarkets = [
      { kind: "marketplace", id: "old", name: "old" },
    ] as ExtensionsItem[];
    store.setContext("e:/other", "rid-2");

    expect(store.skillRepos).toEqual([]);
    expect(store.skillReposError).toBeNull();
    expect(store.pluginMarkets).toEqual([]);
  });
});
