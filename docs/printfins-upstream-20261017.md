# PrintFins Auto upstream update, 2026-10-17

Base: `integration` at `38a858ca8a454c1c418941828e3a0a83b25f4f57`.
Branch: `update/printfins-upstream-20261017`. All work stays in its isolated
worktree. Existing worktrees are untouched; no commit/push/PR/merge authorized.

## Source/API analysis before import

Both commits exist in the clean local official clone (origin
`https://github.com/gittrahan/support-fins.git`). Import reads Git blobs, not
checkout text, so Windows newline conversion cannot alter vendor provenance.
Old pin: `bff031d484bb0f52f56df9ba49c61361ca86377a`; new pin:
`2cf5110efbdcc4ec1906adfba9dcb88f27f7dfb4`.

The recursively resolved static/dynamic literal import closure of
`plugins/shared/engine/fins_entry.js`, its JSON schema and LICENSE grows from
44 to 49 files: 12 changed, 5 added, 32 unchanged, none removed. New modules:
`web/fins/{field,rows,tall}.js`, `web/prop/{curved,pins}.js`.
Changed: entry/schema/seat; `web/draw.js`, `web/fins.js`,
`web/fins/{fill,wedges}.js`, `web/prop.js`,
`web/prop/{brace,config,raster,tines}.js`. MIT LICENSE is unchanged.
No whole-repository merge, prototype, site UI, external package or new runtime
network dependency is required. The old closure exactly matches its manifest.

The computeFins positions/offset/piece ranges contract is unchanged; stats gains
`pins`. The original Auto pass now includes tall-wall face ribs and additional
wedge collision checks. Full-mode row/fill work and curved-wall selection exist
upstream, but their site-only toggles are not forwarded by the plugin entry.
Their modules remain necessary imports, not newly exposed host features.

Schema adds `tineDir` (horizontal FDM default / vertical resin) and `pinDepth`
(0.3 default, 0.05–1 mm). Existing defaults/ranges remain unchanged. The plateOnly
hint text changes, not its semantics. The FDM host hides resin-only controls
and rejects vertical generation; the original upstream files are not edited.
The upstream seat path resets tine direction each call, preventing resin state
from leaking into later default FDM calls. No fundamental architecture conflict
was found. Auto remains the only integrated mode; no Full/Draw/Hybrid/editing or
gap extension is added. Gap remains 0.10–0.40 mm.

Local dependency edges and exact change inventory:
`build/update-upstream/dependency-analysis.json`. Executed tests and the
maintainer's subsequent desktop acceptance are recorded separately below.

## Necessary host changes

- `resources/printfins/schema.mjs` filters only resin direction/depth from the
  unchanged upstream schema. The retained HTML tool uses this FDM presentation.
- `PrintFinsSettings.hpp` applies the same filter to the native panel. Existing
  preset values/defaults, reset source, decimals, steps and gap limits are retained.
- `adapter.mjs` rejects vertical resin requests. Default horizontal FDM calls
  continue through original `optionsFromDialog` / `computeFins`, unchanged.
- `check-snapshot.py --git-source` compares every manifest entry directly with
  the pinned Git object. Its safe.directory exception is scoped to each Git
  invocation; no global Git settings are changed. Checkout CRLF is not used
  as a source for vendoring.
- Host tests cover hidden resin fields, FDM state after a direct resin call,
  original Auto defaults, unchanged gap and native preset/3MF compatibility.
  No worker protocol, support algorithm or Bambu support-type change is needed.

## Executed verification

