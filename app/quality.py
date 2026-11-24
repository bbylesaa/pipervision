"""Penilaian ketidakpastian dan heuristik kesesuaian gambar (tanpa OpenCV; hanya numpy + Pillow).

CATATAN KETERBATASAN: softmax confidence BUKAN detektor gambar asing yang
andal. Model akan tetap memberi probabilitas tinggi untuk objek yang tidak
pernah dilihat saat training. Modul ini hanya memberi PERINGATAN, bukan
jaminan. Strategi yang lebih kuat membutuhkan kelas "bukan daun sirih" pada
dataset training atau detektor out-of-distribution terpisah.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image


def normalized_entropy(probs: np.ndarray) -> float:
    p = np.clip(probs, 1e-12, 1.0)
    h = -float(np.sum(p * np.log(p)))
    return h / math.log(len(probs)) if len(probs) > 1 else 0.0


def green_ratio(img: Image.Image) -> float:
    """Proporsi piksel berwarna hijau (HSV). Heuristik kasar, bukan detektor daun."""
    hsv = np.asarray(img.convert("RGB").resize((160, 160)).convert("HSV"))
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]   # skala Pillow: 0-255 (hijau ~ 50-190 derajat)
    mask = (h >= 35) & (h <= 135) & (s >= 40) & (v >= 40)
    return float(mask.mean())


def blur_score(img: Image.Image) -> float:
    """Varians Laplacian; makin kecil makin buram."""
    g = np.asarray(img.convert("L").resize((256, 256)), dtype=np.float32)
    lap = g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:] - 4.0 * g[1:-1, 1:-1]
    return float(lap.var())


def assess(probs: np.ndarray, img: Image.Image, conf_thr: float, ent_thr: float) -> dict:
    confidence = float(probs.max())
    entropy = normalized_entropy(probs)
    gr = green_ratio(img)
    blur = blur_score(img)

    warnings: list[str] = []
    if confidence < conf_thr:
        warnings.append("Confidence model rendah. Hasil ini tidak dapat diandalkan.")
    if entropy > ent_thr:
        warnings.append("Probabilitas tersebar di beberapa kelas, model ragu-ragu.")
    if gr < 0.10:
        warnings.append("Gambar hampir tidak mengandung warna hijau. Pastikan foto adalah daun sirih.")
    if blur < 40:
        warnings.append("Gambar tampak buram. Gunakan foto yang lebih tajam dan terang.")

    uncertain = confidence < conf_thr or entropy > ent_thr or gr < 0.10
    return {
        "status": "uncertain" if uncertain else "ok",
        "warnings": warnings,
        "diagnostics": {
            "normalized_entropy": round(entropy, 4),
            "green_ratio": round(gr, 4),
            "sharpness": round(blur, 2),
        },
    }
