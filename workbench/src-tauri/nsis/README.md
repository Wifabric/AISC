# NSIS installer template

## Current candidate and acceptance

Workbench **2.1.19-preview.1** carries CLI **0.3.0.dev0**. GitHub Windows run [44458626580](https://github.com/Wifabric/AISC/actions/runs/44458626580) passed silent fresh installation, PATH, reinstall/retention, and upgrade from official 2.1.18 at `58b25ecdfd0dfed3c0d920a05d7d612eccb75d40`. The upgrade verifies real settings/history/project/transcript samples, installed CLI reads, native window creation, and retention after silent uninstall. Later candidate results and exact heads are recorded in [DELIVERY](../../../docs/plans/2.1.19-dev-plans/DELIVERY.md).

`scripts/test-windows-upgrade.ps1` deliberately refuses execution outside a GitHub Windows runner. It validates the official baseline SHA-256 and emits `upgrade-result.json` in the `windows-upgrade-acceptance` artifact. Never remove that guard to run it against a personal installation. Silent checks do not exercise the interactive wizard, Docker dependency onboarding, cancellation, or optional Docker/data cleanup. Those remain separate manual acceptance items. The earlier local sandbox policy block and VM cleanup remain historical evidence; no local VM is required for this CI path.

The desktop configuration uses `installMode: currentUser`. A separate local Windows account can separate user-scoped installation state, but it is not a clean OS and does not isolate shared Docker resources. Portable desktop tests do not exercise the NSIS installation or uninstallation sections.

## Publisher signing configuration

From the repository root, `scripts/build-installer.ps1 -SigningConfig <path-to-tauri-overlay.json>` accepts a publisher-provided Tauri configuration with `bundle.windows.certificateThumbprint` or `bundle.windows.signCommand`. With this option, the script selects an installer produced during the current build, requires a valid Authenticode signature, and checks the signer thumbprint when one was specified. Keep private keys and signing credentials outside the repository.

Omitting the option does not sign the installer. The present candidate is unsigned; adding configuration support is not evidence of a successful signed build or of compatibility with the sandbox policy. Verify the actual output signature and installed behavior separately. Do not use an old setup file as proof of the current build.

## Template implementation

`installer.nsi` is a **Handlebars template** rendered by tauri-bundler at build
time (`bundle.windows.nsis.template`). It is a copy of the tauri-bundler 2.9.4
default template with the G-18 additions:

- `Section Docker` (runs after `Section Install`): on **interactive GUI
  installs only** (`${Silent}` / `$PassiveMode` guards), if Docker Desktop is
  missing it is installed via winget (`Docker.DockerDesktop`) with live
  progress streamed into the INSTFILES Details pane (`nsExec::ExecToLog`).
  Silent/passive installs skip it entirely (the CI smoke installs with `/S`).
  Failures do not abort the install; the Workbench preflight reports the real
  engine state at first launch.
- `RunFinishApp` (finish-page "Start AISC Workbench"): three-way Docker
  handling before launching the Workbench - installed + running → no-op;
  installed + stopped → silently start it; not installed → prompt to open the
  Docker Desktop download page (Workbench still launches).
- Docker detection (`CheckDocker`): by executable presence (per-user
  `%LOCALAPPDATA%` or machine-wide `Program Files\Docker\Docker`) with the
  uninstaller registry entry `InstallLocation` (64-bit view → HKCU →
  WOW6432Node) as a non-standard-path fallback. `CheckWinget` verifies the
  winget alias exists on PATH. `StartDockerDesktop` uses
  `nsis_tauri_utils::FindProcess`/`FindProcessCurrentUser` (0 = running) and
  `ExecShell open` to launch Docker Desktop when it is installed but stopped.
- The G-18 host-Python dependency page was **removed** (`800715c`): the frozen
  sidecar bundles its own Python, so no host Python/winget check page exists.

Source: `https://crates.io/crates/tauri-bundler` 2.9.4,
`src/bundle/windows/nsis/installer.nsi`.

## Bundled AISC CLI bundle (aisc-bundle)

The installer ships the full AISC CLI bundle (`aisc-bundle\`) next to the
sidecar exe so CLI root discovery works on an installed Workbench without a
repository checkout (`resources.py` frozen-bundle branch). The bundle is
**not** committed: CI stages it via `python packaging/artifact.py stage --root . --output workbench/src-tauri/nsis/bundle` before `tauri build` (fails fast on verification), and `tauri.conf.json` maps it into `$INSTDIR` with `bundle.resources` (`nsis/bundle/aisc-bundle` -> `aisc-bundle`, recursive directory copy rendered as one `File /a "/oname=..."` per file by the NSIS template). Locally, `tauri build` requires the staging step to have run first — same friction class as the externalBin sidecar.

## Languages

`bundle.windows.nsis.languages: ["English", "SimpChinese"]` + `displayLanguageSelector:
true` in `tauri.conf.json`: the rendered installer shows the MUI language picker
(remembered in `HKCU\Software\cn.aisc.workbench\...\Installer Language`, so it
appears only on the first install; silent `/S` skips it). The MUI page strings
come from tauri-bundler's embedded language files; the custom S4.1.b strings are
`LangString DEP_*` definitions in `installer.nsi` right after the
`{{#each language_files}}` include block. The file must stay **UTF-8 without
BOM** - tauri-bundler writes the rendered script with a UTF-8 BOM and compiles
with `-INPUTCHARSET UTF8`, which is what makes the CJK strings render correctly
on any locale. `$(DEP_*)` references in code earlier in the file are fine
(makensis resolves LangStrings at the end of the compile pass, same as the
template's own `$(older)`/`$(alreadyInstalled)` references).

## Maintenance

When upgrading tauri-bundler (via `@tauri-apps/cli`), diff this file against
the new default template and re-apply the G-18 additions:

1. `Var DepsDocker*` / `Var DockerWingetExit` declarations in the header var
   block.
2. `CheckDocker` / `CheckWinget` / `StartDockerDesktop` functions next to
   `RunFinishApp`.
3. `Section Docker` between `Section Install` and `Function .onInstSuccess`.
4. The `LangString DOCKER_*` block after the `{{#each language_files}}` include
   (keep it in sync with the strings used above; `${LANG_SIMPCHINESE}`
   requires `SimpChinese` to stay in the `languages` config array).
5. The detection checks. `check-deps-test.nsi` in this directory holds
   `CheckDocker`/`CheckWinget` verbatim: after changing them, compile and run
   the test installer to verify detection against the local machine -
   `makensis check-deps-test.nsi` then `%TEMP%\aisc-check-test.exe /S` and
   read `%TEMP%\aisc-check-result.txt` (`docker_installed` / `winget_installed`
   reflect the local machine). The test installer is not part of the tauri
   build. `StartDockerDesktop` is not covered there (needs the tauri
   `nsis_tauri_utils` plugin, only present in the real build).

Keep all other `{{handlebars}}` placeholders intact - they are required by the
renderer. Do not delete or renumber the page comments; the template depends on
the MUI page order.
