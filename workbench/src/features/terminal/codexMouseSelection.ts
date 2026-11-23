export interface CodexMouseSelectionOptions {
  host: HTMLElement;
  getTerminalElement: () => HTMLElement | null;
  isAgentPane: () => boolean;
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
 * While an agent requests mouse reporting, route text drags through xterm's
 * platform-specific selection modifier. An unmoved click still reaches the TUI.
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
    const doc = options.host.ownerDocument;
    doc.removeEventListener("mousemove", onMouseMove, true);
    doc.removeEventListener("mouseup", onMouseUp, true);
    const terminal = options.getTerminalElement();
    if (!terminal || moved || !terminal.querySelector(".xterm-screen")?.contains(event.target as Node)) return;

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
    if (forwardingClick || event.button !== 0 || event.shiftKey || event.altKey || event.metaKey || event.ctrlKey) return;
    if (!options.isAgentPane() || !event.cancelable) return;
    const terminal = options.getTerminalElement();
    if (!terminal?.classList.contains("enable-mouse-events") ||
        !terminal.querySelector(".xterm-screen")?.contains(event.target as Node)) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    active = true;
    moved = false;
    startX = event.clientX;
    startY = event.clientY;
    const doc = options.host.ownerDocument;
    doc.addEventListener("mousemove", onMouseMove, true);
    // Selection may end outside the pane. Let xterm receive the same mouseup.
    doc.addEventListener("mouseup", onMouseUp, true);
    const mac = /Mac/.test(navigator.platform);
    terminal.dispatchEvent(cloneMouseEvent(event, "mousedown", { shiftKey: !mac, altKey: mac }));
  };

  options.host.addEventListener("mousedown", onMouseDownCapture, true);

  return () => {
    options.host.removeEventListener("mousedown", onMouseDownCapture, true);
    options.host.ownerDocument.removeEventListener("mouseup", onMouseUp, true);
    options.host.ownerDocument.removeEventListener("mousemove", onMouseMove, true);
    active = false;
    forwardingClick = false;
  };
}
