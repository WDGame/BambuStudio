# Native PrintFins Full Coverage

Branch: `feature/printfins-full-coverage`, isolated worktree from
`origin/integration` at `d52a8ca079c840f409f1281ec240ca780b951b49`.
Checkpoint preparation and explicit staging authorized after successful manual
desktop acceptance. Commit, push and PR creation await separate authorization.

## Behavior and compatibility

Under Support > Type > PrintFins, Generation mode selects Auto (default) or
Full Coverage. Full Coverage calls the existing official `computeFins` mode
`full`; Auto calls `auto`. Wide-face coverage remains an independent density
control. Button text and description follow the selected mode.

The host adds a choice to `schema.mjs` and the native C++ presentation schema.
`optionsFromSettings` validates and removes `mode` before calling the original
`optionsFromDialog`, then passes it separately to `computeFins`. The existing
native request/WebView/worker/result path is retained. Other unknown options
remain errors; Draw, Hybrid, custom fill toggles and resin remain unavailable.

The mode is saved inside the existing `printfins_options` JSON string, using
the normal preset/project machinery. Missing mode means Auto. Existing sparse
JSON is preserved when all values match the saved preset. The per-value reset
uses the active saved preset, including its selected generation mode.
Global/object/part settings retain Bambu's existing aggregate-string override
semantics: an object with no override inherits the global value; an old object
JSON override without mode uses Auto. This change does not introduce per-key
merging of separate JSON strings or a new Bambu config enum.

Generated pieces retain the exact original IDs, kinds and triangle ranges.
The existing C++ acceptance checks, detached-model preparation, ordinary
model-part insertion and single generation undo snapshot are reused. Existing
selection/duplicate/cancellation guards are unchanged. The later Undo/Redo
investigation below corrects history availability and snapshot initialization
in Bambu's existing undo core; it does not alter the generation/insertion path.
The maintainer has now confirmed physical GUI Undo/Redo for both modes and
new edits after reopening a native 3MF (see Desktop acceptance below).

All 49 original vendor files, `ORIGIN.json` and the MIT license remain unchanged
at `2cf5110efbdcc4ec1906adfba9dcb88f27f7dfb4`. Support gap remains 0.10–0.40 mm.
No geometry algorithm, rendering change or unrelated feature is added.

## Verification

| Check | Result and actual scope |
| --- | --- |
| Vendor snapshot | PASS: all 49 SHA-256/Git blob hashes match the unchanged manifest and exact official Git commit bytes. |
| Node regression suite | 39 PASS: original Auto output/defaults, both modes against original computeFins on eight fixtures, invalid modes, separate density, complete piece ranges, Sway pieces, settings and production page transport. DOM/Worker transport uses test doubles; geometry is real. |
| Python regression suite | 18 PASS: existing driver/oracle unit tests, including Win32 doubles. No physical GUI claim. |
| Dedicated native C++ suite | 14/19 PASS, including all nine PrintFins cases and the new Undo/Redo regression. Mode validation, legacy Auto fallback, real preset reset/dirty state and native global/object/part 3MF pass. Five failures match the previously proven original baseline, with identical normalized messages and exit codes. |
| Windows x64 Release | PASS: build/link exits 0. Isolated incremental build, verified unchanged core libraries/objects reused. The Full host and dedicated test sources were rebuilt; the Undo fix then recompiles Plater, UndoRedo and the extended regression source, with GUI DLL/tests relinked into `undo-redo-fixed-release`. Existing LNK4098/LTCG warnings retained. No clean-from-scratch build claim. |
| Real Bambu slicing and native 3MF | PASS: four Auto/Full fixture cases, 24 complete slices (including Normal/Tree Auto/Manual and reopened PrintFins projects), four native 3MF round trips. Mode/settings and all generated parts retained. Manual Normal/Tree modes were unpainted. Independent triangle matching error at most 0.000003899 mm. |
| Real Windows startup/model/Support page | PASS through the new isolated launcher: actual native main window/canvas/model and Support page, posted Win32 input, normal exit 0. This does not certify physical mouse interaction. |
| Native Full project load and mode control | PASS: actual Bambu GUI opens the backend Full/Sway 3MF and shows Generation mode / Full Coverage. Posted Win32 selection events switch Auto/Full and update the native Generate button, normal exit 0. This is an actual native control/event test, not a DOM double or physical input test. It does not click Generate or exercise GUI Undo/Redo. |
| Targeted native Undo/Redo | PASS: four native scenarios (Auto/Full new generation and Auto/Full loaded-project edits), exact per-part geometry/IDs/transforms, correct availability boundaries and six complete slicer outputs. Real production C++ accept/Plater/Stack/slicer; original Node engine with a file transport double in a separate test image. This automation does not certify physical input or the full WebView route; separate manual acceptance follows. |
| New build physical desktop acceptance | PASS, maintainer-reported on 2026-10-17: Auto and Full generation > Undo > Redo > slicing; additional Full walls; native 3MF save/reopen/reslice; new object move > Undo > Redo after reopening. This is the current Full Coverage build's acceptance, separate from the earlier upstream-update acceptance. |

