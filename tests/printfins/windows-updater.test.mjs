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
    assert.match(nsis, /AutoCloseWindow true|SetAutoClose true/);
    assert.match(nsis, /Var IsUpdate/);
    assert.match(nsis, /MUI_PAGE_CUSTOMFUNCTION_PRE/);
    assert.doesNotMatch(nsis, /SetSilent silent/);
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
    assert.match(source, /std::vector<char> buffer\(64 \* 1024\)/);
    assert.doesNotMatch(source, /std::array<char, 1024 \* 1024> buffer/);
    assert.match(source, /ShellExecuteExW/);
    assert.match(source, /SW_HIDE/);
    assert.match(source, /while \(Get-Process -Id \$ParentPid/);
    assert.match(source, /'\/UPDATE'/);
    assert.doesNotMatch(source, /ArgumentList @\('\/S'/);
    assert.match(source, /\$installer\.WaitForExit\(\)/);
    assert.match(source, /CancelPath/);
    assert.match(source, /Remove-Item -LiteralPath \$InstallerPath/);
    assert.doesNotMatch(source, /case wxID_YES:\s*wxLaunchDefaultBrowser\(version_info\.url\)/);
    assert.match(http, /download_file->write/);
});

test('fork metadata and compiled updater version agree', () => {
    const state = JSON.parse(read('printfins-fork.json'));
    const version = read('src/slic3r/GUI/ForkVersion.hpp');
    assert.ok(Number.isInteger(state.fork_revision) && state.fork_revision > 0);
    assert.equal(state.fork_version, `${state.upstream_version}-ecore.${state.fork_revision}`);
    assert.equal(state.upstream_tag, `v${state.upstream_version}`);
    assert.ok(version.includes(`revision = ${state.fork_revision};`));
    assert.ok(version.includes(`upstream_version = "${state.upstream_version}";`));
    assert.ok(version.includes(`display = "${state.fork_version}";`));
    assert.ok(read('version.inc').includes(`"${state.upstream_version}"`));
});

test('a cached installer skips the download only after size and SHA-256 verification', () => {
    const source = read('src/slic3r/GUI/GUI_App.cpp');
    const update = source.slice(source.indexOf('void GUI_App::download_and_install_update()'),
        source.indexOf('void GUI_App::check_beta_version('));
    assert.match(update, /temp_directory_path\(\)[\s\S]*version_info\.version_str \+ "-Setup\.exe"/);
    assert.match(update, /const bool reuse_installer = boost::filesystem::is_regular_file\(target, ec\) && !ec &&\s*boost::filesystem::file_size\(target, ec\) == version_info\.installer_size && !ec &&\s*sha256_file\(target, cached_sha256\) && cached_sha256 == version_info\.installer_sha256;/);

    // Check the whole cache-miss block (including nested callbacks), not just
    // the relative positions of an if statement and the HTTP call.
    const guard = update.indexOf('if (!reuse_installer) {');
    assert.ok(guard > update.indexOf('const bool reuse_installer'));
    let cursor = update.indexOf('{', guard) + 1;
    const begin = cursor;
    let depth = 1;
    while (cursor < update.length && depth) {
        if (update[cursor] === '{') ++depth;
        if (update[cursor] === '}') --depth;
        ++cursor;
    }
    assert.equal(depth, 0);
    const download = update.slice(begin, cursor - 1);
    assert.match(download, /Http::get\(version_info\.installer_url\)/);
    assert.match(download, /sha256_file\(partial, actual_sha256\)/);
    assert.match(download, /rename\(partial, target, ec\)/);
    const remainder = update.slice(0, guard) + update.slice(cursor);
    assert.doesNotMatch(remainder, /Http::get|remove\(target|rename\(partial/);
    assert.match(update.slice(cursor), /launch_detached_update_helper\(target/);
});

test('installer errors retain the verified EXE for a later retry', () => {
    const source = read('src/slic3r/GUI/GUI_App.cpp');
    const literals = source.slice(source.indexOf('    script <<'), source.indexOf('    script.close();'));
    const helper = [...literals.matchAll(/"(?:\\.|[^"\\])*"/g)].map(match => JSON.parse(match[0])).join('');
    assert.match(helper, /if \(\$installer\.ExitCode -ne 0\) \{ throw [^\n]+\n  Remove-Item -LiteralPath \$InstallerPath/);
    const finallyBlock = helper.slice(helper.indexOf('} finally {'));
    assert.doesNotMatch(finallyBlock, /Remove-Item -LiteralPath \$InstallerPath/);
});
