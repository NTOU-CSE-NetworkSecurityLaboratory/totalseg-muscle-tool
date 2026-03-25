import csv
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from PIL import Image

import draw
from core import csv_service


class _FakeSeriesReader:
    def __init__(self, files, image):
        self._files = [str(f) for f in files]
        self._image = image

    def GetGDCMSeriesFileNames(self, _folder):
        return list(self._files)

    def SetFileNames(self, _files):
        return None

    def Execute(self):
        return self._image


def _make_sitk_image(arr, spacing=(10.0, 10.0, 5.0)):
    image = sitk.GetImageFromArray(np.asarray(arr))
    image.SetSpacing(spacing)
    return image


def _touch(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


@contextmanager
def _sandbox():
    root = Path(__file__).resolve().parent / "_tmp"
    root.mkdir(exist_ok=True)
    case_dir = Path(tempfile.mkdtemp(prefix="cli_", dir=root))
    try:
        yield case_dir
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def _write_spine_json(path: Path, orientation: str):
    path.write_text(json.dumps({"orientation": orientation, "slice_labels": {}}))


class _FakeSitk:
    """Minimal sitk-shaped module for injecting into export_csvs."""

    sitkInt16 = sitk.sitkInt16
    sitkNearestNeighbor = sitk.sitkNearestNeighbor

    def __init__(self, ct_image, ct_arr):
        self._ct_image = ct_image
        self._ct_arr = ct_arr

    def ImageSeriesReader(self):
        ct_image = self._ct_image

        class Reader:
            def GetGDCMSeriesFileNames(self, _): return ["001.dcm", "002.dcm", "003.dcm"]
            def SetFileNames(self, _): pass
            def Execute(self): return ct_image

        return Reader()

    def Cast(self, _img, _dtype):
        return self._ct_image

    def GetArrayFromImage(self, _img):
        return self._ct_arr

    def ResampleImageFilter(self):
        class Resampler:
            def SetReferenceImage(self, _): pass
            def SetInterpolator(self, _): pass
            def SetTransform(self, _): pass
            def Execute(self, img): return img

        return Resampler()

    def Transform(self):
        return None


def _make_load_mask_metrics(slice_area, total_volume, slice_mean_hu, slice_std_hu,
                             total_pixels, summary_mean_hu, summary_median_hu,
                             summary_variance_hu, summary_hu_values=None):
    if summary_hu_values is None:
        summary_hu_values = np.array([], dtype=np.float32)

    def _load(*_args, **_kwargs):
        return (slice_area, total_volume, slice_mean_hu, slice_std_hu,
                total_pixels, summary_mean_hu, summary_median_hu,
                summary_variance_hu, summary_hu_values)

    return _load


def test_volume_csv_preserves_slice_order_for_cranial_orientation():
    with _sandbox() as tmp_path:
        ct_arr = np.zeros((3, 2, 2), dtype=np.int16)
        ct_image = _make_sitk_image(ct_arr)
        fake_sitk = _FakeSitk(ct_image, ct_arr)

        spine_json = tmp_path / "spine.json"
        _write_spine_json(spine_json, "cranial_to_caudal")

        slice_area = np.array([1.00, 0.00, 4.00])
        load_metrics = _make_load_mask_metrics(
            slice_area, 2.5, np.zeros(3), np.zeros(3), 5, 0.0, 0.0, 0.0
        )

        volume_csv = tmp_path / "volume.csv"
        hu_csv = tmp_path / "hu.csv"
        csv_service.export_csvs(
            tmp_path / "masks",
            volume_csv,
            hu_csv,
            tmp_path / "dicom",
            spine_json,
            sitk_module=fake_sitk,
            listdir=lambda _: ["muscle.nii.gz"],
            load_mask_metrics=load_metrics,
            image_reader=None,
            log_info=lambda _: None,
        )

        with volume_csv.open(newline="") as f:
            rows = list(csv.reader(f))

        assert rows[0] == ["# Section 1: per-slice volume/area for original left-right structures"]
        assert rows[1] == ["slicenumber", "muscle"]
        assert rows[2] == ["1", "1.00"]
        assert rows[3] == ["2", "0.00"]
        assert rows[4] == ["3", "4.00"]


def test_volume_csv_reverses_slice_order_for_caudal_orientation():
    with _sandbox() as tmp_path:
        ct_arr = np.zeros((3, 2, 2), dtype=np.int16)
        ct_image = _make_sitk_image(ct_arr)
        fake_sitk = _FakeSitk(ct_image, ct_arr)

        spine_json = tmp_path / "spine.json"
        _write_spine_json(spine_json, "caudal_to_cranial")

        slice_area = np.array([1.00, 0.00, 4.00])
        load_metrics = _make_load_mask_metrics(
            slice_area, 2.5, np.zeros(3), np.zeros(3), 5, 0.0, 0.0, 0.0
        )

        volume_csv = tmp_path / "volume.csv"
        hu_csv = tmp_path / "hu.csv"
        csv_service.export_csvs(
            tmp_path / "masks",
            volume_csv,
            hu_csv,
            tmp_path / "dicom",
            spine_json,
            sitk_module=fake_sitk,
            listdir=lambda _: ["muscle.nii.gz"],
            load_mask_metrics=load_metrics,
            image_reader=None,
            log_info=lambda _: None,
        )

        with volume_csv.open(newline="") as f:
            rows = list(csv.reader(f))

        assert rows[0] == ["# Section 1: per-slice volume/area for original left-right structures"]
        assert rows[1] == ["slicenumber", "muscle"]
        assert rows[2] == ["1", "4.00"]
        assert rows[3] == ["2", "0.00"]
        assert rows[4] == ["3", "1.00"]


def test_dicom_to_overlay_png_avoids_filename_collisions(monkeypatch):
    with _sandbox() as tmp_path:
        ct_arr = np.zeros((3, 2, 2), dtype=np.int16)
        ct_image = _make_sitk_image(ct_arr)
        mask_arr = np.zeros((3, 2, 2), dtype=np.uint8)
        mask_arr[0, 0, 0] = 1
        mask_arr[2, 1, 1] = 1
        fake_files = [
            tmp_path / "CT.1",
            tmp_path / "CT.2",
            tmp_path / "CT.3",
        ]

        monkeypatch.setattr(
            draw.sitk,
            "ImageSeriesReader",
            lambda: _FakeSeriesReader(fake_files, ct_image),
        )
        monkeypatch.setattr(
            draw,
            "discover_mask_files",
            lambda *_args, **_kwargs: [tmp_path / "muscle.nii.gz"],
        )
        monkeypatch.setattr(
            draw,
            "load_masks",
            lambda _mask_files, _reference: [("muscle", mask_arr)],
        )

        out_dir = tmp_path / "png"
        eroded_out_dir = tmp_path / "png_eroded"
        nolabel_out_dir = tmp_path / "png_nolabel"
        eroded_nolabel_out_dir = tmp_path / "png_eroded_nolabel"
        draw.dicom_to_overlay_png(
            tmp_path / "dicom",
            out_dir,
            eroded_out_dir=eroded_out_dir,
            nolabel_out_dir=nolabel_out_dir,
            eroded_nolabel_out_dir=eroded_nolabel_out_dir,
            masks_dir=tmp_path / "masks",
        )

        expected_names = ["0001_CT.1.png", "0002_CT.2.png", "0003_CT.3.png"]
        for current_dir in (out_dir, eroded_out_dir, nolabel_out_dir, eroded_nolabel_out_dir):
            outputs = sorted(current_dir.glob("*.png"))
            assert [p.name for p in outputs] == expected_names

        first = np.array(Image.open(out_dir / expected_names[0]))
        third = np.array(Image.open(out_dir / expected_names[2]))
        assert not np.all(first[..., 0] == first[..., 1])
        assert not np.all(third[..., 0] == third[..., 1])


def test_dicom_to_overlay_png_writes_nolabel_variants_without_annotations(monkeypatch):
    with _sandbox() as tmp_path:
        ct_arr = np.zeros((1, 2, 2), dtype=np.int16)
        ct_image = _make_sitk_image(ct_arr)
        mask_arr = np.ones((1, 2, 2), dtype=np.uint8)
        fake_files = [tmp_path / "CT.1"]

        monkeypatch.setattr(
            draw.sitk,
            "ImageSeriesReader",
            lambda: _FakeSeriesReader(fake_files, ct_image),
        )
        monkeypatch.setattr(
            draw,
            "discover_mask_files",
            lambda *_args, **_kwargs: [tmp_path / "muscle.nii.gz"],
        )
        monkeypatch.setattr(
            draw,
            "load_masks",
            lambda _mask_files, _reference: [("muscle", mask_arr)],
        )
        monkeypatch.setattr(draw, "load_spine_labels", lambda _path: {"0": "L3"})

        calls = []
        original_save_overlay_png = draw.save_overlay_png

        def _record_save(*args, **kwargs):
            calls.append({
                "output_path": kwargs["output_path"],
                "draw_annotations": kwargs.get("draw_annotations", True),
                "spine_label": kwargs.get("spine_label"),
            })
            return original_save_overlay_png(*args, **kwargs)

        monkeypatch.setattr(draw, "save_overlay_png", _record_save)

        draw.dicom_to_overlay_png(
            tmp_path / "dicom",
            tmp_path / "png",
            eroded_out_dir=tmp_path / "png_eroded",
            nolabel_out_dir=tmp_path / "png_nolabel",
            eroded_nolabel_out_dir=tmp_path / "png_eroded_nolabel",
            masks_dir=tmp_path / "masks",
            spine_json=tmp_path / "spine.json",
        )

        flags_by_dir = {call["output_path"].parent.name: call["draw_annotations"] for call in calls}
        assert flags_by_dir == {
            "png": True,
            "png_eroded": True,
            "png_nolabel": False,
            "png_eroded_nolabel": False,
        }
        assert all(call["spine_label"] == "L3" for call in calls)


def test_find_spine_label_uses_spine_json_dict():
    with _sandbox() as tmp_path:
        spine_json = tmp_path / "spine.json"
        spine_json.write_text(json.dumps({
            "orientation": "cranial_to_caudal",
            "slice_labels": {"0": "C3", "1": "T1", "5": "L2"},
        }))

        spine_labels = draw.load_spine_labels(spine_json)

        assert draw.find_spine_label(0, spine_labels) == "C3"
        assert draw.find_spine_label(1, spine_labels) == "T1"
        assert draw.find_spine_label(5, spine_labels) == "L2"
        assert draw.find_spine_label(2, spine_labels) is None
        assert draw.find_spine_label(0, {}) is None
        assert draw.load_spine_labels(None) == {}
        assert draw.load_spine_labels(tmp_path / "missing.json") == {}


def test_hu_csv_summary_includes_median_and_variance():
    with _sandbox() as tmp_path:
        ct_arr = np.zeros((3, 5, 5), dtype=np.int16)
        ct_image = _make_sitk_image(ct_arr)
        fake_sitk = _FakeSitk(ct_image, ct_arr)

        spine_json = tmp_path / "spine.json"
        _write_spine_json(spine_json, "cranial_to_caudal")

        # Only slice 1 (index 1) has data; matches slice_start=2, slice_end=2
        hu_values = np.arange(100, 125, dtype=np.float32)
        load_metrics = _make_load_mask_metrics(
            slice_area=np.array([0.0, 25.0, 0.0]),
            total_volume=12.5,
            slice_mean_hu=np.array([0.0, 112.0, 0.0]),
            slice_std_hu=np.zeros(3),
            total_pixels=25,
            summary_mean_hu=112.0,
            summary_median_hu=112.0,
            summary_variance_hu=52.0,
            summary_hu_values=hu_values,
        )

        volume_csv = tmp_path / "volume.csv"
        hu_csv = tmp_path / "hu.csv"
        csv_service.export_csvs(
            tmp_path / "masks",
            volume_csv,
            hu_csv,
            tmp_path / "dicom",
            spine_json,
            sitk_module=fake_sitk,
            listdir=lambda _: ["muscle.nii.gz"],
            load_mask_metrics=load_metrics,
            image_reader=None,
            log_info=lambda _: None,
            slice_start=2,
            slice_end=2,
        )

        with hu_csv.open(newline="") as f:
            rows = list(csv.reader(f))

        summary_header_index = rows.index(["# Section 3: merged structure HU summary"])
        assert rows[summary_header_index + 1] == ["metric", "muscle"]
        assert rows[summary_header_index + 2] == ["mean_hu", "112.0"]
        assert rows[summary_header_index + 3] == ["median_hu", "112.0"]
        assert rows[summary_header_index + 4] == ["variance_hu", "52.0"]
