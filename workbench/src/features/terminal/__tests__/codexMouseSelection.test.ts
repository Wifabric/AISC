import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createCodexMouseSelectionBypass } from "../codexMouseSelection";

function mouseEvent(type: "mousedown" | "mousemove" | "mouseup", init: MouseEventInit = {}) {
  return new MouseEvent(type, { bubbles: true, cancelable: true, buttons: 1, ...init });
}

describe("codex mouse selection bypass", () => {
  let host: HTMLDivElement;
  let terminal: HTMLDivElement;
  let clearSelection: () => void;
  let detach: () => void;

  beforeEach(() => {
    host = document.createElement("div");
    terminal = document.createElement("div");
    terminal.className = "terminal enable-mouse-events";
    host.appendChild(terminal);
    document.body.appendChild(host);
    clearSelection = vi.fn();
    detach = createCodexMouseSelectionBypass({
      host,
      getTerminalElement: () => terminal,
      isCodexPane: () => true,
      clearSelection,
    });
  });

  afterEach(() => {
    detach();
    host.remove();
  });

  it("converts a codex drag into forced xterm selection and does not replay a click", () => {
    const dispatched: MouseEvent[] = [];
    vi.spyOn(terminal, "dispatchEvent").mockImplementation((event) => {
      dispatched.push(event as MouseEvent);
      return true;
    });
    const down = mouseEvent("mousedown", { clientX: 10, clientY: 10 });
    host.dispatchEvent(down);
    expect(down.defaultPrevented).toBe(true);
    expect(dispatched).toHaveLength(1);
    expect(dispatched[0]?.shiftKey).toBe(true);

    let documentSawMouseUp = false;
    const onDocumentMouseUp = () => { documentSawMouseUp = true; };
    document.addEventListener("mouseup", onDocumentMouseUp);
    try {
      host.dispatchEvent(mouseEvent("mousemove", { clientX: 24, clientY: 14 }));
      host.dispatchEvent(mouseEvent("mouseup", { clientX: 24, clientY: 14 }));
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

  it("replays an unmoved click to codex after forced selection starts", () => {
    const dispatched: MouseEvent[] = [];
    vi.spyOn(terminal, "dispatchEvent").mockImplementation((event) => {
      dispatched.push(event as MouseEvent);
      return true;
    });
    host.dispatchEvent(mouseEvent("mousedown", { clientX: 10, clientY: 10 }));
    host.dispatchEvent(mouseEvent("mouseup", { clientX: 11, clientY: 11 }));
    expect(clearSelection).toHaveBeenCalled();
    expect(dispatched.map((event) => [event.type, event.shiftKey])).toEqual([
      ["mousedown", true],
      ["mousedown", false],
      ["mouseup", false],
    ]);
  });

  it("leaves ordinary terminal selection untouched outside codex", () => {
    detach();
    detach = createCodexMouseSelectionBypass({
      host,
      getTerminalElement: () => terminal,
      isCodexPane: () => false,
      clearSelection,
    });
    const dispatched: MouseEvent[] = [];
    vi.spyOn(terminal, "dispatchEvent").mockImplementation((event) => {
      dispatched.push(event as MouseEvent);
      return true;
    });
    const down = mouseEvent("mousedown", { clientX: 10, clientY: 10 });
    host.dispatchEvent(down);
    expect(down.defaultPrevented).toBe(false);
    expect(dispatched).toHaveLength(0);
  });
});
