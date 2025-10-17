"""Tests for api_discovery_helper utilities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from adobe.cli import api_discovery_helper as helper


def _set_home(monkeypatch: pytest.MonkeyPatch, home_dir: Path) -> None:
    """Force Path.home() to point at a temporary directory."""

    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))


def _make_namespace() -> argparse.Namespace:
    return argparse.Namespace()


def test_template_creation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The template command should create the discovery file with required keys."""

    home_dir = tmp_path / "home"
    _set_home(monkeypatch, home_dir)

    project_file = tmp_path / "discovered_endpoints.json"
    monkeypatch.setattr(helper, "PROJECT_DISCOVERY_FILE", project_file)

    data = helper.ensure_template(project_file)

    assert project_file.is_file()
    assert set(data["endpoints"].keys()) == {"upload", "conversion", "status", "download"}
    assert data["status"] == "in_progress"


def test_update_syncs_to_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The update command should validate and sync discovery data into the user cache."""

    home_dir = tmp_path / "home"
    _set_home(monkeypatch, home_dir)

    project_file = tmp_path / "project_endpoints.json"
    monkeypatch.setattr(helper, "PROJECT_DISCOVERY_FILE", project_file)

    data = helper.ensure_template(project_file)
    for key, url in {
        "upload": "https://example.com/assets",
        "conversion": "https://example.com/assets/exportpdf",
        "status": "https://example.com/jobs/status",
        "download": "https://example.com/assets/download_uri",
    }.items():
        data["endpoints"][key]["url"] = url

    helper.write_json(project_file, data)

    helper.cmd_update(_make_namespace())

    project_payload = json.loads(project_file.read_text(encoding="utf-8"))
    home_payload = json.loads(helper.discovery_home_path().read_text(encoding="utf-8"))

    assert project_payload == home_payload
    assert project_payload["status"] == "captured"
    assert all(
        project_payload["endpoints"][key]["url"].startswith("http")
        for key in project_payload["endpoints"]
    )


def test_discovery_home_path_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Fallback cache directories should be used if the home cache is unavailable."""

    bad_path = tmp_path / "bad"
    bad_path.write_text("conflict")  # Occupies the path so mkdir fails
    good_dir = tmp_path / "good"

    monkeypatch.setattr(
        helper,
        "_candidate_cache_dirs",
        lambda: (bad_path, good_dir),
    )

    cache_file = helper.discovery_home_path()

    assert cache_file.parent == good_dir
