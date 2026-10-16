# Reproducible PrintFins stability checks

The maintainer has confirmed successful fin generation, joint slicing and native
3MF saving/reopening through the new GUI. These manual results are retained;
they are not counted as automated test passes. Product code, menu placement and
all 44 original engine files are unchanged by this test work.

## One command on the normal Windows desktop

From this checkout, on `feature/printfins-stability-tests`, with a matching
local build and public preset template:

```powershell
python scripts/printfins/run-stability.py
```

Defaults are `build/runtime/bambu-studio.exe` and the public preset template
under `build/ui-smoke/profile`. This separate test checkout does not copy or
modify an existing runtime/profile. To reuse the retained, matching UI build
in the adjacent worktree with one command:

```powershell
python scripts/printfins/run-stability.py --exe ../ui-tool/build/runtime/bambu-studio.exe --profile-template ../ui-tool/build/ui-smoke/profile
```

The runner checks DLL/source hashes when the runtime's sibling
`native/validation.json` receipt exists and reports whether it was verified.
The DLL hash must match exactly; source receipts allow Git's LF/CRLF checkout
conversion, without accepting other text changes.
For another matching build:

```powershell
python scripts/printfins/run-stability.py --exe PATH_TO_BAMBU_STUDIO_EXE --profile-template PATH_TO_TEST_PROFILE
```

Requirements: Windows 10/11, an unlocked interactive desktop, Python 3.10+,
Node 22+ with built-in WebSocket support, and the branch's working Windows
build with its matching resources. No Python/npm package installation or browser
download is needed. Native object-tree selection additionally uses Windows
UI Automation through PowerShell; local execution policy remains in force.

The run opens visible test-owned Bambu windows and controls their menus, forms
and file dialogs. Leave the keyboard/mouse idle while it runs. It may take
several minutes. Each scenario gets a fresh isolated profile containing only
public system presets and the existing helper's whitelisted settings. Normal
profiles, printer connections, existing windows and earlier test outputs are
not edited. Only processes started by the test may be closed/terminated;
forced shutdown is recorded and cannot count as a pass.

The runner uses a fresh loopback CDP port for the test's WebView2 instance,
following the repository's existing Web-E2E approach. It does not disable
browser/OS sandboxing, change execution policy, run elevated or change global
environment settings. A restricted/locked input desktop or denied WebView2
process is recorded as **BLOCKED**, without attempting a workaround.

## Scenarios and evidence

| Kind | Scope and checks |
| --- | --- |
| Native GUI + CDP | Seven synthetic meshes: tilted box, shelf, round foot, thin tilted wall, mirrored/translated input, two overhangs and a flat model needing no support. Load each model directly as a startup argument; click the actual native menu item, use real settings controls, submit to the actual module worker/engine, accept through C++, slice/export real G-code, save/reopen/resave native 3MF and slice again. |
| Native cancellation | Cancel before submitting; reopen and cancel using Escape/window close; cancel after observing C++'s computing status and a real worker launch on a 6,912-triangle grid, before a result. Compare project geometry/settings immediately and after a bounded two-second late-result check. A lost timing race is inconclusive/BLOCKED, never a pass. |
| Native safety/state | Invalid visible options must not reach the worker. Reject duplicate generation, no selection, multiple selected models, multiple instances, modifiers/negative volumes and a 100,004-triangle input. Check one Undo and one Redo against saved original/generated projects. |
| Native selection | Select one object in a two-object project through the OS accessibility interface; verify the unselected object remains unchanged. An unavailable accessibility provider is BLOCKED for that case. |
| Native fresh-process round trip | Start another Bambu process from the generated native project, compare posed geometry, reject regeneration on existing fins, slice and resave. |
| Fault injection into actual integration | In the test WebView only, turn one real worker-result coordinate into null, or make worker postMessage throw. Check the actual C++/WebView error path and unchanged saved project. These are explicitly labelled fault injections; no engine/vendor file is patched and no invented success is sent to C++. |
| Engine/adapter tests | Existing adapter tests plus deterministic geometry/repetition, output range coverage, finite coordinates, original-engine equality, all numeric schema ranges, malformed geometry/options and host heights. These do not prove Bambu GUI behavior. |
| Simulated DOM/worker tests | Existing settings/transport tests check defaults, units, dependencies, invalid fields and transport lifecycle with test doubles. Kept separate from native GUI tests. |
| Test-infrastructure unit tests | Native/split 3MF component transforms, face reindexing, changed pose/names/types/settings, malformed/cyclic references, input variant creation, protection of existing artifacts and honest report/shutdown status. These are not GUI tests. |

Native project checks follow the 3MF build/component hierarchy, including
external model files. They compare printable part names/types, triangle counts,
world geometry within 0.0001 mm, object metadata and relevant preset settings.
Other normalized settings differences are listed for review. Generated geometry
is independently replayed from the **captured real C++ worker request**, using
the unchanged adapter/engine, and compared with the native saved fin parts.
Slicing success requires an exported Bambu G-code file with a positive layer
count, actual extrusion moves and the complete executable-block end marker.

Each new `build/stability-TIMESTAMP/` contains:

- `report.json` and `report.md`: every scenario, kind, PASS/FAIL/BLOCKED/NOT_RUN,
  errors, timings and log paths. Manual confirmations are separate metadata.
