#!/usr/bin/env python3
"""Validate repository and installable QGIS plugin release structure."""

from __future__ import annotations

import configparser
import py_compile
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "insar_timeseries_viewer"

REQUIRED_FILES = {
    "__init__.py",
    "metadata.txt",
    "LICENSE",
    "README.md",
    "icon.png",
    "index.html",
}
REQUIRED_METADATA = {
    "name",
    "qgisMinimumVersion",
    "description",
    "about",
    "version",
    "author",
    "email",
    "repository",
    "tracker",
    "homepage",
}
BANNED_TEXT = {
    "tre altamira",
    "tre-altamira",
    "vinicius.mendes@tre-altamira.com",
    "logo_tre_ats",
    "internal_use_notice",
    "internal_distribution",
}
BINARY_SUFFIXES = {".dll", ".exe", ".pyd", ".so", ".dylib"}
ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"/(?:home|Users|mnt|opt|srv)/[^\s`\"']+"),
    re.compile(r"\b[A-Za-z]:\\[^\s`\"']+"),
)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    tracked_files: set[Path] = set()
    if (REPO_ROOT / ".git").exists():
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        )
        tracked_files = {Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item}

    if not PLUGIN_DIR.is_dir():
        fail(f"plugin directory not found: {PLUGIN_DIR}")

    missing = sorted(name for name in REQUIRED_FILES if not (PLUGIN_DIR / name).exists())
    if missing:
        fail(f"missing required plugin files: {', '.join(missing)}")

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", PLUGIN_DIR.name):
        fail(f"invalid plugin directory name: {PLUGIN_DIR.name}")

    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")
    if "general" not in parser:
        fail("metadata.txt is missing the [general] section")

    metadata = parser["general"]
    missing_metadata = sorted(key for key in REQUIRED_METADATA if not metadata.get(key, "").strip())
    if missing_metadata:
        fail(f"missing metadata fields: {', '.join(missing_metadata)}")

    for key in ("repository", "tracker", "homepage"):
        if not metadata[key].startswith("https://"):
            fail(f"metadata field {key} must use HTTPS")

    if metadata.get("version") != "1.0.0":
        fail("metadata version must match the prepared public release version 1.0.0")

    for path in sorted(REPO_ROOT.rglob("*")):
        if any(part in {".git", ".venv", "dist", "build"} for part in path.parts):
            continue
        relative = path.relative_to(REPO_ROOT)
        if path.is_dir():
            if path.name == "__pycache__" and relative in tracked_files:
                fail(f"generated directory is tracked: {relative}")
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            fail(f"binary file found: {relative}")
        if path.suffix.lower() in {".pyc", ".pyo"}:
            if relative in tracked_files:
                fail(f"compiled Python file is tracked: {relative}")
            continue

        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lower = text.casefold()
        if path.resolve() != Path(__file__).resolve():
            for banned in BANNED_TEXT:
                if banned in lower:
                    fail(f"banned reference {banned!r} found in {path.relative_to(REPO_ROOT)}")

        if path.name != "LICENSE":
            for pattern in ABSOLUTE_PATH_PATTERNS:
                match = pattern.search(text)
                if match:
                    fail(
                        f"absolute local path {match.group(0)!r} found in "
                        f"{path.relative_to(REPO_ROOT)}"
                    )

    for path in sorted(PLUGIN_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "SPDX-License-Identifier: GPL-2.0-or-later" not in source[:300]:
            fail(f"missing SPDX identifier in {path.name}")
        py_compile.compile(str(path), doraise=True)

    print("Release validation passed.")
    print(f"Plugin: {metadata['name']} {metadata['version']}")
    print(f"Directory: {PLUGIN_DIR.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
