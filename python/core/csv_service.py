from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np

CRANIAL_TO_CAUDAL = "cranial_to_caudal"
CAUDAL_TO_CRANIAL = "caudal_to_cranial"
_VERTEBRA_ORDER = {
    **{f"vertebrae_C{i}": i for i in range(1, 8)},
    **{f"vertebrae_T{i}": 100 + i for i in range(1, 13)},
    **{f"vertebrae_L{i}": 200 + i for i in range(1, 6)},
}


# ---------------------------------------------------------------------------
# Bilateral merge helpers
# ---------------------------------------------------------------------------

def merge_bilateral_hu_data(area_results, hu_results):
    merged_hu = {}
    processed = set()

    for muscle in hu_results.keys():
        if muscle in processed:
            continue

        if muscle.endswith("_left"):
            base_name = muscle.replace("_left", "")
            right_name = f"{base_name}_right"
            if right_name in hu_results:
                left_area = area_results[muscle]
                right_area = area_results[right_name]
                left_hu = hu_results[muscle]
                right_hu = hu_results[right_name]
                total_area = left_area + right_area

                weighted_hu = np.zeros_like(total_area)
                for i in range(len(total_area)):
                    if total_area[i] > 0:
                        weighted_hu[i] = (
                            left_area[i] * left_hu[i] + right_area[i] * right_hu[i]
                        ) / total_area[i]
                merged_hu[base_name] = np.round(weighted_hu, 2)
                processed.add(muscle)
                processed.add(right_name)
            else:
                merged_hu[muscle] = hu_results[muscle]
                processed.add(muscle)
        elif muscle.endswith("_right"):
            base_name = muscle.replace("_right", "")
            left_name = f"{base_name}_left"
            if left_name not in hu_results:
                merged_hu[muscle] = hu_results[muscle]
                processed.add(muscle)
        else:
            merged_hu[muscle] = hu_results[muscle]
            processed.add(muscle)

    return merged_hu, list(merged_hu.keys())


def merge_bilateral_area_data(area_results):
    merged_area = {}
    processed = set()

    for muscle in area_results.keys():
        if muscle in processed:
            continue

        if muscle.endswith("_left"):
            base_name = muscle.replace("_left", "")
            right_name = f"{base_name}_right"
            if right_name in area_results:
                merged_area[base_name] = np.round(
                    area_results[muscle] + area_results[right_name], 2
                )
                processed.add(muscle)
                processed.add(right_name)
                continue

        if muscle.endswith("_right"):
            base_name = muscle.replace("_right", "")
            if f"{base_name}_left" in area_results:
                continue

        merged_area[muscle] = np.round(area_results[muscle], 2)
        processed.add(muscle)

    return merged_area, list(merged_area.keys())


def merge_bilateral_std_data(area_results, hu_results, std_results):
    merged_std = {}
    processed = set()

    for muscle in std_results.keys():
        if muscle in processed:
            continue

        if muscle.endswith("_left"):
            base_name = muscle.replace("_left", "")
            right_name = f"{base_name}_right"

            if right_name in std_results:
                left_area = area_results[muscle]
                right_area = area_results[right_name]
                left_mean = hu_results[muscle]
                right_mean = hu_results[right_name]
                left_std = std_results[muscle]
                right_std = std_results[right_name]
                total_area = left_area + right_area
                merged = np.zeros_like(total_area)

                for i in range(len(total_area)):
                    if total_area[i] > 0:
                        mu = (
                            left_area[i] * left_mean[i] + right_area[i] * right_mean[i]
                        ) / total_area[i]
                        var = (
                            left_area[i]
                            * (left_std[i] ** 2 + (left_mean[i] - mu) ** 2)
                            + right_area[i]
                            * (right_std[i] ** 2 + (right_mean[i] - mu) ** 2)
                        ) / total_area[i]
                        merged[i] = np.sqrt(var)
                merged_std[base_name] = np.round(merged, 2)
                processed.add(muscle)
                processed.add(right_name)
            else:
                merged_std[muscle] = std_results[muscle]
                processed.add(muscle)
        elif muscle.endswith("_right"):
            base_name = muscle.replace("_right", "")
            left_name = f"{base_name}_left"
            if left_name not in std_results:
                merged_std[muscle] = std_results[muscle]
                processed.add(muscle)
        else:
            merged_std[muscle] = std_results[muscle]
            processed.add(muscle)

    return merged_std, list(merged_std.keys())


