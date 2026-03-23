from argparse import Namespace

from seg import (
    FIXED_PIPELINE_AUTO_DRAW,
    FIXED_PIPELINE_FAST,
    FIXED_PIPELINE_SPINE,
    apply_fixed_pipeline_defaults,
)


def test_apply_fixed_pipeline_defaults_overrides_legacy_flags():
    args = Namespace(spine=0, fast=1, auto_draw=0)

    requested = apply_fixed_pipeline_defaults(args)

    assert requested == {"spine": 0, "fast": 1, "auto_draw": 0}
    assert args.spine == FIXED_PIPELINE_SPINE
    assert args.fast == FIXED_PIPELINE_FAST
    assert args.auto_draw == FIXED_PIPELINE_AUTO_DRAW


def test_apply_fixed_pipeline_defaults_keeps_fixed_values_when_already_requested():
    args = Namespace(
        spine=FIXED_PIPELINE_SPINE,
        fast=FIXED_PIPELINE_FAST,
        auto_draw=FIXED_PIPELINE_AUTO_DRAW,
    )

    requested = apply_fixed_pipeline_defaults(args)

    assert requested == {
        "spine": FIXED_PIPELINE_SPINE,
        "fast": FIXED_PIPELINE_FAST,
        "auto_draw": FIXED_PIPELINE_AUTO_DRAW,
    }
    assert args.spine == FIXED_PIPELINE_SPINE
    assert args.fast == FIXED_PIPELINE_FAST
    assert args.auto_draw == FIXED_PIPELINE_AUTO_DRAW
