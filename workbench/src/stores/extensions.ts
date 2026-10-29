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
import { writeText } from "@tauri-apps/plugin-clipboard-manager";

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

export interface ExtensionOperationRecord {
  operationId: string;
  workspace: string;
  runtimeId: string;
  kind: ExtensionsKind;
  action: ExtensionAction;
  id: string;
  label: string;
  attempt: number;
  startedAt: string;
  finishedAt: string;
  status: "success" | "failed" | "unknown";
  diagnostic: string;
}

export interface MarketCacheState {
  source: "remote" | "cache" | string;
  cached: boolean;
  query?: string;
  fetched_at?: number | string;
  error?: string;
}

export interface ExtensionUpdateItem {
  kind: ExtensionsKind | string;
  id: string;
  name?: string;
  status: string;
  update_available: boolean;
  latest_version?: string;
  latest_git_commit_sha?: string;
  current_version?: string;
  current_git_commit_sha?: string;
  reason?: string;
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
  let contextGeneration = 0;

  // Preview b1: every asset owns its list and async state. A skill install
  // can refresh the skills list without blanking/flickering MCP or plugins.
  const itemsByKind = ref<KindRecord<ExtensionsItem[]>>(
    kindRecord<ExtensionsItem[]>([]),
  );
  const loadingByKind = ref(kindRecord(false));
  const busyByKind = ref(kindRecord(false));
  const searchBusyByKind = ref(kindRecord(false));
  const pluginMarketsBusy = ref(false);
  const pluginMarketsError = ref<string | null>(null);
  const skillRepos = ref<ExtensionsItem[]>([]);
  const skillReposBusy = ref(false);
  const skillReposError = ref<string | null>(null);
  let skillReposGeneration = 0;
  let pluginMarketsGeneration = 0;
  const searchGeneration = kindRecord(0);
  const marketCacheByKind = ref<KindRecord<MarketCacheState | null>>(
    kindRecord<MarketCacheState | null>(null),
  );
  const updateItemsByKind = ref<KindRecord<Record<string, ExtensionUpdateItem>>>(
    emptyUpdateItems(),
  );
  const updatesBusy = ref(false);
  const updatesError = ref<string | null>(null);
  const errorsByKind = ref<KindRecord<string | null>>(kindRecord(null));
  const operationsByKind = ref<KindRecord<ExtensionOperation | null>>(
    kindRecord<ExtensionOperation | null>(null),
  );

  const marketSkills = ref<ExtensionsItem[]>([]);
  const marketMcp = ref<ExtensionsItem[]>([]);
  const marketPlugins = ref<ExtensionsItem[]>([]);
  const pluginMarkets = ref<ExtensionsItem[]>([]);
  const operationLog = ref<ExtensionOperationRecord[]>([]);
  let logSequence = 0;
  const retryRecipes = new Map<string, { token: string | null; run: () => Promise<unknown> }>();

