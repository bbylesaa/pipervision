// Konten edukasi, disusun dari literatur (lihat daftar sumber di README/laporan).
// Kunci = nama kelas dari model. Jangan ubah nama jenis di sebelah kiri.
export const SPECIES = {
  "Sirih Cina": {
    summary: "Peperomia pellucida: herba kecil berdaun lunak dan berair, sering tumbuh liar di tempat lembab.",
    detail: "Sirih cina (Peperomia pellucida) termasuk famili Piperaceae dan dikenal juga sebagai ketumpang air atau sirih bumi. Tumbuhan setinggi sekitar 15–45 cm ini berbatang berair dan agak transparan, dengan daun tunggal berukuran kecil (sekitar 1–4 cm), berbentuk lonjong hingga menyerupai hati, bertepi rata, licin, dan lunak. Biasa tumbuh liar di pekarangan, dinding, dan tempat lembab. Secara tradisional dimanfaatkan sebagai obat dan sayuran; kandungannya antara lain minyak atsiri, flavonoid, saponin, tanin, dan triterpenoid.",
    tone: "#3f8f5a",
  },
  "Sirih Hijau": {
    summary: "Piper betle L.: sirih yang paling dikenal, dipakai dalam budaya menginang dan pengobatan tradisional.",
    detail: "Sirih hijau (Piper betle L.) termasuk famili Piperaceae, yang banyak anggotanya berupa semak atau tumbuhan memanjat dan beraroma khas pada remasan daunnya. Daunnya telah lama dipakai untuk menginang dan ramuan tradisional. Daun mengandung antara lain minyak atsiri, saponin, flavonoid, tanin, eugenol, kavikol, dan alkaloid. Sirih hijau dibedakan dari sirih merah (Piper crocatum).",
    tone: "#2e7d4f",
  },
  "Sirih Jawa": {
    summary: "Salah satu jenis sirih yang dibedakan berdasarkan bentuk, warna, rasa, dan aroma daun.",
    detail: "Sirih Jawa dikenal sebagai salah satu jenis sirih, bersama sirih cacing, sirih gading, sirih banda, dan sirih cengkih, yang dibedakan terutama dari bentuk dan warna daun, rasa, serta aroma. Karena berbagai jenis sirih tersebut dapat berada dalam spesies yang sama dengan sirih hijau, perbedaannya bisa halus dan sulit dipastikan hanya dari foto. Ciri rincinya bervariasi antar sumber, sehingga perlu dirujuk ke literatur botani.",
    tone: "#1f5f3d",
  },
};

export const FALLBACK = { summary: "Kelas pada model.", detail: "Belum ada deskripsi untuk kelas ini.", tone: "#2e7d4f" };
export const speciesInfo = (name) => SPECIES[name] || FALLBACK;