- `automated/node.xml`, Node/Python logs and source-snapshot results.
- Per executed GUI case: launch/build identity, native window/menu actions,
  Bambu profile logs, WebView2/CDP/worker traces, settings screenshots where supported, captured
  worker requests, native before/after/round-trip projects, G-code, comparison
  results, exception details and process-cleanup outcome.
- Synthetic input STL/JSON fixtures and a manifest, including cancellation and
  input-limit fixtures. Earlier run directories are preserved.

Exit code 0 means all requested cases passed, 1 means a failure, and 2 means at
least one blocked/not-run case without failures. `--no-gui` deliberately marks
desktop scenarios NOT_RUN and therefore returns 2. Ctrl+C closes the test-owned
session; the report records interruption. Results remain local under ignored
`build/`; raw profiles/logs and generated binaries are not publication content.

## Actual restricted-account result, 2026-10-16

- **36 tests passed:** 27 Node tests, including four simulated DOM/worker tests,
  and nine Python test-infrastructure tests. No executed final test failed.
- **44/44 original files verified** against SHA-256 and upstream Git blob IDs.
- **23 native GUI/fault scenarios not executed:** input-desktop preflight is
  BLOCKED because cursor positioning is denied. The aggregate report also
  contains that separate blocked preflight (24 BLOCKED entries in total).
  No Bambu GUI process was launched by this blocked run.
- The new 3MF comparator was additionally checked against retained real Bambu
  baseline projects, including split model files: three parts, counts
  12/440/13,280 and maximum world-coordinate difference 0.0000005640 mm.
  This reuses artifacts; it is not a fresh GUI round trip.

The report-writer issue found during the initial dry run was corrected and is
covered by regression tests. Native Windows automation/CDP and accessibility
steps were prepared and syntax-checked. A later external run reached the first
native Save command but failed with **File dialog not found**; it did not run
the 23 scenarios. Foreground restrictions, changed UI/native
dialogs or unavailable accessibility may produce BLOCKED/FAIL with diagnostics;
the runner never silently substitutes an engine-only success for a GUI case.

The known separate CLI shutdown hang remains documented; no CLI fix, product
feature, preset tuning, physical print qualification or large-model reliability
claim is included. No commit or push is part of this stability-test work.

## Separate stability checkpoint, 2026-10-16

The branch starts at the GitHub `integration` commit `3e394c951f4b`, which
contains the approved UI integration. Only test infrastructure and its
documentation are transferred; the original UI worktree is preserved.

The failed desktop trace showed that the former driver dismissed the native
popup, then posted `WM_COMMAND` to the main window; Save did not open a dialog.
Bambu uses wx popup-menu routing. The driver now clicks live popup items,
including their submenus, without changing focus away from the active menu.
The separate seed-process/bootstrap save is removed. Each scenario opens its
model directly at process startup; selection variants reuse the first geometry
scenario's native `before.3mf`. If that baseline is unavailable, only scenarios
depending on it are blocked, rather than the entire matrix.

Review also found a test-fixture issue: duplicating split 3MF objects could
remap IDs belonging to another model file when local IDs overlapped. External
component/part IDs now remain in their original file's ID space. Regression
tests cover that case and native-menu dispatch/disabled-item behavior.

Current verification: **45 tests passed** (27 Node, including four simulated
DOM/worker tests; 18 Python infrastructure tests), plus the 44-file provenance
check. `--no-gui` reports all 23 desktop cases as **NOT_RUN**, with exit code 2.
The corrected native-menu path still needs a manual Windows desktop run;
unit tests use native-API doubles and do not prove that the file dialog opens.
The maintainer-confirmed generation/slicing/3MF workflow remains manual
evidence for the product. No GUI test is added to CI.

### Final driver review: menus and focus

The later retained desktop run reached Bambu but recorded six menu/submenu
automation failures and 17 blocked scenarios. This is failed automation,
not evidence of a product/engine failure or a successful GUI matrix. Two
subsequent attempts stopped at `git rev-parse HEAD` with exit 128 before GUI
startup; no Git ownership/security settings were changed to bypass that issue.

The driver had restored every window with `SW_RESTORE`, including visible or
maximized windows, and checked activation immediately. It now restores only
minimized windows, leaves foreground windows of the test process alone, and
allows two seconds for one ordinary foreground activation. A denied focus
request stays BLOCKED; there are no focus-stealing workarounds.

Menu coordinates are read after focusing the main window. Stale popups are
dismissed first. Mouse movement is allowed to settle before a click. Submenus
open by hovering, without the extra click that can toggle an already opened
submenu shut; only leaf commands are clicked. Missing popups produce a native
window snapshot and an explicitly inconclusive/BLOCKED result. The remaining
matrix then stays blocked rather than repeatedly opening applications against
the same automation limitation.

Five additional infrastructure tests cover focus/restore behavior, delayed and
denied activation, submenu hover versus leaf clicks, and honest missing-menu
diagnostics. They use API doubles. The corrected driver has **not** passed a
new real-desktop run; native menus, focus, accessibility-based selection and
the complete 23-case GUI matrix therefore remain open. The one-command manual
Windows runner remains available. The suite is suitable for publication as
test infrastructure with these limitations, not as proof of automated GUI
stability. No product source, UI or original PrintFins files were changed.
