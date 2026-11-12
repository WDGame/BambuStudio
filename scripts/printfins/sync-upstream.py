#!/usr/bin/env python3
"""Prepare a stable upstream candidate; Windows CI owns promotion/publication."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SPEC = importlib.util.spec_from_file_location("upstream_release", Path(__file__).with_name("upstream-release.py"))
RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE)


def run(*args, check=True):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=check, timeout=180)


def gh_json(*args):
    return json.loads(run("gh", *args).stdout)


def summary(text):
    print(text, flush=True)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write(text + "\n")


def report_conflict(repo, tag, conflicts):
    title = f"Upstream {tag} requires manual adaptation"
    body = (f"Automatic integration stopped; the working release is unchanged.\n\n"
            f"Conflicting files:\n```\n{conflicts}\n```\n\n"
            f"Run: https://github.com/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}")
    Path("upstream-conflicts.txt").write_text(body + "\n", encoding="utf-8")
    summary(f"## {title}\n\n{body}")
    # Reporting must never hide the original merge error, even with Issues disabled.
    try:
        if not gh_json("api", f"repos/{repo}")["has_issues"]:
            summary("Issues are disabled. Conflict details remain in this job summary and artifact.")
            return
        issues = gh_json("issue", "list", "--repo", repo, "--state", "open", "--limit", "100",
                         "--json", "number,title")
        if not any(issue["title"] == title for issue in issues):
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as file:
                file.write(body); file.flush()
                run("gh", "issue", "create", "--repo", repo, "--title", title, "--body-file", file.name)
    except (subprocess.SubprocessError, KeyError, ValueError) as error:
        summary(f"Could not create an Issue: {error}. See the preserved conflict report.")


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    state = json.loads(Path("printfins-fork.json").read_text())
    pages = gh_json("api", "--paginate", "--slurp", "repos/bambulab/BambuStudio/releases")
    result = RELEASE.inspect([item for page in pages for item in page], state)
    summary(f"Official stable: **{result['latest_tag']}**; integration: **{result['current_tag']}**.")
    base = run("git", "rev-parse", "HEAD").stdout.strip()
    branch = "integration"
    pr_number = ""
    if result["update_available"]:
        branch = f"update/upstream-{result['latest_version']}"
        run("git", "config", "user.name", "github-actions[bot]")
        run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        run("git", "fetch", "--no-tags", "https://github.com/bambulab/BambuStudio.git",
            f"refs/tags/{result['latest_tag']}:refs/tags/{result['latest_tag']}")
        existing = run("git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}").stdout.strip()
        if existing:
            run("git", "fetch", "--no-tags", "origin", f"refs/heads/{branch}")
            run("git", "switch", "-c", branch, "FETCH_HEAD")
            if run("git", "merge-base", "--is-ancestor", base, "HEAD", check=False).returncode:
                raise RuntimeError("Existing candidate does not include current integration; adapt it before retrying")
        else:
            run("git", "switch", "-c", branch)
            merged = run("git", "merge", "--no-ff", "--no-edit", result["latest_tag"], check=False)
            if merged.returncode:
                conflicts = run("git", "diff", "--name-only", "--diff-filter=U").stdout.strip()
                run("git", "merge", "--abort")
                report_conflict(repo, result["latest_tag"], conflicts or merged.stderr)
                return 1
            upstream_sha = run("git", "rev-parse", f"{result['latest_tag']}^{{commit}}").stdout.strip()
            RELEASE.update_metadata(Path.cwd(), result["latest_tag"], upstream_sha)
            run("git", "add", "printfins-fork.json", "src/slic3r/GUI/ForkVersion.hpp")
            run("git", "diff", "--cached", "--check")
            run("git", "commit", "-m", f"chore: track stable upstream {result['latest_tag']}")
            run("git", "push", "-u", "origin", branch)
        candidate_state = json.loads(Path("printfins-fork.json").read_text())
        if candidate_state["upstream_tag"] != result["latest_tag"]:
            raise RuntimeError("Candidate metadata does not match the selected upstream tag")
        run("git", "merge-base", "--is-ancestor", result["latest_tag"], "HEAD")
        prs = gh_json("pr", "list", "--repo", repo, "--base", "integration", "--head", branch,
                      "--state", "open", "--json", "number")
        if not prs:
            run("gh", "pr", "create", "--repo", repo, "--base", "integration", "--head", branch,
                "--title", f"Update to stable Bambu Studio {result['latest_tag']}",
                "--body", "Stable upstream integration. Windows CI must pass before automatic promotion and publication.")
            prs = gh_json("pr", "list", "--repo", repo, "--base", "integration", "--head", branch,
                          "--state", "open", "--json", "number")
        pr_number = str(prs[0]["number"])
    else:
        # Recover an interrupted publication after a successful integration merge.
        tag = "v" + state["fork_version"]
        published = run("gh", "release", "view", tag, "--repo", repo, "--json", "isDraft,assets", check=False)
        if published.returncode == 0:
            release = json.loads(published.stdout)
            if not release["isDraft"] and any(a["name"] == "latest.json" for a in release["assets"]):
                summary("Integration is current and its release is published.")
                return 0

    sha = run("git", "rev-parse", "HEAD").stdout.strip()
    runs = gh_json("run", "list", "--repo", repo, "--workflow", "printfins-windows.yml",
                   "--branch", branch, "--event", "workflow_dispatch", "--limit", "100",
                   "--json", "headSha,status,conclusion,url")
    previous = next((r for r in runs if r["headSha"] == sha), None)
    if previous and (previous["status"] != "completed" or os.environ.get("ALLOW_RETRY") != "true"):
        summary(f"Candidate already dispatched: {previous['url']} ({previous['status']}, {previous['conclusion']}). "
                "No duplicate build. After a failed run, fix the branch or run sync manually to retry.")
        return 1 if previous["conclusion"] not in ("", None, "success") else 0
    # workflow_dispatch runs even when a GITHUB_TOKEN push would suppress CI.
    run("gh", "workflow", "run", "printfins-windows.yml", "--repo", repo, "--ref", branch,
        "-f", "auto_release=true", "-f", f"expected_sha={sha}", "-f", f"integration_sha={base}",
        "-f", f"sync_pr={pr_number}")
    summary(f"Windows checks/build/publication dispatched for `{sha}` on `{branch}`. "
            "No stable release is published unless all checks and the Windows build succeed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (subprocess.SubprocessError, RuntimeError, KeyError, ValueError) as error:
        summary(f"## Upstream integration blocked\n\n{error}")
        sys.exit(1)
