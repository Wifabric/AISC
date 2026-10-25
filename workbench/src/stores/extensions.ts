/**
 * b5 (2.1.16): Extensions store — skills / MCP / plugins unified management.
 * Data plane boundary (F-A01): components never import ipc directly.
 */
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as ipc from "../lib/ipc";
import type { ExtensionsItem } from "../lib/ipc";
import { groupSkillItems, skillUpdateSpec, type SkillGroup } from "../features/workspace-explorer/skillGroups";
import { useToastStore } from "./toast";
import { i18n } from "../i18n";

export type ExtensionsKind = "skills" | "mcp" | "plugins";
export type ExtensionAction =
  | "install" | "update" | "remove" | "toggle" | "add" | "import";

export interface ExtensionOperation {
  kind: ExtensionsKind;
  action: ExtensionAction;
  id: string;
  label: string;
  completed: number;
  total: number;
}

export interface MarketCacheState {
  source: "remote" | "cache" | string;
  cached: boolean;
  query?: string;
  fetched_at?: string;
  error?: string;
}

type KindRecord<T> = Record<ExtensionsKind, T>;

function kindRecord<T>(value: T): KindRecord<T> {
  return { skills: value, mcp: value, plugins: value };
}

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
  const toast = useToastStore();
  const kind = ref<ExtensionsKind>("skills");
  const context = ref<{ workspace: string; runtimeId: string } | null>(null);

  // Preview b1: every asset owns its list and async state. A skill install
  // can refresh the skills list without blanking/flickering MCP or plugins.
  const itemsByKind = ref<KindRecord<ExtensionsItem[]>>(
    kindRecord<ExtensionsItem[]>([]),
  );
  const loadingByKind = ref(kindRecord(false));
  const busyByKind = ref(kindRecord(false));
  const searchBusyByKind = ref(kindRecord(false));
  const marketCacheByKind = ref(kindRecord<MarketCacheState | null>(null));
  const errorsByKind = ref<KindRecord<string | null>>(kindRecord(null));
  const operationsByKind = ref<KindRecord<ExtensionOperation | null>>(
    kindRecord<ExtensionOperation | null>(null),
  );

  const marketSkills = ref<ExtensionsItem[]>([]);
  const marketMcp = ref<ExtensionsItem[]>([]);
  const marketPlugins = ref<ExtensionsItem[]>([]);
  const pluginMarkets = ref<ExtensionsItem[]>([]);

  const canLoad = computed(() => context.value !== null);
  const items = computed(() => itemsByKind.value[kind.value]);
  const loading = computed(() => loadingByKind.value[kind.value]);
  const busy = computed(() => busyByKind.value[kind.value]);
  const marketBusy = computed(() => searchBusyByKind.value[kind.value]);
  const error = computed(() => errorsByKind.value[kind.value]);
  const activeOperation = computed(() => operationsByKind.value[kind.value]);
  const opBusyId = computed(() => activeOperation.value?.id ?? null);
  const installedSkillGroups = computed(() => groupSkillItems(itemsByKind.value.skills));
  const marketSkillGroups = computed(() => groupSkillItems(marketSkills.value));

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

  async function refresh(
    target: ExtensionsKind,
    options: { silent?: boolean } = {},
  ): Promise<void> {
    if (!context.value) return;
    if (!options.silent) loadingByKind.value[target] = true;
    errorsByKind.value[target] = null;
    try {
      const out = await call<{ items?: ExtensionsItem[] }>("list", { kind: target });
      itemsByKind.value[target] = out.items ?? [];
    } catch (e) {
      errorsByKind.value[target] = errorText(e);
    } finally {
      if (!options.silent) loadingByKind.value[target] = false;
    }
  }

  async function load(target?: ExtensionsKind): Promise<void> {
    const targetKind = target ?? kind.value;
    kind.value = targetKind;
    await refresh(targetKind);
  }

  function operationSuccess(action: ExtensionAction, target: string): string {
    return i18n.global.t(`extensions.toast.${action}Success`, { target });
  }

  function operationFailure(target: string, message: string): string {
    return i18n.global.t("extensions.toast.operationFailed", { target, message });
  }

  async function runOperation(
    target: ExtensionsKind,
    action: ExtensionAction,
    id: string,
    label: string,
    operations: Array<() => Promise<unknown>>,
  ): Promise<void> {
    if (operations.length === 0) return;
    busyByKind.value[target] = true;
    errorsByKind.value[target] = null;
    operationsByKind.value[target] = {
      kind: target, action, id, label, completed: 0, total: operations.length,
    };
    try {
      for (let index = 0; index < operations.length; index += 1) {
        await operations[index]();
        operationsByKind.value[target] = {
          ...operationsByKind.value[target]!,
          completed: index + 1,
        };
      }
      await refresh(target, { silent: true });
      toast.success(operationSuccess(action, label));
    } catch (e) {
      const message = errorText(e);
      errorsByKind.value[target] = message;
      toast.error(operationFailure(label, message));
      await refresh(target, { silent: true }).catch(() => undefined);
    } finally {
      busyByKind.value[target] = false;
      operationsByKind.value[target] = null;
    }
  }

  async function runSearch(
    target: ExtensionsKind,
    op: string,
    query: string,
    setter: (items: ExtensionsItem[]) => void,
  ): Promise<void> {
    if (!query.trim()) {
      setter([]);
      return;
    }
    searchBusyByKind.value[target] = true;
    errorsByKind.value[target] = null;
    try {
      const out = await call<{ items?: ExtensionsItem[]; cache?: MarketCacheState }>(op, { query });
      setter(out.items ?? []);
      marketCacheByKind.value[target] = out.cache ?? null;
    } catch (e) {
      errorsByKind.value[target] = errorText(e);
    } finally {
      searchBusyByKind.value[target] = false;
    }
  }

  function clearMarketResults(target: ExtensionsKind): void {
    if (target === "skills") marketSkills.value = [];
    else if (target === "mcp") marketMcp.value = [];
    else marketPlugins.value = [];
    marketCacheByKind.value[target] = null;
  }

  async function toggle(
    item: ExtensionsItem,
    agent: "claude" | "codex",
    on: boolean,
  ): Promise<void> {
    const target = kind.value;
    await runOperation(target, "toggle", item.id, item.name, [
      () => call("toggle", { kind: target, id: item.id, agent, on }),
    ]);
  }

  async function remove(item: ExtensionsItem): Promise<void> {
    const target = kind.value;
    await runOperation(target, "remove", item.id, item.name, [
      () => call(target === "plugins" ? "plugin-uninstall" : "delete", {
        kind: target, id: item.id,
      }),
    ]);
  }

  async function installSkill(spec: string): Promise<void> {
    await runOperation("skills", "install", spec, spec, [
      () => call("skill-install", { spec }),
    ]);
  }

  async function updateSkill(item: ExtensionsItem): Promise<void> {
    const spec = skillUpdateSpec(item);
    await runOperation("skills", "update", item.id, item.name, [
      () => call("skill-update", { spec }),
    ]);
  }

  async function installSkillGroup(group: SkillGroup): Promise<void> {
    await runOperation("skills", "install", `market:${group.id}`, group.name,
      group.items.map((item) => () => call("skill-install", { spec: item.id })));
  }

  async function updateSkillGroup(group: SkillGroup): Promise<void> {
    await runOperation("skills", "update", `installed:${group.id}`, group.name,
      group.items.map((item) => () =>
        call("skill-update", { spec: skillUpdateSpec(item) })));
  }

  async function removeSkillGroup(group: SkillGroup): Promise<void> {
    await runOperation("skills", "remove", `installed:${group.id}`, group.name,
      group.items.map((item) =>
        () => call("delete", { kind: "skills", id: item.id })));
  }

  async function toggleSkillGroup(
    group: SkillGroup,
    agent: "claude" | "codex",
    on: boolean,
  ): Promise<void> {
    await runOperation(
      "skills", "toggle", `installed:${group.id}:${agent}`, group.name,
      group.items.map((item) =>
        () => call("toggle", { kind: "skills", id: item.id, agent, on })),
    );
  }

  async function addMcp(configJson: string, apps: string): Promise<void> {
    await runOperation("mcp", "add", "mcp-add", "MCP", [
      () => call("mcp-add", { apps, config: configJson }),
    ]);
  }

  async function pluginAction(
    op: "plugin-install" | "plugin-update",
    id: string,
  ): Promise<void> {
    await runOperation("plugins", op === "plugin-install" ? "install" : "update", id, id, [
      () => call(op, { id }),
    ]);
  }

  async function searchPlugins(query: string): Promise<void> {
    await runSearch("plugins", "plugin-search", query, (items) => {
      marketPlugins.value = items;
    });
  }

  async function searchSkills(query: string): Promise<void> {
    await runSearch("skills", "skill-search", query, (items) => {
      marketSkills.value = items;
    });
  }

  async function importDeeplink(url: string): Promise<void> {
    await runOperation("mcp", "import", "mcp-import", "MCP", [
      () => call("deeplink", { url }),
    ]);
  }

  async function addSkillRepo(source: string): Promise<void> {
    await runOperation("skills", "add", source, source, [
      () => call("skill-repo-add", { id: source }),
    ]);
  }

  async function searchMcp(query: string): Promise<void> {
    await runSearch("mcp", "mcp-search", query, (items) => {
      marketMcp.value = items;
    });
  }

  async function installMcpMarket(marketId: string): Promise<void> {
    await runOperation("mcp", "install", marketId, marketId, [
      () => call("mcp-market-install", { id: marketId }),
    ]);
  }

  async function loadPluginMarkets(): Promise<void> {
    searchBusyByKind.value.plugins = true;
    errorsByKind.value.plugins = null;
    try {
      const out = await call<{ items?: ExtensionsItem[] }>("plugin-market-list");
      pluginMarkets.value = out.items ?? [];
    } catch (e) {
      errorsByKind.value.plugins = errorText(e);
    } finally {
      searchBusyByKind.value.plugins = false;
    }
  }

  async function addPluginMarket(source: string): Promise<void> {
    await runOperation("plugins", "add", source, source, [
      () => call("plugin-market-add", { id: source }),
    ]);
    await loadPluginMarkets();
  }

  function setContext(workspace: string, runtimeId: string): void {
    context.value = workspace && runtimeId ? { workspace, runtimeId } : null;
  }

  return {
    kind, itemsByKind, items, loading, busy, error, canLoad,
    marketSkills, marketSkillGroups, installedSkillGroups, marketBusy,
    pluginMarkets, marketPlugins, opBusyId, marketMcp, activeOperation,
    operationsByKind, marketCacheByKind,
    clearMarketResults,
    installSkillGroup, updateSkill, updateSkillGroup, removeSkillGroup,
    toggleSkillGroup, searchSkills, searchPlugins, searchMcp,
    installMcpMarket, importDeeplink, addSkillRepo, loadPluginMarkets,
    addPluginMarket, load, toggle, remove, installSkill, addMcp,
    pluginAction, setContext,
  };
});
