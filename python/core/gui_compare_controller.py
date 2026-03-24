from __future__ import annotations

from PySide6.QtWidgets import QFileDialog


class GuiCompareController:
    def __init__(self, window, *, compare_masks):
        self.window = window
        self.compare_masks = compare_masks

    def select_compare_ai(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "選取 AI 比對檔案 (.nii.gz)",
            "",
            "NIfTI GZ (*.nii.gz)",
        )
        if path:
            self.window.compare_ai_mask = path
            self.window.ai_mask_path_lbl.setText(path)
            self.check_compare_ready()

    def select_compare_manual(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "選取人工比對檔案 (NIfTI/NRRD)",
            "",
            "Medical Images (*.nii *.nii.gz *.nrrd)",
        )
        if path:
            self.window.compare_manual_mask = path
            self.window.manual_mask_path_lbl.setText(path)
            self.check_compare_ready()

    def check_compare_ready(self) -> None:
        self.window.btn_run_compare.setEnabled(
            bool(self.window.compare_ai_mask and self.window.compare_manual_mask)
        )

    def run_compare_analysis(self) -> None:
        self.window.log_area.clear()
        self.window.append_log("[INFO] Starting compare analysis...\n")
        self.window.btn_run_compare.setEnabled(False)

        try:
            result = self.compare_masks(self.window.compare_ai_mask, self.window.compare_manual_mask)
            slice_idx = int(result["slice_index_1based"])
            dice = float(result["dice"])
            ai_area = float(result["ai_area_cm2"])
            manual_area = float(result["manual_area_cm2"])

            self.window.append_log(f"[INFO] Slice: {slice_idx}\n")
            self.window.append_log("-" * 40 + "\n")
            self.window.append_log(f"AI area: {ai_area:.2f} cm2\n")
            self.window.append_log(f"Manual area: {manual_area:.2f} cm2\n")
            self.window.append_log(f"Dice: {dice:.4f} (max 1.0)\n")
            self.window.append_log("-" * 40 + "\n")

            if dice >= 0.9:
                self.window.append_log(
                    "<span style='color: #198754; font-weight: bold;'>"
                    "Excellent overlap (Dice >= 0.9)</span><br>",
                    is_html=True,
                )
            elif dice >= 0.8:
                self.window.append_log(
                    "<span style='color: #0d6efd; font-weight: bold;'>"
                    "Good overlap (Dice >= 0.8)</span><br>",
                    is_html=True,
                )
            else:
                self.window.append_log(
                    "<span style='color: #dc3545; font-weight: bold;'>"
                    "Low overlap. Please review masks.</span><br>",
                    is_html=True,
                )
        except Exception as exc:
            self.window.append_log(f"[ERROR] Compare failed: {str(exc)}\n")
        finally:
            self.window.btn_run_compare.setEnabled(True)