def merge_bilateral_summary_data(summary_results):
    """Returns merged summary dict with pixelcount, volume_cm3, and HU stats."""
    merged = {}
    processed = set()

    for muscle, data in summary_results.items():
        if muscle in processed:
            continue

        if muscle.endswith("_left"):
            base_name = muscle.replace("_left", "")
            right_name = f"{base_name}_right"
            if right_name in summary_results:
                left = data
                right = summary_results[right_name]
                total_pixels = left["pixelcount"] + right["pixelcount"]
                if total_pixels > 0:
                    combined_hu = np.concatenate((left["hu_values"], right["hu_values"]))
                    mean_hu = round(float(np.mean(combined_hu)), 2)
                    median_hu = round(float(np.median(combined_hu)), 2)
                    variance_hu = round(float(np.var(combined_hu)), 2)
                else:
                    mean_hu = median_hu = variance_hu = 0.0
                merged[base_name] = {
                    "pixelcount": total_pixels,
                    "volume_cm3": round(left["volume_cm3"] + right["volume_cm3"], 2),
                    "mean_hu": mean_hu,
                    "median_hu": median_hu,
                    "variance_hu": variance_hu,
                }
                processed.add(muscle)
                processed.add(right_name)
                continue

        if muscle.endswith("_right"):
            base_name = muscle.replace("_right", "")
            if f"{base_name}_left" in summary_results:
                continue

        merged[muscle] = {
            "pixelcount": data["pixelcount"],
            "volume_cm3": round(float(data["volume_cm3"]), 2),
            "mean_hu": round(float(data["mean_hu"]), 2),
            "median_hu": round(float(data["median_hu"]), 2),
            "variance_hu": round(float(data["variance_hu"]), 2),
        }
        processed.add(muscle)

    return merged


# ---------------------------------------------------------------------------
# Spine orientation
# ---------------------------------------------------------------------------

def infer_spine_orientation(
    spine_mask_dir,
    *,
    sitk_module,
    image_reader,
    resampler,
):
    spine_mask_dir = Path(spine_mask_dir)
    if not spine_mask_dir.is_dir():
        raise RuntimeError(f"Spine segmentation folder not found: {spine_mask_dir}")

    slice_ranks: dict[int, list[int]] = {}
    for mask_file in sorted(spine_mask_dir.glob("vertebrae_*.nii.gz")):
        vertebra_name = mask_file.stem.replace(".nii", "")
        rank = _VERTEBRA_ORDER.get(vertebra_name)
        if rank is None:
            continue

        mask_img = image_reader(mask_file)
        mask_arr = sitk_module.GetArrayFromImage(resampler.Execute(mask_img))
        for slice_idx in np.where(np.any(mask_arr > 0, axis=(1, 2)))[0]:
            slice_ranks.setdefault(int(slice_idx), []).append(rank)

    if not slice_ranks:
        raise RuntimeError(f"No spine evidence found in: {spine_mask_dir}")

    ranked_slices = sorted(
        (slice_idx, float(np.mean(ranks))) for slice_idx, ranks in slice_ranks.items()
    )
    left = 0
    right = len(ranked_slices) - 1
    while left < right and ranked_slices[left][1] == ranked_slices[right][1]:
        left += 1
        right -= 1

    if left >= right:
        raise RuntimeError(
            "Spine evidence is ambiguous; unable to determine cranial/caudal direction."
        )

    if ranked_slices[left][1] < ranked_slices[right][1]:
        return CRANIAL_TO_CAUDAL
    return CAUDAL_TO_CRANIAL


def build_export_indices(num_slices: int, orientation: str) -> list[int]:
    if orientation == CRANIAL_TO_CAUDAL:
        return list(range(num_slices))
    if orientation == CAUDAL_TO_CRANIAL:
        return list(range(num_slices - 1, -1, -1))
    raise ValueError(f"Unsupported orientation: {orientation}")


def write_section_title(writer, title: str) -> None:
    writer.writerow([f"# {title}"])


def write_transposed_summary_table(writer, structures, metrics_by_structure, metric_order) -> None:
    writer.writerow(["metric"] + list(structures))
    for metric_name in metric_order:
        row = [metric_name]
        for structure in structures:
            row.append(metrics_by_structure[structure][metric_name])
        writer.writerow(row)


# ---------------------------------------------------------------------------
# Spine JSON — 步驟一產生，步驟二讀取
# ---------------------------------------------------------------------------

