#!/usr/bin/env python3
"""Create a deterministic installable ZIP and SHA-256 checksum."""

from __future__ import annotations

import configparser
import hashlib
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "insar_timeseries_viewer"
DIST_DIR = REPO_ROOT / "dist"
FIXED_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def metadata_version() -> str:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")
    return parser["general"]["version"].strip()


def should_include(path: Path) -> bool:
    relative = path.relative_to(PLUGIN_DIR)
    return not any(part in EXCLUDED_PARTS for part in relative.parts) and path.suffix not in EXCLUDED_SUFFIXES


def main() -> int:
    version = metadata_version()
    DIST_DIR.mkdir(exist_ok=True)
    archive = DIST_DIR / f"insar_timeseries_viewer-{version}.zip"
    checksum = archive.with_suffix(archive.suffix + ".sha256")

    files = sorted(path for path in PLUGIN_DIR.rglob("*") if path.is_file() and should_include(path))
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            arcname = Path(PLUGIN_DIR.name) / path.relative_to(PLUGIN_DIR)
            info = zipfile.ZipInfo(arcname.as_posix(), date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, path.read_bytes())

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(archive)
    print(checksum)
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
