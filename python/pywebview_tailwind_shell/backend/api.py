from __future__ import annotations

import atexit
import json
import os
import random
import re
import shutil
import string
import subprocess
import tempfile
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import webview

from core.app_version import read_local_app_version
from core.shared_core import (
    build_seg_command,
    compare_masks,
    filter_tasks_by_modality,
    folder_numeric_sort_key,
    scan_dicom_cases,
)
from core.shared_core import (
    normalize_slice_range as normalize_slice_range_core,
)
from core.update_service import (
    build_update_status,
    download_release_zip,
    extract_release_payload,
    spawn_release_update,
)

TASK_OPTIONS = [
    "abdominal_muscles",
    "aortic_sinuses",
    "appendicular_bones",
    "appendicular_bones_mr",
    "body",
    "body_mr",
    "brain_structures",
    "breasts",
    "cerebral_bleed",
    "coronary_arteries",
    "craniofacial_structures",
    "face",
    "face_mr",
    "head_glands_cavities",
    "head_muscles",
    "headneck_bones_vessels",
    "headneck_muscles",
    "heartchambers_highres",
    "hip_implant",
    "kidney_cysts",
    "liver_segments",
    "liver_segments_mr",
    "lung_nodules",
    "lung_vessels",
    "oculomotor_muscles",
    "pleural_pericard_effusion",
    "thigh_shoulder_muscles",
    "thigh_shoulder_muscles_mr",
    "tissue_4_types",
    "tissue_types",
    "tissue_types_mr",
    "ventricle_parts",
    "vertebrae_body",
    "vertebrae_mr",
    "total_mr",
    "total",
]

LICENSE_APPLY_URL = "https://backend.totalsegmentator.com/license-academic/"


