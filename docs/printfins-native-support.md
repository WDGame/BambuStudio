# Native PrintFins support integration — staged implementation

For the isolated engine update to `2cf5110efbdc`, see the
[upstream update report](printfins-upstream-20261017.md). The original checkpoint
and implementation history below retain their original pin and test scope.

## Local development checkpoint (2026-10-17)

The maintainer authorized a local commit on `feature/printfins-native-support`;
no push, pull request or merge is authorized. This checkpoint preserves the
native integration, its diagnosed fixes, tests and documentation. It introduces
no further product behavior. Support gap stays **0.10–0.40 mm** and all 44 pinned
upstream files remain unchanged (SHA-256 and Git blob verification passed).

The latest Windows Release build passed. Existing matching-source results are
31 Node passes, 18 Python passes and 12/17 C++ cases passing, including all seven
PrintFins cases. Native Bambu 3MF backend persistence passed; physical desktop
acceptance and full native generation remain open. Test doubles and native
window-message diagnostics are not human desktop confirmation. The CLI exit
hang remains open. See [current settings verification](printfins-native-settings.md)
for the five exact open C++ cases, limitations and latest local launcher.

The following sections retain the implementation and diagnostic history;
earlier build paths and test counts describe their respective intermediate
states, not the final checkpoint.

## Verified source baseline (2026-10-16)

