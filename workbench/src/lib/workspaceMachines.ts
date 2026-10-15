
import type { RemoteMachine } from "../types";

export interface WorkspaceMachineRecord {
  machine_name?: string | null;
  machine_host?: string | null;
}

function normalizedTokens(record: WorkspaceMachineRecord): string[] {
  return [record.machine_name, record.machine_host]
    .flatMap((value) => (value ?? "").trim().toLowerCase())
    .filter(Boolean);
}

/**
 * b13 wrote some remote history identities as the SSH destination
 * (`admin@host`) before the workspace binding learned to preserve the profile
 * name. Resolve those aliases back to the configured machine profile so a
 * recent entry opens `win-test`, not an unregistered pseudo-machine.
 */
export function configuredMachineName(
  machines: RemoteMachine[],
  record: WorkspaceMachineRecord,
): string | null {
  const tokens = normalizedTokens(record);
  if (!tokens.length) return null;
  const match = machines.find((machine) => {
    const values = [
      machine.name,
      machine.host,
      machine.user ? `${machine.user}@${machine.host}` : "",
    ]
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean);
    return tokens.some((token) => values.includes(token));
  });
  return match?.name ?? null;
}
