# PrintFins UI tool

`feature/printfins-ui-tool` starts at the GitHub `integration` merge
`379b3eca790f8d25d817b54130ed003b0c8ce7e0`. The existing worktrees are preserved.
The current menu placement is retained. This change targets `integration` via
a feature-branch pull request; no merge or additional feature is included.

## Operation

In **Prepare**, select one complete model, open the top-left dropdown next to
**File**, then **Edit > PrintFins...**. Edit the settings and click **Generate
fins**. Successful generation adds printable `PrintFins <kind> <id>` parts to
that object in one undo step. Use Bambu Studio's normal **Slice plate**,
**Save Project As** and **Open Project** commands. Nothing is exported or saved
automatically by the tool. Opening Bambu no longer triggers the startup PoC.

The dialog builds all 12 editable options directly from the unchanged original
`vendor/plugins/shared/engine/options.json`: defaults, ranges, steps, labels,
choices and hints. Original `optionVisible()` evaluates dependencies;
`optionsFromDialog()` validates values and assembles nested engine options.
Percent controls display 0..100 and send the original fractional units.
`layerHeight` is omitted as required by `hostSupplied: "slicer"`; the effective
object/preset layer and first-layer heights are displayed and supplied by C++.
No material mapping or custom geometry options are introduced.

Native Cancel, Escape and window close discard the computation and destroy the
WebView. Late results are ignored. Engine/worker/page errors and timeouts leave
the project unchanged. Startup has a 30-second deadline; the original
120-second computation limit starts only when generation is requested.
An empty result leaves the model unchanged. Output ranges, finite coordinates,
slice contours and unchanged input selection/geometry/heights are checked before
the undo snapshot and model mutation. Meshes and hulls are prepared in a detached
model. Normal Bambu volume-copy and undo paths handle insertion and rollback.

Windows/WebView2 and FFF only. Supported input is one complete object with one
instance, plain model parts, constant layer heights and at most 100,000 triangles.
Other project objects may remain present. Modifiers, negative volumes, multiple
instances, height ranges, singular transforms and generated output beyond the
existing one-million-triangle limit are rejected. A selected object containing
parts whose names begin `PrintFins ` (including earlier `PrintFins PoC` parts)
is rejected; existing parts are never replaced automatically. Keep those names
so detection survives saving/reopening. Fin parameters are not persisted for
regeneration; saved 3MF projects contain ordinary printable geometry.

## Verification on 2026-10-16

| Check | Actual result |
| --- | --- |
| Original provenance | PASS: all 44 vendor files match SHA-256 and upstream Git blob IDs in ORIGIN.json, and the retained pinned upstream source. No vendor changes. |
| Existing adapter tests | PASS: 7 tests for exact original output/defaults, ranges, placement, gap, rejected old options, layer metadata and invalid inputs. |
| Dialog/transport tests | PASS: 4 Node tests using a small DOM/worker double; all editable defaults/ranges/choices, visibility, percent conversion, invalid/hidden input, explicit submit, host heights, worker result/errors and termination on close. These do not test native rendering or project mutation. |
| Native build | PASS: changed MainFrame.cpp, GUI_App.cpp and PrintFinsPoC.cpp compiled with MSVC Release settings and linked into a separate runtime using the existing baseline libraries. This is an incremental validation build, not a fresh full CMake build. |
| New runtime startup | PASS: isolated profile and tilted-box STL loaded; native import log confirms load_model_objects completed. Window capture confirms Prepare view. |
| Local desktop workflow | CONFIRMED by the maintainer: the new GUI generated fins, sliced the model with them, saved a native 3MF project and reopened it successfully. The current placement is retained. This is manual desktop evidence, not a new automated pass. |
| Additional stability coverage | A reproducible runner now prepares geometry, invalid-input, cancellation, duplicate-generation, selection, undo/redo and 3MF scenarios. The automated native GUI matrix remains blocked in the restricted account. See the [stability report and one-command desktop run](printfins-stability.md). |
| Restricted-account attempt | Earlier attempt blocked by WebView2 GPU process exit 0xC0000022 and unavailable cursor positioning. This environment limitation does not supersede the maintainer's successful desktop UI check. |
| Earlier original integration | Existing successful desktop generation, joint slicing, native 3MF save/reopen and placement evidence retained in the historical baseline report. Not repeated or counted as a pass for this changed UI host. |

