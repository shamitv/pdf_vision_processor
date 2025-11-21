import os
from typing import Iterable, Tuple
from PIL import Image, ImageDraw

_COLOR_MAP = {
    "heading": (0, 0, 255, 255),  # blue
    "table": (0, 128, 0, 255),    # green
    "image": (255, 140, 0, 255),  # orange
}
_DEFAULT_COLOR = (255, 0, 0, 255)
_OVERLAY_VERSION = "v4"
_NORM_MAX = 999  # New normalized scale upper bound


def generate_overlay_image(image_path: str, elements: Iterable[dict]) -> str:
    """Generate (or reuse cached) overlay image visualizing detected elements."""
    base, _ = os.path.splitext(image_path)
    overlay_path = f"{base}_overlay_{_OVERLAY_VERSION}.png"

    source_mtime = os.path.getmtime(image_path)
    if os.path.exists(overlay_path) and os.path.getmtime(overlay_path) >= source_mtime:
        return overlay_path

    with Image.open(image_path) as base_image:
        image = base_image.convert("RGBA")

    # Create a transparent overlay layer for high-quality alpha blending
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size

    for element in elements or []:
        bbox = element.get("box_2d")
        if not bbox or len(bbox) != 4:
            continue

        xmin, ymin, xmax, ymax = _normalize_bbox(bbox, width, height)
        if xmin >= xmax or ymin >= ymax:
            continue

        outline = _COLOR_MAP.get(element.get("type"), _DEFAULT_COLOR)
        # Use a translucent fill (alpha=60)
        fill = (*outline[:3], 60)
        draw.rectangle([xmin, ymin, xmax, ymax], outline=outline, fill=fill, width=3)

    # Composite the overlay onto the base image
    image = Image.alpha_composite(image, overlay)

    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    image.save(overlay_path)
    image.close()
    return overlay_path


def _normalize_bbox(bbox: Iterable[float], image_width: int, image_height: int) -> Tuple[int, int, int, int]:
    xmin, ymin, xmax, ymax = bbox

    max_abs = max(abs(xmin), abs(ymin), abs(xmax), abs(ymax))

    if max_abs <= 1:
        # Coordinates normalized to 0-1 range
        xmin = xmin * image_width
        xmax = xmax * image_width
        ymin = ymin * image_height
        ymax = ymax * image_height
    elif max_abs <= 1000:
        # Coordinates normalized to 0-1000 (or 0-999) range
        # HEURISTIC COMPATIBILITY:
        # We treat all values <= 1000 as normalized.
        # Legacy 0-1000 values are treated as 0-999, resulting in a <0.1% shift
        # which is visually negligible.
        xmin = (xmin / _NORM_MAX) * image_width
        xmax = (xmax / _NORM_MAX) * image_width
        ymin = (ymin / _NORM_MAX) * image_height
        ymax = (ymax / _NORM_MAX) * image_height
    # Otherwise treat as absolute pixel coordinates

    xmin = max(0, min(image_width, xmin))
    xmax = max(0, min(image_width, xmax))
    ymin = max(0, min(image_height, ymin))
    ymax = max(0, min(image_height, ymax))

    if xmin > xmax:
        xmin, xmax = xmax, xmin
    if ymin > ymax:
        ymin, ymax = ymax, ymin

    return int(round(xmin)), int(round(ymin)), int(round(xmax)), int(round(ymax))
