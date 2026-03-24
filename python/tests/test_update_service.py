import json
import zipfile

from core.update_service import (
    ReleaseInfo,
    build_update_status,
    ensure_update_supported_install,
    extract_release_payload,
    is_newer_version,
)


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_is_newer_version_handles_simple_semver():
    assert is_newer_version("0.0.1", "0.0.2") is True
    assert is_newer_version("0.0.2", "0.0.2") is False
    assert is_newer_version("0.1.0", "0.0.9") is False


def test_ensure_update_supported_install_rejects_git_checkout(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "pyproject.toml").write_text('version = "0.0.1"\n', encoding="utf-8")
    (tmp_path / "START 啟動.bat").write_text("@echo off\n", encoding="utf-8")

    ok, reason = ensure_update_supported_install(tmp_path)

    assert ok is False
    assert "git" in reason.lower()


def test_build_update_status_marks_update_available(tmp_path):
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    (python_dir / "pyproject.toml").write_text(
        '[project]\nversion = "0.0.1"\n',
        encoding="utf-8",
    )
    (tmp_path / "START 啟動.bat").write_text("@echo off\n", encoding="utf-8")

    payload = json.dumps(
        {
            "tag_name": "v0.0.2",
            "name": "v0.0.2",
            "html_url": "https://example.com/release",
            "zipball_url": "https://example.com/release.zip",
            "published_at": "2026-03-24T00:00:00Z",
        }
    ).encode("utf-8")

    status = build_update_status(
        app_root=tmp_path,
        python_base_dir=python_dir,
        opener=lambda *_args, **_kwargs: _FakeResponse(payload),
    )

    assert status.current_version == "0.0.1"
    assert status.latest_version == "0.0.2"
    assert status.update_available is True
    assert status.install_supported is True
    assert status.release == ReleaseInfo(
        tag_name="v0.0.2",
        name="v0.0.2",
        html_url="https://example.com/release",
        zipball_url="https://example.com/release.zip",
        published_at="2026-03-24T00:00:00Z",
    )


def test_extract_release_payload_finds_project_root(tmp_path):
    zip_path = tmp_path / "release.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("totalseg-muscle-tool-main/python/pyproject.toml", '[project]\nversion = "0.0.2"\n')
        archive.writestr("totalseg-muscle-tool-main/START 啟動.bat", "@echo off\n")

    payload_root = extract_release_payload(zip_path, tmp_path / "extract")

    assert payload_root.name == "totalseg-muscle-tool-main"
    assert (payload_root / "python" / "pyproject.toml").exists()
