import { API_BASE_URL } from "./config.js";

async function request(path, options = {}, timeoutMs = 60000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(API_BASE_URL + path, { ...options, signal: ctrl.signal });
    let body = null;
    try { body = await res.json(); } catch { /* bukan JSON */ }
    if (!res.ok) {
      const err = new Error(body?.detail || `Server mengembalikan status ${res.status}.`);
      err.status = res.status;
      throw err;
    }
    return body;
  } catch (e) {
    if (e.name === "AbortError") {
      const err = new Error("Server tidak merespons tepat waktu. Layanan gratis kadang perlu ±1 menit untuk bangun. Coba lagi.");
      err.status = 0;
      throw err;
    }
    if (e instanceof TypeError) {
      const err = new Error("Tidak dapat terhubung ke server. Periksa koneksi internet atau konfigurasi API_BASE_URL/CORS.");
      err.status = 0;
      throw err;
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export const getHealth = () => request("/health", {}, 45000);
export const getModelInfo = () => request("/model-info", {}, 45000);
export function predict(file) {
  const fd = new FormData();
  fd.append("file", file);
  return request("/predict", { method: "POST", body: fd }, 90000);
}
