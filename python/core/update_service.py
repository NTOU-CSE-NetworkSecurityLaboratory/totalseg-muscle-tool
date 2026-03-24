from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

from core.app_version import read_local_app_version

RELEASES_PAGE_URL = "https://github.com/NTOU-CSE-NetworkSecurityLaboratory/totalseg-muscle-tool/releases"
LATEST_RELEASE_API_URL = (
    "https://api.github.com/repos/NTOU-CSE-NetworkSecurityLaboratory/totalseg-muscle-tool/releases/latest"
)
_UPDATE_RUNNER_NAME = "totalseg_release_updater.py"
_UPDATE_LOG_DIR_NAME = "totalseg_update_logs"
_SKIP_NAMES = {
    ".git",
    ".pytest_cache",
    ".pytest-tmp",
    ".ruff_cache",
    ".uv-cache",
    ".venv",
    "__pycache__",
}


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    name: str
    html_url: str
    zipball_url: str
    published_at: str


@dataclass(frozen=True)
class UpdateStatus:
    current_version: str
    latest_version: str | None
    update_available: bool
    install_supported: bool
    install_block_reason: str | None
    release_page_url: str
    release: ReleaseInfo | None


def _normalize_version(version: str | None) -> tuple:
    if not version:
        return tuple()
    text = str(version).strip().lstrip("vV")
    if not text:
        return tuple()

    parts: list[int | str] = []
    for token in text.replace("-", ".").split("."):
        if token.isdigit():
            parts.append(int(token))
        elif token:
            parts.append(token.lower())
    return tuple(parts)


def is_newer_version(current_version: str, latest_version: str) -> bool:
    current = _normalize_version(current_version)
    latest = _normalize_version(latest_version)
    if current and latest:
        return latest > current
    return str(latest_version).strip() != str(current_version).strip()


def ensure_update_supported_install(app_root: str | Path) -> tuple[bool, str | None]:
    app_root = Path(app_root).resolve()
    if (app_root / ".git").exists():
        return False, "GUI 更新器不支援直接覆蓋開發中的 git 工作目錄。"
    if not (app_root / "python" / "pyproject.toml").exists():
        return False, "找不到 python/pyproject.toml，無法辨識為可更新的部署資料夾。"
    if not (app_root / "START 啟動.bat").exists():
        return False, "找不到 START 啟動.bat，無法辨識為標準 Windows 部署資料夾。"
    return True, None


def fetch_latest_release(*, api_url: str = LATEST_RELEASE_API_URL, opener=urlopen) -> ReleaseInfo:
    with opener(api_url, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return ReleaseInfo(
        tag_name=str(payload["tag_name"]),
        name=str(payload.get("name") or payload["tag_name"]),
        html_url=str(payload["html_url"]),
        zipball_url=str(payload["zipball_url"]),
        published_at=str(payload.get("published_at") or ""),
    )


def build_update_status(
    *,
    app_root: str | Path,
    python_base_dir: str | Path,
    opener=urlopen,
) -> UpdateStatus:
    current_version = read_local_app_version(python_base_dir)
    install_supported, install_block_reason = ensure_update_supported_install(app_root)
    try:
        release = fetch_latest_release(opener=opener)
    except Exception:
        return UpdateStatus(
            current_version=current_version,
            latest_version=None,
            update_available=False,
            install_supported=install_supported,
            install_block_reason=install_block_reason,
            release_page_url=RELEASES_PAGE_URL,
            release=None,
        )

    latest_version = release.tag_name.lstrip("vV")
    return UpdateStatus(
        current_version=current_version,
        latest_version=latest_version,
        update_available=is_newer_version(current_version, latest_version),
        install_supported=install_supported,
        install_block_reason=install_block_reason,
        release_page_url=release.html_url or RELEASES_PAGE_URL,
        release=release,
    )


def download_release_zip(release: ReleaseInfo, destination: str | Path, *, opener=urlopen) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with opener(release.zipball_url, timeout=60) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return destination


def extract_release_payload(zip_path: str | Path, destination: str | Path) -> Path:
    zip_path = Path(zip_path)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)

    for child in sorted(destination.iterdir()):
        if child.is_dir() and (child / "python" / "pyproject.toml").exists():
            return child
    raise RuntimeError("更新壓縮檔缺少 python/pyproject.toml，無法辨識程式根目錄。")


