"""Validasi upload gambar (sisi server)."""
from __future__ import annotations

import io

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_image_bytes(data: bytes, content_type: str | None, max_bytes: int,
                         max_pixels: int, min_side: int) -> Image.Image:
    if not data:
        raise HTTPException(400, "File kosong.")
    if len(data) > max_bytes:
        raise HTTPException(413, f"Ukuran file melebihi batas {max_bytes // (1024 * 1024)} MB.")
    if content_type and content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(415, "Tipe file tidak didukung. Gunakan JPG, PNG, atau WebP.")

    Image.MAX_IMAGE_PIXELS = max_pixels  # lindungi dari decompression bomb
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        probe.verify()  # cek integritas; objek tidak bisa dipakai lagi setelah verify
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError):
        raise HTTPException(400, "File bukan gambar yang valid atau rusak.")

    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(415, "Format gambar tidak didukung. Gunakan JPG, PNG, atau WebP.")

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (Image.DecompressionBombError, OSError):
        raise HTTPException(400, "Gambar tidak dapat dibaca atau terlalu besar.")

    w, h = img.size
    if w * h > max_pixels:
        raise HTTPException(413, "Resolusi gambar terlalu besar.")
    if min(w, h) < min_side:
        raise HTTPException(400, f"Gambar terlalu kecil (minimal {min_side}px pada sisi terpendek).")
    return img
