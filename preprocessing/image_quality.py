

from pathlib import Path
import csv
import cv2

ROOT = Path("data/toothbrush")
REPORT = Path("results/image_quality_report.csv")

EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

def check_image(path):
    image = cv2.imread(str(path))

    if image is None:
        return {
            "file": str(path),
            "readable": False,
            "width": "",
            "height": "",
            "blur_score": "",
        }

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

    return {
        "file": str(path),
        "readable": True,
        "width": width,
        "height": height,
        "blur_score": round(float(blur_score), 2),
    }

def main():
    if not ROOT.exists():
        raise FileNotFoundError(f"Dataset not found: {ROOT.resolve()}")

    images = [
        path for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in EXTENSIONS
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file", "readable", "width", "height", "blur_score"]

    with REPORT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for path in images:
            writer.writerow(check_image(path))

    print(f"Images checked: {len(images)}")
    print(f"Report saved to: {REPORT.resolve()}")

if __name__ == "__main__":
    main()

