import argparse
import colorsys
import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import SimpleITK as sitk
from PIL import Image, ImageDraw, ImageFont


def validate_path_ascii(path: Path):
    try:
        _ = str(path).encode("ascii")
    except Exception:
        print(
            f"[ERROR] Path contains non-ASCII characters: {path}\n"
            "Please move to a path with only ASCII characters and retry."
        )
        sys.exit(1)


def get_base_name(name: str):
    base = name.replace(".nii.gz", "").replace(".nii", "")
    for suffix in ["_left", "_right"]:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base


def generate_color_palette(n: int):
    colors = []
    for i in range(n):
        h, s, v = (i / max(1, n)) % 1.0, 0.8, 0.9
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors


def draw_legend(image, slice_labels, color_map):
    if not slice_labels:
        return

    font_size = 14
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(image)
    slice_labels = list(dict.fromkeys(slice_labels))  # unique

    padding, swatch, row_height = 8, 10, 14
    usable_h = max(1, image.height - 2 * padding)
    max_rows = max(1, usable_h // row_height)
    cols = max(1, (len(slice_labels) + max_rows - 1) // max_rows)
    col_width = min(160, max(80, (image.width - 2 * padding) // cols))

    for idx, name in enumerate(slice_labels):
        x0 = padding + (idx // max_rows) * col_width
        y0 = padding + (idx % max_rows) * row_height
        color = color_map.get(name, (255, 255, 255))
        draw.rectangle([x0, y0, x0 + swatch, y0 + swatch], fill=color + (255,))
        tx, ty = x0 + swatch + 3, y0 - 1
        draw.text((tx + 1, ty + 1), name, fill=(0, 0, 0, 230), font=font)
        draw.text((tx, ty), name, fill=(255, 255, 255, 255), font=font)


def discover_mask_files(
    dicom_dir: Path, masks_dir: Path = None, task_name=None
):
    """
    原始邏輯：如果有傳 masks_dir 就用，否則自己算
    """
    mask_files = []

    # 優先使用傳入的 masks_dir
    if masks_dir and masks_dir.exists():
        mask_files.extend(
            sorted([*masks_dir.glob("*.nii"), *masks_dir.glob("*.nii.gz")])
        )
        return mask_files

    # Fallback: 自己算（舊邏輯）
    seg_dir_name = f"segmentation_{task_name}"
    seg_dir = dicom_dir.parent / f"{dicom_dir.name}_output" / seg_dir_name

    if seg_dir.exists():
        mask_files.extend(sorted([*seg_dir.glob("*.nii"), *seg_dir.glob("*.nii.gz")]))

    return mask_files


def load_masks(mask_files, reference):
    masks = []
    if not mask_files:
        print("[ERROR] No mask files found!")
        raise RuntimeError("No mask files found!")

    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    resampler.SetTransform(sitk.Transform())

    for mf in mask_files:
        try:
            mask_img = sitk.ReadImage(str(mf))
            mask_arr = sitk.GetArrayFromImage(resampler.Execute(mask_img))
            masks.append((get_base_name(mf.stem), mask_arr))
        except Exception as err:
            print(f"[ERROR] Failed to load mask: {mf} - {err}")
            raise

    return masks


def find_spine_label(slice_idx: int, spine_labels: dict) -> str | None:
    """從 spine.json 的 slice_labels dict 查找指定 slice 的脊椎標籤。"""
    return spine_labels.get(str(slice_idx))


def load_spine_labels(spine_json: Path) -> dict:
    """讀取 spine.json，回傳 slice_labels dict。找不到或格式錯誤時回傳空 dict。"""
    if spine_json is None or not spine_json.exists():
        return {}
    try:
        meta = json.loads(spine_json.read_text())
        return meta.get("slice_labels", {})
    except Exception:
        return {}


# 加入 0.1 版本：在影像上繪製脊椎標籤文字
def draw_spine_label(image, spine_label):
    if not spine_label:
        return
    font_size = 18
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(image)
    x, y = image.width - 90, 8
    labeltext = f"Spine:{spine_label}"
    draw.text((x + 1, y + 1), labeltext, fill=(0, 0, 0, 240), font=font)
    draw.text((x, y), labeltext, fill=(255, 255, 255, 255), font=font)


def save_overlay_png(
    overlay_rgb,
    *,
    output_path: Path,
    slice_labels,
    color_map,
    spine_label=None,
    draw_annotations=True,
):
    overlay_img = Image.fromarray(np.clip(overlay_rgb, 0, 255).astype(np.uint8))
    if draw_annotations:
        draw_legend(overlay_img, list(dict.fromkeys(slice_labels)), color_map)
    if draw_annotations and spine_label:
        draw_spine_label(overlay_img, spine_label)
    overlay_img.save(output_path)


def erode_mask_slice(mask_slice, erosion_iters):
    if erosion_iters <= 0:
        return mask_slice.astype(bool)

    mask_u8 = mask_slice.astype(np.uint8)
    original_pixels = np.sum(mask_u8 > 0)
    if original_pixels == 0:
        return mask_u8.astype(bool)

    kernel = np.ones((3, 3), np.uint8)
    eroded = cv2.erode(mask_u8, kernel, iterations=erosion_iters)
    eroded_pixels = np.sum(eroded > 0)

    if erosion_iters > 3 and (
        eroded_pixels < 50 or eroded_pixels < original_pixels * 0.2
    ):
        eroded = cv2.erode(mask_u8, kernel, iterations=3)
        eroded_pixels = np.sum(eroded > 0)

    if eroded_pixels < 20:
        eroded = mask_u8

    return eroded.astype(bool)


def build_overlay_png_names(dicom_files):
    # CT exports may use filenames like `CT.1`, `CT.2`, which all collapse to `CT.png`
    # if only the final suffix is replaced.
    raw_names = [Path(dicom_file).with_suffix(".png").name for dicom_file in dicom_files]
    counts = Counter(raw_names)
    resolved = []

    for idx, (dicom_file, raw_name) in enumerate(zip(dicom_files, raw_names), start=1):
        if counts[raw_name] == 1:
            resolved.append(raw_name)
            continue

        original_name = Path(dicom_file).name
        if Path(original_name).suffix.lower() == ".dcm":
            original_name = Path(original_name).stem
        resolved.append(f"{idx:04d}_{original_name}.png")

    return resolved


def dicom_to_overlay_png(
    dicom_dir: Path,
    out_dir: Path | None,
    *,
    eroded_out_dir: Path = None,
    nolabel_out_dir: Path = None,
    eroded_nolabel_out_dir: Path = None,
    masks_dir: Path = None,
    spine_json: Path = None,
    task_name="abdominal_muscles",
    erosion_iters=2,
    slice_start=None,
    slice_end=None,
):
    validate_path_ascii(dicom_dir)
    output_dirs = [
        path
        for path in (out_dir, eroded_out_dir, nolabel_out_dir, eroded_nolabel_out_dir)
        if path is not None
    ]
    if not output_dirs:
        raise RuntimeError("No output PNG directory provided.")
    for output_dir in output_dirs:
        validate_path_ascii(output_dir)

    reader = sitk.ImageSeriesReader()
    files = reader.GetGDCMSeriesFileNames(str(dicom_dir))
    if not files:
        print(f"[ERROR] No DICOM found in: {dicom_dir}")
        raise RuntimeError(f"No DICOM found in: {dicom_dir}")

    reader.SetFileNames(files)
    image = sitk.Cast(reader.Execute(), sitk.sitkInt16)
    arr = sitk.GetArrayFromImage(image)

    wc, ww = 40, 400  # Window center and width

    mask_files = discover_mask_files(dicom_dir, masks_dir, task_name)
    all_masks = load_masks(mask_files, image)

    color_map = {
        name: color
        for name, color in zip(
            [name for name, _ in all_masks], generate_color_palette(len(all_masks))
        )
    }

    spine_labels = load_spine_labels(spine_json)

    for output_dir in output_dirs:
        output_dir.mkdir(parents=True, exist_ok=True)
    output_count = 0

    # Slice range logic
    total_slices = len(files)
    start = max(0, int(slice_start) - 1) if slice_start else 0
    end = min(total_slices, int(slice_end)) if slice_end else total_slices
    png_names = build_overlay_png_names(files)

    for idx, dicom_file in enumerate(files):
        # Skip if outside range
        if idx < start or idx >= end:
            continue

        try:
            slice_arr = arr[idx]
            minv, maxv = wc - ww / 2, wc + ww / 2
            windowed = np.clip((slice_arr - minv) / (maxv - minv), 0, 1)
            base_u8 = (windowed * 255.0 + 0.5).astype(np.uint8)
            base_rgb = np.stack([base_u8] * 3, axis=-1).astype(np.float32)
            overlay_rgb = base_rgb.copy()
            eroded_overlay_rgb = base_rgb.copy()

            slice_labels_used = []
            eroded_slice_labels_used = []
            for name, mask_arr in all_masks:
                mask_slice = mask_arr[idx] > 0
                if np.any(mask_slice):
                    slice_labels_used.append(name)
                    color = color_map.get(name, (255, 0, 0))
                    for c in range(3):
                        overlay_rgb[mask_slice, c] = (
                            overlay_rgb[mask_slice, c] * 0.4 + color[c] * 0.6
                        )

                eroded_mask_slice = erode_mask_slice(mask_slice, erosion_iters)
                if np.any(eroded_mask_slice):
                    eroded_slice_labels_used.append(name)
                    color = color_map.get(name, (255, 0, 0))
                    for c in range(3):
                        eroded_overlay_rgb[eroded_mask_slice, c] = (
                            eroded_overlay_rgb[eroded_mask_slice, c] * 0.4 + color[c] * 0.6
                        )

            png_filename = png_names[idx]
            spine_label = find_spine_label(idx, spine_labels) if spine_labels else None
            if out_dir is not None:
                save_overlay_png(
                    overlay_rgb,
                    output_path=out_dir / png_filename,
                    slice_labels=slice_labels_used,
                    color_map=color_map,
                    spine_label=spine_label,
                )
            if eroded_out_dir is not None:
                save_overlay_png(
                    eroded_overlay_rgb,
                    output_path=eroded_out_dir / png_filename,
                    slice_labels=eroded_slice_labels_used,
                    color_map=color_map,
                    spine_label=spine_label,
                )
            if nolabel_out_dir is not None:
                save_overlay_png(
                    overlay_rgb,
                    output_path=nolabel_out_dir / png_filename,
                    slice_labels=slice_labels_used,
                    color_map=color_map,
                    spine_label=spine_label,
                    draw_annotations=False,
                )
            if eroded_nolabel_out_dir is not None:
                save_overlay_png(
                    eroded_overlay_rgb,
                    output_path=eroded_nolabel_out_dir / png_filename,
                    slice_labels=eroded_slice_labels_used,
                    color_map=color_map,
                    spine_label=spine_label,
                    draw_annotations=False,
                )
            output_count += 1

        except Exception as e:
            print(
                f"[WARNING] Overlay failed for slice {idx}: {files[idx]}, error: {e}"
            )
            continue

    print(f"[SUCCESS] Total overlays saved: {output_count} slices in {output_dirs[0]}")


def main():
    parser = argparse.ArgumentParser(description="Draw overlays for segmentation.")
    parser.add_argument(
        "--dicom", type=str, required=True, help="Input DICOM folder"
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output root folder",
    )
    parser.add_argument(
        "--task", type=str, default="abdominal_muscles", help="Segmentation task"
    )
    parser.add_argument(
        "--erosion_iters",
        type=int,
        default=2,
        help="Erosion iterations for PNG output (default: 2)",
    )
    parser.add_argument("--slice_start", type=int, default=None, help="Start slice (1-indexed)")
    parser.add_argument("--slice_end", type=int, default=None, help="End slice (1-indexed)")

    args = parser.parse_args()

    dicom_path = Path(args.dicom).resolve()
    output_base = (
        Path(args.out) if args.out else dicom_path.parent
    ) / f"{dicom_path.name}_output"

    seg_dir = output_base / f"segmentation_{args.task}"
    png_dir = seg_dir / "png"
    png_eroded_dir = seg_dir / "png_eroded"
    png_nolabel_dir = seg_dir / "png_nolabel"
    png_eroded_nolabel_dir = seg_dir / "png_eroded_nolabel"
    spine_json = output_base / "spine.json"

    if not dicom_path.exists():
        print(f"[ERROR] DICOM folder not found: {dicom_path}")
        sys.exit(1)

    if not seg_dir.exists():
        print(f"[ERROR] Mask folder not found: {seg_dir}")
        print("   Please run seg.py (step 1) first.")
        sys.exit(1)

    if not spine_json.exists():
        print(f"[ERROR] spine.json not found: {spine_json}")
        print("   Please run seg.py (step 1) first.")
        sys.exit(1)

    try:
        dicom_to_overlay_png(
            dicom_path,
            png_dir,
            eroded_out_dir=png_eroded_dir,
            nolabel_out_dir=png_nolabel_dir,
            eroded_nolabel_out_dir=png_eroded_nolabel_dir,
            masks_dir=seg_dir,
            spine_json=spine_json,
            task_name=args.task,
            erosion_iters=args.erosion_iters,
            slice_start=args.slice_start,
            slice_end=args.slice_end,
        )
    except Exception as ex:
        print("\n[FATAL ERROR] Unexpected error during drawing:")
        print(f"   {type(ex).__name__}: {ex}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
