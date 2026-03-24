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


def _resolve_spine_mask_dir(mask_dir) -> Path:
    mask_path = Path(mask_dir)
    if mask_path.name == "segmentation_spine_fast":
        return mask_path
    return mask_path.parent / "segmentation_spine_fast"


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


def export_areas_and_volumes_to_csv(
    mask_dir,
    output_csv,
    dicom_dir,
    *,
    sitk_module,
    listdir,
    load_mask_metrics,
    image_reader,
    log_info,
    erosion_iters=2,
    slice_start=None,
    slice_end=None,
):
    t0 = time.perf_counter()
    log_info(
        "Stage: CSV export started "
        f"(mask_dir={mask_dir}, output_csv={output_csv}, erosion_iters={erosion_iters})"
    )

    reader = sitk_module.ImageSeriesReader()
    files = reader.GetGDCMSeriesFileNames(str(dicom_dir))
    if not files:
        log_info(f"[ERROR] No DICOM found in: {dicom_dir}")
        raise RuntimeError(f"No DICOM found in: {dicom_dir}")
    log_info(f"DICOM slices discovered: {len(files)} from {dicom_dir}")

    reader.SetFileNames(files)
    ct_image = sitk_module.Cast(reader.Execute(), sitk_module.sitkInt16)
    ct_arr = sitk_module.GetArrayFromImage(ct_image)
    spacing = ct_image.GetSpacing()

    resampler = sitk_module.ResampleImageFilter()
    resampler.SetReferenceImage(ct_image)
    resampler.SetInterpolator(sitk_module.sitkNearestNeighbor)
    resampler.SetTransform(sitk_module.Transform())

    spine_orientation = infer_spine_orientation(
        _resolve_spine_mask_dir(mask_dir),
        sitk_module=sitk_module,
        image_reader=image_reader,
        resampler=resampler,
    )

    mask_files = [f for f in listdir(mask_dir) if f.endswith(".nii.gz")]
    if not mask_files:
        raise RuntimeError(f"No mask .nii.gz files found in: {mask_dir}")
    log_info(f"Masks discovered for CSV export: {len(mask_files)}")
    muscles = [f.replace(".nii.gz", "") for f in mask_files]

    area_results = {}
    hu_results = {}
    hu_std_results = {}

    for idx, fname in enumerate(mask_files, 1):
        nii_path = Path(mask_dir) / fname
        log_info(f"Processing mask [{idx}/{len(mask_files)}]: {nii_path}")
        slice_area, _, slice_mean_hu, slice_std_hu, _ = load_mask_metrics(
            nii_path,
            ct_arr,
            spacing,
            resampler,
            erosion_iters=erosion_iters,
            slice_start=slice_start,
            slice_end=slice_end,
        )
        muscle_name = fname.replace(".nii.gz", "")
        area_results[muscle_name] = np.round(slice_area, 2)
        hu_results[muscle_name] = slice_mean_hu
        hu_std_results[muscle_name] = slice_std_hu

    merged_hu, merged_muscles = merge_bilateral_hu_data(area_results, hu_results)
    merged_std, merged_std_muscles = merge_bilateral_std_data(
        area_results, hu_results, hu_std_results
    )
    max_slices = max(len(area) for area in area_results.values())
    export_indices = build_export_indices(max_slices, spine_orientation)

    with open(output_csv, "w", newline="") as csvfile:
        fieldnames = ["slicenumber"] + muscles
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row_number, export_index in enumerate(export_indices, start=1):
            row = {"slicenumber": str(row_number)}
            for muscle in muscles:
                row[muscle] = (
                    f"{area_results[muscle][export_index]:.2f}"
                    if export_index < len(area_results[muscle])
                    else "0.00"
                )
            writer.writerow(row)

        writer = csv.writer(csvfile)
        writer.writerow([])
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
        writer.writerow(["structure", "pixelcount", "volume_cm3"])
        for idx, fname in enumerate(mask_files, 1):
            nii_path = Path(mask_dir) / fname
            log_info(f"Computing summary volume [{idx}/{len(mask_files)}]: {nii_path.name}")
            _, volume, _, _, total_pixels = load_mask_metrics(
                nii_path,
                ct_arr,
                spacing,
                resampler,
                erosion_iters=erosion_iters,
                slice_start=slice_start,
                slice_end=slice_end,
            )
            writer.writerow([fname.replace(".nii.gz", ""), total_pixels, round(float(volume), 2)])

    log_info(
        f"Stage: CSV export completed in {time.perf_counter()-t0:.2f}s. "
        f"Output saved to: {output_csv}"
    )


