import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/printfins' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROMOTE = load('promote-release')
PUBLISH = load('publish-release')
SYNC = load('sync-upstream')


class ReleasePipelineTests(unittest.TestCase):
    def test_current_source_metadata_matches_compiled_updater_and_bambu(self):
        tag = PROMOTE.validate_metadata(ROOT)
        self.assertTrue(tag.startswith('v02.'))

    def test_upstream_bump_preserves_settings_and_rejects_partial_header_update(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            header = root / 'src/slic3r/GUI/ForkVersion.hpp'
            header.parent.mkdir(parents=True)
            header.write_text((ROOT / 'src/slic3r/GUI/ForkVersion.hpp').read_text())
            state = json.loads((ROOT / 'printfins-fork.json').read_text())
            (root / 'printfins-fork.json').write_text(json.dumps(state))
            SYNC.RELEASE.update_metadata(root, 'v02.10.00.10', 'a' * 40)
            actual = json.loads((root / 'printfins-fork.json').read_text())
            self.assertEqual(actual['fork_version'], '02.10.00.10-ecore.1')
            for key in ('features', 'release_repository', 'release_channel'):
                self.assertEqual(actual[key], state[key])
            before = (root / 'printfins-fork.json').read_text()
            header.write_text('missing version fields')
            with self.assertRaises(ValueError):
                SYNC.RELEASE.update_metadata(root, 'v02.11.00.10', 'b' * 40)
            self.assertEqual((root / 'printfins-fork.json').read_text(), before)

    def test_conflict_report_survives_disabled_issues_and_does_not_send_issue(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(SYNC, 'gh_json', return_value={'has_issues': False}), \
                patch.object(SYNC, 'run') as command, patch.object(SYNC, 'summary'):
            previous = Path.cwd()
            try:
                os.chdir(directory)
                SYNC.report_conflict('owner/repo', 'v02.09.01.70', 'src/changed.cpp')
                self.assertIn('src/changed.cpp', Path('upstream-conflicts.txt').read_text())
                command.assert_not_called()
            finally:
                os.chdir(previous)

    def test_deduplicates_conflict_issue(self):
        title = 'Upstream v02.09.01.70 requires manual adaptation'
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(SYNC, 'gh_json', side_effect=[{'has_issues': True}, [{'title': title}]]), \
                patch.object(SYNC, 'run') as command, patch.object(SYNC, 'summary'):
            previous = Path.cwd()
            try:
                os.chdir(directory)
                SYNC.report_conflict('owner/repo', 'v02.09.01.70', 'src/changed.cpp')
                command.assert_not_called()
            finally:
                os.chdir(previous)

    def test_changed_integration_blocks_promotion_before_merge_or_tag(self):
        expected = 'a' * 40
        def api(path, *args, **kwargs):
            if path.endswith('git/ref/heads/integration'):
                return {'object': {'sha': 'c' * 40}}
            if path.endswith('pulls/1'):
                return {'merged': False, 'head': {'sha': expected, 'repo': {'full_name': 'owner/repo'}},
                        'base': {'ref': 'integration'}}
            self.fail(f'Unexpected mutation/API call: {path}')
        with patch.dict(os.environ, {'GITHUB_REPOSITORY': 'owner/repo', 'EXPECTED_SHA': expected,
                                     'INTEGRATION_SHA': 'b' * 40, 'SYNC_PR': '1'}), \
                patch.object(PROMOTE, 'run', return_value=expected), patch.object(PROMOTE, 'api', side_effect=api):
            with self.assertRaisesRegex(ValueError, 'Integration changed'):
                PROMOTE.main()

    def test_merged_commit_uses_graphql_when_new_rest_omits_field(self):
        expected, merged = 'a' * 40, 'b' * 40
        with patch.object(PROMOTE, 'run', return_value=json.dumps({
                'state': 'MERGED', 'headRefOid': expected, 'mergeCommit': {'oid': merged}})):
            self.assertEqual(PROMOTE.merged_commit('owner/repo', '1', {'merged': True}, expected), merged)

    def test_merged_commit_rejects_changed_head_or_missing_merge_identity(self):
        expected = 'a' * 40
        for state in [
                {'state': 'MERGED', 'headRefOid': 'c' * 40, 'mergeCommit': {'oid': 'b' * 40}},
                {'state': 'OPEN', 'headRefOid': expected, 'mergeCommit': {'oid': 'b' * 40}},
                {'state': 'MERGED', 'headRefOid': expected, 'mergeCommit': None}]:
            with self.subTest(state=state), patch.object(PROMOTE, 'run', return_value=json.dumps(state)):
                with self.assertRaises(RuntimeError):
                    PROMOTE.merged_commit('owner/repo', '1', {'merged': True}, expected)

    def test_assets_are_verified_before_upload_and_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {'schema': 2, 'channel': 'stable', 'tag': 'vtest', 'commit': 'a' * 40}
            sums = []
            for kind, name in [('installer', 'test_Setup.exe'), ('portable', 'test.zip')]:
                data = kind.encode()
                (root / name).write_bytes(data)
                digest = hashlib.sha256(data).hexdigest()
                manifest[kind] = {'asset': name, 'size': len(data), 'sha256': digest}
                sums.append(f'{digest}  {name}')
            (root / 'latest.json').write_text(json.dumps(manifest))
            (root / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n')
            self.assertEqual(len(PUBLISH.validate_assets(root, 'vtest', 'a' * 40)), 4)
            with self.assertRaisesRegex(ValueError, 'tested commit'):
                PUBLISH.validate_assets(root, 'vtest', 'b' * 40)
            (root / 'test_Setup.exe').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                PUBLISH.validate_assets(root, 'vtest', 'a' * 40)


if __name__ == '__main__':
    unittest.main()
