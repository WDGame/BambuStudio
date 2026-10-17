# Original PrintFins snapshot

`vendor/` is the unchanged dependency closure of `computeFins()` from
[gittrahan/support-fins](https://github.com/gittrahan/support-fins), pinned to
[2cf5110efbdcc4ec1906adfba9dcb88f27f7dfb4](https://github.com/gittrahan/support-fins/commit/2cf5110efbdcc4ec1906adfba9dcb88f27f7dfb4).
It contains 49 original files, including the MIT license and copyright notice.
`ORIGIN.json` records their upstream Git blob IDs and SHA-256 hashes.

The adapter validates host data and serializes the original engine result.
It uses `optionsFromDialog()` and upstream defaults; no geometry algorithm or
modified-project tunable is implemented here. In this upstream version the
support clearance is `gap`; the old material option is no longer supported.

The modified-engine `starts.js`, `lower.js`, Lower Foot Gap and
`alignLowerLayers` extensions are absent. Unknown old options are errors.
The native **Support > Type > PrintFins** integration and retained
**Edit > PrintFins...** tool use the existing C++/WebView2 connection,
coordinate conversion and separate printable model parts. Its settings are
built directly from the original `options.json`, `optionVisible()` and
`optionsFromDialog()`. Host presentation excludes the new resin direction/depth
controls; this integration retains horizontal FDM tines. The adapter rejects
vertical resin generation. The slicer's effective layer heights are supplied by C++.
The startup PoC is no longer invoked. Saving and slicing use Bambu's normal UI.

Verify with `python scripts/printfins/check-snapshot.py`.
Use `--git-source <official-local-clone>` to compare exact pinned Git blobs,
independently of checkout newline conversion. See
`docs/printfins-upstream-20261017.md` for update scope and current evidence.
See `docs/printfins-ui-tool.md` for use and the actual current test status.
`docs/printfins-engine-poc.md` retains the earlier baseline's test evidence.
