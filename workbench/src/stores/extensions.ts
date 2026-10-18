/**
 * b5 (2.1.16): Extensions store — skills / MCP / plugins unified management.
 * Data plane boundary (F-A01): components never import ipc directly.
 */
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as ipc from "../lib/ipc";
import type { ExtensionsItem } from "../lib/ipc";

export type ExtensionsKind = "skills" | "mcp" | "plugins";

export const useExtensionsStore = defineStore("extensions", () => {
  const kind = ref<ExtensionsKind>("skills");
  const items = ref<ExtensionsItem[]>([]);
  const loading = ref(false);
  const busy = ref(false);
  const error = ref<string | null>(null);

  const context = ref<{ workspace: string; runtimeId: string } | null>(null);
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
      error.value = String(e);
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
      error.value = String(e);
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
      error.value = String(e);
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
      error.value = String(e);
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
      error.value = String(e);
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
      error.value = String(e);
    } finally {
      busy.value = false;
    }
  }

  function setContext(workspace: string, runtimeId: string): void {
    context.value = workspace && runtimeId ? { workspace, runtimeId } : null;
  }

  return {
    kind, items, loading, busy, error, canLoad,
    load, toggle, remove, installSkill, addMcp, pluginAction, setContext,
  };
});