Reproducible synthetic fixtures demonstrate an actual mode difference:

| Fixture | Auto | Full Coverage | Observation |
| --- | --- | --- | --- |
| Shelf | 452 triangles, one support piece | 1,692 triangles, three support pieces | Original fill adds two walls at the same default density. |
| 110-mm shelf with Sway | 3,048 triangles, four pieces | 4,340 triangles, five pieces | One additional fill wall; both original Sway braces remain separate. |

The direct original-engine comparison converts dotted dialog Sway keys with
the original `optionsFromDialog` before calling computeFins. Passing dotted
keys straight to computeFins would omit the nested Sway options and give a
false mismatch; no product algorithm change is needed for that test setup.

The first native mode probe loaded the project and displayed the Full controls,
but sent only `CBN_SELCHANGE`, which does not commit a wxChoice selection. The
local Bambu wxWidgets source (`src/msw/choice.cpp:763`) sends `wxEVT_CHOICE` on
`CBN_SELENDOK`. The final probe uses that notification and passes both switches;
the first failed probe remains in the evidence. The fixture's expected
Customized Preset import notice is acknowledged only in the test-owned window
for our self-generated project; no G-code is sent to a printer.

Known original-Bambu C++ failures are tracked separately from feature tests:
legacy config validation/accessor expectations, binary config serialization
of `coPointsGroups`, enum `draft_shield` setup, and the sinking-object convex
hull reference. The previous update matched their messages/exit codes to
independently built original baseline `926a7192574bcb9b3a732e1ec59a46d79cb45466`.
The newly rebuilt suite reproduces exactly these five failures; per-case XML,
failure messages and the comparison receipt are retained. No new C++ failure
was classified as baseline without a matching comparison.

The original site Auto-worker test's `Worker is not defined` error under the
Node/Deno shim remains a known test-runtime limitation from the unchanged
upstream snapshot. It is not a passing browser test. The original 85 passing
upstream invariant/contact tests were not unnecessarily rerun for unchanged
vendor bytes; the new direct Full/Auto tests execute the real engine here.

Full Coverage is the original bounded fill pass, not a guarantee that every
overhang is supportable. It retains original collision/attachment rules and
can leave unsupported areas. The existing 100,000 input-triangle and output/
120-second generation limits still apply. Physical print quality, exhaustive
intersection/manifold certification, painted manual Normal/Tree supports,
shared WebView-cache isolation and broad physical GUI automation are not
certified. The known CLI shutdown hang is outside this change.

## Evidence and repeat commands

Evidence remains ignored under this worktree's `build/`, including
`full-coverage/node-final.log`, `python.log`, the per-fixture engine soups,
`full-coverage/cpp/`, `full-coverage/backend/`, independent project checks,
and `update-release/` compile/link logs, PDBs, runtime and identity receipt.
`update-release/startup-result.json` and `native-mode-result.json` record the
two successful native-window checks; `native-mode-first-probe.json` retains
the earlier test-driver failure. These probes do not replace physical input.
Local backend/build runners record the reused artifact paths and never write
to another worktree. Build files, profiles and logs must not be staged.

```powershell
python scripts/printfins/check-snapshot.py
node --test tests/printfins/*.test.mjs
python -m unittest discover -s tests/printfins -p 'test_*.py'
```

## Undo/Redo investigation (2026-10-17)

The generation snapshot/insertion code is byte-identical between the original
Auto integration at the integration base and this Full Coverage implementation.
One snapshot is taken before insertion. Bambu captures the complete current
model at the first Undo so that Redo can restore it. No additional post-insertion
snapshot is necessary and none was added.

