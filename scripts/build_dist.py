#!/usr/bin/env python3
"""Utility script for building and validating distribution artifacts."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATH = ROOT / "pdf_vision_processor" / "_version.py"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
EGG_INFO_DIR = ROOT / "pdf_vision_processor.egg-info"
VERSION_PATTERN = re.compile(r'__version__\s*=\s*"(?P<version>[^\"]+)"')


def read_version() -> str:
    match = VERSION_PATTERN.search(VERSION_PATH.read_text(encoding="utf-8"))
    if not match:  # pragma: no cover - defended by tests
        raise RuntimeError("Unable to locate __version__ in package __init__.py")
    return match.group("version")


def write_version(new_version: str) -> None:
    text = VERSION_PATH.read_text(encoding="utf-8")
    updated = VERSION_PATTERN.sub(f'__version__ = "{new_version}"', text)
    VERSION_PATH.write_text(updated, encoding="utf-8")


def bump_version(kind: str) -> str:
    major, minor, patch = (int(part) for part in read_version().split("."))
    if kind == "major":
        major += 1
        minor = 0
        patch = 0
    elif kind == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    new_version = f"{major}.{minor}.{patch}"
    write_version(new_version)
    return new_version


def clean_artifacts() -> None:
    for path in (DIST_DIR, BUILD_DIR, EGG_INFO_DIR):
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def run_command(args: Iterable[str]) -> None:
    subprocess.run(list(args), cwd=ROOT, check=True)


def build_distributions() -> None:
    run_command([sys.executable, "setup.py", "sdist", "bdist_wheel"])


def twine_check() -> None:
    artifacts = sorted(str(path) for path in DIST_DIR.glob("*"))
    if not artifacts:
        raise RuntimeError("No artifacts found in dist/; did the build step run?")
    run_command([sys.executable, "-m", "twine", "check", *artifacts])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and validate distribution artifacts")
    parser.add_argument("--bump", choices=("major", "minor", "patch"), help="Bump version before building")
    parser.add_argument("--skip-twine", action="store_true", help="Skip running 'twine check'")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.bump:
        new_version = bump_version(args.bump)
        print(f"Bumped version to {new_version}")

    clean_artifacts()
    build_distributions()

    if not args.skip_twine:
        twine_check()
        print("twine check completed successfully")

    print("Artifacts available under dist/:")
    for artifact in sorted(DIST_DIR.glob("*")):
        print(f" - {artifact.name}")


if __name__ == "__main__":  # pragma: no cover
    main()
