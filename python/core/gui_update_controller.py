from __future__ import annotations

import os
import tempfile
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from core.update_service import (
    build_update_status,
    download_release_zip,
    extract_release_payload,
    spawn_release_update,
)


class GuiUpdateController:
    def __init__(self, window, *, app_root: Path, base_dir: Path, app_version: str):
        self.window = window
        self.app_root = Path(app_root)
        self.base_dir = Path(base_dir)
        self.app_version = app_version

    def refresh_update_status(self) -> None:
        self.window.btn_check_update.setEnabled(False)
        try:
            status = build_update_status(app_root=self.app_root, python_base_dir=self.base_dir)
            self.window.update_status = status
            self.window.latest_release = status.release

            if status.latest_version is None:
                self.window.update_status_lbl.setText(f"目前版本：v{status.current_version}")
                self.window.update_hint_lbl.setText("目前無法取得最新正式版資訊。")
                self.window.btn_install_update.setEnabled(False)
                return

            self.window.update_status_lbl.setText(
                f"目前版本：v{status.current_version}｜最新正式版：v{status.latest_version}"
            )

            if not status.install_supported:
                self.window.update_hint_lbl.setText(
                    status.install_block_reason or "目前環境不支援 GUI 更新。"
                )
                self.window.btn_install_update.setEnabled(False)
                return

            if status.update_available:
                self.window.update_hint_lbl.setText("偵測到較新正式版，可更新到最新 release。")
                self.window.btn_install_update.setEnabled(True)
            else:
                self.window.update_hint_lbl.setText("目前已是最新正式版。")
                self.window.btn_install_update.setEnabled(False)
        except Exception as exc:
            self.window.update_status = None
            self.window.latest_release = None
            self.window.update_status_lbl.setText(f"目前版本：v{self.app_version}")
            self.window.update_hint_lbl.setText(f"檢查更新失敗：{exc}")
            self.window.btn_install_update.setEnabled(False)
        finally:
            self.window.btn_check_update.setEnabled(True)

    def open_releases_page(self) -> None:
        target_url = "https://github.com/proadress/totalseg-muscle-tool/releases"
        if self.window.update_status is not None:
            target_url = self.window.update_status.release_page_url
        webbrowser.open(target_url)

    def install_latest_release_update(self) -> None:
        self.refresh_update_status()
        status = self.window.update_status
        if status is None or status.release is None:
            QMessageBox.warning(self.window, "更新失敗", "目前無法取得最新 release 資訊。")
            return
        if not status.install_supported:
            QMessageBox.information(
                self.window,
                "目前環境不支援 GUI 更新",
                status.install_block_reason or "這個安裝型態不支援 GUI 更新。",
            )
            return
        if not status.update_available:
            QMessageBox.information(self.window, "已是最新版本", "目前已是最新正式版。")
            return

        confirm = QMessageBox.question(
            self.window,
            "確認更新",
            (
                f"目前版本：v{status.current_version}\n"
                f"最新正式版：v{status.latest_version}\n\n"
                "程式會下載最新 release，關閉目前視窗後完成更新並重新啟動。"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            release = status.release
            work_dir = Path(tempfile.mkdtemp(prefix="totalseg_release_gui_"))
            zip_path = download_release_zip(release, work_dir / f"{release.tag_name}.zip")
            payload_root = extract_release_payload(zip_path, work_dir / "extract")
            spawn_release_update(
                app_root=self.app_root,
                payload_root=payload_root,
                current_pid=os.getpid(),
                launcher_path=self.app_root / "START 啟動.bat",
            )
        except Exception as exc:
            QMessageBox.critical(self.window, "更新失敗", str(exc))
            self.window.append_log(f"[錯誤] 更新失敗：{exc}\n")
            return

        QMessageBox.information(
            self.window,
            "開始更新",
            "已啟動更新程序。主視窗關閉後會套用最新正式版並重新開啟。",
        )
        self.window.close()