Final local test DLL SHA-256:
`4ccf3ba4fae6fe1b6d0e98eaecc4963f48f6a1fabe5a61782deebf5527a7f4be`.
The cached native sources differ from the integration baseline only in the
replaced PrintFins host; all three changed translation units were rebuilt.
Raw build logs remain under ignored `build/native/`; isolated startup evidence,
window capture and WebView2 failure log remain under ignored `build/ui-smoke/`.
The startup test preceded the final cancel/error cleanup in the tool; the menu
and application-startup code did not change afterward. No new geometry was
inserted in this restricted GUI run, and that test process was closed.

The known additional CLI shutdown hang remains documented in
[the baseline report](printfins-engine-poc.md). No CLI fix, security workaround,
new dependency, preset change or unrelated feature is included.

Run the automated checks from this checkout:

```powershell
node --test tests/printfins/adapter.test.mjs tests/printfins/settings.test.mjs
python scripts/printfins/check-snapshot.py
python scripts/printfins/check-snapshot.py PATH_TO_PINNED_UPSTREAM_SOURCE
git diff --check
```

## Desktop acceptance checklist

Opening and operating the UI, fin generation, joint slicing and native 3MF
save/reopen are confirmed by the maintainer. The checklist below retains the
detailed acceptance cases; individual safety and undo cases are not claimed as
passed without an explicit result. The automated checks and provenance checks
were rerun before publication; native build/startup evidence was reused after
checking that the compiled source hashes and local DLL hash still match.

Build this checkout with the normal Windows build/dependencies. A local
incrementally linked test runtime is also available under `build/runtime/`,
with resources pointing to this checkout. Do not substitute the previous
baseline DLL: it lacks the new menu and host.

Prepare an isolated profile and synthetic tilted box using an existing working
profile as a read-only template. The helper copies public system presets and
whitelisted settings; it does not copy accounts or printer connections.
In a normal desktop PowerShell, from this checkout:

```powershell
$exe = (Resolve-Path 'build/runtime/bambu-studio.exe').Path
$template = (Resolve-Path (Read-Host 'Working test profile template')).Path
$run = Join-Path $PWD ('build/ui-desktop-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
python scripts/printfins/prepare-run.py $run --profile-template $template
if ($LASTEXITCODE -ne 0) { throw 'Profile preparation failed' }
$previous = $env:WEBVIEW2_USER_DATA_FOLDER
try {
    $env:WEBVIEW2_USER_DATA_FOLDER = Join-Path $run 'webview-profile'
    Start-Process -FilePath $exe -WorkingDirectory $run -WindowStyle Normal -ArgumentList ('--datadir "{0}\profile" "{0}\input.stl"' -f $run)
} finally { $env:WEBVIEW2_USER_DATA_FOLDER = $previous }
```

1. Verify no automatic PrintFins dialog opens. With no selection, multiple
   models selected, or a modifier selected, the tool must reject or be disabled.
   No geometry or settings may change. Select the entire tilted box.
2. Open **Edit > PrintFins...**. Verify upstream defaults (45-degree threshold,
   tines on, gap 0.2 mm, pad Auto, sway off, coverage 50%). Toggle tines and sway;
   dependent controls must follow the original schema. Confirm displayed host
   layer heights. Invalid numeric input must prevent submission.
3. Cancel with the button, Escape and window close in separate runs, including
   once during generation. Verify unchanged object parts, pose, settings and
   undo state, and no delayed insertion. Close immediately after reopening too.
4. Generate with original defaults. In **Objects**, verify the original model
   plus printable fin/pad parts. Verify pose and existing settings are preserved.
   Reinvoking on that whole object must reject existing fins without changes.
5. Click **Slice plate**; inspect Preview, including support/contact layers.
   Save a native Bambu 3MF project under the new run directory. Reopen it with
   the new runtime and a fresh isolated profile, verify all normal parts and
   slice again. Reinvoking PrintFins must still reject the saved fin parts.
6. On a separate copy/run, undo generation once: only the original model must
   remain with its prior pose/configuration. Redo should restore the fin parts.
   Also test a supported selected model when another project object is present;
   the unselected object must remain unchanged.

Record the build/DLL identity, actions, part/triangle counts, project hash and
actual pass/fail for each item. Physical print qualification and large-model
qualification remain outside this change.