Before the fix, native Auto and Full runs restored every generated model part,
mesh vertex, triangle index, ID and transform exactly after Undo/Redo. The
reported loss of fin geometry was not reproduced in those runs. Two actual
history-boundary errors were reproduced instead: the initial Load Project
separator could count as undoable, and the current topmost state could count
as redoable even though no successor existed. The real native trace showed
`can_redo=true` after returning to the final state. Separately, default-created
`SnapshotData.snapshot_type` was uninitialized, including the temporary state
captured by Undo. A standalone build against the original header on memory
filled with 0xA5 retained type byte 165 instead of Action (0).

The targeted correction initializes that field to Action and makes
`StackImpl::has_undo_snapshot()` / `has_redo_snapshot()` respect the same
initial/terminal boundaries as Plater navigation. The small shared predicates
retain the existing selection/non-modifying-action classification and are
covered by the dedicated C++ regression case. No model geometry, snapshot
format, PrintFins option or rendering code changes as part of this fix.

Reloading a 3MF after restarting Bambu creates a new history. Missing previous
Undo/Redo actions is expected. New generation or model edits in that loaded
project must create new undoable actions. A merely selected object must not
make the initial project undoable; returning to the current tip must disable
Redo. This is distinct from restoring saved project geometry/settings.

### Targeted test scope and evidence

The normal native WebView generation probe could not load the settings page
in this restricted environment. Its failed run/logs are retained. A separate
instrumented test image exchanges request/result JSON with Node executing the
unchanged original engine. It then uses the **production C++ result acceptance,
native model insertion, Plater Undo/Redo, snapshot serialization and slicer**.
Only WebView transport is doubled; this is not physical desktop acceptance or
proof of the complete WebView path. The regular Release contains no probe,
file transport, test trigger or test-only environment handling.

The native probe compares full per-part mesh arrays, IDs and transforms before
generation, after generation, after Undo and after Redo. It also makes a new
move in a freshly loaded generated 3MF, checks Undo/Redo and slices the restored
model. Initial fixtures inherited a 100-mm factory print-height limit although
the test shelf is 112 mm tall; that made the GUI classify it outside the bed.
Test inputs and the test slicer now use an explicit adequate print height;
the geometry assertions were retained. This was a fixture correction, not a
product or geometry workaround. Earlier backend PASS results establish G-code
generation and serialization, not GUI build-volume validation of that factory
profile. One pre-fix loaded-Full GUI startup was blocked
by access denied creating the existing shared WebView2 cache; no cache/security
settings or files outside this worktree were changed.

Evidence is under ignored `build/undo-redo-20261017/`: original-header repro,
source overlay/probe, real engine requests/results, per-stage model dumps,
native stack traces, G-codes and launcher logs. The new regression case is in
`tests/printfins/native-options-group.cpp`.

Final results with the corrected native undo core:

| Scenario | Result |
| --- | --- |
| Auto generation > Undo > Redo > slicing | PASS. Original model restored by Undo; all four generated fin/Sway parts restored exactly by Redo, then sliced. A subsequent move/Undo/Redo/reslice also passes. |
| Full generation > Undo > Redo > slicing | PASS. All five generated fin/fill/Sway parts restored exactly, then sliced. Subsequent move/Undo/Redo/reslice passes. |
| Freshly loaded Auto 3MF > new move > Undo > Redo > slicing | PASS. Empty old history is expected; the new edit is undoable/redoable and all four support parts remain intact. |
| Freshly loaded Full 3MF > new move > Undo > Redo > slicing | PASS. Same behavior, preserving all five support parts. |
| Availability | PASS in all four native cases. Fresh project: Undo/Redo both false. After Undo: Redo true. Current tip after Redo: Redo false. |
| Application exits and outputs | All four test-owned applications exit 0. Six G-codes contain positive layer counts, extrusion moves and the end marker. |
| Regular corrected Release | PASS: separate non-instrumented binary launches, loads the model, opens Support and exits 0. Binary/source hashes recorded; the probe transport marker is absent from this image. |

See `build/undo-redo-20261017/native-final-results.json`, `cpp/results.json`,
`cpp/baseline-comparison.json`, `node-final.log`, `python-final.log` and the
four `native-fixed-*` / `loaded-fixed-*` directories. The regular build's
receipt and startup result are under `build/undo-redo-fixed-release/`.
The regular image contains no probe code; it was checked separately from the
instrumented image. Existing source/vendor hashes and `git diff --check` pass.
These implementation/test runs did not change another worktree or protected
branch and created no commit. Checkpoint staging is separately authorized below.

