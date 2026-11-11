#!/usr/bin/env python3
"""Publish all verified assets atomically via a draft, without rebuilding them."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def run(*args, check=True):
    return subprocess.run(args, text=True, capture_output=True, check=check, timeout=600)


def validate_assets(directory, tag, commit):
    manifest = json.loads((directory / "latest.json").read_text())
    if (manifest.get("schema") != 2 or manifest.get("channel") != "stable"
            or manifest.get("tag") != tag or manifest.get("commit") != commit):
        raise ValueError("Release manifest does not describe the tested commit/tag")
    files = [directory / "latest.json", directory / "SHA256SUMS.txt"]
    for kind in ("installer", "portable"):
        info = manifest[kind]
        name = info["asset"]
        if Path(name).name != name:
            raise ValueError("Unsafe asset name")
        path = directory / name
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if path.stat().st_size != info["size"] or digest != info["sha256"]:
            raise ValueError(f"Incorrect {kind} size or checksum")
        if f"{digest}  {name}" not in (directory / "SHA256SUMS.txt").read_text().splitlines():
            raise ValueError("SHA256SUMS disagrees with the manifest")
        files.append(path)
    return files


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    tag = os.environ["RELEASE_TAG"]
    commit = run("git", "rev-parse", "HEAD").stdout.strip()
    files = validate_assets(Path("release"), tag, commit)
    # A malicious/moved tag must not turn a tested artifact into another release.
    tag_commit = json.loads(run("gh", "api", f"repos/{repo}/commits/{tag}").stdout)["sha"]
    if tag_commit != commit:
        raise ValueError("Release tag does not point to the tested source commit")
    view = run("gh", "release", "view", tag, "--repo", repo, "--json", "isDraft,assets", check=False)
    if view.returncode:
        state = json.loads(Path("printfins-fork.json").read_text())
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as notes:
            notes.write(f"Stable E-Core build based on Bambu Studio {state['upstream_version']}.\n\n"
                        "Includes PrintFins, Make overhangs printable, Russian localization, "
                        "E-Core branding, Windows 3D Repair, and verified installer updates.\n\n"
                        f"Tested source commit: {commit}\n")
            notes.flush()
            run("gh", "release", "create", tag, "--repo", repo, "--draft", "--verify-tag",
                "--title", f"Bambu Studio E-Core {tag}", "--notes-file", notes.name)
    elif not json.loads(view.stdout)["isDraft"]:
        with tempfile.TemporaryDirectory() as directory:
            run("gh", "release", "download", tag, "--repo", repo, "--pattern", "latest.json", "--dir", directory)
            if Path(directory, "latest.json").read_bytes() != Path("release/latest.json").read_bytes():
                raise ValueError("A different stable release already exists; it will not be overwritten")
        print(f"Release {tag} is already published; no assets were replaced.")
        return
    run("gh", "release", "upload", tag, *(str(f) for f in files), "--repo", repo, "--clobber")
    # Verify uploaded bytes using the server's digests before exposing latest.json.
    assets = json.loads(run("gh", "api", f"repos/{repo}/releases/tags/{tag}").stdout)["assets"]
    for file in files:
        asset = next(a for a in assets if a["name"] == file.name)
        with file.open("rb") as stream:
            digest = "sha256:" + hashlib.file_digest(stream, "sha256").hexdigest()
        if asset.get("digest") != digest or asset["size"] != file.stat().st_size:
            raise ValueError(f"Uploaded asset verification failed: {file.name}")
    run("gh", "release", "edit", tag, "--repo", repo, "--draft=false", "--latest")
    print(f"Published https://github.com/{repo}/releases/tag/{tag}")


if __name__ == "__main__":
    main()
