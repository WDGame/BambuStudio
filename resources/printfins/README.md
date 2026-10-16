# Original PrintFins snapshot

`vendor/` is the unchanged dependency closure of `computeFins()` from
[gittrahan/support-fins](https://github.com/gittrahan/support-fins), pinned to
[bff031d484bb0f52f56df9ba49c61361ca86377a](https://github.com/gittrahan/support-fins/commit/bff031d484bb0f52f56df9ba49c61361ca86377a).
It contains 44 original files, including the MIT license and copyright notice.
`ORIGIN.json` records their upstream Git blob IDs and SHA-256 hashes.

The adapter validates host data and serializes the original engine result.
It uses `optionsFromDialog()` and upstream defaults; no geometry algorithm or
modified-project tunable is implemented here. In this upstream version the
support clearance is `gap`; the old material option is no longer supported.

The modified-engine `starts.js`, `lower.js`, Lower Foot Gap and
`alignLowerLayers` extensions are absent. Unknown old options are errors.
The **Edit > PrintFins...** tool uses the existing C++/WebView2 connection,
coordinate conversion and separate printable model parts. Its settings are
built directly from the original `options.json`, `optionVisible()` and
`optionsFromDialog()`. The slicer's effective layer heights are supplied by C++.
The startup PoC is no longer invoked. Saving and slicing use Bambu's normal UI.

Verify with `python scripts/printfins/check-snapshot.py`.
See `docs/printfins-ui-tool.md` for use and the actual current test status.
`docs/printfins-engine-poc.md` retains the earlier baseline's test evidence.