The reproduced issues were incorrect history availability and uninitialized
snapshot metadata, not missing fin meshes. Their correction does not claim
that the original physical-desktop observation was uniquely explained.
The maintainer's regular-build acceptance now confirms both mode sequences and
new-edit Undo/Redo after reopening a 3MF. It does not establish a unique cause
for the earlier observation. Prior Undo history across restart is not expected.

## Desktop acceptance

On 2026-10-17 the maintainer reported successful completion on the Windows
desktop of all following acceptance scenarios:

| Physical desktop scenario | Maintainer result |
| --- | --- |
| Auto: Generate > Undo > Redo > slicing | PASS |
| Full Coverage: Generate > Undo > Redo > slicing | PASS |
| Additional support walls in Full Coverage | PASS |
| Save native 3MF, reopen and slice | PASS |
| After reopening 3MF: object move > Undo > Redo | PASS |

This report is direct maintainer confirmation, not an automated observation;
no new desktop log or recording was supplied. The earlier automated evidence
retains its original scope and historical OPEN flags. Preset reset and
global/object/part settings are covered by real native C++ tests; individual
physical reset/override, cancel/retry and duplicate-protection checks were not
separately enumerated in this desktop report and are not newly certified here.
The checklist below remains available to reproduce or broaden the acceptance.

From PowerShell, launch the new build with a fresh public A1 profile and the
110-mm shelf. Leave the console open until Bambu Studio exits:

```powershell
python 'C:\3D-Dev\BambuStudio-PrintFins\.worktrees\printfins-full-coverage\build\undo-redo-fixed-release\start.py'
```

Executable: `build/undo-redo-fixed-release/runtime/bambu-studio.exe` in this
worktree. The older `update-release` DLL could not be replaced (linker LNK1104);
no existing Bambu process was terminated. The corrected Release is isolated.
The launcher verifies binary identity and vendor hashes and records its owned
process, profile/log directory and exit code. Existing profiles are not used.

1. Enable support > Type PrintFins. Verify Generation mode defaults to Auto.
   Enable Sway braces, generate and slice. Undo removes all generated parts
   together; Redo restores them without duplicates.
   Check the toolbar and shortcuts with the 3D viewport focused. After Redo
   reaches the latest state, its button must be disabled.
2. Undo generation, select Full Coverage and regenerate with the same density.
   Expect an additional fill wall and two separate Sway parts; slice again.
   Check mode-dependent button text and description, rotation and selection.
3. Save a process preset with Full selected. Change to Auto and use the orange
   mode reset arrow: it must restore Full and preserve the other settings.
   Verify Global/object overrides and an older project with no mode (Auto).
4. Save as native 3MF, close, then reopen with the same launcher plus
   `--project 'C:\path\saved.3mf'`. Check mode/settings/parts and reslice.
   An empty old history is expected. Make a new model move and verify that
   Undo/Redo now work and that the generated parts remain complete.
   Also check cancel/retry and duplicate-generation protection on a disposable
   project. Keep successful completion distinct from a cancellation test.

For a smaller fixture, append `--model` with the absolute path to this
worktree's `build/desktop-fixture/full-coverage-shelf.stl` (one versus three
walls, without Sway). Record PASS/FAIL/NOT_RUN and the run directory when
repeating or broadening the tests. The maintainer-reported scenarios above
are accepted; the remaining limitations in Verification still apply.

## Checkpoint review (2026-10-17)

The reviewed scope is 16 files: nine host/undo implementation and resource
files, six test/fixture files, and this report. The base remains
`d52a8ca079c840f409f1281ec240ca780b951b49`. No vendor, manifest, license,
support algorithm, rendering, generated build, runtime log or profile file
belongs in the checkpoint. Support gap remains 0.10-0.40 mm.

The checkpoint rerun passes 39 Node tests and 18 Python tests. The rebuilt
dedicated C++ executable again passes 14/19 cases, including all nine
PrintFins cases; all five failures match the retained baseline by normalized
failure messages and exit codes. Exact official Git-byte/hash verification
covers all 49 vendor files. Existing Release, backend, native Undo/Redo and
3MF evidence is reused after checking source/binary receipt hashes; no
unnecessary rebuild or physical desktop repetition is required.

Only these explicitly reviewed files are staged:

