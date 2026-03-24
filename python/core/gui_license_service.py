from __future__ import annotations

import json
import os
import random
import re
import shutil
import string
import subprocess
from datetime import datetime
from pathlib import Path


def parse_license_input(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return ""

    match = re.search(r"(?:^|\s)(?:-l|--license_number)\s+([^\s\"']+)", text)
    if match:
        return match.group(1).strip()

    match = re.search(r"(?:^|\s)(?:-l|--license_number)\s+[\"']([^\"']+)[\"']", text)
    if match:
        return match.group(1).strip()

    return text


def classify_totalseg_error(log_text: str) -> str | None:
    text = (log_text or "").lower()
    if "jsondecodeerror" in text and "totalsegmentator" in text and "config.py" in text:
        return "totalseg_config_json_broken"
    if (
        "requires a license" in text
        or "not openly available" in text
        or "missing_license" in text
        or "invalid_license" in text
        or "license number" in text
    ):
        return "license_missing_or_invalid"
    return None


def build_default_totalseg_config() -> dict[str, object]:
    return {
        "totalseg_id": "totalseg_" + "".join(
            random.choices(string.ascii_uppercase + string.digits, k=8)
        ),
        "send_usage_stats": True,
        "prediction_counter": 0,
    }


def repair_totalseg_config_if_broken(cfg_path: Path) -> tuple[bool, str]:
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    if not cfg_path.exists():
        cfg = build_default_totalseg_config()
        cfg_path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        return True, f"[系統] 已建立 TotalSegmentator 設定檔: {cfg_path}\n"

    try:
        json.loads(cfg_path.read_text(encoding="utf-8"))
        return True, ""
    except Exception:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = cfg_path.parent / f"config.broken_{ts}.json"
        try:
            backup.write_text(cfg_path.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass

        cfg = build_default_totalseg_config()
        cfg_path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        return True, (
            f"[系統] 偵測到損壞設定檔，已重建: {cfg_path}\n"
            f"[系統] 損壞檔案備份於: {backup}\n"
        )


def apply_totalseg_license(license_key: str, *, base_dir: Path) -> tuple[bool, str]:
    if shutil.which("uv") is None:
        return False, "找不到 uv，無法寫入授權金鑰。"

    script = (
        "import os; "
        "from totalsegmentator.config import set_license_number; "
        "set_license_number(os.environ['TOTALSEG_LICENSE_KEY'])"
    )
    env = {k: v for k, v in os.environ.items()}
    env["TOTALSEG_LICENSE_KEY"] = license_key

    try:
        result = subprocess.run(
            ["uv", "run", "--no-sync", "python", "-c", script],
            cwd=str(base_dir),
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        output = ""
        if result.stdout:
            output += result.stdout + ("" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            output += result.stderr + ("" if result.stderr.endswith("\n") else "\n")
        return True, output
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        return False, (stderr or stdout or "授權寫入失敗。")
