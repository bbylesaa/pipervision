// Riwayat disimpan HANYA di perangkat pengguna (localStorage). Tidak dikirim ke server.
const KEY = "pipervision.history.v1";
const MAX = 50;

export function loadHistory() {
  try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch { return []; }
}
function save(list) {
  try { localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX))); return true; }
  catch { return false; } // kuota penuh / diblokir
}
export function addEntry(entry) {
  const list = loadHistory();
  list.unshift({ id: crypto.randomUUID(), time: new Date().toISOString(), ...entry });
  return save(list);
}
export function deleteEntry(id) { save(loadHistory().filter((e) => e.id !== id)); }
export function clearHistory() { try { localStorage.removeItem(KEY); } catch { /* abaikan */ } }

// Gambar mini 160px (JPEG) hanya jika pengguna mencentang persetujuan.
export function makeThumbnail(file, max = 160) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const r = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * r); c.height = Math.round(img.height * r);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(url);
      resolve(c.toDataURL("image/jpeg", 0.7));
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(null); };
    img.src = url;
  });
}
