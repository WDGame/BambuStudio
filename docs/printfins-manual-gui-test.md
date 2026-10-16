# Manual test of original PrintFins

Use `feature/printfins-original-clean`. Existing successful desktop generation,
joint slicing, native saving and GUI reopening evidence is retained in the
source worktree; no regeneration is needed to validate those records. See the
[validation report](printfins-engine-poc.md#verified-test-stand-2026-10-16) for
artifact hashes and the additional CLI shutdown limitation.

For a new manual test, use a normal Release build including this checkout's
native host, or the already validated Release runtime with these local assets.
Choose a new isolated run directory. The template profile is read only; only
public system presets and whitelisted settings are copied, without accounts,
printer connections, plugins, user presets or recent projects.

From this checkout in a normal desktop PowerShell session:

```powershell
if ((git branch --show-current) -ne 'feature/printfins-original-clean') { throw 'Wrong branch' }
$exe = (Resolve-Path (Read-Host 'Path to the working Bambu Studio executable')).Path
$template = (Resolve-Path (Read-Host 'Path to the test profile template')).Path
$run = Join-Path $PWD ('build\original-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
python scripts/printfins/prepare-run.py $run --profile-template $template
if ($LASTEXITCODE -ne 0) { throw 'Profile preparation failed' }
$settings = @{
    BBS_PRINTFINS_POC_ENABLE = '1'
    BBS_PRINTFINS_POC_OUTPUT = Join-Path $run 'result'
    BBS_PRINTFINS_POC_ASSETS = Join-Path $PWD 'resources\printfins'
    BBS_PRINTFINS_POC_OPTIONS = Join-Path $run 'options.json'
    BBS_PRINTFINS_POC_AUTOCLOSE = '1'
    WEBVIEW2_USER_DATA_FOLDER = Join-Path $run 'webview-profile'
}
$saved = @{}
try {
    foreach ($name in $settings.Keys) {
        $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process')
    }
    Start-Process -FilePath $exe -WorkingDirectory $run -WindowStyle Normal -ArgumentList ('--datadir "{0}\profile" "{0}\input.stl"' -f $run)
} finally {
    foreach ($name in $saved.Keys) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
}
```

No execution-policy change is required. After the computation dialog closes,
open **Prepare > Objects**. Expand `input.stl`: the original part,
`PrintFins PoC prop 0` and `PrintFins PoC pad pad` are separate printable parts
of one object. Select parts to highlight them without moving/scaling the model.
Click **Slice plate**, then inspect **Preview** and the lower/contact layers.
Tutorial/recommendation prompts can be declined. Do not use Print/Send controls;
save only inside the new run directory.

The native project is automatically exported as `result/project.3mf`. To reopen
it, start the executable with a fresh isolated `--datadir` and that file, with
`BBS_PRINTFINS_POC_ENABLE` unset or `0`. Its parts then load without regeneration.
Use a copy when manually saving changes. Preserve successful test artifacts.

`options.json` accepts original schema keys such as `gap`, `tines`, `padStyle`
and `coverage`; leave it `{}` for upstream defaults. The old `lowerFootGap`,
`alignLowerLayers`, `material`, `nozzle` and `bodyThickness` extensions are not
accepted. The example is not physically print-qualified.
