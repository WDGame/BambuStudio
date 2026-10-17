# Native PrintFins settings: verification

Branch: `feature/printfins-native-support`. The maintainer authorized a local
development checkpoint only. No push, pull request or merge is authorized.

The native panel uses Bambu's existing `TextInput`,
`TextInputValChecker::CreateDoubleRangeChecker`, `spin_inc` / `spin_dec`
buttons, and the original `undo` / `dot` preset icons. It accepts decimal
input, normalizes the alternative decimal separator like Bambu's `Field`,
and supports arrow buttons and Up/Down keys. Invalid visible inputs cannot
be committed or submitted. Native validation marks invalid text red.

| Field | Display range | Arrow increment | Unchanged default |
| --- | --- | --- | --- |
| Overhang | 30–70 degrees | 1 degree | 45 degrees |
| Tine grip | 0–100% | 1 percentage point | 0% |
| Support gap | **0.10–0.40 mm, extension blocked** | 0.01 mm | 0.20 mm |
| Wide-face coverage | 0–100% | 1 percentage point | 50% |
| Brace grip from | 0–2000 mm | 1 mm | 0 mm |
| Brace tine spacing | 2–30 mm | 0.5 mm | 6 mm |
| Brace depth | 5–50% | 1 percentage point | 15% |

Increments apply to arrow operations; valid typed and saved decimals are
not silently quantized. At a range boundary, arrows stop at the boundary.
Hidden settings are retained in the project configuration, while hidden
fields are omitted from engine requests. This preserves values when tines
or sway braces are disabled and re-enabled.

## Preset reset source

`Tab.cpp` supplies `m_presets->get_selected_preset().config`, the same source
as `Page::new_optgroup()` supplies through `m_get_initial_config` for Bambu's
normal saved-value reset. It is fetched again on refresh/reset, rather than
captured once. Object tabs use their own `m_prints` collection, which Bambu
initializes from the parent configuration in `TabPrintModel::set_model_config`.
The reset changes only the clicked JSON member; other settings are retained.
Missing preset members use the unchanged original schema defaults.
When all values match again, the exact saved JSON string is restored so
Bambu's string-based preset comparison does not leave a false dirty marker.

## Confirmed support-gap conflict

The unchanged pinned engine rejects the requested 0.04 and 1.00 mm values
twice: `fins_entry.js:76` validates the dialog schema's 0.10–0.40 range;
`seat.js:19–24` independently enforces the same range even for direct
`computeFins()` calls. The adapter calls the former, and `computeFins()`
calls `clearances()` before geometry generation.

Downstream, `web/fins.js:84–98` applies the clearance to `PROP.gap` and
`PERP.gap`; `fins_entry.js:156` also forwards it to sway braces. Contact and
clearance geometry use this value (`web/prop/contact.js`, `clearance.js`,
`brace.js`). Simply widening the native input limits or bypassing only
`optionsFromDialog()` cannot extend the supported engine entry point.

No engine file or original entry-point validation is changed or bypassed.
For this checkpoint the maintainer explicitly retained **0.10–0.40 mm**.
No alternative integration or range extension is included.

## Automated evidence

- `tests/printfins/gap-clearance.test.mjs`: real original engine and production
  adapter, no engine doubles. Both requested out-of-range values are rejected.
  These rejection passes **do not** establish functional extended-gap support.
- The horizontal shelf fixture has an underside at z=20 mm. With tines and
  bed pad off, measured vertical clearances from generated mesh vertices are
  0.1000003815 / 0.2000007629 / 0.3999996185 mm for requested 0.10 / 0.20 / 0.40.
  Tolerance: 0.00001 mm. No geometry exists to measure at 0.04 or 1.00.
- `tests/printfins/native-options-group.cpp`: C++ numeric limits, real Bambu
  validator, arrow increments, finite/type checks, real `PresetCollection`
  switching/reset, and native `store_bbs_3mf` / `load_bbs_3mf` roundtrip.
  These are backend/widget-validator tests, not physical desktop interaction.
- Node regression: **31 tests passed**. DOM/Worker transport tests use doubles;
  they do not certify native GUI rendering, focus or mouse operation.
- Python regression: **18 tests passed**, including simulated Win32-driver
  scenarios. These are not evidence of successful physical desktop automation.
- Complete Windows x64 Release build: **PASS**, including the final incremental
  rebuilds after settings and native 3MF fixes. The output is separate from the
  still-running older Bambu binary; no existing application was terminated.
- Final C++ regression: **12/17 cases passed; all 7 PrintFins cases passed**.
  Real numeric checker, boundary/decimal/step tests, preset switching, exact
  saved-value reset and actual `PresetCollection::current_is_dirty()` passed.
  The native Bambu 3MF writer/reader retained all global settings and the
  tested object/part overrides. This is an API roundtrip, not a GUI save test.
- Five previously observed branch-test failures recur; see the exact cases
  below. Their individual reports remain in `cpp-final/*.xml`.
- Real Windows main-window creation and model loading: **PASS**. Interactive
  focus was blocked (`Cannot focus the test-owned window`); no physical input
  or settings operation was tested. The probe terminated only its own new
  process after its close request could not complete without interaction;
  normal user-initiated application shutdown is not confirmed by this probe.
