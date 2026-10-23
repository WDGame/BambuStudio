#!/usr/bin/env python3
"""Select the newest official stable Bambu Studio release deterministically."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TAG = re.compile(r"^v(?P<version>\d{2}\.\d{2}\.\d{2}\.\d{2})$")


def version_tuple(tag: str) -> tuple[int, int, int, int]:
    match = TAG.fullmatch(tag)
    if not match:
        raise ValueError(f"Unsupported stable tag: {tag}")
    return tuple(int(part) for part in match.group("version").split("."))


def newest_stable(releases: list[dict]) -> dict:
    candidates = []
    for release in releases:
        tag = release.get("tag_name", "")
        if release.get("draft") or release.get("prerelease") or not TAG.fullmatch(tag):
            continue
        candidates.append((version_tuple(tag), release))
    if not candidates:
        raise ValueError("No stable Bambu Studio release was found")
    return max(candidates, key=lambda item: item[0])[1]


def inspect(releases: list[dict], state: dict) -> dict:
    release = newest_stable(releases)
    tag = release["tag_name"]
    current = state["upstream_tag"]
    return {
        "current_tag": current,
        "latest_tag": tag,
        "latest_version": TAG.fullmatch(tag).group("version"),
        "release_url": release.get("html_url", ""),
        "update_available": version_tuple(tag) > version_tuple(current),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--releases-json", type=Path, required=True)
    parser.add_argument("--state", type=Path, default=Path("printfins-fork.json"))
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    result = inspect(json.loads(args.releases_json.read_text(encoding="utf-8")),
                     json.loads(args.state.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            for key, value in result.items():
                output.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"upstream release check failed: {error}", file=sys.stderr)
        raise SystemExit(2)
