# Native PrintFins — final release acceptance (2026-10-17)

## Scope and source identity

This acceptance record accompanies PR #6, based on native feature checkpoint
`862caca22220009e089d0855b2debf6b6e7ed611`. The change integrates the pinned
original PrintFins Auto engine into Bambu Studio's native Support Type options and
native setting controls. The original 44 vendored engine files were verified
unchanged against the pinned provenance manifest. Support gap remains 0.10–0.40 mm;
a wider range is deliberately outside this change.

## Automated evidence (from the completed development review)

- Windows x64 Release build and native linkage: PASS.
- 31 Node tests: PASS; some DOM/worker tests use test doubles.
- 18 Python tests: PASS; some driver tests use test doubles.
- All seven dedicated PrintFins C++ cases: PASS.
- Five other C++ cases failed both in the feature branch and in the unmodified
  Bambu baseline with the same diagnostic messages and exit codes. These are
  not newly introduced by this integration. The cases concern generic config
  validation, config accessors, full binary config serialization, skirt-distance
  setup, and a sinking-object convex-hull reference mismatch. They remain
  independently unresolved.
- The original engine generated three fins and two Sway Braces on the prepared
  model. Bambu's backend sliced the resulting parts with the model.
- Native 3MF backend save/load/re-slice preserved geometry and settings,
  including tested global, object and part settings. These backend tests alone
  are not substitutes for the GUI workflow.

## Manual desktop acceptance

On 2026-10-17, the maintainer reported that **all requested desktop checks
worked** in the updated native PrintFins build on the prepared test model:
automatic fin generation with Sway Braces, slicing, Undo/Redo, native preset
editing/reset, 3MF saving and reopening, cancellation and subsequent
generation, and switching among existing support types and PrintFins.

This is a maintainer-reported manual acceptance, not an automated GUI-matrix pass
or broad compatibility/physical-print certification. The local detailed
test report and generated diagnostic artifacts under `build/` are not included
in the Git commit.

## Known limitations and follow-up work

- A multi-monitor ghost-image/sidebar-resize artifact was reproduced identically
  in the signed unmodified Bambu Studio; it is tracked as upstream behavior,
  not a confirmed regression caused by PrintFins. Root cause remains unresolved.
- Some sandbox sessions had WebView2 navigation/focus limitations; the local
  GUI automation matrix is not fully certified. Known CLI shutdown behavior
  remains outside this change.
- The five baseline-matching C++ failures remain open upstream/test-maintenance
  issues; no unrelated production changes were made to mask them.
- Full coverage, manual Draw in the Bambu viewport, automatic+manual mixing,
  original per-fin semantic editing and native overhang overlays are not part
  of this stage.
- No extended support-gap limits, engine algorithm changes or original vendor
  file modifications are included.

The accepted scope is the first native **Auto** integration and its original
settings. Future rendering investigations and additional PrintFins modes should
be developed and reviewed separately.
