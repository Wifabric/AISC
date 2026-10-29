<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { useExtensionsStore } from "../../stores/extensions";

const { t } = useI18n();
const store = useExtensionsStore();
const skillSource = ref("");
const marketSource = ref("");
const pending = ref<null | { type: "skill" | "plugin"; id: string }>(null);

async function addSkillRepo(): Promise<void> {
  const value = skillSource.value.trim();
  if (!value || store.busy) return;
  await store.addSkillRepo(value);
  skillSource.value = "";
  await store.loadSkillRepos();
}

async function addPluginMarket(): Promise<void> {
  const value = marketSource.value.trim();
  if (!value || store.busy) return;
  await store.addPluginMarket(value);
  marketSource.value = "";
  await store.loadPluginMarkets();
}

async function confirmRemove(): Promise<void> {
  const target = pending.value;
  if (!target || store.busy) return;
  pending.value = null;
  if (target.type === "skill") await store.removeSkillRepo(target.id);
  else await store.removePluginMarket(target.id);
}
</script>

<template>
  <div class="extension-source-manager" data-testid="extension-source-manager">
    <section>
      <header>
        <h3>{{ t("extensions.sources.skillRepos") }}</h3>
        <button type="button" :disabled="store.skillReposBusy" @click="store.loadSkillRepos()">
          {{ t("common.refresh") }}
        </button>
      </header>

      <form class="source-form" @submit.prevent="addSkillRepo">
        <!-- Keep the visible control type=button for testable direct activation; Enter still submits the form. -->
        <input
          v-model="skillSource"
          type="text"
          :placeholder="t('extensions.skillLink')"
          :aria-label="t('extensions.skillLink')"
          data-testid="skill-repo-add"
          :disabled="store.busy"
        >
        <button
          type="button"
          data-testid="skill-repo-add-btn"
          :disabled="!skillSource.trim() || store.busy || store.skillReposBusy"
          @click="addSkillRepo"
        >{{ t("extensions.sources.add") }}</button>
      </form>

      <p v-if="store.skillReposError" class="source-error" role="alert">{{ store.skillReposError }}</p>
      <div class="source-list" data-testid="skill-source-list">
        <div
          v-for="repo in store.skillRepos"
          :key="repo.id"
          class="source-row"
          :data-testid="'skill-source-row-' + repo.id"
        >
          <div class="source-copy">
            <strong>{{ repo.name || repo.id }}</strong>
            <span>{{ repo.branch || "-" }}</span>
          </div>
          <span class="source-state" :data-enabled="repo.enabled ? 'true' : 'false'">
            {{ repo.enabled ? t("extensions.sources.enabled") : t("extensions.sources.disabled") }}
          </span>
          <button
            type="button"
            data-testid="skill-repo-remove"
            :disabled="store.busy"
            @click="pending = { type: 'skill', id: repo.id }"
          >{{ t("extensions.sources.remove") }}</button>
        </div>
        <p v-if="!store.skillRepos.length" class="source-empty">{{ t("extensions.sources.noSkillRepos") }}</p>
      </div>
    </section>

    <section>
      <header>
        <h3>{{ t("extensions.sources.pluginMarkets") }}</h3>
        <button type="button" :disabled="store.pluginMarketsBusy" @click="store.loadPluginMarkets()">
          {{ t("common.refresh") }}
        </button>
      </header>

      <form class="source-form" @submit.prevent="addPluginMarket">
        <!-- Keep the visible control type=button for testable direct activation; Enter still submits the form. -->
        <input
          v-model="marketSource"
          type="text"
          :placeholder="t('extensions.pluginMarketLink')"
          :aria-label="t('extensions.pluginMarketLink')"
          data-testid="plugin-market-add"
          :disabled="store.busy"
        >
        <button
          type="button"
          data-testid="plugin-market-add-btn"
          :disabled="!marketSource.trim() || store.busy || store.pluginMarketsBusy"
          @click="addPluginMarket"
        >{{ t("extensions.sources.add") }}</button>
      </form>

      <p v-if="store.pluginMarketsError" class="source-error" role="alert">{{ store.pluginMarketsError }}</p>
      <div class="source-list" data-testid="plugin-source-list">
        <div
          v-for="market in store.pluginMarkets"
          :key="market.id"
          class="source-row"
          :data-testid="'plugin-source-row-' + market.id"
        >
          <div class="source-copy">
            <strong>{{ market.name || market.id }}</strong>
            <span>{{ market.source || market.repo || "-" }}</span>
          </div>
          <button
            type="button"
            data-testid="plugin-market-remove"
            :disabled="store.busy"
            @click="pending = { type: 'plugin', id: market.id }"
          >{{ t("extensions.sources.remove") }}</button>
        </div>
        <p v-if="!store.pluginMarkets.length" class="source-empty">{{ t("extensions.sources.noPluginMarkets") }}</p>
      </div>
    </section>

    <section class="mcp-note">
      <h3>{{ t("extensions.sources.mcp") }}</h3>
      <p data-testid="mcp-source-note">{{ t("extensions.sources.mcpNote") }}</p>
    </section>

    <div v-if="pending" class="source-confirm" role="alertdialog" :aria-label="t('extensions.sources.confirmTitle')">
      <p v-if="pending.type === 'skill'">{{ t("extensions.sources.skillRemoveWarning", { id: pending.id }) }}</p>
      <p v-else>{{ t("extensions.sources.pluginRemoveWarning", { id: pending.id }) }}</p>
      <footer>
        <button type="button" @click="pending = null">{{ t("common.cancel") }}</button>
        <button type="button" data-testid="confirm-source-remove" :disabled="store.busy" @click="confirmRemove">
          {{ t("extensions.sources.confirmRemove") }}
        </button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.extension-source-manager {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--space-3);
  overflow: auto;
}
section {
  min-width: 0;
  padding: var(--space-3);
  border: var(--border-w) solid var(--border-2);
  border-radius: var(--radius-md);
  background: var(--surface-2);
}
header { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
h3 { margin: 0; color: var(--text); font-size: var(--font-md); }
.source-form { display: flex; gap: var(--space-2); margin-top: var(--space-2); }
.source-form input { flex: 1; min-width: 0; }
.source-list { display: grid; gap: var(--space-1); margin-top: var(--space-2); }
.source-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: var(--control-h-md);
  padding: var(--space-1) var(--space-2);
  border: var(--border-w) solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
}
.source-copy { display: grid; flex: 1 1 auto; min-width: 0; gap: 1px; }
.source-copy strong { color: var(--text); font-size: var(--font-sm); overflow-wrap: anywhere; }
.source-copy span, .source-state, .source-empty { color: var(--text-muted); font-size: var(--font-xs); }
.source-state[data-enabled="true"] { color: var(--success); }
.source-error { margin: var(--space-2) 0 0; color: var(--error); font-size: var(--font-xs); }
.mcp-note { background: transparent; border-style: dashed; }
.mcp-note p { margin: var(--space-1) 0 0; color: var(--text-muted); font-size: var(--font-xs); line-height: var(--leading-normal); }
.source-confirm {
  position: sticky;
  bottom: 0;
  padding: var(--space-3);
  border: var(--border-w) solid var(--warn-border);
  border-radius: var(--radius-md);
  background: var(--warn-bg);
  color: var(--warn-fg);
}
.source-confirm p { margin: 0; font-size: var(--font-sm); line-height: var(--leading-normal); }
.source-confirm footer { display: flex; justify-content: flex-end; gap: var(--space-2); margin-top: var(--space-2); }
</style>
