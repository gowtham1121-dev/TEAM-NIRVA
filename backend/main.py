
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import uuid

import cv2
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from backend.database import (
    initialize_database,
    save_inspection,
    get_inspections,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
UPLOAD_DIR = RESULTS_DIR / "inspection_uploads"
HEATMAP_DIR = RESULTS_DIR / "heatmaps"
MODEL_DIR = PROJECT_ROOT / "models"

MODEL_PATH = MODEL_DIR / "toothbrush_v1.pt"
THRESHOLDS_PATH = MODEL_DIR / "toothbrush_v3_thresholds.json"
QUALITY_LIMITS_PATH = MODEL_DIR / "quality_limits.json"

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inspector = None
quality_gate = None
model_error = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global inspector, quality_gate, model_error

    for directory in (UPLOAD_DIR, HEATMAP_DIR, MODEL_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    initialize_database()

    # The API can start before a trained model is installed.
    # Actual inspection stays unavailable until model loading succeeds.
    if MODEL_PATH.exists() and THRESHOLDS_PATH.exists():
        try:
            from inspector.inspector import Inspector

            inspector = Inspector.load(
                str(MODEL_PATH),
                str(THRESHOLDS_PATH),
                policy="starter",
            )
            logger.info("PatchCore inspector loaded.")
        except Exception as exc:
            model_error = str(exc)
            logger.exception("Could not load PatchCore model.")
    else:
        model_error = (
            "Missing model or threshold file. "
            f"Expected {MODEL_PATH.name} and {THRESHOLDS_PATH.name} "
            "inside the models directory."
        )
        logger.warning(model_error)

    if QUALITY_LIMITS_PATH.exists():
        try:
            from inspector.quality import QualityGate

            quality_gate = QualityGate.load(str(QUALITY_LIMITS_PATH))
            logger.info("Image quality gate loaded.")
        except Exception:
            logger.exception("Could not load quality limits.")
            quality_gate = None

    yield


app = FastAPI(
    title="Autonomous Visual Quality Inspector",
    description="Image-based product inspection API for small manufacturers.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "application": "Autonomous Visual Quality Inspector",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {
        "status": "running",
        "database": "initialized",
        "model_loaded": inspector is not None,
        "quality_gate_loaded": quality_gate is not None,
        "model_error": model_error,
    }


@app.post("/inspect")
async def inspect_product(file: UploadFile = File(...)):
    global inspector

    if inspector is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Inspection model is not ready. Check /health and install "
                "a compatible trained model and threshold configuration."
            ),
        )

    original_name = Path(file.filename or "product.jpg").name
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Upload a JPG, JPEG, PNG, or BMP image.",
        )

    contents = await file.read(MAX_FILE_SIZE + 1)

    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="The maximum upload size is 10 MB.",
        )

    # Decode the bytes as an image; don't trust the file extension alone.
    image = cv2.imdecode(
        __import__("numpy").frombuffer(contents, dtype="uint8"),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise HTTPException(status_code=400, detail="The file is not a valid image.")

    if quality_gate is not None:
        temporary_path = UPLOAD_DIR / f"quality_check_{uuid.uuid4().hex}{extension}"
        temporary_path.write_bytes(contents)
        try:
            quality_result = quality_gate.check(str(temporary_path))
        finally:
            temporary_path.unlink(missing_ok=True)

        if quality_result.get("accepted") is False or quality_result.get("ok") is False:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Image quality check failed.",
                    "quality": quality_result,
                },
            )

    unique_name = f"{uuid.uuid4().hex}{extension}"
    image_path = UPLOAD_DIR / unique_name
    heatmap_path = HEATMAP_DIR / f"{Path(unique_name).stem}_heatmap.png"

    image_path.write_bytes(contents)

    try:
        result = inspector.inspect(
            str(image_path),
            overlay_path=str(heatmap_path),
        )

        score = result.get("score")
        verdict = result.get("verdict")

        if score is None or verdict is None:
            raise ValueError("Inspector result is missing score or verdict.")

        record_id = save_inspection(
            filename=original_name,
            score=score,
            decision=verdict,
            heatmap_path=(
                str(heatmap_path.relative_to(PROJECT_ROOT))
                if heatmap_path.exists()
                else None
            ),
        )

        return {
            "inspection_id": record_id,
            "filename": original_name,
            "result": result,
            "heatmap_url": (
                f"/heatmaps/{heatmap_path.name}"
                if heatmap_path.exists()
                else None
            ),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Product inspection failed.")
        raise HTTPException(
            status_code=500,
            detail=f"Inspection failed: {exc}",
        ) from exc


@app.get("/inspections")
def inspection_history(limit: int = Query(default=100, ge=1, le=1000)):
    return {"inspections": get_inspections(limit=limit)}


@app.get("/heatmaps/{filename}")
def get_heatmap(filename: str):
    # Only serve PNG heatmaps from the designated output directory.
    if (
        not filename.endswith("_heatmap.png")
        or Path(filename).name != filename
    ):
        raise HTTPException(status_code=400, detail="Invalid heatmap filename.")

    path = HEATMAP_DIR / filename

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Heatmap not found.")

    return FileResponse(path, media_type="image/png")
