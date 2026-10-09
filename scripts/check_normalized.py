
from pathlib import Path
import cv2

folder = Path("data/processed/toothbrush/train/good")

for path in list(folder.glob("*.png"))[:10]:
    image = cv2.imread(str(path))

    if image is None:
        print(f"Unreadable: {path.name}")
        continue

    print(f"{path.name}: {image.shape}")
