import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createCodexMouseSelectionBypass } from "../codexMouseSelection";

function mouseEvent(type: "mousedown" | "mousemove" | "mouseup", init: MouseEventInit = {}) {
  return new MouseEvent(type, { bubbles: true, cancelable: true, buttons: 1, ...init });
}

describe("codex mouse selection bypass", () => {
  let host: HTMLDivElement;
  let terminal: HTMLDivElement;
  let surface: HTMLDivElement;
  let clearSelection: () => void;
  let detach: () => void;

  beforeEach(() => {
    host = document.createElement("div");
    terminal = document.createElement("div");
    terminal.className = "terminal enable-mouse-events";
    surface = document.createElement('div');
    surface.className = 'xterm-screen';
    terminal.appendChild(surface);
    host.appendChild(terminal);
    document.body.appendChild(host);
    clearSelection = vi.fn();
    detach = createCodexMouseSelectionBypass({
      host,
      getTerminalElement: () => terminal,
      isAgentPane: () => true,
      clearSelection,
    });
  });

  afterEach(() => {
    detach();
    host.remove();
  });

  it("converts an agent drag into forced xterm selection and does not replay a click", () => {
    const dispatched: MouseEvent[] = [];
    vi.spyOn(terminal, "dispatchEvent").mockImplementation((event) => {
      dispatched.push(event as MouseEvent);
      return true;
    });
    const down = mouseEvent("mousedown", { clientX: 10, clientY: 10 });
    surface.dispatchEvent(down);
    expect(down.defaultPrevented).toBe(true);
    expect(dispatched).toHaveLength(1);
    expect(dispatched[0]?.shiftKey).toBe(true);

    let documentSawMouseUp = false;
    const onDocumentMouseUp = () => { documentSawMouseUp = true; };
    document.addEventListener("mouseup", onDocumentMouseUp);
    try {
      surface.dispatchEvent(mouseEvent("mousemove", { clientX: 24, clientY: 14 }));
      document.dispatchEvent(mouseEvent("mouseup", { clientX: 24, clientY: 14 }));
    } finally {
      document.removeEventListener("mouseup", onDocumentMouseUp);
    }
    expect(dispatched).toHaveLength(1);
    expect(clearSelection).not.toHaveBeenCalled();
    // xterm's SelectionService finalizes and fires selection change from a
    // document mouseup listener. Blocking that event made drag selection visible
    // but silently skipped clipboard auto-copy.
    expect(documentSawMouseUp).toBe(true);
  });

  it("replays an unmoved click to the agent after forced selection starts", () => {
    const dispatched: MouseEvent[] = [];
    vi.spyOn(terminal, "dispatchEvent").mockImplementation((event) => {
      dispatched.push(event as MouseEvent);
      return true;
    });
    surface.dispatchEvent(mouseEvent("mousedown", { clientX: 10, clientY: 10 }));
    surface.dispatchEvent(mouseEvent("mouseup", { clientX: 11, clientY: 11 }));
    expect(clearSelection).toHaveBeenCalled();
    expect(dispatched.map((event) => [event.type, event.shiftKey])).toEqual([
      ["mousedown", true],
      ["mousedown", false],
      ["mouseup", false],
    ]);
  });

  it("keeps modified clicks and clicks on the scrollbar native", () => {
    const modified = mouseEvent("mousedown", { ctrlKey: true });
    surface.dispatchEvent(modified);
    expect(modified.defaultPrevented).toBe(false);
    const scrollbar = terminal.appendChild(document.createElement("div"));
    const down = mouseEvent("mousedown");
    scrollbar.dispatchEvent(down);
    expect(down.defaultPrevented).toBe(false);
  });

  it("leaves ordinary terminal selection untouched in a shell pane", () => {
    detach();
    detach = createCodexMouseSelectionBypass({
      host,
      getTerminalElement: () => terminal,
      isAgentPane: () => false,
      clearSelection,
    });
    const dispatched: MouseEvent[] = [];
    vi.spyOn(terminal, "dispatchEvent").mockImplementation((event) => {
      dispatched.push(event as MouseEvent);
      return true;
    });
    const down = mouseEvent("mousedown", { clientX: 10, clientY: 10 });
    surface.dispatchEvent(down);
    expect(down.defaultPrevented).toBe(false);
    expect(dispatched).toHaveLength(0);
  });
});
