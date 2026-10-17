![Bambu Studio](https://user-images.githubusercontent.com/106916061/179006347-497d24c0-9bd6-45b7-8c49-d5cc8ecfe5d7.png)

# BambuStudio + PrintFins

An independent fork of [Bambu Studio](https://github.com/bambulab/BambuStudio) with native [PrintFins](https://github.com/gittrahan/support-fins) integration.

The project aims to provide lightweight, removable support structures directly within Bambu Studio while maintaining upstream compatibility.

## Features

- Native PrintFins integration in Bambu Studio's Support settings
- Automatic support-fin generation
- Breakaway tines and Sway Braces
- Adjustable support gaps, coverage, bed pads and cutouts
- Native slicing, Undo/Redo and 3MF project support
- All standard Bambu Studio slicing and printer features

## Roadmap

- Full Coverage support mode
- Manual fin drawing and placement
- Combined automatic and manual supports
- Individual fin editing
- Extended support-gap range
- Improved support generation for complex geometry

## Development

The `integration` branch contains the latest approved development state.

PrintFins engine files are kept separate, version-pinned and verified against the original repository to simplify future updates.

The custom integration is currently validated on Windows x64.

See [Project Rules](AGENTS.md) and [PrintFins Documentation](docs/printfins-native-support.md).

## Credits

- [Bambu Lab](https://github.com/bambulab/BambuStudio) — Bambu Studio
- [Matthew Trahan](https://github.com/gittrahan/support-fins) — PrintFins
- [Prusa Research](https://github.com/prusa3d/PrusaSlicer) — PrusaSlicer
- [Alessandro Ranellucci](https://github.com/Slic3r/Slic3r) — Slic3r

## License

Bambu Studio and this fork are licensed under **AGPL-3.0**.

PrintFins is integrated under its original **MIT License**, with copyright and attribution preserved.

The optional Bambu networking plugin contains proprietary components subject to separate terms.

See [LICENSE](LICENSE) and [PrintFins LICENSE](resources/printfins/vendor/LICENSE).

**This is an independent community project, not officially affiliated with Bambu Lab or PrintFins.**
