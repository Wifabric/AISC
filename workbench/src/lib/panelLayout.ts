/**
 * Panel layout (FIX-3, 2026-09-09): user-resizable / collapsible panel
 * geometry — Explorer dock width + collapse (b4 F1 removed TabBar height).
 *
 * Module-level reactive state (theme.ts pattern): WorkspaceView remounts per
 * workspace (keyed by runtime id) so component-local state would be lost on
 * workspace switch. Persisted to localStorage (NOT the settings chain): this
 * the top bar is not a resize boundary. This state is local UI geometry,
 * loss falls back to defaults harmlessly, and it avoids the settings doc's
 * revision-locked explicit-save flow (drag-to-size must stick immediately).
 */

import { reactive } from "vue";

export interface PanelLayout {
  /** Explorer dock width in LAYOUT px (the zoom-invariant domain; rendering
   * multiplies by the .app scale). */
  explorerWidth: number;
  /** true = dock collapsed to the 40px rail (VS Code-style). */
  explorerCollapsed: boolean;
}

const CACHE_KEY = "aisc-wb-panel-layout-v1";

const DEFAULTS: PanelLayout = {
  explorerWidth: 320,
  explorerCollapsed: false,
};

export const EXPLORER_MIN_W = 240;
export const EXPLORER_MAX_W = 600;
export const EXPLORER_COLLAPSED_W = 40;

export function clampExplorerWidth(px: number): number {
  if (!Number.isFinite(px)) return DEFAULTS.explorerWidth;
  return Math.min(EXPLORER_MAX_W, Math.max(EXPLORER_MIN_W, Math.round(px)));
}

/** Visual px per layout px — the `.app` zoom factor. Derived (never read
 * from ui.font_scale: the effective scale is clamped by window size in
 * App.vue). Same formula as TabBar.placeMenu; engine-neutral because `.app`
 * width is `calc(100vw / scale)`, so offsetWidth divides out exactly. */
export function appScale(): number {
  if (typeof window === "undefined" || typeof document === "undefined") return 1;
  const app = document.querySelector(".app");
  const w = (app as HTMLElement | null)?.offsetWidth ?? 0;
  if (!w) return 1;
  const s = window.innerWidth / w;
  return Number.isFinite(s) && s > 0 ? s : 1;
}

function readPersisted(): PanelLayout {
  try {
    if (typeof window === "undefined") return { ...DEFAULTS };
    const raw = window.localStorage.getItem(CACHE_KEY);
    if (!raw) return { ...DEFAULTS };
    const data = JSON.parse(raw) as Partial<PanelLayout>;
    return {
      explorerWidth: clampExplorerWidth(
        typeof data.explorerWidth === "number" ? data.explorerWidth : DEFAULTS.explorerWidth),
      explorerCollapsed: data.explorerCollapsed === true,
    };
  } catch {
    return { ...DEFAULTS };
  }
}

function persist(): void {
  try {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(CACHE_KEY, JSON.stringify({ ...panelLayout }));
  } catch {
    /* storage unavailable (e.g. sandboxed): best-effort */
  }
}

/** Live panel geometry — components bind to this (module singleton). */
export const panelLayout = reactive<PanelLayout>(readPersisted());

export function setExplorerWidth(px: number): void {
  panelLayout.explorerWidth = clampExplorerWidth(px);
  persist();
}

export function setExplorerCollapsed(collapsed: boolean): void {
  panelLayout.explorerCollapsed = collapsed;
  persist();
}

export function toggleExplorerCollapsed(): void {
  setExplorerCollapsed(!panelLayout.explorerCollapsed);
}

/** P2-3 (D-4): what ONE activity-rail icon click does — VS Code semantics.
 * - dock collapsed → expand AND land on the clicked view;
 * - dock open, clicked view already active → collapse (the toggle);
 * - dock open, other view active → plain switch.
 * Kinds stay strings (not the store's ExplorerKind) so this module keeps its
 * zero-store-imports purity; the view passes/uses its own kind values. */
export type RailAction =
  | { do: "expand"; kind: string }
  | { do: "switch"; kind: string }
  | { do: "collapse" };

export function railIconAction(
  collapsed: boolean,
  activeKind: string,
  target: string,
): RailAction {
  if (collapsed) return { do: "expand", kind: target };
  if (activeKind === target) return { do: "collapse" };
  return { do: "switch", kind: target };
}
