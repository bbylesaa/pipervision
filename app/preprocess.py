"""Preprocessing inferensi.

PENTING: fungsi `apply_preprocessing` harus identik dengan yang dipakai di
training/train.py. Mode dan ukuran input dibaca dari models/model_config.json
yang ditulis otomatis oleh skrip training, sehingga keduanya tidak bisa berbeda
tanpa disengaja.

Mode:
  - "raw_0_255":    nilai piksel mentah 0-255, tanpa normalisasi (ImageDataGenerator
                    tanpa rescale/preprocessing_function). Alias lama: "efficientnet".
  - "resnet":       RGB -> BGR lalu kurangi mean ImageNet (setara
                    keras.applications.resnet.preprocess_input, mode 'caffe').
  - "rescale_1_255": piksel dibagi 255.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

RESNET_MEAN_BGR = np.array([103.939, 116.779, 123.68], dtype=np.float32)


def apply_preprocessing(batch: np.ndarray, mode: str) -> np.ndarray:
    """batch: float32 RGB, shape (N, H, W, 3), rentang 0-255."""
    x = batch.astype(np.float32, copy=True)
    if mode in ("raw_0_255", "efficientnet"):
        return x
    if mode == "resnet":
        x = x[..., ::-1]  # RGB -> BGR
        return x - RESNET_MEAN_BGR
    if mode == "rescale_1_255":
        return x / 255.0
    raise ValueError(f"Mode preprocessing tidak dikenal: {mode}")


def pil_to_model_input(img: Image.Image, size: tuple[int, int], mode: str,
                       interpolation: str = "bilinear") -> np.ndarray:
    """Konversi PIL -> tensor (1, H, W, 3).

    interpolation:
      - "nearest":  PIL NEAREST, sama dengan default Keras ImageDataGenerator.flow_from_directory
                    dan load_img (dipakai bila model dilatih dengan generator tsb).
      - "bilinear": tf.image.resize bilinear, sama dengan training/train.py.
    """
    img = ImageOps.exif_transpose(img).convert("RGB")
    if interpolation == "nearest":
        resized = np.asarray(img.resize((size[1], size[0]), Image.NEAREST), dtype=np.float32)
    elif interpolation == "bilinear":
        import tensorflow as tf
        arr = np.asarray(img, dtype=np.uint8)
        resized = tf.image.resize(arr, size, method="bilinear").numpy().astype(np.float32)
    else:
        raise ValueError(f"Interpolasi tidak dikenal: {interpolation}")
    return apply_preprocessing(resized[None, ...], mode)


def load_pil_from_bytes(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img