- All **44 original files** match the pinned SHA-256 and Git blob manifest.

Local evidence: `build/settings-native-20261017` contains full/final build logs,
`node.log`, `gap-final.log`, `python.log`, `cpp-final/results.json`, per-case
JUnit/stdout/stderr, the native 3MF files, startup window/log records and the
final binary/source receipt. Generated artifacts are not staged.

## Five open C++ cases at the local checkpoint

| Case (Catch2 scenario name) | Latest evidence and remaining limitation |
| --- | --- |
| Generic config validation performs as expected. | `test_config.cpp:45,52`: removed `perimeter_extrusion_width` and `perimeters` keys. Stale test inputs, not a sandbox failure. |
| Config accessor functions perform as expected. | `test_config.cpp:66–208`: removed keys including `gcode_comments`, `bed_temperature`, `perimeter_speed`, `end_gcode` and `first_layer_extrusion_width`; exception/default expectations also differ (`layer_height` 0.2 versus 0.3). Checked access avoids the diagnosed test null dereference but does not make this case pass. |
| DynamicPrintConfig serialization | `test_config.cpp:248`: binary save reports `Unknown option type for option extruder_printable_area` (`coPointsGroups` archive support absent). This is a full-config binary serialization limitation, distinct from the passing native 3MF JSON/XML roundtrip. |
| get_real_skirt_dist calculates the correct boundary including loop width | `test_config.cpp:266`: string setter used on enum `draft_shield` throws `Conversion to a wrong type` before the geometry assertion. Test API mismatch. |
| 2D convex hull of sinking object | `test_3mf.cpp:128`: calculated hull fails the reference comparison. Geometry/reference mismatch remains unresolved. |

All five are real failing cases, not five demonstrated environment failures.
No clean-baseline run establishes that all five predate this branch; no such
blanket regression exclusion is claimed. The earlier symbolized test crash,
application startup crash and Generate-button crash have separate diagnoses
in [the implementation history](printfins-native-support.md).

The checkpoint is a recoverable development state, not a completed desktop
acceptance. Full native generation still needs verification after the handled
WebView navigation failure; physical input/sidebar rendering, native GUI
slicing, Undo/Redo, save/reopen and Normal/Tree slicing regression checks remain
open on this build. Earlier UI-tool successes do not certify this native UI.
The previously documented CLI shutdown hang remains open and unchanged.

## Native 3MF bug found and fixed

The new native roundtrip found an actual storage defect: object/part
`printfins_options` contains JSON quotes, while `bbs_3mf.cpp` previously wrote
its C-string serialization directly into XML attributes. Backslash-escaped
quotes are invalid XML. The saved archive failed to reopen with an XML error
at line 6 of `Metadata/model_settings.config`. The fix uses the existing
`xml_escape()` only for this integration key, at the object and volume writers.
Other configuration values retain their previous serialization path.

The initial test setup also had an independent initialization defect. Copying
raw `full_print_config()` defaults left enum-vector `keys_map` pointers null.
The local PDB debugger traced 0xC0000005 to `ConfigOptionEnumsGeneric::vserialize`
through `ConfigBase::save_to_json`, before XML loading. The fixture now uses
the existing dynamic option factory, which installs the dictionaries from the
option definitions, and initializes/restores `Slic3r::temporary_dir()` locally.
No product exception handler or enum-serialization workaround was introduced.
The subsequent XML roundtrip failure and its product fix were verified separately.

To rerun the focused C++ tests from PowerShell, after building the Release:

```powershell
Push-Location .\build\settings-native-20261017
.\runtime\printfins_integration_tests.exe '[PrintFins]' --reporter junit --out focused.xml
Pop-Location
```

## Desktop acceptance still required

Use `python .\build\desktop-native-settings-20261017\start.py` from the
worktree root. To reopen a saved project in a fresh profile, add
`--project 'C:\path\project.3mf'`. Keep its console
open to record the process exit code. Each run receives fresh public presets,
its own profile, temporary directory and logs. A separate WebView profile is
requested through the environment; Bambu still prepares its normal shared
cache path. Complete WebView-cache isolation is not established.

1. Enable support and select PrintFins. Check units, decimal editing, Up/Down
   keys and arrow buttons against the table, including both range boundaries.
2. Save a process preset with gap 0.23, coverage 77%, brace spacing 6.5.
   Change values, then click each orange reset arrow: it must restore this
   preset's values, not 0.20 / 50% / 6. Confirm other edited fields survive.
3. Set tine grip to 37%; toggle Tines off/on. Repeat with sway values and
   Sway braces off/on. Switch presets and repeat the reset check.
4. Switch through Normal/Tree Auto/Manual and back to PrintFins. Verify the
   PrintFins panel hides for other types and normal support fields still work.
5. Generate at supported gap 0.20 with Sway enabled; slice, Undo/Redo, save a
   native 3MF, close, reopen it with `--project`, and verify settings and slicing.
   Also slice using an existing Normal/Tree type on an unfinned model.

The prior WebView navigation failure and separate sidebar/input report are
not fixed by this settings change. No physical desktop acceptance is claimed.