def build_spine_meta(spine_seg_dir, ct_image, sitk_module) -> dict:
    """從 spine segmentation 資料夾計算方向與 slice 標籤，回傳 dict 供寫入 spine.json。"""
    spine_seg_dir = Path(spine_seg_dir)

    resampler = sitk_module.ResampleImageFilter()
    resampler.SetReferenceImage(ct_image)
    resampler.SetInterpolator(sitk_module.sitkNearestNeighbor)
    resampler.SetTransform(sitk_module.Transform())

    orientation = infer_spine_orientation(
        spine_seg_dir,
        sitk_module=sitk_module,
        image_reader=lambda p: sitk_module.ReadImage(str(p)),
        resampler=resampler,
    )

    # 每個 slice 記錄第一個（最頭側）出現的脊椎名稱
    slice_labels: dict[str, str] = {}
    for mask_file in sorted(spine_seg_dir.glob("vertebrae_*.nii.gz")):
        label = mask_file.stem.replace(".nii", "").replace("vertebrae_", "")
        mask_img = sitk_module.ReadImage(str(mask_file))
        arr = sitk_module.GetArrayFromImage(resampler.Execute(mask_img))
        for slice_idx in np.where(np.any(arr > 0, axis=(1, 2)))[0]:
            idx_str = str(int(slice_idx))
            if idx_str not in slice_labels:
                slice_labels[idx_str] = label

    return {"orientation": orientation, "slice_labels": slice_labels}


def write_spine_json(path, meta: dict) -> None:
    Path(path).write_text(json.dumps(meta, ensure_ascii=False, indent=2))


def read_spine_json(path) -> dict:
    p = Path(path)
    if not p.exists():
        raise RuntimeError(
            f"spine.json 不存在：{p}\n"
            "請先執行步驟一（分割）產生此檔案。"
        )
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# 主要輸出函式：export_csvs
# ---------------------------------------------------------------------------

