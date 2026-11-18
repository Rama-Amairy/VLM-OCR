from PIL import Image

from src.preprocessing.steps import STEPS


def check_steps(steps: list[str]) -> None:
    unknown = [s for s in steps if s not in STEPS]
    if unknown:
        raise ValueError(f"unknown preprocessing step {unknown}, available: {', '.join(STEPS)}")


def apply_steps(img: Image.Image, steps: list[str]) -> Image.Image:
    """Apply the steps one after the other, in the order given."""
    check_steps(steps)
    for name in steps:
        img = STEPS[name](img)
    return img
