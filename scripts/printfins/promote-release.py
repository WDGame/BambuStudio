#!/usr/bin/env python3
"""Promote exactly the successfully built candidate, respecting GitHub merge rules."""
import json
import os
from pathlib import Path
import re
import subprocess
import time


def run(*args):
    return subprocess.check_output(args, text=True, timeout=60).strip()


def api(path, method=None, **fields):
    args = ["gh", "api", "-H", "X-Octopool-Require: merge-async-v1", path,
            "-H", "X-GitHub-Api-Version: 2026-03-10", "-H", "Cache-Control: max-age=0"]
    if method:
        args += ["--method", method]
    for key, value in fields.items():
        args += ["-f", f"{key}={value}"]
    return json.loads(run(*args))


def merged_commit(repo, number, pr, expected):
    sha = pr.get("merge_commit_sha")
    if not sha:
        # REST 2026-03-10 omits merge_commit_sha; GraphQL retains mergeCommit.
        state = json.loads(run("gh", "pr", "view", number, "--repo", repo,
                               "--json", "state,headRefOid,mergeCommit"))
        if state["state"] != "MERGED" or state["headRefOid"] != expected:
            raise RuntimeError("PR merge identity differs from the tested candidate")
        sha = (state.get("mergeCommit") or {}).get("oid", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError("Merged commit could not be verified")
    return sha


def validate_metadata(root):
    state = json.loads((root / "printfins-fork.json").read_text())
    version = state["upstream_version"]
    revision = state["fork_revision"]
    if not re.fullmatch(r"\d{2}\.\d{2}\.\d{2}\.\d{2}", version):
        raise ValueError("Invalid upstream version")
    if type(revision) is not int or revision < 1:
        raise ValueError("Invalid fork revision")
    if state["upstream_tag"] != f"v{version}" or state["fork_version"] != f"{version}-ecore.{revision}":
        raise ValueError("Inconsistent release metadata")
    header = (root / "src/slic3r/GUI/ForkVersion.hpp").read_text()
    for field in (f'upstream_version = "{version}";', f'revision = {revision};',
                  f'display = "{state["fork_version"]}";'):
        if field not in header:
            raise ValueError("Compiled updater metadata differs from release manifest")
    if f'"{version}"' not in (root / "version.inc").read_text():
        raise ValueError("Bambu version.inc differs from release manifest")
    return "v" + state["fork_version"]


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    expected = os.environ["EXPECTED_SHA"]
    base = os.environ["INTEGRATION_SHA"]
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (expected, base)):
        raise ValueError("Pinned candidate and integration SHAs are required")
    if run("git", "rev-parse", "HEAD") != expected:
        raise ValueError("The built commit is not the approved candidate")
    tag = validate_metadata(Path.cwd())
    pr_number = os.environ.get("SYNC_PR", "")
    current = api(f"repos/{repo}/git/ref/heads/integration")["object"]["sha"]
    if pr_number:
        if not pr_number.isdigit():
            raise ValueError("Invalid PR number")
        pr = api(f"repos/{repo}/pulls/{pr_number}")
        if pr["head"]["sha"] != expected or pr["head"]["repo"]["full_name"] != repo or pr["base"]["ref"] != "integration":
            raise ValueError("PR does not target the exact tested E-Core candidate")
        if not pr["merged"]:
            if current != base:
                raise ValueError("Integration changed during the build; rebase/adapt and rebuild")
            path = f"repos/{repo}/pulls/{pr_number}/merge-async"
            receipt = api(path, "PUT", sha=expected, merge_method="merge", merge_action="default")
            details = receipt.get("details", receipt)
            uuid = details.get("uuid")
            if not uuid:
                raise RuntimeError(f"Merge API did not return a request UUID: {receipt}")
            # A queue/pending request is not a successful merge. Never bypass rules.
            for _ in range(60):
                pr = api(f"repos/{repo}/pulls/{pr_number}")
                if pr["merged"]:
                    break
                result = api(f"{path}/{uuid}")
                result = result.get("details", result)
                if result.get("status") == "failed" or result.get("state") == "failed":
                    raise RuntimeError(f"GitHub rejected promotion: {result}")
                time.sleep(10)
            else:
                raise RuntimeError(f"Merge request {uuid} is still pending; no release was published")
        if not pr["merged"] or pr["head"]["sha"] != expected:
            raise RuntimeError("PR merge was not verified")
        current = api(f"repos/{repo}/git/ref/heads/integration")["object"]["sha"]
        if current != merged_commit(repo, pr_number, pr, expected):
            raise RuntimeError("Integration moved after candidate promotion; refusing a stale release")
        merged = api(f"repos/{repo}/git/commits/{current}")
        if merged["tree"]["sha"] != run("git", "rev-parse", "HEAD^{tree}"):
            raise RuntimeError("Merged source tree differs from the tested build")
    elif current != expected or base != expected:
        raise ValueError("Publication recovery must build the unchanged integration commit")
    # Tag the tested commit, not an unbuilt moving branch. The tag push made with
    # GITHUB_TOKEN deliberately does not trigger another duplicate Windows build.
    refs = api(f"repos/{repo}/git/matching-refs/tags/{tag}")
    exact = next((ref for ref in refs if ref["ref"] == f"refs/tags/{tag}"), None)
    if exact:
        obj = exact["object"]
        if obj["type"] == "tag":
            obj = api(f"repos/{repo}/git/tags/{obj['sha']}")["object"]
        if obj["sha"] != expected:
            raise RuntimeError("Existing release tag points to another commit; it will not be replaced")
    else:
        api(f"repos/{repo}/git/refs", "POST", ref=f"refs/tags/{tag}", sha=expected)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        out.write(f"tag={tag}\n")


if __name__ == "__main__":
    main()
