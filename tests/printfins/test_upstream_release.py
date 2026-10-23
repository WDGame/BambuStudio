import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).parents[2] / "scripts" / "printfins" / "upstream-release.py"
SPEC = importlib.util.spec_from_file_location("upstream_release", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class UpstreamReleaseTests(unittest.TestCase):
    def test_selects_highest_stable_and_ignores_prereleases_and_drafts(self):
        releases = [
            {"tag_name": "v02.08.04.57", "prerelease": True, "draft": False},
            {"tag_name": "v02.08.03.12", "prerelease": False, "draft": True},
            {"tag_name": "v02.08.02.61", "prerelease": False, "draft": False},
            {"tag_name": "nightly", "prerelease": False, "draft": False},
        ]
        self.assertEqual(MODULE.newest_stable(releases)["tag_name"], "v02.08.02.61")

    def test_detects_only_newer_stable_versions(self):
        state = {"upstream_tag": "v02.08.02.61"}
        same = [{"tag_name": "v02.08.02.61", "prerelease": False, "draft": False}]
        newer = same + [{"tag_name": "v02.09.00.10", "prerelease": False, "draft": False,
                         "html_url": "https://example.invalid/release"}]
        self.assertFalse(MODULE.inspect(same, state)["update_available"])
        result = MODULE.inspect(newer, state)
        self.assertTrue(result["update_available"])
        self.assertEqual(result["latest_version"], "02.09.00.10")

    def test_rejects_missing_stable_release_and_malformed_current_tag(self):
        with self.assertRaisesRegex(ValueError, "No stable"):
            MODULE.newest_stable([{"tag_name": "v2.8-beta", "prerelease": True}])
        with self.assertRaisesRegex(ValueError, "Unsupported stable tag"):
            MODULE.inspect([{"tag_name": "v02.08.02.61"}], {"upstream_tag": "main"})


if __name__ == "__main__":
    unittest.main()
