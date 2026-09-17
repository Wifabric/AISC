# Active Planning

Active/in-progress implementation plans live here. Completed plans are archived
under `docs/archive/`: version-cycle plan sets as `docs/archive/<version>-dev-plans/`
(e.g. `2.1.9-dev-plans/`), topical plans under their own directories
(e.g. `container-service-access/`, `aisc-next-followup/b05-terminal-stability/`).

## Current active plan

- (none — 0.1.0 closed 2026-09-17; see ../archive/0.1.0-dev-plans/) Theme: PyPI
  first release + self-update chain (`aisc bundle fetch` / `aisc update` /
  Workbench self-update), Docker resource-management UI, rebuild button, and
  a research batch (provider templating, codex computer use). Execution
  blueprint: [`pypi-release-guide.md`](0.1.0-dev-plans/pypi-release-guide.md);
  rulings R1-R8 in its `decisions.md`. The prior `v2.1.11-dev` cycle closed on
  2026-09-12 (Preview released; plans archived at
  [`2.1.11-dev-plans/`](../archive/2.1.11-dev-plans/), 2.1.11 final explicitly
  skipped per D-1); carry-over backlog stays parked in `docs/todo.md`.

Each active plan must define scope, risks, contracts, implementation order,
automated/manual acceptance, decisions and rollback behavior.
