import csv
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from PIL import Image

import draw
import seg


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


def _make_image(arr, spacing=(10.0, 10.0, 5.0)):
    image = sitk.GetImageFromArray(np.asarray(arr))
    image.SetSpacing(spacing)
    return image


@contextmanager
def _sandbox():
    root = Path(__file__).resolve().parent / "_tmp"
    root.mkdir(exist_ok=True)
    case_dir = Path(tempfile.mkdtemp(prefix="cli_", dir=root))
    try:
        yield case_dir
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_export_areas_to_csv_preserves_slice_order(monkeypatch):
    with _sandbox() as tmp_path:
        ct_arr = np.zeros((3, 2, 2), dtype=np.int16)
        ct_image = _make_image(ct_arr)
        mask_arr = np.zeros((3, 2, 2), dtype=np.uint8)
        mask_arr[0, 0, 0] = 1
        mask_arr[2, :, :] = 1
        mask_image = _make_image(mask_arr)
        fake_files = [tmp_path / "001.dcm", tmp_path / "002.dcm", tmp_path / "003.dcm"]

        monkeypatch.setattr(
            seg.sitk,
            "ImageSeriesReader",
            lambda: _FakeSeriesReader(fake_files, ct_image),
        )
        monkeypatch.setattr(seg.os, "listdir", lambda _mask_dir: ["muscle.nii.gz"])
        monkeypatch.setattr(seg, "read_image_with_ascii_fallback", lambda _path: mask_image)

        output_csv = tmp_path / "mask.csv"
        seg.export_areas_and_volumes_to_csv(
            str(tmp_path / "masks"),
            str(output_csv),
            str(tmp_path / "dicom"),
        )

        with output_csv.open(newline="") as f:
            rows = list(csv.reader(f))

        assert rows[0] == ["slicenumber", "muscle"]
        assert rows[1] == ["1", "1.00"]
        assert rows[2] == ["2", "0.00"]
        assert rows[3] == ["3", "4.00"]


def test_dicom_to_overlay_png_avoids_filename_collisions(monkeypatch):
    with _sandbox() as tmp_path:
        ct_arr = np.zeros((3, 2, 2), dtype=np.int16)
        ct_image = _make_image(ct_arr)
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
        draw.dicom_to_overlay_png(
            tmp_path / "dicom",
            out_dir,
            masks_dir=tmp_path / "masks",
            show_spine=False,
            eroded_out_dir=None,
        )

        outputs = sorted(out_dir.glob("*.png"))
        assert [p.name for p in outputs] == [
            "0001_CT.1.png",
            "0002_CT.2.png",
            "0003_CT.3.png",
        ]

        first = np.array(Image.open(outputs[0]))
        third = np.array(Image.open(outputs[2]))
        assert not np.all(first[..., 0] == first[..., 1])
        assert not np.all(third[..., 0] == third[..., 1])
