import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(new URL(`../../${path}`, import.meta.url), 'utf8');

test('Windows release builds and publishes a per-user NSIS installer', () => {
    const build = read('.github/workflows/build_bambu.yml');
    const release = read('.github/workflows/printfins-windows.yml');
    const nsis = read('packaging/windows/ecore-installer.nsi');

    assert.match(build, /Create E-Core installer Win/);
    assert.match(build, /makensis\.exe/);
    assert.match(build, /BambuStudio_ECore_.*_Setup\.exe/);
    assert.match(release, /name '\*_Setup\.exe'/);
    assert.match(release, /"schema": 2/);
    assert.match(release, /"installer": installer, "portable": portable/);

    assert.match(nsis, /RequestExecutionLevel user/);
    assert.match(nsis, /InstallDir "\$LOCALAPPDATA\\Programs\\Bambu Studio PrintFins"/);
    assert.match(nsis, /BambuStudio-PrintFins-Data/);
    assert.match(nsis, /WriteUninstaller/);
    assert.match(nsis, /Section "Uninstall"/);
    assert.match(nsis, /Bambu Studio PrintFins\.previous/);
    assert.match(nsis, /\/UPDATE/);
});

test('E-Core updater downloads only a hashed installer and starts it hidden', () => {
    const source = read('src/slic3r/GUI/GUI_App.cpp');
    const header = read('src/slic3r/GUI/GUI_App.hpp');
    const http = read('src/slic3r/Utils/Http.cpp');

    assert.match(header, /installer_sha256/);
    assert.match(header, /installer_size/);
    assert.match(source, /releases\/latest\/download\/latest\.json/);
    assert.doesNotMatch(source, /api\.github\.com\/repos\/"\) \+ ForkVersion::repository/);
    assert.match(source, /manifest\.value\("schema", 0\) != 2/);
    assert.match(source, /manifest\.value\("channel", ""\) != "stable"/);
    assert.match(source, /installer\.value\("sha256", ""\)/);
    assert.match(source, /sha256_file\(partial, actual_sha256\)/);
    assert.match(source, /actual_sha256 != version_info\.installer_sha256/);
    assert.match(source, /ShellExecuteExW/);
    assert.match(source, /SW_HIDE/);
    assert.match(source, /while \(Get-Process -Id \$ParentPid/);
    assert.match(source, /'\/S','\/UPDATE'/);
    assert.match(source, /\$installer\.WaitForExit\(\)/);
    assert.match(source, /CancelPath/);
    assert.match(source, /Remove-Item -LiteralPath \$InstallerPath/);
    assert.doesNotMatch(source, /case wxID_YES:\s*wxLaunchDefaultBrowser\(version_info\.url\)/);
    assert.match(http, /download_file->write/);
});

test('fork revision is bumped for the direct-manifest updater release', () => {
    const state = JSON.parse(read('printfins-fork.json'));
    const version = read('src/slic3r/GUI/ForkVersion.hpp');
    assert.equal(state.fork_revision, 6);
    assert.equal(state.fork_version, '02.08.02.61-ecore.6');
    assert.match(version, /revision = 6/);
    assert.match(version, /02\.08\.02\.61-ecore\.6/);
});
