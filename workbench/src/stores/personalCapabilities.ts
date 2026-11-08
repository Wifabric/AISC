import { computed, ref, watch } from "vue";
import { useRuntimeStore } from "./runtime";
import { topicCall, type PersonalCapabilityDraft, type PersonalProfile, type PersonalRevision, type PersonalTemplate } from "../lib/ipc";

import { defineStore } from "pinia";

export const usePersonalCapabilitiesStore = defineStore("personalCapabilities", () => {
const runtime = useRuntimeStore();
const templates = ref<PersonalTemplate[]>([]);
const profiles = ref<PersonalProfile[]>([]);
const draft = ref<PersonalCapabilityDraft | null>(null);
const error = ref("");
const notice = ref("");
const loading = ref(false);
const busy = ref(false);
const loaded = ref(false);
const historical = ref(0);
let epoch = 0;
let request = 0;
let original = "";
const dirty = computed(() => !!draft.value && JSON.stringify(draft.value) !== original);
const selected = computed(() => profiles.value.find(p => p.id === draft.value?.id));
const oldRevision = computed(() => selected.value?.history.find(r => r.revision === historical.value));
const latest = (p: PersonalProfile) => p.history[p.history.length - 1]!;
const message = (e: unknown) => {
  const value = e as { message?: string; technical_detail?: string };
  return value.technical_detail || value.message || String(e);
};

async function load() {
  if (!runtime.workspace || busy.value) return;
  const token = epoch, turn = ++request;
  const workspace = runtime.workspace;
  loading.value = true; error.value = "";
  try {
    const result = await topicCall<{ templates: PersonalTemplate[]; profiles: PersonalProfile[] }>({ workspace, operation: "personal-list" });
    if (token !== epoch || turn !== request) return;
    templates.value = result.templates; profiles.value = result.profiles; loaded.value = true;
    // A refresh never overwrites an unsaved draft, including a conflict draft.
    if (draft.value?.id && !dirty.value) {
      const current = profiles.value.find(p => p.id === draft.value?.id);
      if (current) edit(current);
    }
  } catch (e) { if (token === epoch && turn === request) { error.value = message(e); loaded.value = false; } }
  finally { if (token === epoch && turn === request) loading.value = false; }
}
watch([() => runtime.workspace, () => runtime.id], () => {
  epoch++; request++; templates.value = []; profiles.value = []; draft.value = null;
  original = ""; error.value = ""; notice.value = ""; historical.value = 0;
  busy.value = false; loading.value = false; loaded.value = false;
  void load();
}, { immediate: true });

function edit(profile: PersonalProfile) {
  const value = latest(profile);
  draft.value = { id: profile.id, template_id: profile.template_id, expected_revision: value.revision,
    name: value.name, rules: value.rules, skill: value.skill, reason: "", verification: "待验证", enabled: value.enabled };
  original = JSON.stringify(draft.value); historical.value = 0; notice.value = "";
}
function create(template?: PersonalTemplate) {
  draft.value = { id: "", template_id: template?.id ?? "custom", expected_revision: 0,
    name: template ? `${template.name} · 我的副本` : "", rules: template?.rules ?? "", skill: template?.skill ?? "",
    reason: "建立个人能力", verification: "待验证", enabled: false };
  original = ""; historical.value = 0; notice.value = "";
}
function discard() {
  if (selected.value) edit(selected.value);
  else { draft.value = null; original = ""; }
}
function restore(revision: PersonalRevision) {
  if (!draft.value) return;
  Object.assign(draft.value, { name: revision.name, rules: revision.rules, skill: revision.skill,
    reason: `恢复第 ${revision.revision} 版内容`, verification: "恢复后的内容待验证" });
  // Keep the current enable choice and optimistic revision; restore appends.
}
async function save() {
  if (!draft.value || !runtime.workspace || busy.value || !loaded.value) return;
  const token = epoch;
  const workspace = runtime.workspace;
  busy.value = true; error.value = ""; notice.value = ""; ++request; loading.value = false;
  try {
    const result = await topicCall<{ profile: PersonalProfile }>({ workspace, operation: "personal-save", personal: { ...draft.value } });
    if (token !== epoch) return;
    profiles.value = [result.profile, ...profiles.value.filter(p => p.id !== result.profile.id)];
    edit(result.profile);
    notice.value = latest(result.profile).enabled ? "已保存。之后新建的 Claude / Codex 会话会注入这一版本。" : "已保存，当前未启用注入。";
  } catch (e) { if (token === epoch) error.value = message(e); }
  finally { if (token === epoch) busy.value = false; }
}
function openAgent(agent: "claude" | "codex") {
  if (dirty.value || busy.value) return;
  if (!runtime.createTab(agent)) error.value = "无法新建会话，请检查运行环境和会话数量。";
}

return { templates, profiles, draft, error, notice, loading, busy, loaded, historical, dirty, selected, oldRevision, latest, load, edit, create, discard, restore, save, openAgent };
});
