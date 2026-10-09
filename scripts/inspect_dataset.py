from pathlib import Path

root = Path("data/toothbrush")

extensions = {
    ".png", ".jpg", ".jpeg",
    ".bmp", ".tif", ".tiff"
}

if not root.exists():
    raise FileNotFoundError(root.resolve())

print("Dataset:", root.resolve())

for folder in sorted(root.iterdir()):
    if folder.is_dir():
        files = [
            p for p in folder.rglob("*")
            if p.is_file()
            and p.suffix.lower() in extensions
        ]

        print(f"\n{folder.name}: {len(files)} images")

        for path in files[:3]:
            print(" ", path.relative_to(root))

print("\nDataset inspection completed.")