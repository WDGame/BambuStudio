# Original PrintFins integration

This feature branch starts directly at `origin/integration`
(`e87152e35ab69a36c79fefa069f7de901ca73ead`). It
copies the reviewed integration from `feature/printfins-original` without
cherry-picking its PoC commit or other branch history. The source worktree is
preserved. The base's `AGENTS.md` remains unchanged. A remote fetch was
unavailable during preparation; the existing local remote-tracking ref was used.

## Source and scope

The engine is the unmodified dependency closure of
`plugins/shared/engine/fins_entry.js` from
[gittrahan/support-fins](https://github.com/gittrahan/support-fins), pinned to
[bff031d484bb0f52f56df9ba49c61361ca86377a](https://github.com/gittrahan/support-fins/commit/bff031d484bb0f52f56df9ba49c61361ca86377a).
The pin is intentional; no tracking of later upstream changes is implied.

The snapshot contains 44 original files (544,542 bytes), including the MIT
license and copyright notice. `resources/printfins/vendor/ORIGIN.json` records
all SHA-256 hashes and upstream Git blob IDs. They match the retained upstream
source and saved upstream tree. The complete dependency closure is checked;
there are no missing imports, extra engine files or engine patches.
`.gitattributes` preserves the exact upstream bytes across Windows checkouts.
Only upstream `web/prop/sweep.js` is exempted from Git's blank-at-EOF check;
its original trailing blank line is retained. Other whitespace checks remain on.

The old modified-engine `starts.js`, `lower.js`, Lower Foot Gap, custom
layer-grid alignment and material mapping are absent. The adapter delegates to
upstream `optionsFromDialog()` and `computeFins()` with original defaults.
Unsupported old options fail explicitly. The original clearance option is `gap`.
The host's first-layer height is metadata for native contour checks only.

## Bambu integration

The native host and its JS/worker transport are copied unchanged from the
reviewed, tested source. Existing `PrintFinsPoC` symbol/file names are retained
to avoid renaming or refactoring the working integration.

1. `src/slic3r/CMakeLists.txt` includes the two native host source files.
   `GUI_App::post_init()` schedules its opt-in entry point; normal startup is
   unaffected without `BBS_PRINTFINS_POC_ENABLE=1`.
2. The host requires a fresh `result` directory next to its active scratch
   `profile`, and one plain model object/instance. It passes posed triangle
   positions in millimetres, Z up, to a local WebView2 module worker.
3. The worker calls the thin adapter and the unmodified upstream engine.
   No Node/Python runtime is required inside Bambu Studio.
4. C++ maps output back with `inverse(instance) * (position - offset)` and adds
   separate printable `MODEL_PART` volumes through `ModelObject::add_volume()`.
   The original source part is preserved.
5. Existing native contour checks and `Plater::export_3mf()` save the model,
   fin and pad as a native Bambu `project.3mf`.

The two existing Bambu files receive only the source-list entries, include and
startup call. No unrelated Bambu code, build artifacts, profiles, account data,
old material/CI work or old regression runners are transferred.

## Verified test stand (2026-10-16)

The following native evidence is reused from the reviewed source worktree;
these are not newly executed desktop tests of this checkout. Native host,
transport and adapter code are identical to that tested source. The Bambu
base differs from the tested baseline only in the retained project rules.

| Check | Confirmed result |
| --- | --- |
| Upstream provenance | 44/44 files match SHA-256, upstream Git blob IDs, retained upstream source and saved tree. No live GitHub retrieval is claimed. |
| Adapter tests | Seven passing original-engine tests: exact output/defaults, piece ranges, placement, gap/reset, rejection of old options, first-layer metadata and invalid input. |
| Desktop generation | User saw a newly generated fin; native report confirms the full C++/WebView2/worker/engine/C++ path and native export. 12 source triangles, 440 fin triangles with four tines, 13,280 pad triangles; three printable parts, 13,732 triangles total. |
| Placement | Independent Node replay/export comparison passed; maximum position error 0.0000010338 mm; instance transform delta 0. |
| Joint slicing and native save | Newly generated native project reimported, fully sliced and resaved: process exit 0, slicer return code 0, 1.00 s, 977,457-byte G-code. |
| Native round trip | Three normal parts and triangle counts preserved. Accounting for component transforms, split files and Bambu recentering, maximum world-position change is 0.0000005640 mm. |
| GUI reopening | Fresh isolated profile, generation disabled; native Bambu project recognized, model import completed and all three part names present in model/BVH log. |
| Additional CLI reopening | Resaved project imported and sliced with return code 0 and identical G-code, but the process did not exit within 50 s. Shutdown check remains open; no fix is included. |

Artifact SHA-256 hashes retained for reproducible identification:

- Initial native project: `ef0ad6e6483d0b2cc79366a365f0323b791cbe95956497570ce041ba1004db6c`.
- Resaved native project: `880b1a5fb5c11f9d1d235089d92b5766f54eed93e27d2ae6d164ef0ddf75d403`.
- Both CLI G-code outputs: `566f43cbccb5f94e3f24d26d572d4104f16aa543e4edc82b65f52aff36d640a5`.
- Existing Release native DLL: `4667b5063e4cbd34e3ae38746b48358b7733332549905ad17a0c731fd555b883`.

Raw evidence remains in the source worktree's ignored
`build/timeout-control-normal/`: `lifecycle-verification.json`,
`result/report.json`, `result/placement-check.json`, `result/project.3mf`,
`native-roundtrip-check.json`, the `verified-slice-save/` and `verified-reopen/`
CLI receipts/G-code, and `verified-gui-reopen/` importer log/receipt.
No raw runtime artifacts or personal filesystem paths are staged.

## Verification and use

The normal Windows build must include the transferred native host. Alternatively,
the already validated Release runtime can run against this checkout's assets.
This transfer does not claim a fresh native rebuild or another desktop generation.
Prepare a new isolated profile with `scripts/printfins/prepare-run.py`; its
`options.json` is `{}` for original defaults. The profile template is read only.
See [manual GUI instructions](printfins-manual-gui-test.md).

```powershell
node --test tests/printfins/adapter.test.mjs
python scripts/printfins/check-snapshot.py
python scripts/printfins/check-snapshot.py PATH_TO_PINNED_UPSTREAM_SOURCE
python scripts/printfins/check-result.py PATH_TO_NEW_RUN/result
```

The optional upstream folder must contain the pinned original source, not the
old modified project. The snapshot checker also rejects missing/extra files.
The snapshot and adapter checks are rerun in this new checkout after transfer.
Before commit approval, the staged snapshot is checked again against its hashes,
the full staged diff is reviewed and `git diff --cached --check` must pass.
No commit, push, merge or release is part of this preparation.

## Known limits

Windows/WebView2 only; one object/instance, plain model parts and at most 100,000
input triangles. No production settings UI, persistent editable fin settings,
large-model qualification or physical print qualification is claimed. The test
preset selects PETG while the original engine uses its own default gap.

The restricted agent context failed before the page/worker handshake: WebView2's
GPU child exited with `0xC0000022` and the existing 120-second timer expired.
Disabling GPU acceleration did not resolve it. The user's normal desktop control
succeeded with the same runtime/assets; no security or runtime workarounds were
added. The additional CLI process-exit issue above remains documented only.

Use native `project.3mf`. Generic diagnostic `result.3mf` previously exhibited an
import access violation; that separate importer path was not repaired or
revalidated. The verified native route is the intended project format.
