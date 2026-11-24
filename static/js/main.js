import { getHealth, predict } from "./api.js";
import { speciesInfo } from "./content.js";
import { addEntry, clearHistory, deleteEntry, loadHistory, makeThumbnail } from "./history.js";

const $ = (s, r = document) => r.querySelector(s);
const el = (tag, props = {}, ...kids) => {
  const n = Object.assign(document.createElement(tag), props);
  kids.flat().forEach((k) => n.append(k));
  return n;
};
const pct = (x) => (x * 100).toFixed(1).replace(".", ",") + "%";
const MAX_MB = 5;
const OK_TYPES = ["image/jpeg", "image/png", "image/webp"];

const state = { health: null, file: null };

/* ------------------------------------------------------------ routing */
const ROUTES = { "": "home", "/": "home", "/klasifikasi": "klasifikasi", "/riwayat": "riwayat", "/jenis": "jenis", "/tentang": "tentang" };
function route() {
  const key = ROUTES[location.hash.replace(/^#/, "")] || "home";
  document.querySelectorAll("[data-page]").forEach((p) => (p.hidden = p.dataset.page !== key));
  document.querySelectorAll("nav a").forEach((a) =>
    a.dataset.route === key ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"));
  $("#nav").classList.remove("open"); $("#navToggle").setAttribute("aria-expanded", "false");
  window.scrollTo(0, 0);
  if (key === "riwayat") renderHistory();
  if (key === "jenis") renderSpecies();
}
window.addEventListener("hashchange", route);
$("#navToggle").addEventListener("click", () => {
  const open = $("#nav").classList.toggle("open");
  $("#navToggle").setAttribute("aria-expanded", String(open));
});

/* ------------------------------------------------------------ model status */
async function loadHealth() {
  const banner = $("#modelBanner");
  try {
    state.health = await getHealth();
    const h = state.health;
    if (!h.model_loaded) {
      banner.className = "banner err"; banner.hidden = false;
      banner.textContent = "Model AI belum dikonfigurasi di server. Klasifikasi belum dapat dilakukan. " + (h.message || "");
      $("#btnPredict").disabled = true;
    } else if (h.config_verified === false) {
      banner.className = "banner"; banner.hidden = false;
      banner.textContent = "Perhatian: urutan nama kelas dan preprocessing model belum diverifikasi dengan data berlabel. Nama jenis pada hasil bisa tertukar sampai verifikasi dilakukan.";
    } else banner.hidden = true;
  } catch (e) {
    state.health = null;
    banner.className = "banner err"; banner.hidden = false;
    banner.textContent = "Server AI tidak dapat dihubungi. " + e.message;
  }
  renderSpecies();
  updatePredictButton();
}

function classNames() { return state.health?.class_names?.length ? state.health.class_names : []; }

function speciesCard(name) {
  const s = speciesInfo(name);
  const c = el("div", { className: "sp" }, el("h3", { textContent: name }), el("p", { textContent: s.summary }));
  c.style.borderLeftColor = s.tone;
  return c;
}
function renderSpecies() {
  const names = classNames();
  const note = names.length ? null : el("p", { className: "muted", textContent: "Daftar jenis akan tampil setelah server dan model tersambung." });
  const fill = (target, withDetail) => {
    target.replaceChildren();
    if (note) { target.append(note.cloneNode(true)); return; }
    names.forEach((n) => {
      const card = speciesCard(n);
      if (withDetail) card.append(el("p", { className: "muted", textContent: speciesInfo(n).detail }));
      target.append(card);
    });
  };
  fill($("#homeSpecies"), false);
  fill($("#speciesList"), true);
}

/* ------------------------------------------------------------ upload */
const drop = $("#drop"), fileInput = $("#file");
const showFileError = (m) => { const e = $("#fileError"); e.textContent = m || ""; e.hidden = !m; };
function updatePredictButton() {
  $("#btnPredict").disabled = !(state.file && state.health?.model_loaded);
}
function validateFile(f) {
  if (!OK_TYPES.includes(f.type)) return "Format tidak didukung. Gunakan JPG, PNG, atau WebP.";
  if (f.size > MAX_MB * 1024 * 1024) return `Ukuran file ${(f.size / 1048576).toFixed(1)} MB melebihi batas ${MAX_MB} MB.`;
  if (f.size === 0) return "File kosong.";
  return null;
}
function setFile(f) {
  showFileError("");
  const err = f && validateFile(f);
  if (err) { showFileError(err); return; }
  if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
  state.file = f;
  state.previewUrl = URL.createObjectURL(f);
  $("#preview").src = state.previewUrl; $("#preview").hidden = false; $("#dropEmpty").hidden = true;
  $("#btnReset").hidden = false;
  resetResult();
  updatePredictButton();
}
function clearFile() {
  state.file = null; fileInput.value = "";
  $("#preview").hidden = true; $("#preview").removeAttribute("src"); $("#dropEmpty").hidden = false;
  $("#btnReset").hidden = true; showFileError(""); resetResult(); updatePredictButton();
}
drop.addEventListener("click", () => fileInput.click());
drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); } });
fileInput.addEventListener("change", () => fileInput.files[0] && setFile(fileInput.files[0]));
["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => { const f = e.dataTransfer.files[0]; if (f) setFile(f); });
$("#btnReset").addEventListener("click", clearFile);

/* ------------------------------------------------------------ predict */
function resetResult() {
  $("#result").hidden = true; $("#errorBox").hidden = true; $("#loading").hidden = true; $("#resultEmpty").hidden = false;
}
let hintTimer;
$("#btnPredict").addEventListener("click", async () => {
  if (!state.file) return;
  $("#resultEmpty").hidden = true; $("#result").hidden = true; $("#errorBox").hidden = true; $("#loading").hidden = false;
  $("#btnPredict").disabled = true; $("#loadingHint").textContent = "";
  hintTimer = setTimeout(() => ($("#loadingHint").textContent = "Server mungkin sedang bangun. Mohon tunggu sebentar."), 6000);
  try {
    const r = await predict(state.file);
    showResult(r);
    if ($("#optSave").checked) {
      const thumb = $("#optThumb").checked ? await makeThumbnail(state.file) : null;
      const ok = addEntry({ result: r, thumb, fileName: state.file.name });
      if (!ok) $("#resMeta").textContent += " (Riwayat gagal disimpan: penyimpanan browser penuh atau diblokir.)";
    }
  } catch (e) {
    $("#loading").hidden = true;
    const box = $("#errorBox"); box.hidden = false;
    box.textContent = e.status === 503 ? "Model AI belum dikonfigurasi di server. " + e.message : e.message;
    if (e.status === 0 || e.status === 503) loadHealth();
  } finally {
    clearTimeout(hintTimer); updatePredictButton();
  }
});

function explain(r) {
  const top = speciesInfo(r.predicted_class);
  const sorted = Object.entries(r.class_probabilities).sort((a, b) => b[1] - a[1]);
  const second = sorted[1];
  if (r.status === "uncertain")
    return `Model memberi peluang tertinggi pada ${r.predicted_class} (${pct(r.confidence)}), tetapi hasilnya tidak meyakinkan. Coba foto yang lebih jelas, atau anggap hasil ini hanya petunjuk awal.`;
  return `Dari tiga kelas yang dikenal, pola foto ini paling mirip dengan ${r.predicted_class} (${pct(r.confidence)}).` +
    (second ? ` Kemungkinan terdekat berikutnya adalah ${second[0]} (${pct(second[1])}).` : "") + " " + top.summary;
}

function showResult(r) {
  $("#loading").hidden = true; $("#result").hidden = false;
  const unc = r.status === "uncertain";
  const badge = $("#resultStatus");
  badge.className = "badge " + (unc ? "uncertain" : "ok");
  badge.textContent = unc ? "Hasil tidak meyakinkan" : "Prediksi model";
  $("#resName").textContent = (unc ? "Kemungkinan: " : "") + r.predicted_class;
  $("#resConf").textContent = pct(r.confidence);
  const w = $("#warnings"); w.replaceChildren(...(r.warnings || []).map((t) => el("div", { className: "warn", textContent: t })));
  const bars = $("#bars"); bars.replaceChildren();
  Object.entries(r.class_probabilities).sort((a, b) => b[1] - a[1]).forEach(([name, p], i) => {
    const fill = el("i", { className: i === 0 ? "top" : "" });
    bars.append(el("div", {}, el("div", { className: "bar-label" }, el("span", { textContent: name }), el("span", { textContent: pct(p) })),
      el("div", { className: "bar", role: "img", ariaLabel: `${name} ${pct(p)}` }, fill)));
    requestAnimationFrame(() => requestAnimationFrame(() => (fill.style.width = p * 100 + "%")));
  });
  $("#resExplain").textContent = explain(r);
  $("#resMeta").textContent = `Model: ${r.model_name} · waktu inferensi server ${r.inference_ms} ms`;
}

/* ------------------------------------------------------------ riwayat */
function renderHistory() {
  const list = loadHistory(), box = $("#historyList");
  $("#btnClearAll").hidden = !list.length;
  box.replaceChildren();
  if (!list.length) { box.append(el("div", { className: "empty" }, el("p", { textContent: "Belum ada riwayat. Hasil klasifikasi yang Anda simpan akan muncul di sini." }), el("a", { className: "btn btn-primary", href: "#/klasifikasi", textContent: "Mulai klasifikasi" }))); return; }
  list.forEach((e) => {
    const thumb = e.thumb ? el("img", { className: "h-thumb", src: e.thumb, alt: "Gambar mini" }) : el("div", { className: "h-thumb", textContent: "tanpa gambar" });
    const info = el("div", {}, el("b", { textContent: e.result.predicted_class }),
      el("div", { className: "muted small", textContent: `${pct(e.result.confidence)} · ${new Date(e.time).toLocaleString("id-ID")}` }));
    const detail = el("button", { className: "btn btn-ghost", textContent: "Detail" });
    detail.addEventListener("click", () => openDetail(e));
    const del = el("button", { className: "btn btn-danger", textContent: "Hapus", ariaLabel: "Hapus entri ini" });
    del.addEventListener("click", () => { deleteEntry(e.id); renderHistory(); });
    box.append(el("div", { className: "h-item" }, thumb, info, el("div", { className: "row" }, detail, del)));
  });
}
function openDetail(e) {
  const b = $("#detailBody"); b.replaceChildren(el("h2", { textContent: e.result.predicted_class }),
    el("p", { className: "muted", textContent: `${new Date(e.time).toLocaleString("id-ID")} · ${e.result.model_name}` }));
  if (e.thumb) b.append(el("img", { src: e.thumb, alt: "Gambar mini" }));
  b.append(el("table", {}, el("tbody", {}, ...Object.entries(e.result.class_probabilities).sort((a, c) => c[1] - a[1])
    .map(([n, p]) => el("tr", {}, el("td", { textContent: n }), el("td", { textContent: pct(p) }))))));
  if (e.result.status === "uncertain") b.append(el("p", { className: "warn", textContent: "Saat itu hasil ditandai tidak meyakinkan." }));
  $("#detail").showModal();
}
$("#btnClearAll").addEventListener("click", () => { if (confirm("Hapus seluruh riwayat di perangkat ini?")) { clearHistory(); renderHistory(); } });

route();
loadHealth();
