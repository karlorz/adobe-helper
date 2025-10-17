"""Tests for endpoint discovery and configuration utilities."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adobe import urls
from adobe.constants import DEFAULT_SESSION_DIR


def _set_home(monkeypatch: pytest.MonkeyPatch, home_dir: Path) -> None:
    """Force pathlib.Path.home() to return a temporary directory during tests."""

    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))


def test_get_api_endpoints_uses_discovery_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Endpoints from the discovery JSON file should override placeholders and be cached."""

    home_dir = tmp_path / "home"
    _set_home(monkeypatch, home_dir)

    sample_endpoints = {
        "upload": "https://pdfnow.test-region.adobe.io/tenant/assets",
        "conversion": "https://pdfnow.test-region.adobe.io/tenant/assets/exportpdf",
        "status": "https://pdfnow.test-region.adobe.io/tenant/jobs/status",
        "download": "https://pdfnow.test-region.adobe.io/tenant/assets/download_uri",
    }

    discovery_payload = {
        "discovery_date": "2024-10-01T00:00:00",
        "status": "captured",
        "endpoints": {key: {"url": value} for key, value in sample_endpoints.items()},
        "instructions": list(urls._DISCOVERY_INSTRUCTIONS),  # type: ignore[attr-defined]
    }

    discovery_file = tmp_path / "custom_discovered_endpoints.json"
    discovery_file.write_text(json.dumps(discovery_payload), encoding="utf-8")
    monkeypatch.setenv("ADOBE_HELPER_ENDPOINTS_FILE", str(discovery_file))

    endpoints = urls.get_api_endpoints()

    assert endpoints == sample_endpoints

    cached_path = home_dir / DEFAULT_SESSION_DIR / urls._DISCOVERY_FILENAME  # type: ignore[attr-defined]
    assert cached_path.is_file()
    cached_payload = json.loads(cached_path.read_text(encoding="utf-8"))
    assert cached_payload == discovery_payload


def test_get_api_endpoints_generates_template_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When no discovery data exists, a template file should be generated with placeholders."""

    home_dir = tmp_path / "home"
    _set_home(monkeypatch, home_dir)

    monkeypatch.setattr(
        urls, "_candidate_endpoint_files", lambda config_path=None: [tmp_path / "missing.json"]
    )

    endpoints = urls.get_api_endpoints()

    assert endpoints["upload"] == urls.API_UPLOAD
    assert endpoints["conversion"] == urls.API_CONVERT
    assert endpoints["status"] == urls.API_STATUS
    assert endpoints["download"] == urls.API_DOWNLOAD

    template_path = home_dir / DEFAULT_SESSION_DIR / urls._DISCOVERY_FILENAME  # type: ignore[attr-defined]
    assert template_path.is_file()

    template_payload = json.loads(template_path.read_text(encoding="utf-8"))
    assert template_payload["status"] == "template"
    for key in ("upload", "conversion", "status", "download"):
        entry = template_payload["endpoints"][key]
        assert entry["url"] == ""
    assert template_payload["instructions"]
