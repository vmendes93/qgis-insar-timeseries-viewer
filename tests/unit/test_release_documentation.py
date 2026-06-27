# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Release documentation consistency checks."""

from __future__ import annotations

import configparser
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPOSITORY_ROOT / "insar_timeseries_viewer"


def _metadata():
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")
    return parser["general"]


def test_current_release_version_is_documented():
    metadata = _metadata()
    version = metadata["version"]

    changelog = (PLUGIN_DIR / "CHANGELOG.md").read_text(encoding="utf-8")
    checklist = (PLUGIN_DIR / "VALIDATION_CHECKLIST.md").read_text(encoding="utf-8")
    release_doc = (REPOSITORY_ROOT / "docs" / "RELEASE_1_1_0.md").read_text(
        encoding="utf-8"
    )

    assert version == "1.1.0"
    assert f"## [{version}]" in changelog
    assert f"v{version}" in checklist
    assert f"Release {version}" in release_doc
    assert metadata["changelog"].startswith(f"{version} -")


def test_user_facing_docs_cover_current_major_features():
    readme = (PLUGIN_DIR / "README.md").read_text(encoding="utf-8")
    checklist = (PLUGIN_DIR / "VALIDATION_CHECKLIST.md").read_text(encoding="utf-8")
    release_doc = (REPOSITORY_ROOT / "docs" / "RELEASE_1_1_0.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((readme, checklist, release_doc)).casefold()

    required_terms = [
        "manual field mapping",
        "click-to-plot",
        "csv",
        "active-layer",
        "polygon means",
        "warning-free",
    ]

    for term in required_terms:
        assert term in combined