| Check | Result and scope |
| --- | --- |
| Snapshot/provenance/imports | PASS: 49 files, exact SHA-256 and original Git blobs at target; complete import closure loaded by Node. LICENSE unchanged. |
| Host Node suite | 33 PASS. Real engine geometry/gaps/options plus DOM/Worker transport doubles. The doubles do not establish native WebView2 operation. |
| Python suite | 18 PASS. Driver/Win32 doubles and project-oracle unit tests; no physical GUI claim. |
| Original upstream invariant tests, group 1 | 40 PASS: options, tall walls, wedge clearance, brace collisions, pins, curves, full-mode rows. Full-mode tests exercise the imported library only, not a selectable host mode. |
| Original upstream contact tests, group 2 | 45 PASS, 1 ERROR: FDM one-layer/horizontal tine shape, grip/density/real-part contact and Sway tests pass. The website Auto-worker full-depth test fails before worker construction because Node has no global browser `Worker`. It is a test-runtime limitation, not a new baseline exemption or a passing browser test. |
| Native dedicated C++ suite | 12/17 PASS, including all seven PrintFins cases (real numeric validator, saved-preset reset/dirty state, native global/object/part 3MF, GUI metadata/filtering). Same five failures as the independently compiled original baseline; see below. |
| Windows x64 Release | PASS, incremental build using unchanged verified core artifacts. Plater and PrintFins host were recompiled from this worktree; all four dedicated test sources recompiled. Full GUI archive, application DLL and test executable relinked into this worktree. |
| Real Bambu slicing and native 3MF | PASS for old/new engines on three fixtures: 30 initial slices (Normal/Tree Auto/Manual and PrintFins) plus six reopened-project slices, 36 complete G-code outputs. Six native 3MF projects retain parts/settings. Manual Normal/Tree modes were unpainted, so painted manual supports are not certified. |
| Windows launcher/startup/Support page | PASS: actual main window/canvas, model loaded, Support fields shown using posted native messages, normal exit 0. First probe observed an unfinished/disabled main window and missed the button; a bounded readiness wait resolves the probe. Both runs/logs remain; no product startup workaround was added. |
| Physical Windows desktop acceptance | PASS, reported by the maintainer on 2026-10-17 for all planned desktop checks: Auto, Sway braces, slicing, preset reset, Undo/Redo, native 3MF save/reopen and the optional 110-mm fixture. This is manual acceptance, separate from automated backend tests and input doubles. |

Original Deno-style tests run unchanged from the clean target checkout using
Node with a small Deno test/read-file API shim. Geometry is real, not doubled;
the shim is not a claim of running Deno or a browser. The single Worker failure
is retained in the logs rather than skipped or described as a pass.

The retained original-Bambu baseline is `926a7192574bcb9b3a732e1ec59a46d79cb45466`.
Each newly rebuilt failing case has identical normalized failure messages and
exit code to that independently built baseline; the expensive baseline build
was not repeated. No new C++ regression was found in this suite:

| Existing failing case | Exit | Original limitation |
| --- | --- | --- |
| Generic config validation performs as expected. | 2 | Removed legacy `perimeter_extrusion_width` / `perimeters` keys. |
| Config accessor functions perform as expected. | 23 | Removed keys and outdated exception/default expectations. |
| DynamicPrintConfig serialization | 1 | Full binary archive lacks `coPointsGroups` for `extruder_printable_area`; distinct from passing native 3MF JSON/XML. |
| get_real_skirt_dist calculates the correct boundary including loop width | 1 | String setter on enum `draft_shield` fails before geometry assertion. |
| 2D convex hull of sinking object | 1 | Same reference-comparison assertion failure on the original fixture/transform; not proof of equality of every hull coordinate. |

## Auto comparison and geometry checks

Both pins were executed through their actual host adapter on the same 16
inputs, including the existing seven deterministic fixtures, the established
desktop fixture, short/tall shelves, a larger tilted FDM part and four official
STLs. Fourteen triangle soups are identical. The two changes are the expected
upstream tall-wall ribs, not forced back to the previous result:

| Fixture | Old triangles | New triangles | Observation |
| --- | ---: | ---: | --- |
| Existing native Sway fixture | 2,172 | 2,172 | Three fins, two Sway braces, unchanged. |
| Shelf at 110 mm | 2,384 | 2,544 | Original new tall-wall face ribs, +160 triangles. |
| Shelf at 110 mm with Sway | 2,888 | 3,048 | Same rib change, two Sway braces retained. |
| Larger tilted FDM model | 57,684 | 57,684 | 80 horizontal tines; five fin parts plus one pad. Original collision checks refuse Sway sides blocked by the model, equally in both versions. |

