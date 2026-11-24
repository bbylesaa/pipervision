"""Memuat model terlatih dan menjalankan inferensi nyata.

Dua runtime:
  - Keras (.h5 / .keras): butuh TensorFlow penuh (berat; tidak muat di hosting gratis 512 MB).
  - TFLite (.tflite): butuh pustaka kecil (ai-edge-litert / tflite-runtime). Cocok untuk hosting gratis.
"""
from __future__ import annotations

import importlib
import json
import logging
import threading
import time
from pathlib import Path

import numpy as np
from PIL import Image

from .preprocess import pil_to_model_input

log = logging.getLogger("pipervision.model")


def _make_tflite_interpreter(path: Path):
    """Pakai runtime TFLite ringan bila ada; jika tidak, pakai TensorFlow (untuk uji lokal)."""
    for mod in ("ai_edge_litert.interpreter", "tflite_runtime.interpreter"):
        try:
            m = importlib.import_module(mod)
        except ImportError:
            continue
        return m.Interpreter(model_path=str(path)), mod  # error saat memuat model tidak ditelan
    import tensorflow as tf

    return tf.lite.Interpreter(model_path=str(path)), "tensorflow.lite"


class ModelService:
    def __init__(self, model_path: Path, config_path: Path, eval_report_path: Path):
        self.model_path = model_path
        self.config_path = config_path
        self.eval_report_path = eval_report_path
        self.model = None          # objek Keras ATAU interpreter TFLite
        self.backend: str | None = None   # "keras" | "tflite"
        self.runtime: str | None = None
        self.config: dict = {}
        self.error: str | None = None
        self._lock = threading.Lock()
        self._inp = self._out = None
        self.load()

    def _resolve_model_file(self) -> Path | None:
        if self.model_path.exists():
            return self.model_path
        alt = self.model_path.with_suffix(".tflite")
        return alt if alt.exists() else None

    # ---------------------------------------------------------------- loading
    def load(self) -> None:
        self.model, self.config, self.error, self.backend, self.runtime = None, {}, None, None, None
        f = self._resolve_model_file()
        if f is None:
            self.error = f"File model tidak ditemukan: {self.model_path.name} (atau versi .tflite)"
            return
        if not self.config_path.exists():
            self.error = (f"File konfigurasi model tidak ditemukan: {self.config_path.name}. "
                          "File ini dibuat otomatis oleh training/train.py.")
            return
        try:
            cfg = json.loads(self.config_path.read_text(encoding="utf-8"))
            for key in ("class_names", "input_size", "preprocessing", "model_name"):
                if key not in cfg:
                    raise ValueError(f"Kunci '{key}' tidak ada pada model_config.json")
            h, w = cfg["input_size"]

            if f.suffix.lower() == ".tflite":
                interp, source = _make_tflite_interpreter(f)
                interp.allocate_tensors()
                inp, out = interp.get_input_details()[0], interp.get_output_details()[0]
                if np.dtype(inp["dtype"]) != np.float32:
                    raise ValueError(f"Input TFLite bertipe {inp['dtype']}; yang didukung hanya float32.")
                if tuple(int(v) for v in inp["shape"][1:3]) != (h, w):
                    raise ValueError(f"Ukuran input TFLite {[int(v) for v in inp['shape']]} tidak sama dengan "
                                     f"input_size {cfg['input_size']} di model_config.json.")
                out_dim = int(out["shape"][-1])
                self._inp, self._out = inp, out
                self.model, self.backend, self.runtime = interp, "tflite", f"tflite ({source})"
            else:
                import tensorflow as tf  # impor lambat agar /health tetap cepat saat gagal

                model = tf.keras.models.load_model(f, compile=False)
                out_dim = int(model.output_shape[-1])
                self.model, self.backend, self.runtime = model, "keras", "keras"

            if out_dim != len(cfg["class_names"]):
                raise ValueError(
                    f"Jumlah output model ({out_dim}) tidak sama dengan jumlah class_names "
                    f"({len(cfg['class_names'])}). Periksa urutan/jumlah kelas.")
            self.config = cfg
            self._run(np.zeros((1, h, w, 3), dtype=np.float32))  # warm-up
            log.info("Model dimuat: %s via %s", cfg["model_name"], self.runtime)
        except Exception as exc:  # noqa: BLE001
            self.model, self.config, self.backend, self.runtime = None, {}, None, None
            self.error = f"Gagal memuat model: {exc}"
            log.exception("Gagal memuat model")

    # ---------------------------------------------------------------- status
    @property
    def ready(self) -> bool:
        return self.model is not None

    @property
    def class_names(self) -> list[str]:
        return list(self.config.get("class_names", []))

    @property
    def config_verified(self) -> bool:
        return bool(self.config.get("config_verified", False))

    @property
    def model_name(self) -> str | None:
        return self.config.get("model_name")

    def evaluation_report(self) -> dict | None:
        if not self.eval_report_path.exists():
            return None
        try:
            return json.loads(self.eval_report_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None

    # ---------------------------------------------------------------- inference
    def _run(self, x: np.ndarray) -> np.ndarray:
        if self.backend == "tflite":
            with self._lock:  # Interpreter TFLite tidak thread-safe
                self.model.set_tensor(self._inp["index"], x.astype(np.float32))
                self.model.invoke()
                return np.array(self.model.get_tensor(self._out["index"])[0])
        return np.asarray(self.model.predict(x, verbose=0)[0])

    def predict(self, img: Image.Image) -> tuple[np.ndarray, float]:
        if not self.ready:
            raise RuntimeError(self.error or "Model belum dikonfigurasi")
        size = tuple(self.config["input_size"])
        x = pil_to_model_input(img, size, self.config["preprocessing"],
                               self.config.get("interpolation", "bilinear"))
        t0 = time.perf_counter()
        probs = self._run(x)
        ms = (time.perf_counter() - t0) * 1000
        probs = np.asarray(probs, dtype=np.float64)
        s = probs.sum()
        if not np.isclose(s, 1.0, atol=1e-3):  # jika model mengeluarkan logits
            e = np.exp(probs - probs.max())
            probs = e / e.sum()
        return probs, ms
