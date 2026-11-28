<script setup lang="ts">
/**
 * b6: proxy-node pane restructured as「当前节点 → 代理组 → 组内节点」.
 * The current node of the active group is highlighted first; the group is
 * pickable; the nodes under it are pickable and carry their own latency.
 * All ipc still goes through the usage store (F-A01 layer contract).
 */
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { ProxyGroups } from "../../lib/ipc";
import { useRuntimeStore } from "../../stores/runtime";
import { useUsageStore } from "../../stores/usage";
const { t } = useI18n();
const runtime = useRuntimeStore();
const usage = useUsageStore();
const groups = ref<ProxyGroups>({});
/** The proxy group whose current node and nodes are shown. */
const activeGroup = ref("");
/** Pending node selection inside the active group (applied via 使用节点). */
const picked = ref("");
const busy = ref(false);
const loaded = ref(false);
const error = ref("");
/** Latency per group+node, tested on demand. */
const latency = ref<Record<string, string>>({});
let generation = 0;

const groupNames = computed(() => Object.keys(groups.value));
const active = computed(() => groups.value[activeGroup.value]);
const activeNodes = computed(() => active.value?.nodes ?? []);

function nodeKey(group: string, node: string): string {
  return `${group}\u0000${node}`;
}
function delayLabel(group: string, node: string): string {
  return latency.value[nodeKey(group, node)] ?? t("usage.nodes.untested");
}
/** Keep the pending pick pointing at a node that exists in the group. */
function syncPick(group: string): void {
  const data = groups.value[group];
  picked.value = data
    ? (data.nodes.includes(data.current) ? data.current : data.nodes[0] ?? "")
    : "";
}

watch(
  () => [runtime.workspace, runtime.runtimeId],
  () => {
    generation++;
    busy.value = false;
    loaded.value = false;
    groups.value = {};
    activeGroup.value = "";
    picked.value = "";
    latency.value = {};
    error.value = "";
  },
);
watch(activeGroup, (name) => {
  if (name) syncPick(name);
});

async function run(action: "list" | "select" | "delay", group = "", node = "") {
  if (!runtime.workspace || !runtime.runtimeId || busy.value) return;
  const epoch = generation;
  busy.value = true;
  error.value = "";
  try {
    const result = await usage.proxyNodes(runtime.workspace, runtime.runtimeId, action, group, node);
    if (epoch !== generation) return;
    if (result.groups) {
      loaded.value = true;
      groups.value = result.groups;
      const names = Object.keys(result.groups);
      activeGroup.value = names.includes(activeGroup.value) ? activeGroup.value : names[0] ?? "";
      if (activeGroup.value) syncPick(activeGroup.value);
      latency.value = {};
    }
    if (action === "select" && groups.value[group]) groups.value[group].current = node;
    if (action === "delay") {
      latency.value[nodeKey(group, node)] =
        typeof result.delay === "number" ? `${result.delay} ms` : t("usage.nodes.timeout");
    }
  } catch (e) {
    if (epoch === generation) {
      error.value = (e as { message?: string })?.message || String(e);
      if (action === "list") {
        groups.value = {};
        activeGroup.value = "";
        loaded.value = false;
      }
    }
  } finally {
    if (epoch === generation) busy.value = false;
  }
}
</script>
<template>
  <section v-if="runtime.runtimeId && runtime.workspace" class="proxy-nodes">
    <div class="nodes-head">
      <h3>{{ t("usage.nodes.title") }}</h3>
      <button class="ui-button" :disabled="busy" @click="run('list')">{{ t(busy ? "usage.nodes.loading" : "usage.nodes.list") }}</button>
    </div>
    <p v-if="loaded && !groupNames.length">{{ t("usage.nodes.empty") }}</p>

    <template v-if="active">
      <!-- 1. 当前节点：所属代理组 / 节点名 / 延迟 -->
      <section class="current-node" :aria-label="t('usage.nodes.current')">
        <h4>{{ t("usage.nodes.current") }}</h4>
        <dl class="current-facts">
          <div><dt>{{ t("usage.nodes.group") }}</dt><dd>{{ activeGroup }}</dd></div>
          <div><dt>{{ t("usage.nodes.node") }}</dt><dd class="node-name">{{ active.current || "—" }}</dd></div>
          <div><dt>{{ t("usage.nodes.latency") }}</dt>
            <dd>{{ delayLabel(activeGroup, active.current) }}</dd></div>
        </dl>
        <span v-if="active.selectable === false" class="dim">{{ t("usage.nodes.automatic") }}</span>
      </section>

      <!-- 2. 代理组可选 -->
      <!-- 2+3. 代理组与节点选择（独立面板，与当前节点信息分开） -->
      <section class="node-control" :aria-label="t('usage.nodes.groupLabel')">
      <label class="group-pick">
        <span>{{ t("usage.nodes.groupLabel") }}</span>
        <select v-model="activeGroup" :disabled="busy">
          <option v-for="name in groupNames" :key="name" :value="name">{{ name }}</option>
        </select>
      </label>

      <!-- 3. 组内节点：可选、各自带延迟 -->
      <div class="node-list">
        <h4>{{ t("usage.nodes.nodes") }}</h4>
        <ul>
          <li v-for="node in activeNodes" :key="node" :class="{ current: node === active.current }">
            <label>
              <input v-model="picked" type="radio" :value="node" :disabled="busy" />
              <span class="node-name">{{ node }}</span>
              <span class="node-delay">{{ delayLabel(activeGroup, node) }}</span>
            </label>
            <button class="ui-button sm" :disabled="busy" @click="run('delay', activeGroup, node)">{{ t("usage.nodes.delay") }}</button>
          </li>
        </ul>
        <button
          class="ui-button"
          :disabled="busy || active.selectable === false"
          @click="run('select', activeGroup, picked)"
        >{{ t("usage.nodes.select") }}</button>
        <span v-if="picked === active.current" class="dim">{{ t("usage.nodes.alreadyCurrent") }}</span>
      </div>
      </section>
    </template>
    <p v-if="error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
.proxy-nodes { display: grid; gap: 12px; min-width: 0; }
.nodes-head { display: flex; align-items: center; gap: 12px; }
.nodes-head h3 { margin: 0; }
.current-node { display: grid; gap: 6px; padding: var(--space-3);
  border: var(--border-w) solid var(--accent); border-radius: var(--radius-md);
  background: var(--accent-soft); }
.node-control { display: grid; gap: 10px; padding: var(--space-3);
  border: var(--border-w) solid var(--border); border-radius: var(--radius-md);
  background: var(--surface); }
.current-node h4, .node-list h4 { margin: 0; font-size: var(--font-sm);
  color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.current-facts { display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; margin: 0; }
.current-facts div { display: contents; }
.current-facts dt { color: var(--text-muted); font-size: var(--font-sm); }
.current-facts dd { margin: 0; font-size: var(--font-md); }
.current-facts dd.node-name { font-weight: 600; }
.group-pick { display: grid; gap: 3px; font-size: var(--font-sm); color: var(--text-muted); max-width: 360px; }
.node-list { display: grid; gap: 8px; }
.node-list ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; max-width: 520px; }
.node-list li { display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: var(--space-1) var(--space-2); border: var(--border-w) solid var(--border);
  border-radius: var(--radius-sm); }
.node-list li.current { border-color: var(--accent); background: var(--surface-2); }
.node-list li label { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
.node-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.node-delay { margin-left: auto; color: var(--text-muted); font-size: var(--font-sm);
  font-variant-numeric: tabular-nums; }
.dim { color: var(--text-muted); font-size: var(--font-sm); }
</style>