This branch starts at Bambu `integration` commit `8d23355b7f82` (PR #5 included).
All earlier worktrees are preserved. No engine update is bundled with native UI work.

The official `main` was inspected at [b65f156d278d147f05d2ff12492b9d1ef3be2fda](https://github.com/gittrahan/support-fins/commit/b65f156d278d147f05d2ff12492b9d1ef3be2fda).
Our unchanged 44-file snapshot remains `bff031d484bb0f52f56df9ba49c61361ca86377a`.
The official branch is 28 commits ahead of that pin. Comparing upstream Git blob
IDs: 40 of our 44 files are identical, and four changed:

- `web/fins.js`
- `web/fins/fill.js`
- `web/fins/wedges.js`
- `web/prop/brace.js`

The [complete upstream comparison](https://github.com/gittrahan/support-fins/compare/bff031d484bb0f52f56df9ba49c61361ca86377a...b65f156d278d147f05d2ff12492b9d1ef3be2fda)
includes Full-coverage long-wall changes (and new modules), wedge collision
checks and experimental tall-wall brace work. Updating just those four files
would omit new dependencies and is not an appropriate engine upgrade.
`plugins/shared/engine/options.json` is byte-identical; `fins_entry.js`
also has the same Git blob ID. The current site has features outside that
plugin schema. See the [current native settings schema](https://github.com/gittrahan/support-fins/blob/b65f156d278d147f05d2ff12492b9d1ef3be2fda/plugins/shared/engine/options.json),
[site controls](https://github.com/gittrahan/support-fins/blob/b65f156d278d147f05d2ff12492b9d1ef3be2fda/web/index.html) and
[pointer dispatch](https://github.com/gittrahan/support-fins/blob/b65f156d278d147f05d2ff12492b9d1ef3be2fda/web/app.js). The site must not be
equated with the Auto-only plugin interface.

## Feature inventory and delivery stages

| Original capability | This first stage | Follow-up gate |
| --- | --- | --- |
| Auto placement, contoured walls, tines, support gap, bed pad, cutouts, wide-face coverage, plate-only | Native Support-type entry and schema-driven native fields implemented; unchanged pinned engine used | Native desktop acceptance below |
| Sway braces (automatic) and original grip/spacing/depth | Included through the original schema; off by default | Tall-model desktop and slice checks; this is not a claim of physical print qualification |
| Full coverage | Not exposed by the current plugin options schema; not silently simulated with the coverage slider | Separate engine/adapter and native-mode stage, compared with upstream mode `full` |
| Draw, hand-placed sway braces | Not implemented in Bambu | Native Bambu viewport gizmo and ray picking, invoking the original builders with documented coordinate conversion |
| Auto plus manually added fins | Not implemented | Preserve manual placement records alongside automatic piece IDs; test regeneration and transformations |
| Individual removal / selection / restore | Generated fins are ordinary parts, deletable using Bambu's object list; original semantic removal/restore workflow is not integrated | Native selection/removal with original piece identity, one Bambu undo transaction |
| Overhang / small-face visualization | No PrintFins-specific viewport overlay yet | Native GL overlay using original engine face results, without a second browser viewport |
| Site nozzle size / wall lines / interface material / full brace depth | Site-only controls absent from our plugin schema; not invented as native settings | Audit and expose actual engine contracts after the isolated upstream update |
| New Full-coverage Long walls, experimental tall-wall face ribs | Not imported from newer upstream | Separate versioned engine update and upstream regression tests; prototype work is not a production promise |
| Import, rotate/scale/mirror, object selection, volume insertion, Undo/Redo, slicing and 3MF | Existing Bambu paths reused; no second importer, renderer or project format | Repeat native acceptance for this changed host |
| Orientation/load-direction scoring, lay-face/section-plane/site inspection tools | Not ported | Separate scope decision after the core support workflow; existing Bambu transforms remain authoritative |

The [official README](https://github.com/gittrahan/support-fins/blob/b65f156d278d147f05d2ff12492b9d1ef3be2fda/README.md) describes site features and
known limitations; availability in the website is not evidence that our plugin
entry exposes each one.

Reviewable sequence:
1. **Native Auto on the existing pin (this change).** Review the config enum,
   native settings and geometry transaction; build and pass the native gates.
2. **Isolated upstream update.** Review changed/new dependencies, regenerate the
   provenance manifest from exact original bytes, rerun original and host tests.
   Keep the present pin available in Git until that separate change is approved.
3. **Full coverage and native overhang visualization.** Wire actual upstream
   mode/analysis outputs into existing Bambu viewport paths; compare geometry.
4. **Draw, combining and individual removal.** Native viewport interaction,
   stable engine piece identities and Bambu Undo/Redo/3MF round trips.
5. **Remaining relevant site options.** Expose verified native options only
   where their original engine contracts and dependencies have been tested.

Each stage is a separate review/commit approval boundary. The local checkpoint
authorization above applies only to the existing first-stage development state.

## First-stage behavior

With support enabled, choose **PrintFins** in the existing Support > Type
dropdown. Native controls appear in that same page, generated from the unchanged
original schema. Boolean/choice values, numeric ranges and percentage conversion
come from it; conditional fields follow its `showIf` rules. Layer heights
come from the effective Bambu object/process config. Settings are stored as
`printfins_options` through Bambu's dynamic preset/object config path.

Select one complete, single-instance FFF model in Prepare, then choose
**Generate PrintFins (Auto)**. This is an explicit generation operation, not
automatic regeneration at every slice or after a model edit. A native
progress/cancel dialog hosts the existing WebView2 worker invisibly; its HTML
settings UI is not shown. The original engine and worker transport are reused.
The old Edit-menu tool is retained for rollback/comparison in this stage.

Validated pieces are inserted as normal printable Bambu volumes, in one existing
Bambu undo transaction, only after all output checks pass. Selection changes,
modifiers, invalid geometry, existing PrintFins, variable layers, nonfinite/range
errors and cancellation retain the existing host guards. Conflicting object
overrides are rejected instead of silently generating with another object's
settings. The original part and its instance transform remain authoritative.

Selecting PrintFins suppresses Bambu Normal/Tree support generation; fins are
sliced as model parts. Bambu raft layers must be zero (generation and slicing
reject an incompatible raft). Old presets retain their enum values/defaults.
Turning support off does not delete previously generated parts. Changing
settings or transforming the assembled object does not regenerate fins.
Remove/undo the old parts explicitly before generating again. Cross-version
opening of a project using the new support enum in older Bambu versions is not
guaranteed.

## Verification and acceptance

Executed after the first implementation:
- 28 Node tests pass, including a new test feeding all native flat schema values
  through the real production page transport into the original engine, with
  non-default gap/coverage/sway and slicer heights.
- 18 Python test-infrastructure tests pass.
- 44 original files match SHA-256 and upstream Git blob IDs, also checked against
  the retained pinned upstream source directory.
- MSVC Release `/Zs` syntax checks passed for seven production translation
  units: PrintFinsPoC, Tab, ConfigManipulation, PrintConfig, Preset, PrintObject
  and Print. Cached dependency include paths were reused; this does not link or
  run a newly built Bambu application. Existing signed/unsigned warnings remain.
- A native C++ regression case in the existing config test suite covers all
  old support enum values, the new value/default settings, serialized settings
  and the static object-config copy. The same regression body passed in an
  isolated native executable with the new PrintConfig object and cached support
  libraries. The complete Catch2 suite was not run. This tests configuration
  serialization, not native 3MF save/reopen or GUI behavior.

These Node tests include simulated DOM/worker behavior. They are not native
wxWidgets, project persistence or GUI passes. Earlier confirmed Edit-menu
generation/slicing/3MF tests remain baseline evidence for that host only.
The existing Windows GUI automation still exercises the retained Edit-menu
tool; it is not a test of this new native Support-page workflow. Adding a field
to the static object config requires a consistent full rebuild of dependent
libraries and GUI code. Do not substitute the old runtime or mix cached objects
into a purportedly validated new application.

Before this stage is called working, a matching rebuilt Windows runtime must
pass these native checks (all currently open):
1. Normal/Tree presets still load unchanged. Enable support, select PrintFins,
   verify native defaults, ranges, percent values and tines/sway dependencies.
   Switch global/object scopes, select presets, and return to the Support page.
2. Generate on tilted/translated/mirrored models; cancel before/during generation.
   Invalid selections, existing fins and conflicting object settings must cause
   no unintended model changes. Check no visible browser UI opens.
3. Verify one Undo removes generation and one Redo restores it. Check source
   pose/settings and part names; test the no-geometry result on a flat model.
4. Slice source and fins together; verify no additional Normal/Tree supports.
   Verify a nonzero Bambu raft produces the stated error.
5. Save/reopen a native Bambu 3MF in a fresh process: support enum, native options,
   source pose and fin parts must survive. Slice again; reject duplicate generation.
6. Inspect the existing native dark/light design and resizing on Windows.
   No successful desktop result is inferred from syntax or simulated tests.

## Full Windows Release validation (2026-10-17)

A consistent Windows x64 Release was built from this worktree with MSVC 19.51
and CMake/Ninja, including the complete core, GUI, DeviceWeb frontend,
`BambuStudio.dll` and `bambu-studio.exe`. No old Bambu application objects or
runtime binaries were substituted. Existing third-party dependency caches were
reused. MSBuild FileTracker initialization was denied in this environment;
the normal Ninja/MSVC build succeeded without changing security settings.

The native settings implementation and Support-page caller compiled and linked.
All static imports of 36 runtime EXE/DLL files resolve; Windows successfully
loads the new application DLL and resolves `bambustu_main`. This is a build and
loader pass, not confirmation that the application is operational on the desktop.
The 44 original files still match their SHA-256/Git-blob manifest and the retained
pinned upstream source. No product or engine source was changed for this
validation.

Executed regressions:
- 28 Node and 18 Python cases pass. DOM/worker transport coverage remains
  simulated; it does not exercise native controls or actual WebView2.
- A focused `printfins_integration_tests` Catch2 target uses the existing config,
  utility and 3MF tests, linked with the host utilities they now require. One
  obsolete rotation call in the 3MF test was adapted to the current Model API.
- 6 of its 11 cases pass: the new PrintFins enum/settings/default/static-copy
  case (12 assertions), two utility cases, INI loading, Unicode-path 3MF loading,
  and export/import of transformed 3MF geometry.
- 5 existing cases fail: generic config validation (removed Prusa option names),
  config accessors (removed options followed by an access violation), binary
  DynamicPrintConfig serialization (inequality), skirt-distance setup (wrong
  type), and sinking-object convex-hull reference (mismatch). These failures
  were not repaired or suppressed. A baseline comparison has not established
  whether the serialization/hull failures predate this integration.
- The general C++ test target also cannot compile because unrelated OBJ/SLA
  tests use obsolete APIs. No broad test-suite migration was attempted.

Runtime acceptance is **not complete**. Two fresh-profile startup probes (H2D
and A1) terminated with access violation `0xC0000005` during window
initialization. Both logs also contain a denied default WebView2-cache directory
access. That denial alone does not establish the cause of the access violation.
No native dropdown, option editing, generation, slicing, Undo/Redo or native
3MF-project roundtrip is counted as a GUI pass. The earlier CLI shutdown hang
remains open and was not addressed.

Local ignored artifacts under `build/validation-20261017` contain the build log,
PE-import/loader results, per-case native XML/logs, startup-probe records and a
SHA-256 release receipt. An isolated manual test is prepared under
`build/desktop-native-20261017`; from this worktree use:

```powershell
python .\build\desktop-native-20261017\start.py
```

The launcher verifies the new EXE/DLL hashes and creates a fresh A1 public-preset
profile, temporary directory and logs for every run, then loads a closed test
model directly at startup. At the reference settings (0.16/0.2 mm layer heights,
Sway enabled), the unchanged engine produces three fins and two Sway Braces for
this fixture. That reference was computed outside the native GUI. Follow
`TESTABLAUF.md` there for the still-open desktop checks. To reopen a saved native
project in another fresh process, append `--project 'path-to-project.3mf'`.
The host still attempts to prepare its normal user WebView2-cache root before
the runtime user-data override; complete cache isolation is not established.
No execution-policy, sandbox or WebView2 security flags are changed.

## Startup crash diagnosis and fix (2026-10-17)

The first external desktop launch also crashed. Windows Application events
1000/1001 identify `0xC0000005` in `VCRUNTIME140.dll`; it is a real application
failure, not a demonstrated sandbox restriction. A test-owned debug launch with
the new local PDBs resolves the stack to:

```text
memmove
OptionsGroup::remove_option_if
TabPrintModel::build
Tab::create_preset_tab
MainFrame::create_preset_tabs
```

`append_line()` stores full-width widget lines without an entry in
`m_options_mode`. The model-tab filter wrongly used a line index to erase from
that shorter vector. The new unbound PrintFins widget exposed the invalid erase
during startup. The fix rebuilds the mode entries using the same rules as
`append_line()`, and binds the PrintFins widget to `printfins_options` so the
existing object/plate filter retains or removes it by its actual setting.
Only `OptionsGroup.cpp` and the PrintFins insertion in `Tab.cpp` changed in the
product for this fix. No original engine files or WebView initialization code
were changed.

All 34 staged third-party runtime DLLs, including WebView2Loader, are byte-for-byte
identical to the UI-tool runtime. Resources point to this worktree, all 44
original files verify, all 36 EXE/DLL static imports resolve, and the application
DLL loads with its expected entry point. A missing runtime dependency is not
the demonstrated startup cause. The remaining default WebView-cache access
warning is a separate environment limitation: the fixed application starts
despite that same warning.

After rebuilding/linking, a real test-owned Bambu window became visible,
responded to `WM_NULL`, loaded the STL (`finished load_model_objects`), and
remained alive for several minutes. Closing reached the normal unsaved-project
dialog. The sandbox could not focus/click its No button; only that test process
was terminated for cleanup. Its recorded forced-exit code is not another crash
or a clean-shutdown pass. No other Bambu process was closed. The earlier CLI
shutdown hang remains outside this fix.

The native C++ run now has **7 passing / 5 failing cases**. The additional pass
uses the actual OptionsGroup filter without creating controls, covers unbound
and bound widget lines, retained modes and repeated scope filtering (7
assertions); it is not a GUI interaction test. The five prior failures are
documented without suppressing them:

| Existing case | Evidence and classification |
| --- | --- |
| Generic config validation | Removed `perimeter_extrusion_width`/`perimeters` keys; stale test inputs, not a desktop restriction. |
| Config accessors | Removed `gcode_comments`, then a null option dereference in the original test; see the separate symbolized crash diagnosis below. Missing options remain test failures after the checked-access fix. |
| Binary DynamicPrintConfig | The test swallowed archive exceptions. It now reports `Unknown option type for option extruder_printable_area` at save. The existing HEAD already declares this as `coPointsGroups` without a corresponding archive case: a pre-existing product serialization limitation for full configurations, not a PrintFins string-setting or sandbox failure. It does not establish that the user project/Undo path fails. |
| Skirt-distance calculation | Test setup uses a string setter on an enum (`draft_shield`), producing the wrong-type exception before checking geometry; test API mismatch. |
| Sinking-object hull | Computed hull differs from the expected coordinates. No baseline run isolates this mismatch; retain as an unresolved geometry/reference regression, not a sandbox explanation. |

The 28 Node / 18 Python passes remain applicable; no JS or engine code changed.
Native option editing, automatic fins/Sway, slicing, Undo/Redo and the native
3MF-project roundtrip still require manual desktop acceptance.

The corrected launcher, which also records the actual exit code, is now:

```powershell
python .\build\desktop-native-fixed-20261017\start.py
```

Use its `TESTABLAUF.md`; the older launcher's release receipt intentionally
does not match the repaired DLL. Each invocation uses fresh test profiles and
keeps the console open until Bambu exits. Append `--project 'project.3mf'` for a
fresh-process reopen. Detailed local evidence, the updated release hashes and
per-case native test reports are in `build/startup-diagnosis-20261017`.

### Separate native test-executable access violation

A dedicated debug launch of only `Scenario: Config accessor functions perform
as expected.` reproduced the Windows test-program error. The matching Release
PDB resolves the first-chance and unhandled exception to
`test_config.cpp:73` (before the fix), in the branch setting a boolean through a
serialized string. The exception record confirms a **read from address 0**.
The stack is the generated accessor test function followed by Catch2's
`invokeActiveTestCase` / `runCurrentTest` / `runTest`; it does not contain the
Bambu model-tab filter.

The legacy importer ignores the removed `gcode_comments` key. The subsequent
`config.opt<ConfigOptionBool>("gcode_comments")` returns null, which the test
dereferenced unconditionally. This is the previously reported accessor-case
failure, **not** the separate `OptionsGroup::remove_option_if` startup defect,
and not a sandbox or DLL-load failure. The test now uses the existing checked
`option_throw<T>` accessor where it expects an option to exist. Unknown or
wrongly typed legacy options stay explicit test errors rather than Windows
access violations. No product accessor or legacy-import behavior was changed.
The focused MSVC test target now also emits a full PDB while retaining Release
optimization, to keep this diagnosis reproducible. The original trace and
exception record are retained in the local diagnosis directory.

Reverification: the repaired accessor test completes under the same debugger
with Catch2 exit code **23**, zero access-violation events, and explicit errors
for removed keys/default assumptions. The complete focused run also finishes
without a process crash: **7/12 cases pass, 5 fail**. Do not read the nonzero
Catch2 failure count as `0xC0000005` or as a passing test. The Bambu DLL remains
identical to the version whose visible, responsive main window and model import
were verified above; subsequent changes only affect test code/link symbols and
documentation. No additional application launch is inferred from the test run.
Running all focused cases together in a single process also completes with
controlled Catch2 exit code **28**, without `SIGSEGV` or an access violation.

## Support-page map exception (2026-10-17)

The next external desktop run started correctly but opening the main Support
category raised `invalid map<K, T> key`. A test-owned debug launch reproduced
the actual native button/page-activation path using posted Win32 mouse messages.
Matching PDB symbols resolve the first-chance C++ exception to:

```text
std::_Xout_of_range
ConfigOptionsGroup::reload_config
Page::activate
Tab::activate_selected_page
Tab::tree_sel_change_delayed
TabCtrl::SelectItem
Button::mouseReleased
```

The missing key is **`printfins_options` in `OptionsGroup::m_options`**, a
`std::map<t_config_option_key, Option>`. The setting exists in PrintConfig,
the preset list and `m_opt_map`; its definition was omitted from `m_options`.
`get_option()` registers the config-key mapping, but `append_line()` returned
early for full-width widgets before storing their option metadata. Thus the
later `m_options.at(opt_id)` in `reload_config()` threw even before the user
selected PrintFins. This is a GUI registration defect, not a missing upstream
engine option or a changed enum value.

A regression using the real ConfigOptionsGroup with only the bound widget
proves the exact key: before the fix `opt_map().count("printfins_options") == 1`,
`m_options` has no such entry, and `reload_config()` throws the same exception.
After the fix all three assertions pass. `append_line()` now registers option
metadata before the widget early-return. No exception is suppressed, and the
existing mode-vector treatment of full-width widgets remains unchanged.

Native UI checks also exposed that the host's group visibility refresh could
reveal the PrintFins panel for Normal/Tree. The panel's Show override now honors
the selected support type, so host layout updates cannot reveal it incorrectly.
No original option schema, defaults, ranges or engine files changed.

After the Release rebuild, a fresh real Bambu process passed native window
automation for:
- opening Quality, Support, Strength, Support, Others and Support;
- enabling support through the existing native checkbox;
- selecting all four original support types, with PrintFins controls hidden;
- selecting PrintFins, showing its native controls;
- typing a gap of 0.25 and retaining it after leaving/reopening the page;
- switching back to Tree with the PrintFins panel hidden;
- toggling Sway/Tines and verifying the original dependent fields;
- normal close through the unsaved-project prompt, process exit code 0.

These are actual native wxWidgets/control paths driven by Win32 messages in a
test-owned window. They are not a human mouse/keyboard desktop confirmation and
not simulated JavaScript tests. The local automation initially used an
inappropriate Edit-text oracle and incomplete input messages; it was corrected
to queued native typing and WM_GETTEXT. A stale Edit window caption must not be
mistaken for the control's current value or a product persistence failure.

The focused C++ suite now reports **8/13 passing cases, 5 existing failures**;
the combined run exits normally with Catch2 code 28, without an access
violation. The five classifications above remain: obsolete test keys,
checked-access test errors, existing full-config binary archive limitation,
enum setter mismatch, and unresolved hull/reference mismatch. No other support
enum values or defaults changed. Actual slicing equivalence for Normal/Tree
was not rerun during this UI repair. Fins generation, slicing, Undo/Redo and
native 3MF-project acceptance on this native UI remain separate manual checks.
The prior 28 Node / 18 Python passes are retained; JavaScript was unchanged.

All 44 original files again match SHA-256/Git blobs and the retained upstream
pin. Runtime imports and the DLL entry point also pass. Local before/after
regression logs, PDB exception traces, native UI results and the new binary
receipt are in `build/support-page-diagnosis-20261017`.

Use the newly identified build from this worktree with:

```powershell
python .\build\desktop-native-support-fixed-20261017\start.py
```

Each run gets a fresh A1 profile/model, logs and an exit-code record. The earlier
launchers intentionally retain their old hashes and must not be used for this
repaired version. No commit or push was made.

### Desktop input and initial camera fit (2026-10-17)

A separate startup defect was reproduced with the direct-model desktop
launcher: the bed and model appeared too small. With the same fresh A1 profile
and STL, the retained `ui-tool` executable reproduced the same small view.
Starting without a file and importing through the actual native Add/file
dialog instead produced a normally sized view. This isolates that symptom
from the new PrintFins settings panel.

Local Release/PDB debugging at `Camera::apply_projection` confirmed that the
startup camera was first fitted at a transient viewport width of 253 pixels,
with zoom 0.494140625. Its width subsequently became 760 pixels while the zoom
remained unchanged. `MainFrame::select_tab()` rendered Prepare synchronously
during the page switch, before its layout settled. It now marks the canvas
dirty for the existing render loop instead. No camera constant, stored zoom,
mouse mapping, exception handler or upstream file is changed. The corrected
debug run starts at width 760 and zoom 1.484375; the direct-STL startup image
matches the normal-sized delayed-import view.

The Release application rebuilt and linked successfully. An initial link
attempt reported LNK1104 because the diagnostic child still had the DLL open;
linking succeeded after that owned process ended. This was a build-artifact
lock, not a product crash.

Tests on the corrected executable used actual native Windows/wxWidgets
windows, with posted input messages and inspection of their rendered output:

- clicking blank space deselects the model; clicking its surface selects it
  again, restoring its outline, toolbar state and object information;
- left dragging rotates the view, and wheel messages zoom it;
- Quality/Support, Strength/Support and Others/Support switches work;
- all four existing support types and PrintFins remain selectable;
- native PrintFins gap editing survives a page rebuild;
- view rotation still works with the PrintFins settings panel visible;
- normal close through the unsaved-project prompt exits with code 0;
- the three focused PrintFins C++ regression cases pass on the relinked test
  executable. The prior complete 8/13 result and its five classified failures
  are retained; the unrelated failures were not rerun for this render change.

Before and after the change, the observed main window was enabled, its UI
thread had no modal/menu loop or mouse capture, and its visible child windows
showed no blocking overlay across the viewport. Native window events reached
the sidebar and viewport. This does **not** establish the cause of the user's
physical-input blockage: the sandbox denies interactive cursor access, so
physical clicks, dragging and wheel input on the user's desktop remain
unconfirmed. No speculative input fix or security workaround was introduced.
There is no evidence yet that the input blockage and camera fit share a cause.

All 44 originals were rechecked against manifest SHA-256, Git blobs and the
retained upstream checkout. Runtime evidence, before/after camera records,
screenshots and per-scenario results are in `build/input-diagnosis-20261017`.

Use the updated local desktop launcher:

```powershell
python .\build\desktop-native-input-20261017\start.py
```

It checks the new binary hashes and creates fresh profile/log directories.
An additional read-only observer records focus, capture, main-window DPI,
cursor/button state and native hit targets in `input-state.jsonl`. It never
moves the cursor, changes focus or sends synthetic input. Keep its console
open and close Bambu normally to retain the final exit code. This prepares
the remaining real-desktop diagnosis without claiming a physical-input pass.
No commit or push was made.

### Generate-button process crash (2026-10-17)

The external desktop run recorded exit **0xC0000005**, not a normal generation
cancel. Windows Application events 1000/1001 identify `BambuStudio.dll` at
offset `0x03b2049c`. A fresh native Generate-button run under the debugger
reproduced the same exception, both first and second chance, reading address
0. Matching local Release PDB symbols resolve its stack to:

```
NativePrintFinsSettings Generate-button lambda (PrintFinsPoC.cpp:451 before fix)
wxEvtHandler::SearchDynamicEventTable / ProcessEvent
Button::mouseReleased (Button.cpp:423)
wxWindow::HandleMouseEvent / MSWHandleMessage
wxGUIEventLoop / GUI_Run
```

The handler copied `plater.config()`, which is intentionally only a subset of
the print configuration. `Plater::priv` initializes that subset without
`support_type` or `printfins_options`. With the usual global setting and no
object override, `effective.opt_enum<SupportType>("support_type")` dereferenced
the missing option. This happens before constructing PrintFinsDialog, creating
its WebView or starting an engine worker.

The fix copies the native settings panel's complete `m_config()` instead,
then applies the selected object's overrides as before. It does not add keys
to Plater's subset, invent defaults or change the unchecked global config
accessors. Diagnostics now record WebView URL/error/state and the actual
mapping, page-ready, worker and accepted-volume stages. No upstream file is
modified.

After the config-source fix, the same native click passes this guard and opens
the dialog. The local validation then encounters a distinct handled navigation
failure: `about:blank`, `COREWEBVIEW2_WEB_ERROR_STATUS_CONNECTION_ABORTED`, before
mapping or page-ready (`mapped=false`, `ready=false`). Cancelling that dialog
and closing the application have returned exit 0. Full native generation is
therefore still **unconfirmed**, not a passing test or a proven sandbox issue.
Experiments with the startup navigation sequence did not remove this error;
those behavior changes were reverted. The original navigation behavior and
error handling remain in the final code, with additional evidence in logs.

The sidebar rendering report is investigated separately. Native child-window
resize diagnostics exercise WM_SIZE and the renderer, but cannot stand in for
a physical AUI sidebar drag on the user's desktop. No rendering change is
justified by the Generate-button exception. The earlier five C++ test failures
retain their documented classifications; none is the faulting Generate lambda.

On the final matching Release, the debugger Generate run has no recorded
access violation and closes normally with exit 0 after the handled navigation
error. The relinked three focused C++ cases pass all 22 assertions. Rendered
model positioning is correct through native viewport widths 760, 600, 420 and
760 again (0.5 pixel center deviation). That test changes the actual GL child
window size through Win32 and verifies the rendered image; it is not a mouse
drag of the AUI sidebar. No speculative rendering fix was added.

Local exception stacks, Windows events, separate trial logs and final results
are retained in `build/generation-crash-20261017`. The updated desktop launcher
is `build/desktop-native-generate-fixed-20261017/start.py`; it checks binary
identity, uses a fresh profile and records exit/input/viewport state. No commit
or push was made.
