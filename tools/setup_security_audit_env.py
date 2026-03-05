#!/usr/bin/env python3
"""Set up local Python environment for security audit tooling.

Usage:
  python3 tools/setup_security_audit_env.py
  python3 tools/setup_security_audit_env.py --venv .venv-security-audit
  python3 tools/setup_security_audit_env.py --verify-only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REQUIREMENTS_PATH = Path("tools/security_audit/requirements.txt")
DEFAULT_VENV_PATH = Path(".venv-security-audit")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or verify a local venv with security audit dependencies."
    )
    parser.add_argument(
        "--venv",
        default=str(DEFAULT_VENV_PATH),
        help="Virtual environment path (default: .venv-security-audit)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Skip creation/install and only run verification output.",
    )
    return parser.parse_args()


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        if error.stdout.strip():
            print(error.stdout.strip())
        if error.stderr.strip():
            print(error.stderr.strip(), file=sys.stderr)
        raise


def get_venv_python(venv_path: Path) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def create_venv_if_missing(venv_path: Path) -> None:
    if venv_path.exists():
        return
    print(f"Creating virtual environment at {venv_path}...")
    run_command([sys.executable, "-m", "venv", str(venv_path)])


def install_requirements(venv_python: Path) -> None:
    print("Upgrading pip...")
    run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])

    print(f"Installing requirements from {REQUIREMENTS_PATH}...")
    run_command([str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)])


def parse_required_packages() -> list[str]:
    packages: list[str] = []
    for raw_line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        packages.append(line.split("==", maxsplit=1)[0].strip().lower())
    return packages


def verify_with_pip_freeze(venv_python: Path) -> int:
    required_names = set(parse_required_packages())
    freeze_result = run_command([str(venv_python), "-m", "pip", "freeze"])

    installed_by_name: dict[str, str] = {}
    for raw_line in freeze_result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        name, version = line.split("==", maxsplit=1)
        installed_by_name[name.lower()] = version

    missing = sorted(required_names.difference(installed_by_name.keys()))
    if missing:
        print(
            "Missing required packages after installation: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2

    print("Required packages present (from pip freeze):")
    for package_name in sorted(required_names):
        print(f"- {package_name}=={installed_by_name[package_name]}")
    return 0


def main() -> int:
    args = parse_args()
    if not REQUIREMENTS_PATH.exists():
        print(f"Requirements file not found: {REQUIREMENTS_PATH}", file=sys.stderr)
        return 1

    venv_path = Path(args.venv)
    venv_python = get_venv_python(venv_path)

    if not args.verify_only:
        create_venv_if_missing(venv_path)
        if not venv_python.exists():
            print(f"Virtualenv Python executable not found at {venv_python}", file=sys.stderr)
            return 1
        install_requirements(venv_python)
    elif not venv_python.exists():
        print(
            f"Cannot verify because virtualenv Python does not exist: {venv_python}",
            file=sys.stderr,
        )
        return 1

    return verify_with_pip_freeze(venv_python)


if __name__ == "__main__":
    raise SystemExit(main())