```text
docs/printfins-full-coverage.md
resources/printfins/README.md
resources/printfins/adapter.mjs
resources/printfins/schema.mjs
resources/printfins/settings.mjs
resources/printfins/tool.mjs
src/slic3r/GUI/PrintFinsPoC.cpp
src/slic3r/GUI/PrintFinsSettings.hpp
src/slic3r/Utils/UndoRedo.cpp
src/slic3r/Utils/UndoRedo.hpp
tests/printfins/full-coverage.test.mjs
tests/printfins/geometry-fixtures.mjs
tests/printfins/native-options-group.cpp
tests/printfins/native-transport.test.mjs
tests/printfins/settings.test.mjs
tests/printfins/upstream-compatibility.test.mjs
```

The staged list and full staged diff have been reviewed;
`git diff --cached --check` passes. There are no additional unstaged changes
in this worktree. Commit/push/PR creation have not been performed; maintainer
authorization is required before proceeding under AGENTS.md rule 8.

### Prepared commit description

```text
feat(printfins): add Full Coverage and fix undo history state

Expose original Auto/Full Coverage modes through the native settings and
existing WebView transport. Persist the selection in presets and native 3MF,
default legacy settings to Auto, and keep coverage density independent.

Initialize captured snapshot metadata and correct undo/redo availability
at initial and terminal history boundaries without changing model insertion.
Keep all 49 upstream files unchanged and support gap at 0.10-0.40 mm.

Verify original-engine geometry, native slicing/3MF, preset reset and undo
round trips. Record successful maintainer desktop acceptance, 39 Node and
18 Python passes, all nine PrintFins C++ passes, and five baseline failures.
```

### Prepared PR description

Title: `PrintFins Full Coverage and Undo/Redo history correction`

Target: `integration`

Full Coverage adds the original engine's fill walls through a native
Generation mode choice under Support > Type > PrintFins. Auto stays the
default, including old projects without a mode. The choice passes through
the existing C++/WebView/worker path, persists in presets and native 3MF, and
uses the active preset's reset value. Host-only `mode` is removed before
original `optionsFromDialog` validation; Wide-face coverage remains density.

The Undo/Redo correction initializes snapshot type and excludes initial and
terminal non-navigable history boundaries from availability checks. Native
probes restored all geometry even before the correction: missing fin meshes
were not reproduced, and no extra generation snapshot was introduced.

Validation:

- 49 vendor files, manifest and license unchanged at upstream
  `2cf5110efbdcc4ec1906adfba9dcb88f27f7dfb4`; exact official Git blobs verified.
- 39 Node and 18 Python tests pass. Auto/Full geometry matches original
  `computeFins` on eight fixtures; range coverage and separate Sway pieces pass.
- Dedicated C++: 14/19 pass, including all nine PrintFins cases. Preset reset,
  legacy Auto, global/object/part native 3MF and history regression pass.
  Five failures match original Bambu baseline
  `926a7192574bcb9b3a732e1ec59a46d79cb45466` by messages and exit codes.
- Real backend: four fixture/mode cases, 24 slices including existing
  Normal/Tree types, and four native 3MF round trips pass. Manual Normal/Tree
  cases are unpainted; they do not certify painted support workflows.
- Four native Undo/Redo scenarios preserve exact per-part geometry/IDs/
  transforms and produce six complete G-codes. These use production C++
  acceptance/Plater/history/slicing and the real engine, with a file transport
  double in a separate test image. Node DOM/Worker and Python Win32 doubles
  are not physical desktop tests.
- Windows x64 incremental Release build/link and native startup pass; the
  normal executable contains no test transport or probe.
- Maintainer desktop acceptance on 2026-10-17 passes Auto and Full
  generation > Undo > Redo > slicing, additional Full walls, 3MF save/reopen/
  reslice, and a new move > Undo > Redo after reopening.

Known limitations: the five baseline C++ failures concern legacy config
validation/accessors, `coPointsGroups` binary serialization, `draft_shield`
test setup and the sinking-object hull reference. The original site worker
test still reports `Worker is not defined` under Node/Deno; it is not claimed
as passing. Physical print quality, exhaustive geometry certification,
painted supports, shared WebView-cache isolation and CLI shutdown are outside
this validation. Prior Undo history is intentionally not persisted across
restart. The confirmed upstream multi-monitor rendering issue is unchanged.
The desktop report does not separately certify physical reset/override or
cancel/retry/duplicate-protection checks; native reset/override tests pass.

No vendor algorithms, Manual Draw, Hybrid, individual-fin editing, rendering
fixes or support-gap extension are included. Full Coverage retains the
original bounded fill/collision behavior and existing generation limits.
Detailed scope, evidence, launcher and limitations:
`docs/printfins-full-coverage.md`.