def export_csvs(
    mask_dir,
    volume_csv,
    hu_csv,
    dicom_dir,
    spine_json_path,
    *,
    sitk_module,
    listdir,
    load_mask_metrics,
    image_reader,
    log_info,
    erosion_iters=2,
    slice_start=None,
    slice_end=None,
    hu_min=None,
    hu_max=None,
    write_volume=True,
    write_hu=True,
):
    """
    從 segmentation mask 產生 volume CSV 和 HU CSV。

    load_mask_metrics(nii_path, ct_arr, spacing, resampler,
                      erosion_iters, slice_start, slice_end, hu_min, hu_max)
        → (slice_area, total_volume, slice_mean_hu, slice_std_hu,
           total_pixels, summary_mean_hu, summary_median_hu,
           summary_variance_hu, summary_hu_values)
    """
    t0 = time.perf_counter()
    log_info(f"Stage: CSV export started (mask_dir={mask_dir})")

    # --- 讀 CT ---
    reader = sitk_module.ImageSeriesReader()
    files = reader.GetGDCMSeriesFileNames(str(dicom_dir))
    if not files:
        raise RuntimeError(f"No DICOM found in: {dicom_dir}")
    log_info(f"DICOM slices: {len(files)}")

    reader.SetFileNames(files)
    ct_image = sitk_module.Cast(reader.Execute(), sitk_module.sitkInt16)
    ct_arr = sitk_module.GetArrayFromImage(ct_image)
    spacing = ct_image.GetSpacing()

    resampler = sitk_module.ResampleImageFilter()
    resampler.SetReferenceImage(ct_image)
    resampler.SetInterpolator(sitk_module.sitkNearestNeighbor)
    resampler.SetTransform(sitk_module.Transform())

    # --- 讀 spine.json 取方向 ---
    spine_meta = read_spine_json(spine_json_path)
    orientation = spine_meta["orientation"]
    log_info(f"Spine orientation: {orientation}")

    # --- 載入 mask 並計算 metrics ---
    mask_files = sorted(f for f in listdir(mask_dir) if f.endswith(".nii.gz"))
    if not mask_files:
        raise RuntimeError(f"No mask .nii.gz files found in: {mask_dir}")
    log_info(f"Masks found: {len(mask_files)}")
    muscles = [f.replace(".nii.gz", "") for f in mask_files]

    area_results = {}
    hu_results = {}
    hu_std_results = {}
    summary_results = {}

    for idx, fname in enumerate(mask_files, 1):
        nii_path = Path(mask_dir) / fname
        log_info(f"Processing mask [{idx}/{len(mask_files)}]: {nii_path.name}")
        (
            slice_area,
            total_volume,
            slice_mean_hu,
            slice_std_hu,
            total_pixels,
            summary_mean_hu,
            summary_median_hu,
            summary_variance_hu,
            summary_hu_values,
        ) = load_mask_metrics(
            nii_path,
            ct_arr,
            spacing,
            resampler,
            erosion_iters,
            slice_start,
            slice_end,
            hu_min,
            hu_max,
        )
        muscle_name = fname.replace(".nii.gz", "")
        area_results[muscle_name] = np.round(slice_area, 2)
        hu_results[muscle_name] = slice_mean_hu
        hu_std_results[muscle_name] = slice_std_hu
        summary_results[muscle_name] = {
            "pixelcount": int(total_pixels),
            "volume_cm3": float(total_volume),
            "mean_hu": float(summary_mean_hu),
            "median_hu": float(summary_median_hu),
            "variance_hu": float(summary_variance_hu),
            "hu_values": summary_hu_values,
        }

    merged_hu, merged_muscles = merge_bilateral_hu_data(area_results, hu_results)
    merged_area, merged_area_muscles = merge_bilateral_area_data(area_results)
    merged_std, merged_std_muscles = merge_bilateral_std_data(
        area_results, hu_results, hu_std_results
    )
    merged_summary = merge_bilateral_summary_data(summary_results)
    max_slices = max(len(area) for area in area_results.values())
    export_indices = build_export_indices(max_slices, orientation)

    # --- Volume CSV ---
    if write_volume:
        volume_csv = Path(volume_csv)
        volume_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(volume_csv, "w", newline="") as f:
            writer = csv.writer(f)

            write_section_title(writer, "Section 1: per-slice volume/area for original left-right structures")
            writer.writerow(["slicenumber"] + muscles)
            for row_number, export_index in enumerate(export_indices, start=1):
                row = [str(row_number)]
                for muscle in muscles:
                    row.append(
                        f"{area_results[muscle][export_index]:.2f}"
                        if export_index < len(area_results[muscle])
                        else "0.00"
                    )
                writer.writerow(row)

            writer.writerow([])
            write_section_title(writer, "Section 2: per-slice volume/area with left-right structures merged")
            writer.writerow(["slicenumber"] + merged_area_muscles)
            for row_number, export_index in enumerate(export_indices, start=1):
                row = [str(row_number)]
                for muscle in merged_area_muscles:
                    row.append(
                        f"{merged_area[muscle][export_index]:.2f}"
                        if export_index < len(merged_area[muscle])
                        else "0.00"
                    )
                writer.writerow(row)

            writer.writerow([])
            write_section_title(writer, "Section 3: merged structure volume summary")
            write_transposed_summary_table(
                writer,
                merged_summary.keys(),
                {
                    structure: {
                        "pixelcount": data["pixelcount"],
                        "volume_cm3": round(float(data["volume_cm3"]), 2),
                    }
                    for structure, data in merged_summary.items()
                },
                ["pixelcount", "volume_cm3"],
            )
        log_info(f"Volume CSV saved: {volume_csv}")

    # --- HU CSV ---
    if write_hu:
        hu_csv = Path(hu_csv)
        hu_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(hu_csv, "w", newline="") as f:
            writer = csv.writer(f)
            # 前情提要
            writer.writerow([f"# erosion_iters: {erosion_iters}"])
            writer.writerow([f"# slice_start: {slice_start if slice_start is not None else ''}"])
            writer.writerow([f"# slice_end: {slice_end if slice_end is not None else ''}"])
            writer.writerow([f"# hu_threshold_min: {hu_min if hu_min is not None else ''}"])
            writer.writerow([f"# hu_threshold_max: {hu_max if hu_max is not None else ''}"])
            writer.writerow([])

            # per-slice mean HU
            write_section_title(writer, "Section 1: per-slice mean HU with left-right structures merged")
            writer.writerow(["slicenumber"] + merged_muscles)
            for row_number, export_index in enumerate(export_indices, start=1):
                row = [str(row_number)]
                for muscle in merged_muscles:
                    row.append(
                        f"{merged_hu[muscle][export_index]:.2f}"
                        if export_index < len(merged_hu[muscle])
                        else "0.00"
                    )
                writer.writerow(row)

            writer.writerow([])

            # per-slice HU std
            write_section_title(writer, "Section 2: per-slice HU standard deviation with left-right structures merged")
            writer.writerow(["slicenumber"] + merged_std_muscles)
            for row_number, export_index in enumerate(export_indices, start=1):
                row = [str(row_number)]
                for muscle in merged_std_muscles:
                    row.append(
                        f"{merged_std[muscle][export_index]:.2f}"
                        if export_index < len(merged_std[muscle])
                        else "0.00"
                    )
                writer.writerow(row)

            writer.writerow([])

            # HU summary
            write_section_title(writer, "Section 3: merged structure HU summary")
            write_transposed_summary_table(
                writer,
                merged_summary.keys(),
                {
                    structure: {
                        "mean_hu": round(float(data["mean_hu"]), 2),
                        "median_hu": round(float(data["median_hu"]), 2),
                        "variance_hu": round(float(data["variance_hu"]), 2),
                    }
                    for structure, data in merged_summary.items()
                },
                ["mean_hu", "median_hu", "variance_hu"],
            )
        log_info(f"HU CSV saved: {hu_csv}")

    log_info(f"Stage: CSV export completed in {time.perf_counter() - t0:.2f}s")
