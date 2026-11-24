"""Konfigurasi dari environment variables."""
import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    allowed_origins: list[str] = field(
        default_factory=lambda: _list(os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"))
    )
    max_upload_bytes: int = int(float(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024)
    max_image_pixels: int = int(os.getenv("MAX_IMAGE_PIXELS", "25000000"))
    min_image_side: int = int(os.getenv("MIN_IMAGE_SIDE", "64"))
    uncertain_confidence: float = float(os.getenv("UNCERTAIN_CONFIDENCE_THRESHOLD", "0.70"))
    uncertain_entropy: float = float(os.getenv("UNCERTAIN_ENTROPY_THRESHOLD", "0.60"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
    model_path: Path = BASE_DIR / os.getenv("MODEL_PATH", "models/resnet50.h5")
    model_config_path: Path = BASE_DIR / os.getenv("MODEL_CONFIG_PATH", "models/model_config.json")
    eval_report_path: Path = BASE_DIR / os.getenv("EVAL_REPORT_PATH", "models/evaluation_report.json")


def get_settings() -> Settings:
    return Settings()
