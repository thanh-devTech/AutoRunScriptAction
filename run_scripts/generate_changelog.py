#!/usr/bin/env python3
"""Generate a filtered WordPress-style changelog from git history."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

PLUGIN_FILE = "plug.php"
DEFAULT_OUTPUT = "log.txt"
MIN_VERSION = "1.0.0"
MIN_DATE = "2026-03-27"

VERSION_LINE_RE = re.compile(r"^\+Version:\s*([0-9][0-9A-Za-z._-]*)\s*$")
VERSION_ONLY_RE = re.compile(r"^v?\d+(?:\.\d+)+(?:\.\d+)?$", re.IGNORECASE)
LEADING_VERSION_RE = re.compile(r"^\s*v?\d+(?:\.\d+)+(?:\.\d+)?\s*[-:]?\s*", re.IGNORECASE)
TYPE_PREFIX_RE = re.compile(
    r"^(fix(?:ed)?|hotfix|bugfix|bug|add(?:ed)?|new|create(?:d)?|feat(?:ure)?|"
    r"update(?:d)?|change(?:d)?|remove(?:d)?|refactor(?:ed)?|rename(?:d)?|"
    r"move(?:d)?|sync|improve(?:d)?|optimi[sz]e(?:d)?|revert)\b[\s:._-]*",
    re.IGNORECASE,
)


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def version_key(version: str) -> tuple[tuple[int, object], ...]:
    parts: list[tuple[int, object]] = []
    for part in re.split(r"[.-]", version):
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part.lower()))
    return tuple(parts)


def parse_release_date(value: str) -> date:
    return date.fromisoformat(value)


def get_release_boundaries() -> list[dict[str, str]]:
    output = run_git(
        "log",
        "--follow",
        "-p",
        "--reverse",
        "--date=short",
        "--format=__COMMIT__%n%H\t%ad\t%s",
        "--",
        PLUGIN_FILE,
    )

    releases: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    saw_version_in_commit = False

    for raw_line in output.splitlines():
        line = raw_line.rstrip("\n")
        if line == "__COMMIT__":
            current = None
            saw_version_in_commit = False
            continue

        if current is None:
            parts = line.split("\t", 2)
            if len(parts) == 3:
                current = {"hash": parts[0], "date": parts[1], "subject": parts[2]}
            continue

        if saw_version_in_commit:
            continue

        match = VERSION_LINE_RE.match(line)
        if not match:
            continue

        releases.append(
            {
                "hash": current["hash"],
                "date": current["date"],
                "subject": current["subject"],
                "version": match.group(1),
            }
        )
        saw_version_in_commit = True

    return releases


def get_reachable_order() -> list[str]:
    output = run_git("rev-list", "--reverse", "--topo-order", "HEAD")
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_releases_from_tags() -> list[dict[str, str]]:
    """Fallback: Get releases from git tags (v*.*.*)"""
    try:
        output = run_git("tag", "-l", "v*", "--format=%(refname:short)%09%(creatordate:short)%09%(subject)")
        releases: list[dict[str, str]] = []
        
        for line in output.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t", 2)
            if len(parts) >= 2:
                tag = parts[0]
                date = parts[1] if len(parts) > 1 else "2026-01-01"
                version = tag.lstrip("v")
                
                try:
                    hash_output = run_git("rev-list", "-n", "1", tag)
                    commit_hash = hash_output.strip()
                    releases.append({
                        "hash": commit_hash,
                        "date": date,
                        "subject": f"Release {version}",
                        "version": version,
                    })
                except RuntimeError:
                    continue
        
        return releases
    except RuntimeError:
        return []


def subject_type(subject: str) -> str:
    lowered = subject.strip().lower()
    if re.match(r"^(fix|fixed|hotfix|bugfix|bug)\b", lowered):
        return "Fix"
    if re.match(r"^(add|added|new|create|created|feat|feature|implement|enable)\b", lowered):
        return "Add"
    if re.match(r"^(update|updated|change|changed|remove|removed|refactor|rename|move|sync)\b", lowered):
        return "Update"
    if re.match(r"^(improve|improved|optimi[sz]e|optimized|tweak|cleanup|revert)\b", lowered):
        return "Tweak"
    return "Update"


def normalize_subject(subject: str, version: str) -> str | None:
    text = subject.strip()
    if not text:
        return None

    if VERSION_ONLY_RE.fullmatch(text):
        return None

    text = LEADING_VERSION_RE.sub("", text).strip()
    if not text or text == version:
        return None

    if text.lower().startswith("merge branch ") or text.lower().startswith("merge remote-tracking "):
        return None

    text = TYPE_PREFIX_RE.sub("", text).strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" -._")
    if not text:
        return None

    return text[0].upper() + text[1:]


def get_commits_for_release(previous_hash: str | None, current_hash: str) -> list[tuple[str, str]]:
    if previous_hash:
        rev_range = f"{previous_hash}..{current_hash}"
        args = ["log", "--reverse", "--no-merges", "--format=%H\t%s", rev_range]
    else:
        args = ["log", "--reverse", "--no-merges", "--format=%H\t%s", current_hash]

    output = run_git(*args)
    commits: list[tuple[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        commit_hash, _, subject = line.partition("\t")
        commits.append((commit_hash, subject.strip()))
    return commits


def build_changelog(selected_releases: list[tuple[dict[str, str], str | None]]) -> str:
    blocks: list[str] = []

    for release, previous_hash in selected_releases:
        bullets: list[str] = []
        seen: set[str] = set()

        for _, subject in get_commits_for_release(previous_hash, release["hash"]):
            cleaned = normalize_subject(subject, release["version"])
            if not cleaned:
                continue

            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)

            bullet_type = subject_type(subject)
            if cleaned[-1] not in ".!?":
                cleaned += "."
            bullets.append(f"* {bullet_type} - {cleaned}")

        if not bullets:
            bullets.append("* Update - Internal maintenance.")

        blocks.append(f"= {release['version']} - {release['date']} =\n" + "\n".join(bullets))

    return "\n\n".join(reversed(blocks)) + ("\n" if blocks else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output file name inside plugin root (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    # Try to get releases from Version: changes first
    releases = get_release_boundaries()
    fallback_tags = False
    
    if not releases:
        print("⚠️  No release boundaries found from Version: changes in plug.php, trying git tags...", file=sys.stderr)
        releases = get_releases_from_tags()
        fallback_tags = True
        
        if not releases:
            print("❌ No releases found from Version: changes or git tags", file=sys.stderr)
            return 1
        print(f"✅ Found {len(releases)} releases from git tags", file=sys.stderr)

    reachable_order = get_reachable_order()
    reachable_index = {commit_hash: index for index, commit_hash in enumerate(reachable_order)}
    releases = [release for release in releases if release["hash"] in reachable_index]
    releases.sort(key=lambda release: reachable_index[release["hash"]])

    unique_releases: list[dict[str, str]] = []
    seen_versions: set[str] = set()
    for release in releases:
        if release["version"] in seen_versions:
            continue
        seen_versions.add(release["version"])
        unique_releases.append(release)
    releases = unique_releases

    if not releases:
        print("❌ No release boundaries found on the current branch history", file=sys.stderr)
        return 1

    min_date = parse_release_date(MIN_DATE)
    selected_releases: list[tuple[dict[str, str], str | None]] = []

    for index, release in enumerate(releases):
        if version_key(release["version"]) <= version_key(MIN_VERSION):
            continue
        if parse_release_date(release["date"]) <= min_date:
            continue

        previous_hash = releases[index - 1]["hash"] if index > 0 else None
        selected_releases.append((release, previous_hash))

    if not selected_releases:
        print(f"⚠️  No releases matching filters (version > {MIN_VERSION}, date > {MIN_DATE})", file=sys.stderr)
        output_path = REPO_ROOT / args.output
        output_path.write_text("", encoding="utf-8")
        return 0

    content = build_changelog(selected_releases)
    output_path = REPO_ROOT / args.output
    output_path.write_text(content, encoding="utf-8")
    print(
        f"✅ Wrote {len(selected_releases)} releases to {output_path} "
        f"(version > {MIN_VERSION}, date > {MIN_DATE})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
