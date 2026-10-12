/**
 * b3: explicit ownership of the terminal viewport.
 *
 * xterm already avoids moving the viewport when the user has scrolled away
 * from the bottom. The remaining surprise is standard alt-screen semantics:
 * entering a full-screen CLI saves the normal-buffer viewport, and leaving it
 * restores that stale position even when the normal buffer has since grown.
 * This state machine makes the policy explicit without forcing output onto a
 * user who is deliberately reviewing history.
 */
export interface ScrollOwnership {
  /** Live output may move the viewport only outside review mode. */
  shouldFollowOutput(): boolean;
  /** Called by a viewport scroll event when it is within the bottom threshold. */
  onUserScrollAtBottom(): void;
  /** Called by a viewport scroll event after an explicit scroll away from bottom. */
  onUserScrollAway(): void;
  /** Returns true when typing must first restore the viewport to the bottom. */
  onUserInput(): boolean;
  /** Returns true when leaving alt-screen should restore live-output tracking. */
  onAltScreenExit(): boolean;
}

export function createScrollOwnership(): ScrollOwnership {
  let reviewing = false;

  return {
    shouldFollowOutput: () => !reviewing,
    onUserScrollAtBottom: () => {
      reviewing = false;
    },
    onUserScrollAway: () => {
      reviewing = true;
    },
    onUserInput: () => {
      if (!reviewing) return false;
      reviewing = false;
      return true;
    },
    onAltScreenExit: () => !reviewing,
  };
}

/**
 * Codex 0.154 does not switch to the alternate screen. Its startup sequence is
 * `CSI H + CSI 2J + CSI 3J`; the final ED3 discards normal-buffer scrollback,
 * which trims `ybase`/`ydisp` and is perceived by users as a jump to the top.
 * A CSI handler must return true to suppress xterm's default ED3 behavior while
 * leaving ED0 (erase below) and ED2 (erase display/TUI redraw) untouched.
 */
export function isEraseScrollbackRequest(params: readonly (number | number[])[]): boolean {
  return params[0] === 3;
}

/**
 * Focus-reporting TUIs make xterm emit CSI I/O through onData when focus state
 * is reported. These are terminal protocol responses, not keystrokes, so they
 * must not pull a reviewing user back to the live prompt.
 */
export function isTerminalFocusReport(data: string): boolean {
  return data === "\u001b[I" || data === "\u001b[O";
}

const TERMINAL_REPORTS: RegExp[] = [
  /^\x1b\[[0-9;]*R$/, // cursor position
  /^\x1b\[\?[0-9;]*c$/, // primary device attributes
  /^\x1b\]1[01];[^\x07\x1b]*(?:\x07|\x1b\\)$/, // foreground/background color
  /^\x1bP[^\x1b]*\x1b\\$/, // DCS response (for example XTVERSION)
];

/** True when the entire onData payload is a terminal-generated mode report. */
export function isTerminalGeneratedInput(data: string): boolean {
  return isTerminalFocusReport(data) || TERMINAL_REPORTS.some((re) => re.test(data));
}

/** Exact DEC private mode sequences used by common full-screen TUIs. */
const ALT_SCREEN_ENTER = new Uint8Array([
  0x1b, 0x5b, 0x3f, 0x31, 0x30, 0x34, 0x39, 0x68,
]);
const ALT_SCREEN_EXIT = new Uint8Array([
  0x1b, 0x5b, 0x3f, 0x31, 0x30, 0x34, 0x39, 0x6c,
]);

export interface AltScreenEvent {
  entered: boolean;
  exited: boolean;
}

/**
 * Detects alt-screen transitions across arbitrary write batches. Keeping the
 * last seven bytes lets a sequence whose final byte arrives in the next batch
 * complete without treating any partial prefix as either transition.
 */
export function createAltScreenDetector() {
  let tail = new Uint8Array(0);

  const findSequence = (haystack: Uint8Array, needle: Uint8Array): boolean => {
    outer: for (let i = 0; i <= haystack.length - needle.length; i++) {
      for (let j = 0; j < needle.length; j++) {
        if (haystack[i + j] !== needle[j]) continue outer;
      }
      return true;
    }
    return false;
  };

  return {
    feed(bytes: Uint8Array): AltScreenEvent {
      const joined = new Uint8Array(tail.length + bytes.length);
      joined.set(tail, 0);
      joined.set(bytes, tail.length);

      const event: AltScreenEvent = {
        entered: findSequence(joined, ALT_SCREEN_ENTER),
        exited: findSequence(joined, ALT_SCREEN_EXIT),
      };
      tail = joined.slice(Math.max(0, joined.length - 7));
      return event;
    },
  };
}
