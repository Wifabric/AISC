import { computed, ref } from "vue";
import { defineStore } from "pinia";
import * as ipc from "../lib/ipc";
import type { ExtensionModuleDefinition, ExtensionModuleDocument, ExtensionModuleMember } from "../lib/ipc";
import { BUILTIN_EXTENSION_MODULES } from "../features/workspace-explorer/moduleCatalog";

export const moduleMemberKey = (member: ExtensionModuleMember) => `${member.kind}:${member.identity}`;
export const copyModule = (module: ExtensionModuleDefinition): ExtensionModuleDefinition =>
  JSON.parse(JSON.stringify(module)) as ExtensionModuleDefinition;

export const useExtensionModulesStore = defineStore("extensionModules", () => {
  const document = ref<ExtensionModuleDocument | null>(null);
  const busy = ref(false);
  const error = ref<string | null>(null);
  const modules = computed(() => [
    ...BUILTIN_EXTENSION_MODULES.filter(m => !document.value?.hidden_builtin_ids.includes(m.id)),
    ...document.value?.definitions ?? [],
  ]);
  const isBuiltin = (id: string) => BUILTIN_EXTENSION_MODULES.some(m => m.id === id);
  const message = (e: unknown) => {
    const err = e as { technical_detail?: string; message?: string };
    return err.technical_detail || err.message || String(e);
  };
  async function load() {
    if (busy.value) return;
    busy.value = true; error.value = null;
    try { document.value = await ipc.loadExtensionModules(); }
    catch (e) { document.value = null; error.value = message(e); }
    finally { busy.value = false; }
  }
  async function persist(next: ExtensionModuleDocument): Promise<boolean> {
    if (busy.value || !document.value) return false;
    busy.value = true; error.value = null;
    try {
      document.value = await ipc.saveExtensionModules(document.value.revision, next);
      return true;
    } catch (e) { error.value = message(e); return false; }
    finally { busy.value = false; }
  }
  async function save(module: ExtensionModuleDefinition) {
    if (!document.value || isBuiltin(module.id)) return false;
    const definition = copyModule(module);
    definition.name = definition.name.trim();
    const seen = new Set<string>();
    definition.members = definition.members.filter(m => {
      const key = moduleMemberKey(m);
      if (seen.has(key)) return false;
      seen.add(key); return true;
    });
    return persist({ ...document.value, definitions: [
      ...document.value.definitions.filter(m => m.id !== definition.id), definition,
    ] });
  }
  async function remove(id: string) {
    if (!document.value) return false;
    return persist({ ...document.value,
      definitions: document.value.definitions.filter(m => m.id !== id),
      hidden_builtin_ids: isBuiltin(id) ? [...new Set([...document.value.hidden_builtin_ids, id])] : document.value.hidden_builtin_ids,
    });
  }
  async function restoreBuiltins() {
    if (!document.value) return false;
    return persist({ ...document.value, hidden_builtin_ids: [] });
  }
  return { document, modules, busy, error, load, save, remove, isBuiltin, restoreBuiltins };
});
