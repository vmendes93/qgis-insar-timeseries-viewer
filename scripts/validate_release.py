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

VERSION_PATTERN = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+"
    r"(?:-[0-9A-Za-z.-]+)?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)

REQUIRED_FILES = {
    "__init__.py",
    "metadata.txt",
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
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
    "changelog",
}

BANNED_TEXT = {
    "tre altamira",
    "tre-altamira",
    "vinicius.mendes@tre-altamira.com",
    "logo_tre_ats",
    "internal_use_notice",
    "internal_distribution",
}

BINARY_SUFFIXES = {
    ".dll",
    ".exe",
    ".pyd",
    ".so",
    ".dylib",
}

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dist",
    "build",
}

ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"/(?:home|Users|mnt|opt|srv)/[^\s`\"']+"),
    re.compile(r"\b[A-Za-z]:\\[^\s`\"']+"),
)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def path_is_ignored(path: Path) -> bool:
    for part in path.parts:
        if part in IGNORED_DIRECTORY_NAMES:
            return True
        if part == ".venv" or part.startswith(".venv-"):
            return True
    return False


def read_metadata() -> configparser.SectionProxy:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")

    if "general" not in parser:
        fail("metadata.txt is missing the [general] section")

    return parser["general"]


def validate_metadata(metadata: configparser.SectionProxy) -> str:
    missing_metadata = sorted(
        key
        for key in REQUIRED_METADATA
        if not metadata.get(key, "").strip()
    )

    if missing_metadata:
        fail(
            "missing metadata fields: "
            + ", ".join(missing_metadata)
        )

    for key in ("repository", "tracker", "homepage"):
        if not metadata[key].startswith("https://"):
            fail(f"metadata field {key} must use HTTPS")

    version = metadata["version"].strip()

    if not VERSION_PATTERN.fullmatch(version):
        fail(
            "metadata version must use semantic versioning, "
            f"for example 1.0.1: {version!r}"
        )

    metadata_changelog = metadata["changelog"].strip()

    if not metadata_changelog.startswith(f"{version} -"):
        fail(
            "metadata changelog must begin with the current version "
            f"{version!r}"
        )

    changelog_path = PLUGIN_DIR / "CHANGELOG.md"
    changelog_text = changelog_path.read_text(encoding="utf-8")

    release_heading = re.compile(
        rf"^## \[{re.escape(version)}\](?:\s|$)",
        flags=re.MULTILINE,
    )

    if not release_heading.search(changelog_text):
        fail(
            "CHANGELOG.md is missing a release section for "
            f"version {version}"
        )

    return version


def tracked_repository_files() -> set[Path]:
    if not (REPO_ROOT / ".git").exists():
        return set()

    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )

    return {
        Path(item.decode("utf-8"))
        for item in result.stdout.split(b"\0")
        if item
    }


def validate_repository_files(tracked_files: set[Path]) -> None:
    for path in sorted(REPO_ROOT.rglob("*")):
        relative = path.relative_to(REPO_ROOT)

        if path_is_ignored(relative):
            continue

        if path.is_dir():
            if path.name == "__pycache__":
                prefix = relative.as_posix().rstrip("/") + "/"

                if any(
                    tracked.as_posix().startswith(prefix)
                    for tracked in tracked_files
                ):
                    fail(
                        f"generated directory is tracked: {relative}"
                    )

            continue

        suffix = path.suffix.lower()

        if suffix in BINARY_SUFFIXES:
            fail(f"binary file found: {relative}")

        if suffix in {".pyc", ".pyo"}:
            if relative in tracked_files:
                fail(
                    f"compiled Python file is tracked: {relative}"
                )
            continue

        if suffix in {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".zip",
        }:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lower = text.casefold()

        if path.resolve() != Path(__file__).resolve():
            for banned in BANNED_TEXT:
                if banned in lower:
                    fail(
                        f"banned reference {banned!r} found in "
                        f"{relative}"
                    )

        if path.name != "LICENSE":
            for pattern in ABSOLUTE_PATH_PATTERNS:
                match = pattern.search(text)

                if match:
                    fail(
                        f"absolute local path {match.group(0)!r} "
                        f"found in {relative}"
                    )


def validate_python_files() -> None:
    for path in sorted(PLUGIN_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")

        if (
            "SPDX-License-Identifier: GPL-2.0-or-later"
            not in source[:300]
        ):
            fail(
                f"missing SPDX identifier in {path.name}"
            )

        py_compile.compile(str(path), doraise=True)


def main() -> int:
    if not PLUGIN_DIR.is_dir():
        fail(f"plugin directory not found: {PLUGIN_DIR}")

    missing_files = sorted(
        name
        for name in REQUIRED_FILES
        if not (PLUGIN_DIR / name).exists()
    )

    if missing_files:
        fail(
            "missing required plugin files: "
            + ", ".join(missing_files)
        )

    if not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_-]*",
        PLUGIN_DIR.name,
    ):
        fail(
            f"invalid plugin directory name: {PLUGIN_DIR.name}"
        )

    metadata = read_metadata()
    version = validate_metadata(metadata)

    tracked_files = tracked_repository_files()

    validate_repository_files(tracked_files)
    validate_python_files()

    print("Release validation passed.")
    print(f"Plugin: {metadata['name']} {version}")
    print(f"Directory: {PLUGIN_DIR.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
