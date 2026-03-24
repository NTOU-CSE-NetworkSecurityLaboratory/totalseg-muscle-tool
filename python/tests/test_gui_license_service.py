import json

from core.gui_license_service import classify_totalseg_error, repair_totalseg_config_if_broken


def test_classify_totalseg_error_detects_license_issue():
    text = "This task is not openly available. It requires a license."
    assert classify_totalseg_error(text) == "license_missing_or_invalid"


def test_repair_totalseg_config_if_broken_recreates_invalid_json(tmp_path):
    cfg_path = tmp_path / ".totalsegmentator" / "config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text("{broken", encoding="utf-8")

    ok, message = repair_totalseg_config_if_broken(cfg_path)

    assert ok is True
    assert "已重建" in message
    parsed = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "totalseg_id" in parsed
