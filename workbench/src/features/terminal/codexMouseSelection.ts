export interface CodexMouseSelectionOptions {
  host: HTMLElement;
  getTerminalElement: () => HTMLElement | null;
  isCodexPane: () => boolean;
  clearSelection: () => void;
}

const CLICK_SLOP_PX = 4;

function cloneMouseEvent(
  source: MouseEvent,
  type: "mousedown" | "mouseup" = source.type as "mousedown" | "mouseup",
  overrides: MouseEventInit = {},
): MouseEvent {
  return new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    composed: source.composed,
    view: source.view,
    detail: source.detail,
    screenX: source.screenX,
    screenY: source.screenY,
    clientX: source.clientX,
    clientY: source.clientY,
    button: source.button,
    buttons: source.buttons,
    relatedTarget: source.relatedTarget,
    ctrlKey: source.ctrlKey,
    altKey: source.altKey,
    shiftKey: source.shiftKey,
    metaKey: source.metaKey,
    ...overrides,
  });
}

/**
 * Codex enables terminal mouse tracking. xterm then forwards ordinary drags to
 * the TUI and disables its selection service; Shift+drag remains xterm's
 * built-in forced-selection bypass. This adapter converts a Codex drag into a
 * synthetic Shift+drag while preserving a click without movement: the latter is
 * replayed to Codex as normal mousedown/mouseup after the forced selection is
 * cleared.
 */
export function createCodexMouseSelectionBypass(options: CodexMouseSelectionOptions): () => void {
  let active = false;
  let forwardingClick = false;
  let moved = false;
  let startX = 0;
  let startY = 0;

  const onMouseMove = (event: MouseEvent): void => {
    if (!active) return;
    if (!moved && Math.hypot(event.clientX - startX, event.clientY - startY) > CLICK_SLOP_PX) {
      moved = true;
    }
  };

  const onMouseUp = (event: MouseEvent): void => {
    if (!active || forwardingClick) return;
    active = false;
    document.removeEventListener("mousemove", onMouseMove, true);
    const terminal = options.getTerminalElement();
    if (!terminal || moved) return;

    options.clearSelection();
    forwardingClick = true;
    try {
      const down = cloneMouseEvent(event, "mousedown", { shiftKey: false, buttons: 1 });
      const up = cloneMouseEvent(event, "mouseup", { shiftKey: false, buttons: 0 });
      terminal.dispatchEvent(down);
      terminal.dispatchEvent(up);
    } finally {
      forwardingClick = false;
    }
  };

  const onMouseDownCapture = (event: MouseEvent): void => {
    if (forwardingClick || event.button !== 0 || event.shiftKey) return;
    if (!options.isCodexPane() || !event.cancelable) return;
    const terminal = options.getTerminalElement();
    if (!terminal?.classList.contains("enable-mouse-events")) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    active = true;
    moved = false;
    startX = event.clientX;
    startY = event.clientY;
    document.addEventListener("mousemove", onMouseMove, true);
    terminal.dispatchEvent(cloneMouseEvent(event, "mousedown", { shiftKey: true }));
  };

  const onMouseUpCapture = (event: MouseEvent): void => {
    // Do not stop this event: xterm's SelectionService listens on document and
    // needs the same mouseup to finalize the selection and fire copy auto-sync.
    if (!active || forwardingClick) return;
    onMouseUp(event);
  };

  options.host.addEventListener("mousedown", onMouseDownCapture, true);
  options.host.addEventListener("mouseup", onMouseUpCapture, true);

  return () => {
    options.host.removeEventListener("mousedown", onMouseDownCapture, true);
    options.host.removeEventListener("mouseup", onMouseUpCapture, true);
    document.removeEventListener("mousemove", onMouseMove, true);
    active = false;
    forwardingClick = false;
  };
}
