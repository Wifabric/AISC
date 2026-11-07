<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useExtensionsStore } from "../../stores/extensions";
import { useSettingsStore } from "../../stores/settings";

type Agent = "claude" | "codex";
interface AuthState { revision: string; engines: Record<Agent, { enabled: boolean; configured: boolean; connection: string }> }
const emit = defineEmits<{ close: [] }>();
const { t } = useI18n();
const extensions = useExtensionsStore();
const settings = useSettingsStore();
const state = ref<AuthState | null>(null);
const token = ref("");
const agents = ref<Agent[]>([]);
const busy = ref(false);
const error = ref("");
const saved = ref(false);
let alive = true;
const contextKey = computed(() => JSON.stringify([extensions.context, settings.target?.kind, settings.target?.machine?.name]));
const ownerKey = contextKey.value;
const owner = extensions.context ? { ...extensions.context } : null;
watch(contextKey, () => { token.value = ""; state.value = null; emit("close"); });
onUnmounted(() => { alive = false; token.value = ""; });
const available = computed(() => !busy.value && !extensions.busyByKind.mcp && ownerKey === contextKey.value);
const codes: Record<string, string> = {
  AISC_ERR_GITHUB_AUTH_CUSTOM_CONFIG: "custom", AISC_ERR_GITHUB_AUTH_CONFLICT: "conflict",
  AISC_ERR_GITHUB_AUTH_DISABLED: "disabledError", AISC_ERR_GITHUB_AUTH_NOT_FOUND: "missing",
  AISC_ERR_GITHUB_AUTH_INVALID_REQUEST: "invalid",
};
async function execute(op: "github-auth-status" | "github-auth-save" | "github-auth-check") {
  if (!owner || !available.value) return;
  busy.value = true; error.value = ""; saved.value = false;
  const reserved = extensions.busyByKind;
  if (op !== "github-auth-status") reserved.mcp = true;
  try {
    const request = op === "github-auth-status" ? {} : { revision: state.value?.revision, agents: [...agents.value],
      ...(op === "github-auth-save" ? { token: token.value } : {}) };
    const pending = extensions.githubAuth(owner, op, request);
    // Never keep a credential in an operation history/retry recipe or draft
    // after dispatch. A failed save requires deliberate re-entry.
    token.value = "";
    const result = await pending as AuthState;
    if (!alive || ownerKey !== contextKey.value) return;
    state.value = result;
    if (op === "github-auth-status") agents.value = (["claude", "codex"] as Agent[]).filter(a => result.engines[a].enabled);
    if (op === "github-auth-save") { saved.value = true; await extensions.refreshKind("mcp", { silent: true }); }
  } catch (e) {
    if (alive && ownerKey === contextKey.value) error.value = t(`githubAuth.${codes[(e as { code?: string })?.code ?? ""] ?? "failed"}`);
  } finally {
    token.value = "";
    if (op !== "github-auth-status") reserved.mcp = false;
    busy.value = false;
  }
}
onMounted(() => { void execute("github-auth-status"); });
</script>

<template>
  <section class="github-auth" data-testid="github-auth" :aria-label="t('githubAuth.title')">
    <div class="auth-heading"><strong>{{ t("githubAuth.title") }}</strong><button type="button" class="ui-button sm" @click="emit('close')">{{ t("githubAuth.close") }}</button></div>
    <p>{{ t("githubAuth.notice") }}</p>
    <p v-if="busy" role="status">{{ t("githubAuth.working") }}</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="saved" role="status">{{ t("githubAuth.saved") }}</p>
    <template v-if="state">
      <label v-for="agent in (['claude', 'codex'] as const)" :key="agent" class="auth-engine">
        <input v-model="agents" type="checkbox" :value="agent" :disabled="!available || !state.engines[agent].enabled" />
        <strong>{{ agent === "claude" ? "Claude" : "Codex" }}</strong>
        <span>{{ t(state.engines[agent].enabled ? (state.engines[agent].configured ? "githubAuth.configured" : "githubAuth.notConfigured") : "githubAuth.disabled") }}</span>
        <span>{{ t(`githubAuth.result.${state.engines[agent].connection}`) }}</span>
      </label>
      <form @submit.prevent="execute('github-auth-save')">
        <label for="github-mcp-token">{{ t("githubAuth.token") }}</label>
        <input id="github-mcp-token" v-model="token" class="ui-input" type="password" autocomplete="off" spellcheck="false" :disabled="!available" />
        <div class="auth-actions">
          <button type="submit" class="ui-button primary" :disabled="!available || !agents.length || token.length < 8">{{ t("githubAuth.save") }}</button>
          <button type="button" class="ui-button" :disabled="!available || !agents.length" @click="execute('github-auth-check')">{{ t("githubAuth.check") }}</button>
          <button type="button" class="ui-button" :disabled="!available" @click="execute('github-auth-status')">{{ t("githubAuth.reload") }}</button>
        </div>
      </form>
    </template>
    <button v-else-if="!busy" type="button" class="ui-button" @click="execute('github-auth-status')">{{ t("githubAuth.reload") }}</button>
  </section>
</template>

<style scoped>
.github-auth { padding: var(--space-3); border-top: 1px solid var(--border); display: grid; gap: var(--space-2); }
.auth-heading,.auth-actions,.auth-engine { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.auth-heading { justify-content: space-between; }
.github-auth p { margin: 0; color: var(--text-muted); }
.github-auth form { display: grid; gap: var(--space-2); }
</style>