For all sampled outputs: finite coordinates, complete/non-overlapping piece
ranges, no degenerate triangles at the measured threshold, no geometry below
the plate. Plate-standing versus part-attached pieces are counted separately;
an elevated piece is not automatically declared unanchored. Original contact,
tine shape, tall-brace and wedge tests provide targeted attachment/collision
checks. This is not exhaustive self-intersection/manifold certification for
every possible input or physical-print qualification.

The real Bambu backend imported each old/new output on the native Sway fixture,
110-mm Sway shelf and 80-tine tilted model, saved/reloaded native projects and
resliced. Independent triangle-by-triangle matching of the posed saved meshes
finds maximum coordinate error **0.000004173 mm**, below 0.0001 mm tolerance.
All 36 G-codes contain layers, extrusion and the end marker. The dense pad
exposed instability in the older oracle's rounded-coordinate sort; the local
checker instead matches every complete triangle exactly once within tolerance.
No geometry assertion was removed and no model/serialization product fix made.

## Evidence and reproducibility

All new evidence/artifacts stay under this worktree's ignored `build/`:

- `update-upstream/dependency-analysis.json`, `snapshot.py`, `import.log`.
- `update-upstream/node-final.log`, `python.log`, `upstream-tests.log`,
  `upstream-contact-tests.log`, `deno-shim.mjs`.
- `update-upstream/engine-comparison.json`, `compare-engines.mjs`, old/new soups;
  `build/old-host` is the exact old Git snapshot and adapter for comparison.
- `update-upstream/cpp`: all 17 per-case JUnit/stdout/stderr reports and
  `baseline-comparison.json`.
- `update-upstream/backend/results.json`, six native projects and 36 G-codes;
  `backend-workflow.cpp`, `check-projects.py`, `independent-project-check.json`.
  Backend insertion is a test harness using real Bambu APIs, not the actual
  native Generate handler or undo stack.
- `update-release`: reproducible build/response files, compile/link logs,
  separate runtime/PDBs, source/binary receipt, launcher and startup results.
  Existing linker LNK4098/LTCG messages are retained; final build exits 0.

Repeat host checks from this worktree:

```powershell
python scripts/printfins/check-snapshot.py --git-source build/upstream/support-fins
node --test tests/printfins/*.test.mjs
python -m unittest discover -s tests/printfins -p 'test_*.py'
```

## Desktop build and maintainer acceptance

The maintainer reports successful completion of all planned desktop tests on
2026-10-17, explicitly confirming Auto generation, Sway braces, slicing, preset
reset, Undo/Redo, native 3MF save/reopen and the optional 110-mm test. This
confirmation closes the pending manual acceptance for this update. No separate
per-scenario desktop logs or exit codes were supplied with that confirmation;
the earlier automated startup receipt retains its original, narrower scope.
The checklist and commands below remain available for reproduction.

Executable:
`C:\3D-Dev\BambuStudio-PrintFins\.worktrees\printfins-upstream-20261017\build\update-release\runtime\bambu-studio.exe`.
Use the verified launcher, which checks hashes and creates a fresh public A1
profile/temp/log directory; leave the console open until normal exit:

```powershell
python 'C:\3D-Dev\BambuStudio-PrintFins\.worktrees\printfins-upstream-20261017\build\update-release\start.py'
```

1. Enable support, select PrintFins, check saved-preset reset/decimal fields and
   retained defaults. Generate Auto with Sway, inspect contact/clearance, slice.
2. Undo generated parts, Redo once, verify no duplicate generation and preserved
   original model. Check cancel/retry; a completed calculation is not a cancel test.
3. Save native 3MF, close normally, reopen in a fresh launcher process with
   `--project 'C:\path\saved.3mf'`; check parts, settings and reslice.
4. Changed-geometry check: use `--model` with this worktree's
   `build\desktop-fixture\tall110.stl` and inspect the new automatic face ribs.
   Also check a normal/tree support slice on an unfinned model.

Exact tall-rib fixture start:

