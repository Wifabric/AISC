/**
 * b5 (2.1.16): Extensions store — skills / MCP / plugins unified management.
 * Data plane boundary (F-A01): components never import ipc directly.
 */
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as ipc from "../lib/ipc";
import type { ExtensionsItem } from "../lib/ipc";

export type ExtensionsKind = "skills" | "mcp" | "plugins";


/** WorkbenchError serializes { code, message, technical_detail }; raw
 * String(e) would render "[object Object]" (b5 pre-handtest finding). */
function errorText(e: unknown): string {
  const err = e as { message?: string; technical_detail?: string };
  const message = err?.message ?? String(e);
  const detail = err?.technical_detail;
  if (!detail || detail === message) return message;
  return `${message}：${detail}`;
}
export const useExtensionsStore = defineStore("extensions", () => {
  const kind = ref<ExtensionsKind>("skills");
  const items = ref<ExtensionsItem[]>([]);
  const loading = ref(false);
  const busy = ref(false);
  const opBusyId = ref<string | null>(null);
  const error = ref<string | null>(null);

  const context = ref<{ workspace: string; runtimeId: string } | null>(null);
  /** b7 商城：技能搜索结果（market-skill 条目）。 */
  const marketSkills = ref<ExtensionsItem[]>([]);
  const marketBusy = ref(false);
  /** b7 商城：插件市场列表。 */
  const pluginMarkets = ref<ExtensionsItem[]>([]);
  const marketMcp = ref<ExtensionsItem[]>([]);
  const canLoad = computed(() => context.value !== null);

  async function call<T = Record<string, unknown>>(
    op: string,
    extra: Partial<ipc.ExtensionsCallParams> = {},
  ): Promise<T> {
    if (!context.value) throw new Error("extensions: no runtime context");
    const out = await ipc.extensionsCall({
      workspace: context.value.workspace,
      runtimeId: context.value.runtimeId,
      op,
      ...extra,
    });
    return out as T;
  }

  async function load(target?: ExtensionsKind): Promise<void> {
    if (target) kind.value = target;
    if (!context.value) return;
    loading.value = true;
    error.value = null;
    try {
      const out = await call<{ items?: ExtensionsItem[] }>("list", { kind: kind.value });
      items.value = out.items ?? [];
    } catch (e) {
      error.value = errorText(e);
    } finally {
      loading.value = false;
    }
  }

  async function toggle(item: ExtensionsItem, agent: "claude" | "codex", on: boolean): Promise<void> {
    busy.value = true;
    error.value = null;
    try {
      await call("toggle", { kind: kind.value, id: item.id, agent, on });
      await load();
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }

  async function remove(item: ExtensionsItem): Promise<void> {
    busy.value = true;
    error.value = null;
    try {
      await call(kind.value === "plugins" ? "plugin-uninstall" : "delete", {
        kind: kind.value,
        id: item.id,
      });
      await load();
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }

  async function installSkill(spec: string): Promise<void> {
    busy.value = true;
    error.value = null;
    try {
      await call("skill-install", { spec });
      await load("skills");
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }

  async function addMcp(configJson: string, apps: string): Promise<void> {
    busy.value = true;
    error.value = null;
    try {
      await call("mcp-add", { apps, config: configJson });
      await load("mcp");
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }

  async function pluginAction(op: "plugin-install" | "plugin-update", id: string): Promise<void> {
    busy.value = true;
    error.value = null;
    try {
      await call(op, { id });
      await load("plugins");
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }

  async function searchSkills(query: string): Promise<void> {
    marketBusy.value = true;
    error.value = null;
    try {
      const out = await call<{ items?: ExtensionsItem[] }>("skill-search", { query });
      marketSkills.value = out.items ?? [];
    } catch (e) {
      error.value = errorText(e);
    } finally {
      marketBusy.value = false;
    }
  }

  async function importDeeplink(url: string): Promise<void> {
    busy.value = true;
    error.value = null;
    try {
      await call("deeplink", { url });
      await load();
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }

  async function addSkillRepo(source: string): Promise<void> {
    busy.value = true;
    error.value = null;
    try {
      await call("skill-repo-add", { id: source });
      await load("skills");
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }

    async function searchMcp(query: string): Promise<void> {
    marketBusy.value = true;
    error.value = null;
    try {
      const out = await call<{ items?: ExtensionsItem[] }>("mcp-search", { query });
      marketMcp.value = out.items ?? [];
    } catch (e) {
      error.value = errorText(e);
    } finally {
      marketBusy.value = false;
    }
  }

  async function installMcpMarket(marketId: string): Promise<void> {
    opBusyId.value = marketId;
    busy.value = true;
    error.value = null;
    try {
      await call("mcp-market-install", { id: marketId });
      await load("mcp");
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false; opBusyId.value = null;
    }
  }
async function loadPluginMarkets(): Promise<void> {
    marketBusy.value = true;
    error.value = null;
    try {
      const out = await call<{ items?: ExtensionsItem[] }>("plugin-market-list");
      pluginMarkets.value = out.items ?? [];
    } catch (e) {
      error.value = errorText(e);
    } finally {
      marketBusy.value = false;
    }
  }

  async function addPluginMarket(source: string): Promise<void> {
    busy.value = true;
    error.value = null;
    try {
      await call("plugin-market-add", { id: source });
      await loadPluginMarkets();
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }

  function setContext(workspace: string, runtimeId: string): void {
    context.value = workspace && runtimeId ? { workspace, runtimeId } : null;
  }

  return {
    kind, items, loading, busy, error, canLoad,
    marketSkills, marketBusy, pluginMarkets, opBusyId, marketMcp,
    searchSkills, searchMcp, installMcpMarket, importDeeplink, addSkillRepo, loadPluginMarkets, addPluginMarket,
    load, toggle, remove, installSkill, addMcp, pluginAction, setContext,
  };
});