class AppApi:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._log_events: list[dict[str, str]] = []
        self._max_log_events = 9000

        self._source_root = ""
        self._compare_ai_mask = ""
        self._compare_manual_mask = ""
        self._tasks: list[dict[str, Any]] = []

        self._running = False
        self._stop_requested = False
        self._worker: threading.Thread | None = None
        self._proc: subprocess.Popen[bytes] | None = None

        self._progress_total = 0
        self._progress_done = 0
        self._current_case = ""
        self._batch_started_at: datetime | None = None

        self._python_dir = Path(__file__).resolve().parents[2]
        self._app_root = self._python_dir.parent
        self._latest_release = None

        self._diagnostics: list[str] = []
        self._pending_action = ""
        self._session_log_path = ""
        self._last_failed_task_id: int | None = None
        self._last_failed_task_config: dict[str, Any] | None = None
        self._last_failed_excerpt = ""
        self._last_failed_reason = ""
        self._license_needed = False
        self._range_hint = ""

        atexit.register(self.shutdown)

    def _push_log_event(self, event_type: str, text: str) -> None:
        payload = {"type": event_type, "text": text}
        with self._lock:
            self._log_events.append(payload)
            if len(self._log_events) > self._max_log_events:
                self._log_events = self._log_events[-self._max_log_events :]

    def _log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._push_log_event("line", f"[{ts}] {message}")

    def _log_ephemeral(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._push_log_event("ephemeral", f"[{ts}] {message}")

    def _session_log_write(self, message: str) -> None:
        with self._lock:
            path_text = self._session_log_path
        if not path_text:
            return
        path = Path(path_text)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(message.rstrip("\n") + "\n")
        except Exception:
            return

    def _start_session_log(self) -> None:
        root = Path(self._source_root) if self._source_root else self._python_dir
        log_dir = root / "totalseg_batch_logs"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"batch_{ts}.log"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")
        with self._lock:
            self._session_log_path = str(log_path)

    def _state(self) -> dict[str, Any]:
        with self._lock:
            tasks = [dict(t) for t in self._tasks]
            running = self._running
            progress_total = self._progress_total
            progress_done = self._progress_done
            current_case = self._current_case
            source_root = self._source_root
            compare_ai = self._compare_ai_mask
            compare_manual = self._compare_manual_mask
            started_at = self._batch_started_at
            diagnostics = list(self._diagnostics)
            pending_action = self._pending_action
            session_log_path = self._session_log_path
            last_failed_excerpt = self._last_failed_excerpt
            last_failed_reason = self._last_failed_reason
            last_failed_task_id = self._last_failed_task_id
            license_needed = self._license_needed
            range_hint = self._range_hint

        elapsed_sec = 0
        if started_at and running:
            elapsed_sec = int(max(0.0, (datetime.now() - started_at).total_seconds()))

        return {
            "source_root": source_root,
            "compare_ai_mask": compare_ai,
            "compare_manual_mask": compare_manual,
            "tasks": tasks,
            "running": running,
            "progress": {
                "done": progress_done,
                "total": progress_total,
                "percent": int((progress_done / progress_total) * 100) if progress_total else 0,
                "current_case": current_case,
                "elapsed_sec": elapsed_sec,
            },
            "diagnostics": diagnostics,
            "pending_action": pending_action,
            "session_log_path": session_log_path,
            "last_failed_excerpt": last_failed_excerpt,
            "last_failed_reason": last_failed_reason,
            "last_failed_task_id": last_failed_task_id,
            "license_needed": license_needed,
            "range_hint": range_hint,
            "license_apply_url": LICENSE_APPLY_URL,
        }

    def get_bootstrap(self) -> dict[str, Any]:
        return {
            "task_options": TASK_OPTIONS,
            "task_options_ct": filter_tasks_by_modality(TASK_OPTIONS, "CT"),
            "task_options_mri": filter_tasks_by_modality(TASK_OPTIONS, "MRI"),
            "current_version": read_local_app_version(self._python_dir),
            "update_status": self.get_update_status(),
            "state": self._state(),
        }

    def get_state(self, log_cursor: int = 0) -> dict[str, Any]:
        state = self._state()
        with self._lock:
            cursor = max(0, int(log_cursor or 0))
            new_events = self._log_events[cursor:]
            next_cursor = len(self._log_events)
        state["log_events"] = new_events
        state["logs"] = [ev["text"] for ev in new_events if ev.get("type") == "line"]
        state["next_log_cursor"] = next_cursor
        return state

    def _get_window(self):
        if not webview.windows:
            raise RuntimeError("視窗尚未就緒")
        return webview.windows[0]

    def choose_source_folder(self) -> dict[str, Any]:
        result = self._get_window().create_file_dialog(
            webview.FileDialog.FOLDER, allow_multiple=False
        )
        if not result:
            return {"ok": False, "message": "Cancelled"}
        return self.scan_source(str(result[0]))

    def choose_compare_ai_file(self) -> dict[str, Any]:
        result = self._get_window().create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("Medical (*.nii;*.nrrd;*.gz)",),
        )
        if not result:
            return {"ok": False, "message": "Cancelled"}
        with self._lock:
            self._compare_ai_mask = str(result[0])
        return {"ok": True, "path": self._compare_ai_mask}

    def choose_compare_manual_file(self) -> dict[str, Any]:
        result = self._get_window().create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("Medical (*.nii;*.nrrd;*.gz)",),
        )
        if not result:
            return {"ok": False, "message": "Cancelled"}
        with self._lock:
            self._compare_manual_mask = str(result[0])
        return {"ok": True, "path": self._compare_manual_mask}

    def scan_source(self, root_path: str) -> dict[str, Any]:
        root = Path(root_path)
        if not root.exists() or not root.is_dir():
            return {"ok": False, "message": "資料夾不存在"}

        valid_cases = scan_dicom_cases(root)
        valid_cases.sort(key=lambda c: folder_numeric_sort_key(c.folder))

        tasks: list[dict[str, Any]] = []
        for idx, item in enumerate(valid_cases):
            label = item.label
            if item.slice_count and item.slice_count > 0:
                label = f"{label} ({item.slice_count} slices)"
            tasks.append(
                {
                    "id": idx,
                    "path": str(item.folder),
                    "label": label,
                    "slice_count": item.slice_count,
                    "selected": True,
                    "status": "Ready",
                }
            )

        with self._lock:
            self._source_root = str(root)
            self._tasks = tasks
            if len(tasks) == 1 and (tasks[0].get("slice_count") or 0) > 0:
                self._range_hint = "single_auto_fill"
            elif len(tasks) > 1:
                self._range_hint = "multi_auto_clamp"
            else:
                self._range_hint = ""

        if tasks:
            self._log(f"掃描完成：找到 {len(tasks)} 個病例")
            return {"ok": True, "count": len(tasks), "state": self._state()}
        self._log("找不到 DICOM 病例")
        return {"ok": False, "message": "找不到 DICOM 病例", "state": self._state()}

    def set_task_selected(self, task_id: int, selected: bool) -> dict[str, Any]:
        with self._lock:
            for t in self._tasks:
                if int(t["id"]) == int(task_id):
                    t["selected"] = bool(selected)
                    break
        return {"ok": True}

    def set_all_selected(self, selected: bool) -> dict[str, Any]:
        with self._lock:
            for t in self._tasks:
                t["selected"] = bool(selected)
        return {"ok": True}

    def get_license_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "needs_license": self._license_needed,
                "pending_action": self._pending_action,
                "last_error": self._last_failed_reason,
                "license_apply_url": LICENSE_APPLY_URL,
            }

    def open_license_apply_url(self) -> dict[str, Any]:
        webbrowser.open(LICENSE_APPLY_URL)
        return {"ok": True, "url": LICENSE_APPLY_URL}

    def get_update_status(self) -> dict[str, Any]:
        try:
            status = build_update_status(app_root=self._app_root, python_base_dir=self._python_dir)
            self._latest_release = status.release
            return {
                "ok": True,
                "current_version": status.current_version,
                "latest_version": status.latest_version,
                "update_available": status.update_available,
                "install_supported": status.install_supported,
                "install_block_reason": status.install_block_reason,
                "release_page_url": status.release_page_url,
            }
        except Exception as exc:
            return {
                "ok": False,
                "current_version": read_local_app_version(self._python_dir),
                "latest_version": None,
                "update_available": False,
                "install_supported": False,
                "install_block_reason": str(exc),
                "release_page_url": "https://github.com/NTOU-CSE-NetworkSecurityLaboratory/totalseg-muscle-tool/releases",
            }

    def open_releases_page(self) -> dict[str, Any]:
        status = self.get_update_status()
        target_url = str(status.get("release_page_url") or "https://github.com/NTOU-CSE-NetworkSecurityLaboratory/totalseg-muscle-tool/releases")
        webbrowser.open(target_url)
        return {"ok": True, "url": target_url}

    def close_for_update(self) -> dict[str, Any]:
        def _close_window() -> None:
            try:
                self._get_window().destroy()
            except Exception:
                pass

        timer = threading.Timer(0.15, _close_window)
        timer.daemon = True
        timer.start()
        return {"ok": True}

    def install_latest_release_update(self) -> dict[str, Any]:
        status = build_update_status(app_root=self._app_root, python_base_dir=self._python_dir)
        if status.release is None:
            return {"ok": False, "message": "目前無法取得最新 release 資訊。"}
        if not status.install_supported:
            return {"ok": False, "message": status.install_block_reason or "目前環境不支援 GUI 更新。"}
        if not status.update_available:
            return {"ok": False, "message": "目前已是最新正式版。"}

        work_dir = Path(tempfile.mkdtemp(prefix="totalseg_release_webview_"))
        zip_path = download_release_zip(status.release, work_dir / f"{status.release.tag_name}.zip")
        payload_root = extract_release_payload(zip_path, work_dir / "extract")
        _runner_path, log_path = spawn_release_update(
            app_root=self._app_root,
            payload_root=payload_root,
            current_pid=os.getpid(),
            launcher_path=self._app_root / "START 啟動.bat",
        )
        return {
            "ok": True,
            "message": (
                "已啟動更新程序，主視窗即將自動關閉並套用最新正式版。"
                f" 更新記錄：{log_path}"
            ),
            "close_window": True,
        }

    def submit_license(self, raw_input: str) -> dict[str, Any]:
        key = self._parse_license_input(raw_input)
        if not key:
            return {"ok": False, "message": "請輸入有效的授權金鑰或指令"}

        ok, message = self._apply_totalseg_license(key)
        if not ok:
            self._log(f"ERROR license apply failed: {message}")
            return {"ok": False, "message": message}

        with self._lock:
            self._license_needed = False
            if self._pending_action == "needs_license":
                self._pending_action = ""
        self._log(f"授權已更新：{self._mask_license_key(key)}")
        self._session_log_write("LICENSE_UPDATED")
        return {"ok": True, "masked_key": self._mask_license_key(key), "message": "授權已套用"}

    def retry_last_failed_case(self) -> dict[str, Any]:
        with self._lock:
            if self._running:
                return {"ok": False, "message": "批次已在執行中"}
            snapshot = dict(self._last_failed_task_config or {})
            task_id = self._last_failed_task_id
            if not snapshot:
                return {"ok": False, "message": "沒有可重試的失敗病例"}

        self._log("開始重試上一個失敗病例...")
        self._worker = threading.Thread(
            target=self._run_batch,
            args=([snapshot], dict(snapshot.get("run_config", {})), True),
            daemon=True,
        )
        with self._lock:
            self._running = True
            self._stop_requested = False
            self._progress_total = 1
            self._progress_done = 0
            self._batch_started_at = datetime.now()
            self._pending_action = ""
        if task_id is not None:
            self._set_task_status_by_id(task_id, "Queued")
        self._worker.start()
        return {"ok": True, "message": "已開始重試"}

    def start_segmentation(self, config: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._running:
                return {"ok": False, "message": "批次已在執行中"}
            selected_tasks = [dict(t) for t in self._tasks if bool(t.get("selected"))]
            if not selected_tasks:
                return {"ok": False, "message": "尚未選擇病例"}
            self._running = True
            self._stop_requested = False
            self._progress_total = len(selected_tasks)
            self._progress_done = 0
            self._current_case = ""
            self._batch_started_at = datetime.now()
            self._diagnostics = []
            self._pending_action = ""
            self._last_failed_excerpt = ""
            self._last_failed_reason = ""
            self._last_failed_task_id = None
            self._last_failed_task_config = None
            self._license_needed = False
            for t in self._tasks:
                if t.get("selected"):
                    t["status"] = "Queued"

        preflight_ok, preflight_message = self._preflight_totalseg_config()
        if preflight_message:
            self._log(preflight_message)
        if not preflight_ok:
            with self._lock:
                self._running = False
            return {"ok": False, "message": "準備 TotalSegmentator 設定失敗"}

        self._start_session_log()
        self._session_log_write(
            f"BATCH_START | selected={len(selected_tasks)} | source={self._source_root}"
        )
        self._log("批次開始")

        run_config = dict(config or {})
        self._worker = threading.Thread(
            target=self._run_batch, args=(selected_tasks, run_config, False), daemon=True
        )
        self._worker.start()
        return {"ok": True}

    def stop_segmentation(self) -> dict[str, Any]:
        with self._lock:
            if not self._running:
                return {"ok": True, "message": "目前沒有執行中的批次"}
            self._stop_requested = True
            proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
        self._log("已送出停止要求")
        return {"ok": True}

    def shutdown(self) -> dict[str, Any]:
        with self._lock:
            proc = self._proc
            self._stop_requested = True
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
        with self._lock:
            self._running = False
            self._current_case = ""
        return {"ok": True}

    def _set_task_status_by_id(self, task_id: int, status: str) -> None:
        with self._lock:
            for t in self._tasks:
                if int(t["id"]) == int(task_id):
                    t["status"] = status
                    return

    def _consume_process_output(self, proc: subprocess.Popen[bytes]) -> str:
        if proc.stdout is None:
            return ""

        stream = proc.stdout
        line_buf = ""
        excerpt_parts: list[str] = []

        while True:
            chunk = stream.read(1)
            if not chunk:
                break
            ch = chunk.decode("utf-8", errors="replace")
            if ch == "\r":
                if line_buf.strip():
                    self._log_ephemeral(line_buf)
                    excerpt_parts.append(line_buf)
                    line_buf = ""
                continue
            if ch == "\n":
                if line_buf.strip():
                    self._log(line_buf)
                    excerpt_parts.append(line_buf)
                line_buf = ""
                continue
            line_buf += ch
            with self._lock:
                if self._stop_requested:
                    break

        if line_buf.strip():
            self._log(line_buf)
            excerpt_parts.append(line_buf)

        if not excerpt_parts:
            return ""
        excerpt = "\n".join(excerpt_parts)
        if len(excerpt) > 12000:
            excerpt = excerpt[-12000:]
        return excerpt

    def _classify_error(self, text: str) -> str:
        t = (text or "").lower()
        if (
            "requires a license" in t
            or "missing_license" in t
            or "invalid_license" in t
            or "license number" in t
            or "not openly available" in t
        ):
            return "license_missing_or_invalid"
        if "jsondecodeerror" in t and "config.py" in t and "totalsegmentator" in t:
            return "totalseg_config_json_broken"
        if "cuda out of memory" in t:
            return "cuda_out_of_memory"
        if "permission denied" in t:
            return "permission_denied"
        if "modulenotfounderror" in t:
            return "module_not_found"
        return "unknown"

    def _diagnostic_messages_for_issue(self, issue: str) -> list[str]:
        mapping = {
            "license_missing_or_invalid": [
                "此任務需要有效的 TotalSegmentator 授權金鑰。",
                "請先套用授權，再重試失敗病例。",
            ],
            "totalseg_config_json_broken": [
                "偵測到損壞的 ~/.totalsegmentator/config.json。",
                "設定已自動重建，可重新嘗試。",
            ],
            "cuda_out_of_memory": [
                "GPU 記憶體不足。",
                "請關閉其他 GPU 程式，或縮小執行範圍後再試。",
            ],
            "permission_denied": [
                "存取檔案時遭到權限拒絕。",
                "請確認資料夾權限後再試。",
            ],
            "module_not_found": [
                "目前環境缺少 Python 相依套件。",
                "請先安裝完整環境後再試。",
            ],
        }
        return mapping.get(issue, ["目前沒有可提供的診斷資訊。"])

    def _run_batch(
        self,
        selected_tasks: list[dict[str, Any]],
        config: dict[str, Any],
        is_retry: bool,
    ) -> None:
        uv_path = shutil.which("uv")
        if not uv_path:
            self._log("錯誤：PATH 中找不到 uv")
            with self._lock:
                self._running = False
            return

        stop_reason = "finished"

        for task in selected_tasks:
            with self._lock:
                if self._stop_requested:
                    stop_reason = "stopped"
                    break
                self._current_case = task["label"]

            task_id = int(task["id"])
            dicom_path = str(task["path"])
            out_path = str(Path(dicom_path).parent)
            self._set_task_status_by_id(task_id, "Running")
            self._log(f"執行病例：{task['label']}")
            self._session_log_write(
                f"CASE_START | id={task_id} | label={task['label']} | path={dicom_path}"
            )

            slice_start = None
            slice_end = None
            if bool(config.get("range_enabled", False)):
                start_val, end_val, err = normalize_slice_range_core(
                    str(config.get("slice_start", "1")),
                    str(config.get("slice_end", "")),
                    task.get("slice_count"),
                )
                if err:
                    self._set_task_status_by_id(task_id, f"RangeError: {err}")
                    self._log(f"錯誤 {task['label']}：{err}")
                    self._session_log_write(
                        f"CASE_END | id={task_id} | status=range_error | reason={err}"
                    )
                    with self._lock:
                        self._progress_done += 1
                    continue
                slice_start = start_val
                slice_end = end_val
                self._log(
                    f"已套用切片範圍 {task['label']}：{slice_start} 到 "
                    f"{slice_end if slice_end is not None else 'auto'}"
                )

            args = build_seg_command(
                dicom_path=dicom_path,
                out_path=out_path,
                task=str(config.get("task", "total")),
                modality=str(config.get("modality", "CT")),
                spine=bool(config.get("spine", True)),
                fast=bool(config.get("fast", False)),
                auto_draw=bool(config.get("auto_draw", True)),
                erosion_iters=config.get("erosion_iters", 2),
                slice_start=slice_start,
                slice_end=slice_end,
            )

            task_snapshot = dict(task)
            task_snapshot["run_config"] = dict(config)

            try:
                proc = subprocess.Popen(
                    [uv_path, *args],
                    cwd=str(self._python_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                with self._lock:
                    self._proc = proc

                excerpt = self._consume_process_output(proc)
                if self._stop_requested and proc.poll() is None:
                    proc.kill()
                code = proc.wait()

                if code == 0 and not self._stop_requested:
                    self._set_task_status_by_id(task_id, "Success")
                    self._log(f"完成：{task['label']}")
                    self._session_log_write(
                        f"CASE_END | id={task_id} | status=success | exit_code={code}"
                    )
                elif self._stop_requested:
                    self._set_task_status_by_id(task_id, "Stopped")
                    self._session_log_write(
                        f"CASE_END | id={task_id} | status=stopped | exit_code={code}"
                    )
                    stop_reason = "stopped"
                else:
                    issue = self._classify_error(excerpt)
                    self._set_task_status_by_id(task_id, f"Failed (code {code})")
                    self._log(f"錯誤 {task['label']}：程序結束碼 {code}")
                    self._session_log_write(
                        f"CASE_END | id={task_id} | status=failed | exit_code={code} | issue={issue}"
                    )

                    diagnostics = self._diagnostic_messages_for_issue(issue)
                    for d in diagnostics:
                        self._log(f"診斷：{d}")

                    with self._lock:
                        self._diagnostics = diagnostics
                        self._last_failed_excerpt = excerpt[-6000:] if excerpt else ""
                        self._last_failed_reason = f"issue={issue}, exit_code={code}"
                        self._last_failed_task_id = task_id
                        self._last_failed_task_config = task_snapshot

                    if issue == "totalseg_config_json_broken":
                        ok, repair_msg = self._repair_totalseg_config_if_broken()
                        if repair_msg:
                            self._log(repair_msg)
                            self._session_log_write(repair_msg)
                        if not ok:
                            self._log("錯誤：自動修復 TotalSegmentator 設定失敗")

                    if issue == "license_missing_or_invalid":
                        with self._lock:
                            self._license_needed = True
                            self._pending_action = "needs_license"
                        self._log("需要授權。請先套用 key，再重試失敗病例。")
                        stop_reason = "needs_license"
                        with self._lock:
                            self._stop_requested = True
            except Exception as exc:
                self._set_task_status_by_id(task_id, "Failed")
                self._log(f"錯誤 {task['label']}：{exc}")
                self._session_log_write(f"CASE_END | id={task_id} | status=failed | error={exc}")
            finally:
                with self._lock:
                    self._proc = None
                    self._progress_done += 1

            with self._lock:
                if self._stop_requested and stop_reason != "needs_license":
                    stop_reason = "stopped"
                    break

        with self._lock:
            total = self._progress_total
            done = self._progress_done
            self._running = False
            if stop_reason != "needs_license":
                self._stop_requested = False
            self._current_case = ""

        self._session_log_write(f"BATCH_END | status={stop_reason} | done={done} | total={total}")

        if stop_reason == "needs_license":
            self._log("批次因授權問題暫停")
        elif stop_reason == "stopped":
            self._log("批次已停止")
        elif is_retry:
            self._log("重試完成")
        else:
            self._log("批次完成")

    def _parse_license_input(self, raw_text: str) -> str:
        text = (raw_text or "").strip()
        if not text:
            return ""

        m = re.search(r"(?:^|\s)(?:-l|--license_number)\s+([^\s\"']+)", text)
        if m:
            return m.group(1).strip()
        m = re.search(r"(?:^|\s)(?:-l|--license_number)\s+[\"']([^\"']+)[\"']", text)
        if m:
            return m.group(1).strip()
        return text

    def _mask_license_key(self, key: str) -> str:
        if not key:
            return ""
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"

    def _apply_totalseg_license(self, license_key: str) -> tuple[bool, str]:
        if shutil.which("uv") is None:
            return False, "PATH 中找不到 uv"

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
                cwd=str(self._python_dir),
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout.strip():
                self._log(result.stdout.strip())
            if result.stderr.strip():
                self._log(result.stderr.strip())
            return True, ""
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            return False, (stderr or stdout or "授權套用失敗")

    def _totalseg_config_path(self) -> Path:
        return Path.home() / ".totalsegmentator" / "config.json"

    def _build_default_totalseg_config(self) -> dict[str, Any]:
        return {
            "totalseg_id": "totalseg_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8)),
            "send_usage_stats": True,
            "prediction_counter": 0,
        }

    def _preflight_totalseg_config(self) -> tuple[bool, str]:
        ok, message = self._repair_totalseg_config_if_broken()
        if ok and message:
            return True, message
        if ok:
            return True, ""
        return False, message or "無法驗證 TotalSegmentator 設定"

    def _repair_totalseg_config_if_broken(self) -> tuple[bool, str]:
        cfg_path = self._totalseg_config_path()
        cfg_path.parent.mkdir(parents=True, exist_ok=True)

        if not cfg_path.exists():
            cfg_path.write_text(json.dumps(self._build_default_totalseg_config(), indent=4), encoding="utf-8")
            return True, f"已建立 TotalSegmentator 設定：{cfg_path}"

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
            cfg_path.write_text(json.dumps(self._build_default_totalseg_config(), indent=4), encoding="utf-8")
            return True, f"已重建損壞的 TotalSegmentator 設定，備份：{backup}"

    def run_compare_analysis(self) -> dict[str, Any]:
        with self._lock:
            ai_path = self._compare_ai_mask
            manual_path = self._compare_manual_mask

        if not ai_path or not manual_path:
            return {"ok": False, "message": "Please select both AI and Manual files"}

        try:
            result = compare_masks(ai_path, manual_path)
            self._log(
                "Compare done: "
                f"slice={result['slice_index_1based']}, dice={result['dice']:.4f}"
            )
            return {"ok": True, **result}
        except Exception as exc:
            self._log(f"ERROR compare: {exc}")
            return {"ok": False, "message": str(exc)}
