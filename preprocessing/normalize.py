
import numpy as np
from pathlib import Path

import cv2


def normalize_image(image_path, output_path, size=256):
    """Resize an image while preserving aspect ratio."""

    image_path = Path(image_path)
    output_path = Path(output_path)

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")

    height, width = image.shape[:2]

    scale = min(size / width, size / height)

    new_width = max(1, round(width * scale))
    new_height = max(1, round(height * scale))

    resized = cv2.resize(
        image,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA
    )

    canvas = np.zeros((size, size, 3), dtype=np.uint8)

    x = (size - new_width) // 2
    y = (size - new_height) // 2

    canvas[y:y + new_height, x:x + new_width] = resized

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not cv2.imwrite(str(output_path), canvas):
        raise OSError(f"Could not save: {output_path}")

    return output_path


if __name__ == "__main__":
    source = Path("data/toothbrush/train/good")
    destination = Path("data/processed/toothbrush/train/good")

    extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

    images = [
        p for p in source.rglob("*")
        if p.is_file() and p.suffix.lower() in extensions
    ]

    for image_path in images:
        output_path = destination / f"{image_path.stem}.png"
        normalize_image(image_path, output_path)

    print(f"Processed {len(images)} images into {destination}")