  function diagnosticText(value: string): string {
    const redacted = value
      .replace(/(Bearer\s+)[^\s,;]+/gi, "$1[redacted]")
      .replace(/((?:token|password|secret|api[_-]?key|authorization)[\s"']*[:=]\s*)("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/gi, "$1[redacted]")
      .replace(/((?:token|password|secret|api[_-]?key|authorization)[\s"']*[:=][\s"']*)[^\s,"';&]+/gi, "$1[redacted]")
      .replace(/(https?:\/\/)[^\s/@]+:[^\s/@]+@/gi, "$1[redacted]@");
    const bytes = new TextEncoder().encode(redacted);
    return bytes.length <= 8192 ? redacted
      : new TextDecoder().decode(bytes.slice(0, 8150)) + "\n[truncated]";
  }

  function logOperation(target: ExtensionsKind, action: ExtensionAction, id: string,
    label: string, startedAt: string, status: ExtensionOperationRecord["status"],
    diagnostic: string, run: () => Promise<unknown>, attempt = 1): void {
    if (!context.value) return;
    const operationId = String(++logSequence);
    operationLog.value.push({ operationId, ...context.value, kind: target, action,
      id, label, attempt, startedAt, finishedAt: new Date().toISOString(), status,
      diagnostic: diagnosticText(diagnostic) });
    if (status === "failed") retryRecipes.set(operationId, { token: contextToken(), run });
    while (operationLog.value.length > 100) {
      retryRecipes.delete(operationLog.value.shift()!.operationId);
    }
  }

  function canRetryOperation(operationId: string): boolean {
    const recipe = retryRecipes.get(operationId);
    return !!recipe && isCurrentContext(recipe.token);
  }

  async function retryOperation(operationId: string): Promise<void> {
    const record = operationLog.value.find((row) => row.operationId === operationId);
    const recipe = retryRecipes.get(operationId);
    if (!record || !recipe || !canRetryOperation(operationId) || busyByKind.value[record.kind]) return;
    retryRecipes.delete(operationId);
    await runOperation(record.kind, record.action, record.id, record.label,
      [recipe.run], [record.id], record.attempt + 1);
  }

  async function copyOperationDiagnostic(operationId: string): Promise<void> {
    const record = operationLog.value.find((row) => row.operationId === operationId);
    if (!record) return;
    try {
      await writeText(diagnosticText(JSON.stringify(record, null, 2)));
      toast.success(i18n.global.t("extensions.log.copied"));
    } catch (e) {
      toast.error(i18n.global.t("extensions.log.copyFailed", { message: errorText(e) }));
    }
  }




  function emptyUpdateItems(): KindRecord<Record<string, ExtensionUpdateItem>> {
    return { skills: {}, mcp: {}, plugins: {} };
  }

  function resetMarketState(): void {
    itemsByKind.value = { skills: [], mcp: [], plugins: [] };
    marketSkills.value = [];
    marketMcp.value = [];
    marketPlugins.value = [];
    pluginMarkets.value = [];
    skillRepos.value = [];
    skillReposError.value = null;
    skillReposBusy.value = false;
    skillReposGeneration += 1;
    marketCacheByKind.value = kindRecord<MarketCacheState | null>(null);
    updateItemsByKind.value = emptyUpdateItems();
    updatesError.value = null;
    updatesBusy.value = false;
    operationLog.value = [];
    retryRecipes.clear();
    loadingByKind.value = kindRecord(false);
    busyByKind.value = kindRecord(false);
    searchBusyByKind.value = kindRecord(false);
    pluginMarketsBusy.value = false;
    pluginMarketsError.value = null;
    pluginMarketsGeneration += 1;
    errorsByKind.value = kindRecord<string | null>(null);
    operationsByKind.value = kindRecord<ExtensionOperation | null>(null);
  }

  function clearUpdateSignals(target: ExtensionsKind, ids: string[]): void {
    const remaining = { ...updateItemsByKind.value[target] };
    for (const id of ids) delete remaining[id];
    updateItemsByKind.value = {
      ...updateItemsByKind.value,
      [target]: remaining,
    };
  }

  function contextToken(): string | null {
    if (!context.value) return null;
    return `${contextGeneration}:${context.value.workspace}:${context.value.runtimeId}`;
  }

  function isCurrentContext(token: string | null): boolean {
    return token !== null && token === contextToken();
  }

  const canLoad = computed(() => context.value !== null);
  const items = computed(() => itemsByKind.value[kind.value]);
  const loading = computed(() => loadingByKind.value[kind.value]);
  const busy = computed(() => busyByKind.value[kind.value]);
  const marketBusy = computed(() => searchBusyByKind.value[kind.value]
    || (kind.value === "plugins" && pluginMarketsBusy.value));
  const marketCache = computed(() => marketCacheByKind.value[kind.value]);
  const error = computed(() => errorsByKind.value[kind.value]);
  const updateItems = computed(() => updateItemsByKind.value[kind.value]);
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
    const token = contextToken();
    if (!options.silent) loadingByKind.value[target] = true;
    errorsByKind.value[target] = null;
    try {
      const out = await call<{ items?: ExtensionsItem[] }>("list", { kind: target });
      if (!isCurrentContext(token)) return;
      itemsByKind.value[target] = out.items ?? [];
    } catch (e) {
      if (!isCurrentContext(token)) return;
      errorsByKind.value[target] = errorText(e);
    } finally {
      if (isCurrentContext(token) && !options.silent) loadingByKind.value[target] = false;
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
    affectedIds: string[] = [id],
    attempt = 1,
  ): Promise<void> {
    if (!context.value || operations.length === 0 || busyByKind.value[target]) return;
    const token = contextToken();
    busyByKind.value[target] = true;
    errorsByKind.value[target] = null;
    operationsByKind.value[target] = {
      kind: target, action, id, label, completed: 0, total: operations.length,
    };
    const failures: string[] = [];
    try {
      for (let index = 0; index < operations.length; index += 1) {
        if (!isCurrentContext(token)) return;
        const started = new Date().toISOString();
        const run = operations[index]!;
        const itemId = affectedIds[index] ?? id;
        try {
          await run();
          if (!isCurrentContext(token)) return;
          logOperation(target, action, itemId, label, started, "success", "", run, attempt);
          if (action !== "toggle") clearUpdateSignals(target, [itemId]);
        } catch (e) {
          if (!isCurrentContext(token)) return;
          const message = errorText(e);
          const code = (e as { code?: string })?.code ?? "";
          const unknown = ["WB_ERR_CLI_TIMEOUT", "WB_ERR_CLI_PROTOCOL", "WB_ERR_CLI_CANCELLED"].includes(code)
            || /timed?\s*out|timeout|non-envelope|connection.*closed|unexpected.*eof/i.test(message);
          logOperation(target, action, itemId, label, started, unknown ? "unknown" : "failed", message, run, attempt);
          failures.push(operations.length === 1 ? message : `${itemId}: ${message}`);
        }
        operationsByKind.value[target] = {
          ...operationsByKind.value[target]!, completed: index + 1,
        };
      }
      await refresh(target, { silent: true });
      if (!isCurrentContext(token)) return;
      if (failures.length) {
        errorsByKind.value[target] = failures.join("; ");
        toast.error(operationFailure(label, failures.join("; ")));
      } else {
        toast.success(operationSuccess(action, label));
      }
    } finally {
      if (isCurrentContext(token)) {
        busyByKind.value[target] = false;
        operationsByKind.value[target] = null;
      }
    }
  }

  async function runSearch(
    target: ExtensionsKind,
    op: string,
    query: string,
    setter: (items: ExtensionsItem[]) => void,
  ): Promise<void> {
    if (!query.trim()) { clearMarketResults(target); return; }
    if (!context.value) return;
    const token = contextToken();
    const generation = ++searchGeneration[target];
    const current = () => isCurrentContext(token) && generation === searchGeneration[target];
    setter([]);
    marketCacheByKind.value[target] = null;
    searchBusyByKind.value[target] = true;
    errorsByKind.value[target] = null;
    try {
      const out = await call<{ items?: ExtensionsItem[]; cache?: MarketCacheState }>(op, { query });
      if (!current()) return;
      setter(out.items ?? []);
      marketCacheByKind.value[target] = out.cache ?? null;
    } catch (e) {
      if (current()) errorsByKind.value[target] = errorText(e);
    } finally {
      if (current()) searchBusyByKind.value[target] = false;
    }
  }

  function clearMarketResults(target: ExtensionsKind): void {
    searchGeneration[target] += 1;
    if (target === "skills") marketSkills.value = [];
    else if (target === "mcp") marketMcp.value = [];
    else marketPlugins.value = [];
    marketCacheByKind.value[target] = null;
    searchBusyByKind.value[target] = false;
    errorsByKind.value[target] = null;
  }

  async function discoverRecommendation(target: ExtensionsKind, query: string): Promise<void> {
    kind.value = target;
    if (!context.value) return;
    const token = contextToken();
    const generation = ++searchGeneration[target];
    await refresh(target);
    if (!isCurrentContext(token) || generation !== searchGeneration[target]) return;
    if (target === "skills") await searchSkills(query);
    else if (target === "mcp") await searchMcp(query);
    else await searchPlugins(query);
  }

  async function checkUpdates(): Promise<void> {
    if (!context.value) return;
    const token = contextToken();
    updateItemsByKind.value = emptyUpdateItems();
    updatesBusy.value = true;
    updatesError.value = null;
    try {
      const out = await call<{ items?: ExtensionUpdateItem[] }>("updates-check");
      if (!isCurrentContext(token)) return;
      const next = emptyUpdateItems();
      for (const item of out.items ?? []) {
        if (item.kind === "skills" || item.kind === "mcp" || item.kind === "plugins") {
          next[item.kind][item.id] = item;
        }
      }
      updateItemsByKind.value = next;
    } catch (e) {
      if (!isCurrentContext(token)) return;
      updatesError.value = errorText(e);
    } finally {
      if (isCurrentContext(token)) updatesBusy.value = false;
    }
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

  async function runSkillGroupOperation(
    group: SkillGroup,
    action: "install" | "update",
    op: "skill-install-group" | "skill-update-group",
    successStatus: "installed" | "updated",
  ): Promise<void> {
    const specs = group.items.map((item) => action === "install" ? item.id : skillUpdateSpec(item));
    if (!context.value || specs.length === 0 || busyByKind.value.skills) return;
    const token = contextToken();
    busyByKind.value.skills = true;
    errorsByKind.value.skills = null;
    operationsByKind.value.skills = {
      kind: "skills", action,
      id: `${action === "install" ? "market" : "installed"}:${group.id}`,
      label: group.name, completed: 0, total: specs.length,
    };
    const started = new Date().toISOString();
    let loggedResults = false;
    try {
      const result = await call<{
        total?: number;
        completed?: number;
        items?: Array<{ spec: string; status: string; error?: string }>;
      }>(op, { specs });
      if (!isCurrentContext(token)) return;
      loggedResults = true;
      for (const [index, spec] of specs.entries()) {
        const identity = (value: string) => {
          const colon = value.lastIndexOf(":");
          return colon < 0 ? value : value.slice(0, colon).toLowerCase() + value.slice(colon);
        };
        const item = result.items?.find((row) => identity(row.spec) === identity(spec));
        const status = item?.status === successStatus ? "success"
          : ["failed", "source_failed", "missing", "state_unavailable"].includes(item?.status ?? "") ? "failed" : "unknown";
        const itemId = group.items[index]!.id;
        logOperation("skills", action, itemId, spec, started, status,
          item?.error || (status === "unknown" ? `${item?.status ?? "unknown"}: refresh installed state before retry` : ""),
          () => call(action === "install" ? "skill-install" : "skill-update", { spec }));
        if (status === "success") clearUpdateSignals("skills", [itemId]);
      }
      const total = result.total ?? specs.length;
      const completed = result.completed ?? total;
      operationsByKind.value.skills = {
        ...operationsByKind.value.skills!, completed,
      };
      if (completed < total) {
        const failures = (result.items ?? [])
          .filter((item) => item.status !== successStatus)
          .map((item) => `${item.spec}: ${item.error || item.status}`);
        throw new Error(
          `${successStatus} ${completed}/${total}; ${failures.join("; ") || "no item detail"}`,
        );
      }
      await refresh("skills", { silent: true });
      if (!isCurrentContext(token)) return;
      toast.success(operationSuccess(action, group.name));
    } catch (e) {
      if (!isCurrentContext(token)) return;
      const message = errorText(e);
      if (!loggedResults) {
        for (const [index, spec] of specs.entries()) {
          logOperation("skills", action, group.items[index]!.id, spec, started, "unknown", message,
            () => call(action === "install" ? "skill-install" : "skill-update", { spec }));
        }
      }
      toast.error(operationFailure(group.name, message));
      await refresh("skills", { silent: true }).catch(() => undefined);
      if (!isCurrentContext(token)) return;
      errorsByKind.value.skills = message;
    } finally {
      if (isCurrentContext(token)) {
        busyByKind.value.skills = false;
        operationsByKind.value.skills = null;
      }
    }
  }

  async function installSkillGroup(group: SkillGroup): Promise<void> {
    await runSkillGroupOperation(
      group, "install", "skill-install-group", "installed",
    );
  }

  async function updateSkillGroup(group: SkillGroup): Promise<void> {
    await runSkillGroupOperation(
      group, "update", "skill-update-group", "updated",
    );
  }

  async function removeSkillGroup(group: SkillGroup): Promise<void> {
    await runOperation("skills", "remove", `installed:${group.id}`, group.name,
      group.items.map((item) =>
        () => call("delete", { kind: "skills", id: item.id })),
      group.items.map((item) => item.id));
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

  async function loadSkillRepos(): Promise<void> {
    if (!context.value) return;
    const token = contextToken();
    const generation = ++skillReposGeneration;
    const current = () => isCurrentContext(token) && generation === skillReposGeneration;
    skillReposBusy.value = true;
    skillReposError.value = null;
    try {
      const out = await call<{ items?: ExtensionsItem[] }>("skill-repos-list");
      if (!current()) return;
      skillRepos.value = out.items ?? [];
    } catch (e) {
      if (current()) skillReposError.value = errorText(e);
    } finally {
      if (current()) skillReposBusy.value = false;
    }
  }

  async function removeSkillRepo(id: string): Promise<void> {
    await runOperation("skills", "remove", `repo:${id}`, id, [
      () => call("skill-repo-remove", { id }),
    ]);
    await loadSkillRepos();
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
    if (!context.value) return;
    const token = contextToken();
    const generation = ++pluginMarketsGeneration;
    const current = () => isCurrentContext(token) && generation === pluginMarketsGeneration;
    pluginMarketsBusy.value = true;
    pluginMarketsError.value = null;
    try {
      const out = await call<{ items?: ExtensionsItem[] }>("plugin-market-list");
      if (!current()) return;
      pluginMarkets.value = out.items ?? [];
    } catch (e) {
      if (current()) pluginMarketsError.value = errorText(e);
    } finally {
      if (current()) pluginMarketsBusy.value = false;
    }
  }

  async function addPluginMarket(source: string): Promise<void> {
    await runOperation("plugins", "add", source, source, [
      () => call("plugin-market-add", { id: source }),
    ]);
    await loadPluginMarkets();
  }

  async function removePluginMarket(id: string): Promise<void> {
    await runOperation("plugins", "remove", `market:${id}`, id, [
      () => call("plugin-market-remove", { id }),
    ]);
    await loadPluginMarkets();
  }

  function setContext(workspace: string, runtimeId: string): void {
    const next = workspace && runtimeId ? { workspace, runtimeId } : null;
    const changed = context.value?.workspace !== next?.workspace
      || context.value?.runtimeId !== next?.runtimeId;
    context.value = next;
    if (changed) {
      contextGeneration += 1;
      resetMarketState();
    }
  }

  return {
    kind, itemsByKind, items, loading, busy, error, canLoad,
    marketSkills, marketSkillGroups, installedSkillGroups, marketBusy,
    pluginMarkets, pluginMarketsError, skillRepos, skillReposBusy,
    skillReposError, marketPlugins, opBusyId, marketMcp, activeOperation,
    operationsByKind, operationLog, canRetryOperation, retryOperation, copyOperationDiagnostic,
    marketCacheByKind, marketCache, updateItemsByKind, updateItems,
    updatesBusy, updatesError,
    clearMarketResults, checkUpdates, discoverRecommendation,
    installSkillGroup, updateSkill, updateSkillGroup, removeSkillGroup,
    toggleSkillGroup, searchSkills, searchPlugins, searchMcp,
    installMcpMarket, importDeeplink, addSkillRepo, loadSkillRepos,
    removeSkillRepo, loadPluginMarkets, addPluginMarket, removePluginMarket,
    load, toggle, remove, installSkill, addMcp,
    pluginAction, setContext,
  };
});