def build_update_log_path(app_root: str | Path) -> Path:
    app_root = Path(app_root).resolve()
    log_dir = app_root / _UPDATE_LOG_DIR_NAME
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return log_dir / f"update_{ts}.log"


def _build_update_runner_script() -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        import argparse
        import os
        import shutil
        import traceback
        import sys
        import time
        from datetime import datetime
        from pathlib import Path

        SKIP_NAMES = {".git", ".pytest_cache", ".pytest-tmp", ".ruff_cache", ".uv-cache", ".venv", "__pycache__"}


        def write_log(path: Path, message: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with path.open("a", encoding="utf-8") as handle:
                handle.write(f"[{ts}] {message}\\n")


        def wait_for_process_exit(pid: int, timeout_sec: int = 120) -> None:
            deadline = time.time() + timeout_sec
            while time.time() < deadline:
                try:
                    os.kill(pid, 0)
                except OSError:
                    return
                time.sleep(0.5)
            raise RuntimeError(f"Timed out waiting for process {pid} to exit")


        def should_skip(path: Path) -> bool:
            if path.name in SKIP_NAMES:
                return True
            if path.name.endswith("_output"):
                return True
            if path.name.startswith("tmp"):
                return True
            return False


        def overlay_tree(source: Path, target: Path) -> None:
            target.mkdir(parents=True, exist_ok=True)
            for child in source.iterdir():
                if should_skip(child):
                    continue
                dest = target / child.name
                if child.is_dir():
                    overlay_tree(child, dest)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(child, dest)


        def main() -> int:
            parser = argparse.ArgumentParser()
            parser.add_argument("--target", required=True)
            parser.add_argument("--source", required=True)
            parser.add_argument("--pid", required=True, type=int)
            parser.add_argument("--launcher", required=True)
            parser.add_argument("--log-path", required=True)
            args = parser.parse_args()

            target = Path(args.target)
            source = Path(args.source)
            launcher = Path(args.launcher)
            log_path = Path(args.log_path)

            write_log(log_path, f"Updater started. target={target}")
            write_log(log_path, f"Payload source={source}")
            write_log(log_path, f"Waiting for process pid={args.pid} to exit")
            try:
                wait_for_process_exit(args.pid)
                write_log(log_path, "Process exited. Starting overlay copy")
                overlay_tree(source, target)
                write_log(log_path, "Overlay copy completed")

                if launcher.exists():
                    write_log(log_path, f"Restarting launcher: {launcher}")
                    os.startfile(str(launcher))  # type: ignore[attr-defined]
                else:
                    write_log(log_path, f"Launcher missing: {launcher}")
                write_log(log_path, "Updater finished successfully")
                return 0
            except Exception:
                write_log(log_path, "Updater failed with exception:")
                write_log(log_path, traceback.format_exc().rstrip())
                raise


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    ).strip() + "\n"


def spawn_release_update(
    *,
    app_root: str | Path,
    payload_root: str | Path,
    current_pid: int,
    launcher_path: str | Path,
    python_executable: str | Path | None = None,
) -> tuple[Path, Path]:
    app_root = Path(app_root).resolve()
    payload_root = Path(payload_root).resolve()
    launcher_path = Path(launcher_path).resolve()
    python_executable = str(python_executable or sys.executable)
    log_path = build_update_log_path(app_root)

    runner_dir = Path(tempfile.mkdtemp(prefix="totalseg_release_update_"))
    runner_path = runner_dir / _UPDATE_RUNNER_NAME
    runner_path.write_text(_build_update_runner_script(), encoding="utf-8")

    popen_kwargs = {
        "args": [
            python_executable,
            str(runner_path),
            "--target",
            str(app_root),
            "--source",
            str(payload_root),
            "--pid",
            str(current_pid),
            "--launcher",
            str(launcher_path),
            "--log-path",
            str(log_path),
        ],
        "cwd": str(runner_dir),
        "close_fds": True,
    }

    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    subprocess.Popen(**popen_kwargs)
    return runner_path, log_path
