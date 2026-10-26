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
    assert.match(source, /browser_download_url/);
    assert.match(source, /https:\/\/github\.com\//);
    assert.match(source, /sha256:/);
    assert.match(source, /sha256_file\(partial, actual_sha256\)/);
    assert.match(source, /actual_sha256 != version_info\.installer_sha256/);
    assert.match(source, /wxEXEC_HIDE_CONSOLE/);
    assert.match(source, /Wait-Process -Id/);
    assert.match(source, /'\/S','\/UPDATE'/);
    assert.match(source, /Remove-Item -LiteralPath \$p/);
    assert.doesNotMatch(source, /case wxID_YES:\s*wxLaunchDefaultBrowser\(version_info\.url\)/);
    assert.match(http, /download_file->write/);
});

test('fork revision is bumped for the updater bootstrap release', () => {
    const state = JSON.parse(read('printfins-fork.json'));
    const version = read('src/slic3r/GUI/ForkVersion.hpp');
    assert.equal(state.fork_revision, 3);
    assert.equal(state.fork_version, '02.08.02.61-ecore.3');
    assert.match(version, /revision = 3/);
    assert.match(version, /02\.08\.02\.61-ecore\.3/);
});
