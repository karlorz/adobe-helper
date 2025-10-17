"""Utility helpers for managing Adobe Helper API discovery data.

This module keeps `docs/discovery/discovered_endpoints.json` and the per-user
cache under `~/.adobe-helper/discovered_endpoints.json` in sync. It also helps
validate captured endpoints and bootstrap new templates.

Usage examples::

    python -m adobe.cli.api_discovery_helper --help
    python -m adobe.cli.api_discovery_helper checklist
    python -m adobe.cli.api_discovery_helper template
    python -m adobe.cli.api_discovery_helper update

When installed, the entry point `adobe-api-discovery` exposes the same commands.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from adobe.constants import DEFAULT_SESSION_DIR

PROJECT_DISCOVERY_FILE = Path("docs/discovery/discovered_endpoints.json")


def _candidate_cache_dirs() -> tuple[Path, ...]:
    """Return candidate directories for storing discovery cache files."""

    return (
        Path.home() / DEFAULT_SESSION_DIR,
        Path.cwd() / DEFAULT_SESSION_DIR,
        Path(tempfile.gettempdir()) / DEFAULT_SESSION_DIR,
    )


def discovery_home_path() -> Path:
    """Return the path to the per-user discovery cache file."""

    errors: list[tuple[Path, Exception]] = []

    for candidate in _candidate_cache_dirs():
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            errors.append((candidate, exc))
            continue

        cache_file = candidate / "discovered_endpoints.json"
        try:
            cache_file.touch(exist_ok=True)
        except OSError as exc:
            errors.append((cache_file, exc))
            continue

        return cache_file

    error_summary = ", ".join(f"{path}: {exc}" for path, exc in errors)
    raise SystemExit(
        "Unable to create a writable discovery cache. "
        "Inspect permissions or set ADOBE_HELPER_ENDPOINTS_FILE."
        + (f" Errors: {error_summary}" if error_summary else "")
    )


def load_json(path: Path) -> dict[str, Any]:
    """Load JSON data from *path*, returning an empty mapping on failure."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:  # pragma: no cover - protects CLI users
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise SystemExit(f"Discovery file {path} must contain a JSON object at the top level")

    return cast(dict[str, Any], raw)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON data to disk with stable formatting."""

    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_template(path: Path) -> dict[str, Any]:
    """Create a discovery template unless the file already exists."""

    if path.exists():
        print(f"ℹ️  Discovery file already exists: {path}")
        return load_json(path)

    template = {
        "discovery_date": datetime.now().isoformat(),
        "status": "in_progress",
        "endpoints": {
            "upload": {
                "url": "",
                "method": "POST",
                "headers": {},
                "payload_type": "multipart/form-data",
                "response_fields": [],
                "notes": "Large POST request containing the PDF bytes",
            },
            "conversion": {
                "url": "",
                "method": "POST",
                "headers": {},
                "payload_example": {},
                "response_fields": [],
                "notes": "Follow-up POST that starts the export job",
            },
            "status": {
                "url": "",
                "method": "GET",
                "headers": {},
                "polling_interval": "~2 seconds",
                "response_fields": [],
                "notes": "Repeated GET request that polls job status",
            },
            "download": {
                "url": "",
                "method": "GET",
                "headers": {},
                "response_fields": [],
                "notes": "Endpoint returning the signed download URI",
            },
        },
        "instructions": [
            "1. Open: https://www.adobe.com/acrobat/online/pdf-to-word.html",
            "2. Press F12 (Chrome DevTools)",
            "3. Go to Network tab",
            "4. Check 'Preserve log'",
            "5. Filter: Only 'Fetch/XHR'",
            "6. Upload a small PDF",
            "7. Document the endpoints below",
            "8. Run: python -m adobe.cli.api_discovery_helper update",
        ],
    }

    write_json(path, template)
    print(f"✅ Created API discovery template at {path}")
    return template


def validate_endpoints(data: dict[str, Any]) -> bool:
    """Return True when all endpoint URLs look valid, printing a summary."""

    endpoints = data.get("endpoints")
    if not isinstance(endpoints, dict):
        print("❌ Discovery file is missing the 'endpoints' mapping")
        return False

    print("\n🔍 Validating discovered endpoints\n")
    all_valid = True

    for key in ("upload", "conversion", "status", "download"):
        entry = endpoints.get(key, {}) if isinstance(endpoints, dict) else {}
        url = entry.get("url") if isinstance(entry, dict) else None

        if not isinstance(url, str) or not url.strip():
            print(f"❌ {key.title()}: missing URL")
            all_valid = False
            continue

        url_text = url.strip()
        if not url_text.startswith("http"):
            print(f"⚠️  {key.title()}: invalid URL ({url_text})")
            all_valid = False
            continue

        print(f"✅ {key.title()}: {url_text}")

    data["status"] = "captured" if all_valid else data.get("status", "in_progress")
    data["discovery_date"] = datetime.now().isoformat()

    return all_valid


def sync_discovery_files(data: dict[str, Any]) -> None:
    """Persist discovery data to both the project file and the per-user cache."""

    if not PROJECT_DISCOVERY_FILE.parent.exists():
        PROJECT_DISCOVERY_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        write_json(PROJECT_DISCOVERY_FILE, data)
    except OSError as exc:  # pragma: no cover - filesystem edge case
        print(f"⚠️  Failed to write project discovery file {PROJECT_DISCOVERY_FILE}: {exc}")
    else:
        print(f"📦 Updated project discovery file: {PROJECT_DISCOVERY_FILE}")

    home_file = discovery_home_path()
    try:
        write_json(home_file, data)
    except OSError as exc:  # pragma: no cover - permission issues (e.g., sandbox)
        print(
            "⚠️  Could not update user discovery cache. "
            "Set ADOBE_HELPER_ENDPOINTS_FILE or run with sufficient permissions."
        )
        print(f"    Details: {exc}")
    else:
        print(f"🏠 Updated user cache discovery file: {home_file}")


def print_checklist() -> None:
    """Display a step-by-step checklist for capturing endpoints."""

    checklist = "\n".join(
        [
            "════════════════════════════════════════════════════════════════",
            " API DISCOVERY CHECKLIST",
            "────────────────────────────────────────────────────────────────",
            "SETUP",
            "  • Open Chrome and browse to the Adobe PDF-to-Word page",
            "  • Open DevTools (F12 / Cmd+Option+I)",
            "  • Network tab → enable 'Preserve log' and filter Fetch/XHR",
            "UPLOAD",
            "  • Select a small PDF and wait for conversion to finish",
            "CAPTURE",
            "  • Upload endpoint: large POST with your PDF bytes",
            "  • Conversion endpoint: follow-up POST returning job URI",
            "  • Status endpoint: repeating GET polling job status",
            "  • Download endpoint: GET that yields signed download URI",
            "DOCUMENT",
            "  • Fill the URLs into docs/discovery/discovered_endpoints.json",
            "  • Run 'python -m adobe.cli.api_discovery_helper update'",
            "  • Execute a test conversion to confirm everything works",
            "════════════════════════════════════════════════════════════════",
        ]
    )

    print(checklist)


def cmd_template(_: argparse.Namespace) -> None:
    ensure_template(PROJECT_DISCOVERY_FILE)


def cmd_update(_: argparse.Namespace) -> None:
    if not PROJECT_DISCOVERY_FILE.exists():
        print("⚠️  No discovery file found. Creating a template…")
        data = ensure_template(PROJECT_DISCOVERY_FILE)
    else:
        data = load_json(PROJECT_DISCOVERY_FILE)

    validate_endpoints(data)
    sync_discovery_files(data)


def cmd_validate(_: argparse.Namespace) -> None:
    if not PROJECT_DISCOVERY_FILE.exists():
        raise SystemExit(
            "No discovery file found. Run 'python -m adobe.cli.api_discovery_helper template' first."
        )

    data = load_json(PROJECT_DISCOVERY_FILE)
    all_good = validate_endpoints(data)
    sync_discovery_files(data)
    if not all_good:
        raise SystemExit(1)


def cmd_checklist(_: argparse.Namespace) -> None:
    print_checklist()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Adobe Helper API discovery data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("template", help="Create a discovery template if missing").set_defaults(
        func=cmd_template
    )

    subparsers.add_parser("update", help="Validate captured URLs and sync caches").set_defaults(
        func=cmd_update
    )

    subparsers.add_parser(
        "validate", help="Validate URLs, sync caches, and fail on errors"
    ).set_defaults(func=cmd_validate)

    subparsers.add_parser("checklist", help="Show the endpoint discovery checklist").set_defaults(
        func=cmd_checklist
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
