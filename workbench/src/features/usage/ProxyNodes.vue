<script setup lang="ts">
import { ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { ProxyGroups } from "../../lib/ipc";
import { useRuntimeStore } from "../../stores/runtime";
import { useUsageStore } from "../../stores/usage";
const { t } = useI18n();
const runtime = useRuntimeStore();
const usage = useUsageStore();
const groups = ref<ProxyGroups>({});
const selection = ref<Record<string, string>>({});
const busy = ref(false);
const loaded = ref(false);
const error = ref("");
const latency = ref<Record<string, string>>({});
let generation = 0;
watch(() => [runtime.workspace, runtime.runtimeId], () => {
  generation++;
  busy.value = false;
  loaded.value = false;
  groups.value = {};
  selection.value = {};
  latency.value = {};
  error.value = "";
});
async function run(action: "list" | "select" | "delay", group = "") {
  if (!runtime.workspace || !runtime.runtimeId || busy.value) return;
  const epoch = generation;
  const node = selection.value[group];
  busy.value = true;
  error.value = "";
  try {
    const result = await usage.proxyNodes(runtime.workspace, runtime.runtimeId, action, group, node);
    if (epoch !== generation) return;
    if (result.groups) {
      loaded.value = true;
      groups.value = result.groups;
      selection.value = Object.fromEntries(Object.entries(result.groups).map(([name, value]) => [name, value.current]));
      latency.value = {};
    }
    if (action === "select") groups.value[group].current = node;
    if (action === "delay") latency.value[group] = result.delay ? node + " · " + result.delay + " ms" : t("usage.nodes.timeout");
  } catch (e) {
    if (epoch === generation) {
      error.value = (e as { message?: string })?.message || String(e);
      if (action === "list") {
        groups.value = {};
        loaded.value = false;
      }
    }
  } finally {
    if (epoch === generation) busy.value = false;
  }
}
</script>
<template>
  <section v-if="runtime.runtimeId && runtime.workspace">
    <h3>{{ t("usage.nodes.title") }}</h3>
    <button class="ui-button" :disabled="busy" @click="run('list')">{{ t(busy ? "usage.nodes.loading" : "usage.nodes.list") }}</button>
    <p v-if="loaded && !Object.keys(groups).length">{{ t("usage.nodes.empty") }}</p>
    <div v-for="(data, name) in groups" :key="name">
      <label>{{ name }} · {{ data.current }}
        <select v-model="selection[name]" :disabled="busy" @change="delete latency[name]">
          <option v-for="node in data.nodes" :key="node">{{ node }}</option>
        </select>
      </label>
      <span v-if="data.selectable === false">{{ t("usage.nodes.automatic") }}</span>
      <button v-else class="ui-button" :disabled="busy || selection[name] === data.current" @click="run('select', name)">{{ t("usage.nodes.select") }}</button>
      <button class="ui-button" :disabled="busy" @click="run('delay', name)">{{ t("usage.nodes.delay") }}</button>
      <output>{{ latency[name] }}</output>
    </div>
    <p v-if="error" role="alert">{{ error }}</p>
  </section>
</template>
