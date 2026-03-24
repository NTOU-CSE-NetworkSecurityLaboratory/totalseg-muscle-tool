from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

try:
    import SimpleITK as sitk
    import numpy as np
except Exception:  # pragma: no cover
    sitk = None
    np = None

OLD = Path(r"C:\Users\cloud\Desktop\SER00005_output")
NEW = Path(r"C:\Users\cloud\Documents\GitHub\totalseg-muscle-tool\SER00005_output")


def rel_files(root: Path) -> set[str]:
    return {
        str(p.relative_to(root)).replace("/", "\\")
        for p in root.rglob("*")
        if p.is_file()
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_csv(a: Path, b: Path) -> str:
    with a.open(newline="", encoding="utf-8") as fa, b.open(newline="", encoding="utf-8") as fb:
        ra = list(csv.reader(fa))
        rb = list(csv.reader(fb))
    if ra == rb:
        return "same"
    if len(ra) != len(rb):
        return f"different rows: {len(ra)} vs {len(rb)}"
    for idx, (row_a, row_b) in enumerate(zip(ra, rb), start=1):
        if row_a != row_b:
            return f"first diff at row {idx}: {row_a} != {row_b}"
    return "different"


def compare_json(a: Path, b: Path) -> str:
    ja = json.loads(a.read_text(encoding="utf-8"))
    jb = json.loads(b.read_text(encoding="utf-8"))
    return "same" if ja == jb else "different json content"


def compare_nifti(a: Path, b: Path) -> str:
    if sitk is None or np is None:
        return "skip (SimpleITK unavailable)"
    ia = sitk.ReadImage(str(a))
    ib = sitk.ReadImage(str(b))
    aa = sitk.GetArrayFromImage(ia)
    ab = sitk.GetArrayFromImage(ib)
    if aa.shape != ab.shape:
        return f"different shape: {aa.shape} vs {ab.shape}"
    if not np.array_equal(aa, ab):
        diff = int(np.count_nonzero(aa != ab))
        return f"different voxels: {diff}"
    if ia.GetSpacing() != ib.GetSpacing():
        return f"same voxels but spacing differs: {ia.GetSpacing()} vs {ib.GetSpacing()}"
    return "same"


def compare_binary(a: Path, b: Path) -> str:
    return "same" if sha256(a) == sha256(b) else "different bytes"


def main() -> None:
    print(f"OLD={OLD}")
    print(f"NEW={NEW}")
    old_files = rel_files(OLD)
    new_files = rel_files(NEW)

    missing = sorted(old_files - new_files)
    extra = sorted(new_files - old_files)
    common = sorted(old_files & new_files)

    print(f"missing_in_new={len(missing)}")
    for item in missing[:20]:
        print(f"  MISSING {item}")
    print(f"extra_in_new={len(extra)}")
    for item in extra[:20]:
        print(f"  EXTRA   {item}")

    interesting = [
        "mask_abdominal_muscles.csv",
        "mask_spine_fast.csv",
        "segmentation_abdominal_muscles\\statistics.json",
        "segmentation_spine_fast\\statistics.json",
    ]

    print("\n--- Key file comparisons ---")
    for rel in interesting:
        a = OLD / rel
        b = NEW / rel
        if not a.exists() or not b.exists():
            print(f"{rel}: missing in one side")
            continue
        if rel.endswith(".csv"):
            result = compare_csv(a, b)
        elif rel.endswith(".json"):
            result = compare_json(a, b)
        else:
            result = compare_binary(a, b)
        print(f"{rel}: {result}")

    print("\n--- First 10 NIfTI comparisons ---")
    nii_common = [p for p in common if p.endswith(".nii.gz")][:10]
    for rel in nii_common:
        print(f"{rel}: {compare_nifti(OLD / rel, NEW / rel)}")

    print("\n--- First 10 PNG comparisons ---")
    png_common = [p for p in common if p.endswith(".png")][:10]
    for rel in png_common:
        print(f"{rel}: {compare_binary(OLD / rel, NEW / rel)}")


if __name__ == "__main__":
    main()
