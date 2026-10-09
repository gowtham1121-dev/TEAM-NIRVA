from pathlib import Path
import cv2
import numpy as np
import csv

# Project folders
project_dir = Path(__file__).resolve().parent.parent

# Prefer the selected 60 images if that folder exists
selected_folder = project_dir / "data" / "toothbrush" / "train" / "good_60"
original_folder = project_dir / "data" / "toothbrush" / "train" / "good"

input_dir = selected_folder if selected_folder.exists() else original_folder
output_dir = project_dir / "data" / "clahe_experiment"
output_dir.mkdir(parents=True, exist_ok=True)

comparison_dir = output_dir / "comparisons"
comparison_dir.mkdir(parents=True, exist_ok=True)

# CLAHE settings
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
image_paths = sorted(
    p for p in input_dir.iterdir()
    if p.is_file() and p.suffix.lower() in extensions
)

if not image_paths:
    raise SystemExit(f"No images found in: {input_dir}")

report_path = output_dir / "clahe_metrics.csv"
comparison_count = 0

with report_path.open("w", newline="", encoding="utf-8") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow([
        "filename",
        "original_mean_brightness",
        "clahe_mean_brightness",
        "original_std_contrast",
        "clahe_std_contrast"
    ])

    for image_path in image_paths:
        image = cv2.imread(str(image_path))

        if image is None:
            print(f"Skipped unreadable image: {image_path.name}")
            continue

        # Convert to LAB and apply CLAHE only to the L (lightness) channel
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lightness, a, b = cv2.split(lab)
        enhanced_lightness = clahe.apply(lightness)
        enhanced_lab = cv2.merge((enhanced_lightness, a, b))
        enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        # Save enhanced image separately
        output_path = output_dir / image_path.name
        cv2.imwrite(str(output_path), enhanced)

        # Save side-by-side comparison: original | CLAHE
        original_resized = cv2.resize(image, (256, 256))
        enhanced_resized = cv2.resize(enhanced, (256, 256))
        comparison = np.hstack((original_resized, enhanced_resized))
        comparison_path = comparison_dir / f"{image_path.stem}_comparison.jpg"
        cv2.imwrite(str(comparison_path), comparison)

        original_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        enhanced_gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)

        writer.writerow([
            image_path.name,
            round(float(np.mean(original_gray)), 2),
            round(float(np.mean(enhanced_gray)), 2),
            round(float(np.std(original_gray)), 2),
            round(float(np.std(enhanced_gray)), 2)
        ])

        comparison_count += 1

print("\nCLAHE experiment completed.")
print(f"Input folder:       {input_dir}")
print(f"Enhanced images:    {output_dir}")
print(f"Comparisons:        {comparison_dir}")
print(f"Metrics CSV:        {report_path}")
print(f"Images processed:   {comparison_count}")
print("Comparison format:  original on left, CLAHE on right")