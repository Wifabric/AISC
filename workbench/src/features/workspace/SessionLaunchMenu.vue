<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { LaunchAgent } from "../../types";
import { AGENTS } from "../../stores/tabLayout";
import SessionDirectory from "./SessionDirectory.vue";
const props = defineProps<{ anchor: HTMLElement | null }>();
const emit = defineEmits<{ close: []; choose: [agent: LaunchAgent | "topics", directory: string] }>();
const directory = defineModel<string>({ default: "" });
const menuRef = ref<HTMLUListElement | null>(null);
const menuPos = ref({ x: 0, y: 0 });
const { t } = useI18n();
function choose(agent: LaunchAgent | "topics") { emit("choose", agent, directory.value); }
function outside(event: MouseEvent) {
  const node = event.target as Node;
  if (!menuRef.value?.contains(node) && !props.anchor?.contains(node)) emit("close");
}
let frame = 0;
onMounted(() => {
  document.addEventListener("mousedown", outside);
  window.addEventListener("resize", placeMenu);
  placeMenu();
  frame = requestAnimationFrame(() => { frame = requestAnimationFrame(() => {
    if (!placeMenu()) { emit("close"); return; }
    menuRef.value?.querySelector("input")?.focus();
  }); });
});
onBeforeUnmount(() => {
  cancelAnimationFrame(frame);
  document.removeEventListener("mousedown", outside);
  window.removeEventListener("resize", placeMenu);
});
function placeMenu(): boolean {
  const btn = props.anchor;
  if (!btn) return false;
  const rect = btn.getBoundingClientRect();
  // 10d: a detached / not-yet-laid-out ref reports an all-zero rect, and the
  // clamped minimum then parked the menu at the window's top-left corner
  // (user evidence 2.png). Refuse to open instead.
  if (rect.width === 0 && rect.height === 0) return false;
  // The teleported menu lives OUTSIDE the zoomed .app, so its fixed px are
  // viewport (VISUAL) px. r4: .app is sized width:100vw/scale, so the live
  // scale is innerWidth / app.offsetWidth regardless of engine. A visual-space
  // rect (modern engines: ratio == scale) is already correct; a layout-space
  // rect (legacy: ratio == 1) must be MULTIPLIED by the scale. Never divided —
  // dividing made the offset grow with the caret's distance from the left
  // edge (user evidence: more tabs → bigger drift at font_scale 1.5).
  const app = document.querySelector<HTMLElement>(".app");
  const scale = app && app.offsetWidth > 0 ? window.innerWidth / app.offsetWidth : 1;
  const ratio = btn.offsetWidth > 0 ? rect.width / btn.offsetWidth : 1;
  const z = Math.abs(scale - 1) < 0.02 ? 1 : (Math.abs(ratio - scale) < 0.05 ? 1 : scale);
  const menuWidth = menuRef.value?.offsetWidth || 250;
  menuPos.value = {
    x: Math.max(4, Math.min(rect.left * z, window.innerWidth - menuWidth)),
    y: Math.max(4, Math.min(rect.bottom * z + 2, window.innerHeight - (menuRef.value?.offsetHeight || 190) - 4)),
  };
  return true;
}

function onMenuKeydown(e: KeyboardEvent) {
  const items = Array.from(menuRef.value?.querySelectorAll<HTMLElement>("[role=menuitem]") ?? []);
  const idx = items.findIndex((el) => el === document.activeElement);
  if (e.key === "Escape" || (e.key === "Tab" && (e.shiftKey ? e.target instanceof HTMLInputElement : idx === items.length - 1))) {
    emit("close");
    if (e.key === "Escape") { e.preventDefault(); props.anchor?.focus(); }
    return;
  }
  if (e.key === "ArrowDown" || e.key === "ArrowRight") {
    e.preventDefault();
    items[(idx + 1) % items.length]?.focus();
  } else if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
    e.preventDefault();
    items[(idx - 1 + items.length) % items.length]?.focus();
  } else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    if (idx >= 0) {
      choose(items[idx].dataset.agent as LaunchAgent | "topics");
    }
  }
}

</script>
<template>
      <Teleport to="body">
        <Transition name="pop">
        <ul
          ref="menuRef"
          class="menu tab-new-menu"
          role="menu"
          :style="{ left: `${menuPos.x}px`, top: `${menuPos.y}px` }"
          @keydown="onMenuKeydown"
        >
          <li><SessionDirectory v-model="directory" /></li>
          <li
            v-for="a in AGENTS"
            :key="a"
            role="menuitem"
            tabindex="0"
            :data-agent="a"
            @click="choose(a)"
          >{{ t(`tabbar.menu.${a}`) }}</li>
          <li role="menuitem" tabindex="0" data-agent="topics" @click="choose('topics')">{{ t("explorer.tab.topics") }}</li>
        </ul>
        </Transition>
      </Teleport>
</template>
<style scoped>
.menu {
  position: fixed; z-index: var(--z-drawer);
  list-style: none; margin: 0; padding: 4px 0;
  background: var(--surface-2); border: 1px solid var(--border-2); border-radius: var(--radius-md);
  width: min(260px, calc(100vw - 8px)); max-height: calc(100vh - 8px); overflow: auto; box-sizing: border-box;
}
.menu li {
  padding: 6px 12px; font-size: var(--font-md); color: var(--text-2); cursor: pointer;
  outline: none;
}
.menu li:hover, .menu li:focus { background: var(--surface-hover); color: var(--text); }
.menu .sep { padding: 0; height: 1px; margin: 4px 8px; background: var(--border); cursor: default; }
.menu .sep:hover, .menu .sep:focus { background: var(--border); }
</style>
