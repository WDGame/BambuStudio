# E-Core stable upstream releases

## Working baseline and the 2.9.1 migration

The starting point is the **published `v02.08.02.61-ecore.8`**, not just the old
`integration` branch. The latter was missing `.8`'s Windows 3D Repair requirement.
The migration includes both histories and the official `v02.09.01.70` tag.

Preserved from `.8`:

- Unchanged NSIS installer, per-user installation directory, separate datadir,
  previous-version backup, shortcuts, uninstaller and visible update progress.
- Existing updater: direct `latest.json` discovery, schema 2, size/SHA-256
  verification with a heap buffer, streaming download, detached helper,
  cancellation and unsaved-work handling.
- PrintFins engine/adapter/settings assets, 49 unchanged vendor files, provenance,
  native controls, Undo/Redo and 3MF serialization.
- Make overhangs printable, its configuration/UI and exclusion with PrintFins.
- Russian translations, E-Core branding, public Product environment and the
  separately downloaded proprietary networking plugin (not redistributed).

Adaptations: the new nozzle-variant selector is used by PrintFins' settings
refresh; upstream timing arguments remain on `slice_volumes`; conical geometry
uses actual adjacent-layer spacing for adaptive/multi-diameter slicing. Windows
3D Repair keeps upstream's new per-source SDK detection and `.8`'s required gate.
Russian MO is rebuilt from the merged PO rather than choosing an old binary.

## Automated chain

1. `printfins-upstream-sync.yml` runs daily or manually on `integration`.
2. `sync-upstream.py` selects the highest official stable version (not beta/RC),
   fetches its tag and merges into `update/upstream-VERSION`. Fork metadata and
   the compiled updater version are bumped together. No feature patch is dropped.
3. Conflicts abort the merge, keep stable unchanged, and produce a job summary,
   downloadable report and one deduplicated Issue if Issues are enabled. Disabled
   Issues cannot erase the actual failure report.
4. A clean candidate gets a PR and an explicit `workflow_dispatch` of
   `printfins-windows.yml`, pinned to its SHA and integration baseline. A bot's
   `GITHUB_TOKEN` push alone does **not** trigger downstream CI.
5. Quick tests, vendor receipts and version agreement must pass. Windows builds
   the installer/portable plus focused native PrintFins/3MF/overhang regressions;
   packaging also requires 3D Repair code in the DLL and successful CLI startup.
6. For automatic runs only, `promote-release.py` requests a rules-respecting PR
   merge for the exact built SHA. A changed integration baseline, a changed PR
   head, pending merge queue, failed merge, different merged tree, or existing
   conflicting tag blocks publication. Never bypass protections or replace tags.
7. The tested commit is tagged. The same run publishes **its existing artifacts**,
   not a second compilation: all four assets go to a draft, server SHA-256 digests
   are checked, then the draft is made stable/latest atomically.
8. The already-working installed updater reads that stable `latest.json` normally.

Manual candidate builds keep `auto_release=false` (default) and never publish.
Manual `v*-ecore.*` tag builds retain the previous release path, with all new
checks. Promotion's bot-created tag intentionally does not spawn a duplicate run.

## Failure recovery

- A failed candidate is not rebuilt every day without changes. Fix its branch or
  run sync manually to explicitly retry. Active builds are never duplicated.
- If integration merged but publication was interrupted, the next sync detects
  the missing/incomplete release and can build unchanged integration to recover.
- A draft is retryable; an already-published stable release is not overwritten.
- If integration advances during a candidate build, adapt the existing update
  branch to the new baseline and rerun; do not release stale artifacts.
- GitHub merge API failures leave the candidate unmerged/unpublished; inspect the
  receipt/request UUID and reconcile state rather than bypassing policy.

## Review commands

```sh
python scripts/printfins/check-snapshot.py
node --test tests/printfins/*.test.mjs
python -m unittest discover -s tests/printfins -p 'test_*.py' -v
actionlint .github/workflows/printfins-upstream-sync.yml .github/workflows/printfins-windows.yml .github/workflows/build_bambu.yml
```

Source checks do not prove that the Windows executable or printer workflow works.
Do not describe a candidate as stable until Windows build/native tests and release
asset verification have actually completed. Do not change or close the user's
installed slicer for these CI checks.