def merge_statistics_to_csv(mask_dir, output_csv, *, log_info):
    t0 = time.perf_counter()
    stats_json_path = Path(mask_dir) / "statistics.json"
    log_info("Stage: merge statistics started " f"(mask_dir={mask_dir}, output_csv={output_csv})")

    if not stats_json_path.exists():
        log_info(f"[WARN] statistics.json not found at {stats_json_path}")
        log_info("  Skipping organ-level HU export. Make sure statistics=True in totalsegmentator.")
        return

    with open(stats_json_path) as f:
        stats_data = json.load(f)
    with open(output_csv, newline="") as f:
        existing_lines = f.readlines()

    summary_start_idx = None
    for i, line in enumerate(existing_lines):
        if line.startswith("structure,pixelcount,volume_cm3"):
            summary_start_idx = i
            break
    if summary_start_idx is None:
        log_info("[WARN] Could not find summary table in CSV; skip merge.")
        return

    summary_rows = list(csv.DictReader(existing_lines[summary_start_idx:]))
    merged_summary = {}
    processed = set()

    for row in summary_rows:
        muscle = row["structure"]
        if muscle in processed:
            continue

        if muscle.endswith("_left"):
            base_name = muscle.replace("_left", "")
            right_name = f"{base_name}_right"
            right_row = next((r for r in summary_rows if r["structure"] == right_name), None)
            if right_row:
                left_pixels = int(row["pixelcount"])
                right_pixels = int(right_row["pixelcount"])
                total_pixels = left_pixels + right_pixels
                left_volume = float(row["volume_cm3"])
                right_volume = float(right_row["volume_cm3"])
                left_hu = stats_data.get(muscle, {}).get("intensity", 0)
                right_hu = stats_data.get(right_name, {}).get("intensity", 0)
                weighted_hu = (
                    (left_pixels * left_hu + right_pixels * right_hu) / total_pixels
                    if total_pixels > 0
                    else 0
                )
                merged_summary[base_name] = {
                    "pixelcount": total_pixels,
                    "volume_cm3": left_volume + right_volume,
                    "mean_hu": weighted_hu,
                }
                processed.add(muscle)
                processed.add(right_name)
            else:
                merged_summary[muscle] = {
                    "pixelcount": int(row["pixelcount"]),
                    "volume_cm3": float(row["volume_cm3"]),
                    "mean_hu": stats_data.get(muscle, {}).get("intensity", 0),
                }
                processed.add(muscle)
        elif muscle.endswith("_right"):
            base_name = muscle.replace("_right", "")
            left_name = f"{base_name}_left"
            if left_name not in [r["structure"] for r in summary_rows]:
                merged_summary[muscle] = {
                    "pixelcount": int(row["pixelcount"]),
                    "volume_cm3": float(row["volume_cm3"]),
                    "mean_hu": stats_data.get(muscle, {}).get("intensity", 0),
                }
                processed.add(muscle)
        else:
            merged_summary[muscle] = {
                "pixelcount": int(row["pixelcount"]),
                "volume_cm3": float(row["volume_cm3"]),
                "mean_hu": stats_data.get(muscle, {}).get("intensity", 0),
            }
            processed.add(muscle)

    with open(output_csv, "w", newline="") as f:
        f.writelines(existing_lines[:summary_start_idx])
        writer = csv.writer(f)
        writer.writerow(["structure", "pixelcount", "volume_cm3", "mean_hu"])
        for structure, data in merged_summary.items():
            writer.writerow(
                [
                    structure,
                    data["pixelcount"],
                    round(data["volume_cm3"], 2),
                    round(data["mean_hu"], 2),
                ]
            )

    log_info(
        f"Stage: merge statistics completed in {time.perf_counter()-t0:.2f}s. "
        f"Output: {output_csv}"
    )