```powershell
python 'C:\3D-Dev\BambuStudio-PrintFins\.worktrees\printfins-upstream-20261017\build\update-release\start.py' --model 'C:\3D-Dev\BambuStudio-PrintFins\.worktrees\printfins-upstream-20261017\build\desktop-fixture\tall110.stl'
```

Shared WebView-cache isolation and broad GUI automation remain unconfirmed;
the known CLI shutdown hang was not repaired or retested. The accepted Windows
live-resize fix from integration is preserved; no rendering change is part of
this update. Manual acceptance does not authorize staging or publication.

## Final checkpoint review

Reviewed on 2026-10-17: correct update branch, HEAD and `origin/integration` at
the stated base; 21 modified tracked files and eight untracked intended files,
with nothing staged. All 29 files belong to the vendor update, its required
FDM compatibility, verification or documentation. Build artifacts, profiles,
logs and the official clone remain ignored and outside the checkpoint.

All 49 original files were rechecked against both manifest SHA-256/Git blob
IDs and exact official target-commit bytes, including the unchanged MIT license.
The official clone is clean and its origin is `gittrahan/support-fins`.
The release receipt still matches all 22 recorded source hashes and 37 runtime
binary hashes. Existing test logs and baseline comparisons were reviewed;
successful builds and expensive suites were not unnecessarily repeated.

Host review found no unintended feature exposure or new security issue in the
changes: native schema filtering operates on a copy, the HTML schema retains
the upstream option definitions, vertical requests are rejected, and existing
finite-input limits and strict upstream option validation remain in place.
No worker protocol, remote import, new runtime dependency, preset default or
support-gap range change was introduced. The source verification command uses
argument arrays and a per-invocation safe.directory exception.

`git diff --check` passes. No new blocking regression was identified in the
reviewed scope. The Node site-worker error and all five proven original-Bambu
C++ failures remain disclosed above; the full test collection is not green.
The update is ready for checkpoint authorization, with no staging, commit,
push, PR creation or merge performed.

## Prepared commit description

```text
feat(printfins): update upstream Auto engine to 2cf5110

Import the unmodified 49-file engine dependency closure and MIT license,
with exact Git blob IDs and SHA-256 provenance. Retain horizontal FDM tines,
existing defaults and the 0.10-0.40 mm support-gap range through small host
schema compatibility changes.

Record Release, engine/backend regression results and successful maintainer
desktop acceptance. Preserve the known Node browser-Worker test limitation
and five independently confirmed original-Bambu C++ failures.
```

## Prepared Draft PR text

Target: `integration`. Title: `Update PrintFins Auto engine to 2cf5110`.
Text prepared locally only; no PR has been created for this update.

```markdown
Update the native PrintFins Auto integration from bff031d to official
2cf5110efbdcc4ec1906adfba9dcb88f27f7dfb4. All 49 vendor files are unchanged
upstream bytes, including MIT licensing and verified blob/SHA-256 provenance.
Auto gains upstream tall-wall ribs and wedge-clearance checks. Small host
schema filters preserve FDM defaults and horizontal tines; support gap remains
0.10-0.40 mm. No Full/Draw/Hybrid or individual editing is exposed.

Validation:
- Windows x64 Release build/link and startup passed (incremental build).
- 33 host Node, 18 Python, 85 original upstream and all seven PrintFins C++
  cases passed. DOM/Worker/Win32 doubles are distinguished in the report.
- Old/new engines compared on 16 fixtures; expected tall-rib changes retained.
  Real Bambu backend completed 36 slices and six native 3MF round trips,
  including Normal/Tree support modes (manual modes unpainted).
- Maintainer confirmed all planned Windows desktop checks, including Auto,
  Sway braces, slicing, preset reset, Undo/Redo, 3MF save/reopen and 110-mm test.

Known limitations: one original site-worker test fails under Node because
browser Worker is unavailable; five C++ failures match the independently
built original-Bambu baseline (12/17 dedicated cases pass). Shared WebView
cache isolation, broad GUI automation and the known CLI shutdown hang remain
outside this acceptance. No rendering fixes are included.

Details: docs/printfins-upstream-20261017.md.
```
