"""PiperVision API - FastAPI."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, get_settings
from .model_service import ModelService
from .quality import assess
from .ratelimit import RateLimiter
from .validators import validate_image_bytes

logging.basicConfig(level=logging.INFO)
settings = get_settings()
limiter = RateLimiter(settings.rate_limit_per_minute)
# Siapa yang boleh menyematkan halaman ini di <iframe>. Default: tidak ada.
# Hugging Face Spaces menampilkan app lewat iframe, sehingga Dockerfile HF mengisinya.
FRAME_ANCESTORS = os.getenv("FRAME_ANCESTORS", "'none'")
API_PATHS = {"/health", "/model-info", "/predict"}
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = ModelService(settings.model_path, settings.model_config_path, settings.eval_report_path)
    yield


app = FastAPI(title="PiperVision API", version="1.0.0", lifespan=lifespan,
              docs_url="/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
    max_age=600,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    # Tolak body terlalu besar lebih awal (berdasarkan Content-Length)
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > settings.max_upload_bytes + 64 * 1024:
        return JSONResponse({"detail": "Ukuran permintaan melebihi batas."}, status_code=413)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    path = request.url.path
    if path in API_PATHS:
        resp.headers["Cache-Control"] = "no-store"
    elif not path.startswith("/docs") and not path.startswith("/openapi"):
        if FRAME_ANCESTORS == "'none'":
            resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; "
            f"base-uri 'none'; form-action 'none'; frame-ancestors {FRAME_ANCESTORS}")
    return resp


def _svc(request: Request) -> ModelService:
    return request.app.state.model


@app.get("/health")
def health(request: Request):
    m = _svc(request)
    return {
        "status": "ok",
        "model_loaded": m.ready,
        "model_name": m.model_name,
        "class_names": m.class_names,
        "input_size": m.config.get("input_size"),
        "config_verified": m.config_verified if m.ready else None,
        "preprocessing": m.config.get("preprocessing"),
        "runtime": getattr(m, "runtime", None),
        "message": None if m.ready else "Model AI belum dikonfigurasi. " + (m.error or ""),
        "max_upload_mb": settings.max_upload_bytes // (1024 * 1024),
    }


@app.get("/model-info")
def model_info(request: Request):
    """Metrik evaluasi nyata dari training. Kosong jika belum pernah dilatih."""
    m = _svc(request)
    return {
        "model_loaded": m.ready,
        "model_name": m.model_name,
        "evaluation_report": m.evaluation_report(),
    }


@app.post("/predict")
async def predict(request: Request, file: UploadFile = File(...)):
    limiter.check(request)
    m = _svc(request)
    if not m.ready:
        raise HTTPException(503, "Model AI belum dikonfigurasi. Letakkan best_model.keras dan "
                                 "model_config.json di backend/models/ (lihat README).")

    data = await file.read(settings.max_upload_bytes + 1)  # baca terbatas
    img = validate_image_bytes(data, file.content_type, settings.max_upload_bytes,
                               settings.max_image_pixels, settings.min_image_side)
    try:
        probs, ms = m.predict(img)
    except Exception:  # noqa: BLE001
        logging.getLogger("pipervision").exception("Inferensi gagal")
        raise HTTPException(500, "Terjadi kesalahan saat inferensi model.")

    names = m.class_names
    top = int(probs.argmax())
    quality = assess(probs, img, settings.uncertain_confidence, settings.uncertain_entropy)
    if not m.config_verified:
        quality["warnings"].insert(0, "Urutan kelas/preprocessing model belum diverifikasi. "
                                      "Nama kelas pada hasil bisa tertukar sampai konfigurasi diverifikasi.")
    # Gambar TIDAK disimpan; hanya diproses di memori lalu dibuang.
    return {
        "predicted_class": names[top],
        "confidence": float(probs[top]),
        "class_probabilities": {n: float(p) for n, p in zip(names, probs)},
        "model_name": m.model_name,
        "config_verified": m.config_verified,
        "status": quality["status"],
        "warnings": quality["warnings"],
        "diagnostics": quality["diagnostics"],
        "inference_ms": round(ms, 1),
    }


# Frontend statis. Harus didaftarkan PALING AKHIR agar tidak menimpa route API.
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="web")
