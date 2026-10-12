import { describe, expect, it, vi } from "vitest";
import { Terminal } from "@xterm/xterm";
import {
  createAltScreenDetector,
  createScrollOwnership,
  isEraseScrollbackRequest,
  isTerminalFocusReport,
  isTerminalGeneratedInput,
} from "./scrollOwnership";

describe("b3 terminal scroll ownership", () => {
  it("starts in follow mode and enters review only when scrolled away from bottom", () => {
    const owner = createScrollOwnership();

    expect(owner.shouldFollowOutput()).toBe(true);

    owner.onUserScrollAway();
    expect(owner.shouldFollowOutput()).toBe(false);

    // Repeated scroll events while already reviewing must stay quiescent.
    owner.onUserScrollAway();
    expect(owner.shouldFollowOutput()).toBe(false);
  });

  it("resumes following when the viewport returns to the bottom", () => {
    const owner = createScrollOwnership();
    owner.onUserScrollAway();

    owner.onUserScrollAtBottom();

    expect(owner.shouldFollowOutput()).toBe(true);
  });

  it("returns to the bottom only when a reviewed user starts typing", () => {
    const owner = createScrollOwnership();

    expect(owner.onUserInput()).toBe(false);
    expect(owner.shouldFollowOutput()).toBe(true);

    owner.onUserScrollAway();
    expect(owner.onUserInput()).toBe(true);
    expect(owner.shouldFollowOutput()).toBe(true);
  });

  it("resumes after alt-screen exit only when the user was following output", () => {
    const following = createScrollOwnership();
    const reviewing = createScrollOwnership();
    reviewing.onUserScrollAway();

    expect(following.onAltScreenExit()).toBe(true);
    expect(reviewing.onAltScreenExit()).toBe(false);

    // The user's review position is deliberately preserved.
    expect(reviewing.shouldFollowOutput()).toBe(false);
  });
});

describe("b3 terminal-generated focus reports", () => {
  it("does not mistake focus mode responses for user input", () => {
    expect(isTerminalFocusReport("\u001b[I")).toBe(true);
    expect(isTerminalFocusReport("\u001b[O")).toBe(true);
    expect(isTerminalFocusReport("x")).toBe(false);
    expect(isTerminalFocusReport("\r")).toBe(false);
  });

  it("does not mistake cursor, attribute, or color reports for keystrokes", () => {
    const ESC = String.fromCharCode(27);
    expect(isTerminalGeneratedInput(`${ESC}[38;1R`)).toBe(true);
    expect(isTerminalGeneratedInput(`${ESC}[?62;c`)).toBe(true);
    expect(isTerminalGeneratedInput(`${ESC}]10;rgb:3333/3333/3333${ESC}\\`)).toBe(true);
    expect(isTerminalGeneratedInput(`${ESC}]11;rgb:ffff/ffff/ffff${ESC}\\`)).toBe(true);
    expect(isTerminalGeneratedInput(`${ESC}P>|xterm(1)${ESC}\\`)).toBe(true);
    expect(isTerminalGeneratedInput("codex")).toBe(false);
    expect(isTerminalGeneratedInput(`${ESC}[A`)).toBe(false);
  });
});

describe("b3 Codex clear-scrollback guard", () => {
  async function fillScrollback(): Promise<{ term: Terminal; lineCount: number }> {
    const mediaList = Object.assign(new EventTarget(), {
      matches: false,
      addListener: () => {},
      removeListener: () => {},
    });
    window.matchMedia = vi.fn().mockReturnValue(mediaList);
    const term = new Terminal({ cols: 8, rows: 3, scrollback: 100 });
    const host = document.createElement("div");
    document.body.appendChild(host);
    term.open(host);
    await new Promise<void>((resolve) => {
      term.write(Array.from({ length: 12 }, (_, i) => `${i + 1}`).join("\r\n"), resolve);
    });
    return { term, lineCount: term.buffer.active.length };
  }

  it("treats only ED3 as a scrollback erase request", () => {
    // Codex launches with CSI H + CSI 2J + CSI 3J. ED2 must continue to redraw
    // the TUI; only ED3 destroys the user's scrollback.
    expect(isEraseScrollbackRequest([])).toBe(false);
    expect(isEraseScrollbackRequest([0])).toBe(false);
    expect(isEraseScrollbackRequest([2])).toBe(false);
    expect(isEraseScrollbackRequest([3])).toBe(true);
  });

  it("lets xterm keep the buffer when the installed guard receives ED3", async () => {
    const { term, lineCount } = await fillScrollback();
    expect(lineCount).toBeGreaterThan(3);
    term.parser.registerCsiHandler(
      { final: "J" },
      (params) => isEraseScrollbackRequest(params),
    );

    await new Promise<void>((resolve) => term.write("\x1b[3J", resolve));
    expect(term.buffer.active.type).toBe("normal");
    expect(term.buffer.active.length).toBe(lineCount);
  });
});

describe("b3 alt-screen sequence detector", () => {
  const ENTER = new Uint8Array([0x1b, 0x5b, 0x3f, 0x31, 0x30, 0x34, 0x39, 0x68]);
  const EXIT = new Uint8Array([0x1b, 0x5b, 0x3f, 0x31, 0x30, 0x34, 0x39, 0x6c]);

  it("detects enter and exit sequences in a complete chunk", () => {
    const detector = createAltScreenDetector();

    expect(detector.feed(ENTER)).toEqual({ entered: true, exited: false });
    expect(detector.feed(EXIT)).toEqual({ entered: false, exited: true });
  });

  it("ignores output that merely looks similar and has no alt-screen sequence", () => {
    const detector = createAltScreenDetector();

    expect(detector.feed(new TextEncoder().encode("plain [?1049h without ESC"))).toEqual({
      entered: false,
      exited: false,
    });
  });

  it("detects a sequence split across chunks without a false positive", () => {
    const detector = createAltScreenDetector();
    let entered = false;
    let exited = false;

    for (const byte of ENTER) {
      const result = detector.feed(new Uint8Array([byte]));
      entered ||= result.entered;
      exited ||= result.exited;
    }
    expect(entered).toBe(true);
    expect(exited).toBe(false);

    for (const byte of EXIT) {
      const result = detector.feed(new Uint8Array([byte]));
      entered ||= result.entered;
      exited ||= result.exited;
    }
    expect(entered).toBe(true);
    expect(exited).toBe(true);
  });

  it("detects both transitions carried by one large output batch", () => {
    const detector = createAltScreenDetector();
    const bytes = new Uint8Array(ENTER.length + EXIT.length);
    bytes.set(ENTER, 0);
    bytes.set(EXIT, ENTER.length);

    expect(detector.feed(bytes)).toEqual({ entered: true, exited: true });
  });
});
