<script setup lang="ts">
import { computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { ExtensionsItem } from "../../lib/ipc";
import { useExtensionsStore, type ExtensionUpdateItem } from "../../stores/extensions";
import type { CategorizedRecommendation } from "./recommendationCatalog";
import { extensionSummary } from "./extensionSummaries";
import ExtensionDetailPanel from "./ExtensionDetailPanel.vue";

const props = defineProps<{ item: ExtensionsItem; recommendation?: CategorizedRecommendation;
  update?: ExtensionUpdateItem; evidenceLabel?: string }>();
const emit = defineEmits<{ close: [] }>();
const store = useExtensionsStore();
const { locale } = useI18n();
const item = computed(() => store.describedItem(props.item));
const state = computed(() => store.descriptionState(props.item));
watch(() => props.item, value => {
  if (extensionSummary(value, locale.value === "en-US" ? "en-US" : "zh-CN").source === "fallback")
    void store.describeSkill(value);
}, { immediate: true });
</script>

<template>
  <ExtensionDetailPanel :item="item" :recommendation="recommendation" :update="update"
    :evidence-label="evidenceLabel" :loading="state?.loading" :error="state?.error"
    @retry="store.describeSkill(props.item)" @close="emit('close')">
    <template v-if="$slots.actions" #actions><slot name="actions" /></template>
  </ExtensionDetailPanel>
</template>
