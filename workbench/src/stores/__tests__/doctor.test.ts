/**
 * Doctor store tests (G-13, Step 12; A-G13-3): run() surfaces the report on
 * success and a structured error on failure, never starts a second doctor
 * while one is in flight, and open/close is standalone - it never touches the
 * runtime/settings stores (A-G13-3 "不改变 startup state").
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { DoctorReport, WorkbenchError } from "../../types";
import { useDoctorStore } from "../doctor";
import type { UpdateHealth } from "../../lib/ipc";

const mockIpc = vi.hoisted(() => ({
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  runDoctor: vi.fn(),
  appUpdateHealth: vi.fn(),
  opTraces: vi.fn(),
  logsTail: vi.fn(),
  diagnosticBundle: vi.fn(),
}));

vi.mock("../../lib/ipc", () => mockIpc);

const report: DoctorReport = {
  checks: [
    { name: "docker-cli", status: "pass", message: "found", detail: null, hint: null },
    { name: "aisc-root", status: "fail", message: "bad", detail: "detail", hint: "run install" },
  ],
  summary: { passed: 1, warnings: 0, failures: 1, skipped: 0 },
};

const wbError: WorkbenchError = {
  code: "WB_ERR_CLI_TIMEOUT",
  message: "AISC CLI 响应超时",
  technical_detail: null,
  retryable: true,
  action: "retry",
};

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
});

describe("run", () => {
  it("surfaces the report on success", async () => {
    mockIpc.runDoctor.mockResolvedValue(report);
    const s = useDoctorStore();
    await s.run();
    expect(s.status).toBe("done");
    expect(s.report).toEqual(report);
    expect(s.error).toBeNull();
    expect(s.hasFailures).toBe(true);
    // lifecycle-logging (P4.5): the UI action lands on the shared timeline
    expect(mockIpc.logUiEvent).toHaveBeenCalledWith("doctor_run", "ok");
  });

  it("surfaces a structured error on failure", async () => {
    mockIpc.runDoctor.mockRejectedValue(wbError);
    const s = useDoctorStore();
    await s.run();
    expect(s.status).toBe("error");
    expect(s.error?.code).toBe("WB_ERR_CLI_TIMEOUT");
    expect(s.error?.message).toBe("AISC CLI 响应超时");
    expect(s.report).toBeNull();
    expect(mockIpc.logUiEvent).toHaveBeenCalledWith(
      "doctor_run", "error", "WB_ERR_CLI_TIMEOUT");
  });

  it("never starts a second doctor while in flight (A-G13-3)", async () => {
    let resolveFirst!: (v: DoctorReport) => void;
    mockIpc.runDoctor.mockImplementation(
      () =>
        new Promise<DoctorReport>((resolve) => {
          resolveFirst = resolve;
        })
    );
    const s = useDoctorStore();
    const p1 = s.run();
    const p2 = s.run(); // re-entry while running
    expect(s.status).toBe("running");
    resolveFirst(report);
    await Promise.all([p1, p2]);
    expect(mockIpc.runDoctor).toHaveBeenCalledTimes(1);
    expect(s.status).toBe("done");
  });
});

describe("openDialog / closeDialog", () => {
  it("opens and runs a fresh diagnosis", async () => {
    mockIpc.runDoctor.mockResolvedValue(report);
    const s = useDoctorStore();
    s.openDialog();
    expect(s.open).toBe(true);
    expect(s.status).toBe("running");
    await vi.waitFor(() => expect(s.status).toBe("done"));
  });

  it("closing does not alter startup state (A-G13-3)", async () => {
    mockIpc.runDoctor.mockResolvedValue(report);
    const s = useDoctorStore();
    s.openDialog();
    await vi.waitFor(() => expect(s.status).toBe("done"));
    s.closeDialog();
    expect(s.open).toBe(false);
    // Status keeps the last result; nothing else in the app was touched.
    expect(s.status).toBe("done");
  });
});

describe("loadLogs (lifecycle-logging P3)", () => {
  it("fills the log tail from logs_tail(100)", async () => {
    mockIpc.logsTail.mockResolvedValue({
      path: "C:\\data\\logs\\aisc.log",
      lines: [
        { ts: "2026-08-20T05:00:00Z", level: "info", source: "app", event: "op" },
        { ts: "2026-08-20T05:00:01Z", level: "info", source: "cli", event: "cli_exit" },
      ],
    });
    const s = useDoctorStore();
    await s.loadLogs();
    expect(mockIpc.logsTail).toHaveBeenCalledWith(100);
    expect(s.logs).toHaveLength(2);
    expect(s.logs[1]?.event).toBe("cli_exit");
  });

  it("degrades to empty on IPC failure (log view never blocks the dialog)", async () => {
    mockIpc.logsTail.mockRejectedValue(new Error("boom"));
    const s = useDoctorStore();
    await s.loadLogs();
    expect(s.logs).toEqual([]);
  });
});


it("invalidates late doctor responses across context changes including A to B to A", async () => {
  let finish!:(r:DoctorReport)=>void;
  mockIpc.runDoctor.mockImplementationOnce(()=>new Promise(r=>{finish=r;})).mockResolvedValue(report);
  const s=useDoctorStore();s.setContext("A");const old=s.run();
  s.setContext("B");s.setContext("A");await s.run();finish({...report,checks:[]});await old;
  expect(s.report?.checks).toEqual(report.checks);expect(s.status).toBe("done");
});
it("closing an in-flight doctor prevents it overwriting a reopened dialog", async () => {
  let finish!:(r:DoctorReport)=>void;
  mockIpc.runDoctor.mockImplementationOnce(()=>new Promise(r=>{finish=r;})).mockResolvedValue(report);
  const s=useDoctorStore();s.openDialog();s.closeDialog();s.openDialog();
  await vi.waitFor(()=>expect(s.status).toBe("done"));finish({...report,checks:[]});await Promise.resolve();
  expect(s.report?.checks).toEqual(report.checks);
});
it("reads local updater observations without changing target doctor facts", async () => {
  const snapshot={workbenchVersion:"2.1.17", observations:[],containerExtensions:{status:"unknown",reason:"not-probed"}};
  mockIpc.appUpdateHealth.mockResolvedValue(snapshot);const s=useDoctorStore();s.report=report;
  await s.loadUpdateHealth();expect(s.updateHealth).toEqual(snapshot);expect(s.report).toEqual(report);
});

describe("update health snapshot lifecycle", () => {
  const snapshot: UpdateHealth = {
    workbenchVersion: "2.1.17",
    observations: [],
    containerExtensions: { status: "unknown", reason: "not-probed" },
  };
  const newer: UpdateHealth = {
    ...snapshot,
    observations: [{
      scope: "host-update", endpoint: "https://github.com", route: "direct",
      transport: "direct", status: "success", latencyMs: 20,
      errorCode: null, checkedAt: 200,
    }],
  };

  function deferHealth() {
    let resolve!: (value: UpdateHealth) => void;
    let reject!: (reason: Error) => void;
    const promise = new Promise<UpdateHealth>((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
  }

  it.each(["success", "failure"])("ignores an older load's %s after a newer snapshot", async (outcome) => {
    const old = deferHealth();
    mockIpc.appUpdateHealth.mockReturnValueOnce(old.promise).mockResolvedValue(newer);
    const s = useDoctorStore();
    const pending = s.loadUpdateHealth();
    await s.loadUpdateHealth();
    if (outcome === "success") old.resolve(snapshot);
    else old.reject(new Error("old failure"));
    await pending;
    expect(s.updateHealth).toEqual(newer);
  });

  it.each(["success", "failure"])("ignores a closed dialog's late %s after reopening", async (outcome) => {
    const old = deferHealth();
    mockIpc.runDoctor.mockResolvedValue(report);
    mockIpc.appUpdateHealth.mockReturnValueOnce(old.promise).mockResolvedValue(newer);
    const s = useDoctorStore();
    s.openDialog();
    const pending = s.loadUpdateHealth();
    s.closeDialog();
    s.openDialog();
    await s.loadUpdateHealth();
    if (outcome === "success") old.resolve(snapshot);
    else old.reject(new Error("closed dialog failure"));
    await pending;
    expect(s.updateHealth).toEqual(newer);
  });

  it("clears the obsolete snapshot while reloading and on close", async () => {
    const next = deferHealth();
    mockIpc.appUpdateHealth.mockResolvedValueOnce(snapshot).mockReturnValueOnce(next.promise);
    const s = useDoctorStore();
    await s.loadUpdateHealth();
    const pending = s.loadUpdateHealth();
    expect(s.updateHealth).toBeNull();
    next.resolve(newer);
    await pending;
    s.closeDialog();
    expect(s.updateHealth).toBeNull();
  });

  it("prevents a pending snapshot from populating a closed dialog", async () => {
    const old = deferHealth();
    mockIpc.appUpdateHealth.mockReturnValueOnce(old.promise);
    const s = useDoctorStore();
    const pending = s.loadUpdateHealth();
    s.closeDialog();
    old.resolve(snapshot);
    await pending;
    expect(s.updateHealth).toBeNull();
  });

  it.each(["success", "failure"])("refreshes an open dialog across A-B-A and ignores old %s", async (outcome) => {
    const old = deferHealth();
    mockIpc.runDoctor.mockResolvedValue(report);
    mockIpc.appUpdateHealth.mockReturnValueOnce(old.promise).mockResolvedValue(newer);
    const s = useDoctorStore();
    s.setContext("A");
    s.openDialog();
    const pending = s.loadUpdateHealth();
    s.setContext("B");
    s.setContext("A");
    await Promise.resolve();
    expect(s.updateHealth).toEqual(newer);
    if (outcome === "success") old.resolve(snapshot);
    else old.reject(new Error("old context failure"));
    await pending;
    expect(s.updateHealth).toEqual(newer);
  });

  it("clears a closed dialog's old context snapshot without loading another", async () => {
    mockIpc.appUpdateHealth.mockResolvedValueOnce(snapshot);
    const s = useDoctorStore();
    s.setContext("A");
    await s.loadUpdateHealth();
    s.setContext("B");
    expect(s.updateHealth).toBeNull();
    expect(mockIpc.appUpdateHealth).toHaveBeenCalledTimes(1);
  });
});
