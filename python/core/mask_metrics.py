from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def calculate_slice_hu_with_erosion(slice_mask, slice_ct, erosion_iters=2):
    if np.sum(slice_mask > 0) == 0:
        return 0.0, 0.0

    original_pixels = np.sum(slice_mask > 0)
    kernel = np.ones((3, 3), np.uint8)
    erosion_iters = max(int(erosion_iters), 0)
    if erosion_iters > 0:
        eroded_mask = cv2.erode(
            slice_mask.astype(np.uint8), kernel, iterations=erosion_iters
        )
    else:
        eroded_mask = slice_mask.astype(np.uint8)

    eroded_pixels = np.sum(eroded_mask > 0)
    if erosion_iters > 3 and (
        eroded_pixels < 50 or eroded_pixels < original_pixels * 0.2
    ):
        eroded_mask = cv2.erode(slice_mask.astype(np.uint8), kernel, iterations=3)
        eroded_pixels = np.sum(eroded_mask > 0)

    if eroded_pixels < 20:
        eroded_mask = slice_mask.astype(np.uint8)

    hu_values = slice_ct[eroded_mask > 0]
    if len(hu_values) > 0:
        return float(np.mean(hu_values)), float(np.std(hu_values))
    return 0.0, 0.0


def get_mask_area_volume_and_hu(
    nii_path,
    ct_arr,
    spacing,
    resampler,
    *,
    sitk_module: Any,
    image_reader,
    erosion_iters=2,
    slice_start=None,
    slice_end=None,
):
    mask_img = image_reader(nii_path)
    mask_arr = sitk_module.GetArrayFromImage(resampler.Execute(mask_img))

    original_shape = mask_arr.shape[0]
    start = max(0, int(slice_start) - 1) if slice_start else 0
    end = min(original_shape, int(slice_end)) if slice_end else original_shape

    filtered_mask = np.zeros_like(mask_arr)
    if start < end:
        filtered_mask[start:end, :, :] = mask_arr[start:end, :, :]
    mask_arr = filtered_mask

    slice_area = np.sum(mask_arr > 0, axis=(1, 2)) * spacing[0] * spacing[1] / 100
    total_pixels = int(np.sum(mask_arr > 0))
    total_volume = float(total_pixels * np.prod(spacing) / 1000)

    slice_mean_hu = []
    slice_std_hu = []
    for i in range(mask_arr.shape[0]):
        mean_hu, std_hu = calculate_slice_hu_with_erosion(
            mask_arr[i, :, :],
            ct_arr[i, :, :],
            erosion_iters,
        )
        slice_mean_hu.append(round(mean_hu, 2))
        slice_std_hu.append(round(std_hu, 2))

    return (
        slice_area,
        total_volume,
        np.array(slice_mean_hu),
        np.array(slice_std_hu),
        total_pixels,
    )
