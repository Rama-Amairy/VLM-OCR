import numpy as np
from PIL import Image, ImageOps


def crop_margins(img: Image.Image, pad: int = 20) -> Image.Image:
    """Cut the white border around the page, keeping a small padding."""
    mask = img.convert("L").point(lambda p: 255 if p < 200 else 0)
    box = mask.getbbox()
    if box is None:
        return img
    left, top, right, bottom = box
    return img.crop((max(left - pad, 0), max(top - pad, 0),
                     min(right + pad, img.width), min(bottom + pad, img.height)))


def deskew(img: Image.Image) -> Image.Image:
    """Straighten a tilted page. The right angle is the one where the text lines
    line up best, i.e. the rows of the page differ most in how much ink they have."""
    gray = img.convert("L")
    small = gray.resize((600, max(1, round(gray.height * 600 / gray.width))))
    ink = Image.fromarray(255 - np.asarray(small))

    best_angle, best_score = 0.0, -1.0
    for angle in np.arange(-5, 5.01, 0.5):
        rows = np.asarray(ink.rotate(angle)).sum(axis=1)
        if rows.var() > best_score:
            best_angle, best_score = float(angle), rows.var()

    if abs(best_angle) < 0.3:
        return img
    return img.rotate(best_angle, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))


def contrast(img: Image.Image) -> Image.Image:
    """Stretch faded or greyish scans so the text is darker on a whiter background."""
    return ImageOps.autocontrast(img, cutoff=1)


STEPS = {
    "crop_margins": crop_margins,
    "deskew": deskew,
    "contrast": contrast,
}
