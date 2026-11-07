<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { onMounted, ref } from "vue";
import { useDialogA11y } from "../../composables/useDialogA11y";
import { useImageRebuildStore } from "../../stores/imageRebuild";
import BuildProgress from "./BuildProgress.vue";
const { t } = useI18n();
const rebuild = useImageRebuildStore();
const panel = ref<HTMLElement | null>(null);
useDialogA11y(panel, rebuild.close);
onMounted(() => panel.value?.focus());
</script>

<template>
  <Teleport to="body">
    <div v-if="rebuild.visible" class="rebuild-overlay">
      <section ref="panel" tabindex="-1" class="rebuild-dialog" role="dialog" aria-modal="true" :aria-label="t('imageRebuild.title')">
        <h2>{{ t("imageRebuild.title") }}</h2>
        <p>{{ t("imageRebuild.localOnly") }}</p>
        <p v-if="rebuild.targetChanged" role="alert">{{ t("imageRebuild.targetChanged") }}</p>
        <template v-if="rebuild.buildStatus === 'idle'">
          <label>{{ t("imageRebuild.reference") }}
            <select v-model="rebuild.selected" :disabled="rebuild.checking" @change="rebuild.refresh()">
              <option v-for="reference in rebuild.references" :key="reference">{{ reference }}</option>
            </select>
          </label>
          <p v-if="rebuild.checking" role="status">{{ t("imageRebuild.checking") }}</p>
          <p v-if="rebuild.error" role="alert">{{ rebuild.error }}</p>
          <template v-if="rebuild.check">
            <p>{{ rebuild.check.exists ? t("imageRebuild.replaceHint") : t("imageRebuild.missing") }}</p>
            <code v-if="rebuild.check.image_id">{{ rebuild.check.image_id }}</code>
            <p v-if="rebuild.check.running_containers.length" role="alert">{{ t("imageRebuild.stopFirst") }} {{ rebuild.check.running_containers.join(", ") }}</p>
            <label><input v-model="rebuild.noCache" type="checkbox" /> {{ t("imageRebuild.noCache") }}</label>
          </template>
          <div class="rebuild-actions">
            <button class="ui-button" :disabled="rebuild.checking || rebuild.targetChanged" @click="rebuild.refresh()">{{ t("imageRebuild.recheck") }}</button>
            <button class="ui-button" @click="rebuild.close()">{{ t("common.cancel") }}</button>
            <button class="ui-button primary" data-testid="confirm-image-rebuild" :disabled="!rebuild.canStart" @click="rebuild.startBuild()">{{ t("imageRebuild.confirm") }}</button>
          </div>
        </template>
        <template v-else>
          <BuildProgress :model="rebuild" :back-label="t('common.close')" :retry-label="t('imageRebuild.recheck')" />
          <p v-if="rebuild.result">{{ t("imageRebuild.result", { id: rebuild.result.new_image_id }) }}
            {{ t(`imageRebuild.old.${rebuild.result.old_image_action}`) }}</p>
        </template>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.rebuild-overlay { position: fixed; inset: 0; z-index: var(--z-dialog); display: grid; place-items: center; background: var(--scrim); padding: var(--space-5); }
.rebuild-dialog { width: min(760px, 100%); max-height: 90vh; overflow: auto; background: var(--surface); color: var(--text); border: var(--border-w) solid var(--border); border-radius: var(--radius-lg); padding: var(--space-5); }
.rebuild-dialog p, .rebuild-dialog code { overflow-wrap: anywhere; }
.rebuild-dialog select { display: block; width: 100%; margin: 8px 0; }
.rebuild-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
</style>
