# Tutorial AutoCrawl

Panduan langkah demi langkah untuk menjalankan AutoCrawl sendiri dari nol. Tidak perlu pengetahuan dalam tentang Python atau Vue. Yang dibutuhkan hanyalah Docker yang sudah terpasang dan terminal yang bisa menjalankan perintah dasar.

Semua perintah di tutorial ini sudah ditest pada Windows 11 dengan Docker Desktop dan WSL2 backend, juga pada Linux Ubuntu 22.04. Untuk Mac, perintah identik dengan Linux.

---

## 1. Pengantar Singkat

AutoCrawl adalah crawler otonom yang berjalan 24 jam non stop untuk dua tujuan utama. Pertama, ia mencari pameran (expo) di bidang security dan defense industry dari berbagai sumber agregator (10times, Wikipedia, Eventbrite). Kedua, dari setiap expo yang ditemukan, ia mengekstrak daftar peserta (vendor) lalu memperkaya datanya dengan informasi seperti website resmi, deskripsi perusahaan, kontak email, lokasi, sosial media, dan teknologi yang dipakai.

Hasil akhirnya disimpan dalam Postgres dan tersedia di dashboard web untuk dilihat, dicari, dan diekspor. Data text vendor (deskripsi, tagline, produk, industri) otomatis diterjemahkan ke Bahasa Indonesia menggunakan model NLLB-200 dari Meta. Versi English aslinya tetap disimpan jadi bisa di toggle bolak balik di dashboard.

Stack teknologi:
- Backend Python 3.11 dengan FastAPI dan LangGraph untuk pipeline orchestration
- Postgres 16 untuk storage utama, ChromaDB untuk vector deduplication, Redis untuk queue dan rate limiting
- Frontend Vue 3 dengan ECharts visualization
- Translasi NLLB-200 distilled 600M via CTranslate2 (jalan di CPU, ~1.2GB int8)
- Semua di dockerize, satu perintah `docker compose up` cukup

---

## 2. Persyaratan Sistem

Yang harus ada di mesin Anda sebelum mulai.

| Item | Minimum | Direkomendasikan |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Disk kosong | 20 GB | 40 GB |
| CPU | 4 core | 8 core |
| Docker Desktop | 4.30 atau lebih baru | terbaru |
| Koneksi internet | wajib (untuk OpenAI, Firecrawl, dan model download) | stabil |
| OS | Windows 10/11, macOS 12+, atau Linux | apa saja yang support Docker |

Yang harus dipersiapkan sebelum lanjut.

1. Docker Desktop terpasang dan running. Cek dengan `docker --version` dan `docker compose version`. Kalau dua duanya jalan, oke.
2. API Key OpenAI (jenis platform.openai.com, bukan ChatGPT). Dapat di https://platform.openai.com/api-keys. Pastikan billing nya aktif minimum 5 USD top up.
3. API Key Firecrawl. Dapat di https://www.firecrawl.dev. Free tier nya 500 credit per bulan, cukup untuk testing dan run dev mode.

Optional kalau mau ganti ke LLM lokal supaya tidak bayar OpenAI.

4. Ollama terpasang di host (bukan dalam Docker). Download di https://ollama.com.

---

## 3. Boot Pertama Kali

Lakukan urutan ini sekali saja saat pertama kali setup.

```bash
# Clone repo (atau extract dari zip kalau dapat versi snapshot)
git clone <REPO_URL> autocrawl
cd autocrawl

# Salin template env, lalu edit dua kunci paid
cp .env.example .env
```

Buka file `.env` di editor pilihan. Cari dua baris ini lalu ganti dengan kunci asli Anda.

```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxx
```

Variabel lain biarkan sesuai default. Bisa diubah kemudian kalau ada keperluan khusus (lihat bagian "Switch LLM Provider" dan "Aktifkan Translation").

Build dan start semua service.

```bash
docker compose build
docker compose up -d
```

Build pertama kali akan memakan waktu 15 sampai 25 menit karena harus download playwright chromium, surya OCR (3 GB), dan NLLB model (1.5 GB). Setelah itu cache nya tersimpan, build berikutnya jauh lebih cepat.

Kalau ingin build tanpa NLLB (untuk hemat ruang dan waktu, akan fallback otomatis ke OpenAI untuk translasi), tambahkan flag.

```bash
docker compose build --build-arg INSTALL_NLLB=false
```

---

## 4. Verifikasi Stack Hidup

Cek semua container running.

```bash
docker compose ps
```

Yang harus terlihat status `running` atau `healthy` (kolom STATUS).

```
autocrawl-crawler        running
autocrawl-api            healthy
autocrawl-db             healthy
autocrawl-frontend       running
autocrawl-redis          healthy
autocrawl-chroma         running
autocrawl-flaresolverr   running
autocrawl-langfuse       running
autocrawl-prometheus     running
autocrawl-grafana        running
```

Akses dashboard web di browser.

| URL | Untuk apa |
|---|---|
| http://localhost:8090 | Dashboard utama AutoCrawl |
| http://localhost:8081/api/health | API health check JSON |
| http://localhost:8081/api/docs | Swagger UI auto generated |
| http://localhost:3001 | Langfuse (LLM tracing, login pertama buat akun saja) |
| http://localhost:3000 | Grafana (metrics dashboard, login admin admin) |
| http://localhost:9090 | Prometheus raw metrics |

Kalau dashboard di port 8090 tampil tapi data kosong, itu wajar karena belum ada run yang dijalankan. Lanjut ke bagian berikutnya.

---

## 5. Run Pertama

Ada dua cara memicu run pertama.

### Cara A. Lewat dashboard

Buka http://localhost:8090. Di pojok kanan atas ada tombol "Jalankan run". Klik. Tombol berubah menjadi "Sedang berjalan" dengan badge kuning di samping judul. Pipeline akan jalan di background selama 5 sampai 15 menit (tergantung mode).

### Cara B. Lewat CLI di dalam container

```bash
docker compose exec api crawl run --mode dev
```

Mode `dev` artinya hanya 1 atau 2 expo yang diproses, cocok untuk smoke test pertama. Mode lain.

| Mode | Expo per run | Waktu | Cost OpenAI |
|---|---|---|---|
| dev | 1 atau 2 | 3 sampai 8 menit | ~0.05 USD |
| normal | 5 sampai 10 | 10 sampai 20 menit | ~0.30 USD |
| aggressive | 15 sampai 25 | 25 sampai 50 menit | ~1.20 USD |

Untuk run berkala otomatis (tiap 30 menit), container `crawler` sudah menjalankan scheduler bawaan. Cek log untuk konfirmasi.

```bash
docker compose logs -f crawler
```

Cari baris yang mengandung `scheduler.started` atau `pipeline.run_complete`.

---

## 6. Membaca Hasil

Setelah run selesai, refresh dashboard. Akan terlihat empat kartu di halaman Ringkasan.

- Vendors enriched: jumlah vendor unik yang sudah diperkaya
- Expos discovered: jumlah expo unik yang ditemukan
- PDFs processed: jumlah brosur PDF yang diekstrak
- Phase 2 progress: progress menuju ambang batas 100 vendor (saat tercapai, fitur paid Crunchbase dan Apollo otomatis aktif)

Klik tab "Daftar Vendor" untuk daftar lengkap. Klik salah satu baris untuk halaman detail. Di halaman detail.

- Header card berisi nama, domain, logo, deskripsi, tagline, industri, dan produk. Kalau vendor sudah diterjemahkan, tampil badge `ID` dan tombol `Lihat English` untuk swap ke teks asli.
- Card "Source Trail" menampilkan timeline dari mana data berasal (aggregator URL, PDF brosur, search resolution).
- Card sebelah kanan berisi kontak email/phone (lengkap dengan skor verifikasi), alamat, sosial media, info domain (registrar, umur, wayback), tech stack, dan daftar expo dimana vendor ini terlihat.

Akses raw data lewat API. Contoh ambil 10 vendor pertama.

```bash
curl http://localhost:8081/api/vendors?limit=10 | jq
```

Atau ambil satu vendor spesifik.

```bash
curl http://localhost:8081/api/vendors/airbus.com | jq
```

---

## 7. Migrasi Data Lama

Kalau Anda mengambil snapshot project ini dengan folder `data/reports/` sudah berisi JSON hasil run terdahulu, jalankan migrasi sekali untuk import ke Postgres.

```bash
docker compose exec api crawl db migrate
docker compose exec api crawl db import-json
```

Output akan menampilkan tabel ringkasan vendor, expo, dan run yang berhasil di import. Kalau ada baris error, cek detail nya di output. Biasanya kasusnya ada JSON lama yang formatnya beda (misal `source_trail` sebagai string biasa di versi awal). Importer otomatis migrate ke format baru.

Setelah import sukses, refresh dashboard. Data akan muncul.

---

## 8. Switch LLM Provider

Default provider adalah OpenAI (cloud, billed). Kalau ingin gratis, switch ke Ollama lokal.

Edit `.env`.

```
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OPENAI_MODEL_HEAVY=qwen3.5:14b
OPENAI_MODEL_LIGHT=qwen3.5:4b
OPENAI_EMBEDDING_MODEL=nomic-embed-text
```

Pull model nya di host (bukan di container).

```bash
ollama pull qwen3.5:14b
ollama pull qwen3.5:4b
ollama pull nomic-embed-text
```

Ollama default listen di `host.docker.internal:11434` yang sudah dikenal oleh container karena Docker Desktop menyediakan itu otomatis. Restart stack.

```bash
docker compose restart crawler api
```

Cek log untuk `ollama.warmup_ok`. Kalau muncul error koneksi, pastikan Ollama service sedang running di host (`ollama serve`).

Kelebihan Ollama: tidak ada limit token, tidak ada biaya. Kekurangan: lebih lambat 3 sampai 6 kali dibanding OpenAI cloud, dan butuh GPU lokal (NVIDIA dengan minimal 8 GB VRAM untuk model 4b, 16 GB untuk 14b).

---

## 9. Aktifkan Translation Bahasa Indonesia

Translation otomatis aktif kalau Anda build dengan default `INSTALL_NLLB=true`. Cek model nya sudah di download.

```bash
docker compose exec crawler ls -lh /app/data/nllb_ct2
```

Yang harus terlihat: file `model.bin` ukuran sekitar 600 sampai 700 MB plus beberapa file tokenizer.

Kalau folder kosong, build ulang dengan flag.

```bash
docker compose build --build-arg INSTALL_NLLB=true crawler
docker compose up -d crawler api
```

Untuk run translation pada vendor yang sudah ada di DB (backfill).

```bash
docker compose exec api crawl translate-vendors
```

Output akan menampilkan progress per vendor dengan tanda centang hijau atau silang merah. Akhir nya tabel ringkasan.

```
Translation results
   Metric        Count
   translated      44
   skipped          0
   failed           0
```

Vendor baru yang diproses setelah ini otomatis ikut diterjemahkan saat enrichment selesai. Jadi cukup sekali jalan backfill untuk data lama.

Verifikasi di dashboard: buka detail satu vendor, deskripsi nya sudah dalam Bahasa Indonesia, dan tombol kecil `Lihat English` aktif untuk balik ke versi asli.

Untuk matikan translation (misal mau simpan English saja), edit `.env`.

```
TRANSLATION_ENABLED=false
```

Lalu restart api dan crawler.

---

## 10. Tambah Scraper Custom

Setiap aggregator punya struktur HTML berbeda. Untuk menambah dukungan aggregator baru, buat file di `backend/src/crawler/tools/scrapers/<nama>.py`. Contoh skeleton.

```python
from __future__ import annotations
from urllib.parse import urljoin
from ...schemas import ExhibitorRef, SourceProvenance
from ..browsers.fetcher import fetch
from ..parsers.html_parser import parse
from ..proxies.rate_limit import acquire as rl_acquire

AGGREGATOR_DOMAIN = "namaaggregator.com"


def matches(url: str) -> bool:
    return AGGREGATOR_DOMAIN in url


async def list_exhibitors(expo_url: str, expo_id: str) -> list[ExhibitorRef]:
    await rl_acquire(expo_url)
    page = await fetch(expo_url, force_render=True)
    if not page.get("html"):
        return []

    tree = parse(page["html"])
    out: list[ExhibitorRef] = []
    for a in tree.css("a.exhibitor-link"):
        href = a.attributes.get("href") or ""
        absolute = href if href.startswith("http") else urljoin(page["url"], href)
        out.append(ExhibitorRef(
            expo_id=expo_id,
            name=a.text(strip=True)[:200],
            raw_url=absolute,
            aggregator_domain=AGGREGATOR_DOMAIN,
            provenance=[SourceProvenance(
                type="aggregator",
                url=absolute,
                extraction_method="custom_html",
            )],
        ))
    return out
```

Daftarkan di `backend/src/crawler/tools/scrapers/registry.py`.

```python
from . import generic, tentimes, wikipedia, namaaggregator

_REGISTRY = {
    "10times.com": tentimes,
    "wikipedia.org": wikipedia,
    "namaaggregator.com": namaaggregator,
}
```

Rebuild image agar code tersimpan.

```bash
docker compose build crawler api
docker compose up -d crawler api
```

Test cepat tanpa run penuh.

```bash
docker compose exec api python -c "
import asyncio
from crawler.tools.scrapers.namaaggregator import list_exhibitors
print(asyncio.run(list_exhibitors('https://namaaggregator.com/expo/foo', 'foo-2026')))
"
```

---

## 11. Test PDF Brosur

Brosur PDF expo seringkali memuat daftar exhibitor lengkap dengan nomor booth. AutoCrawl bisa download dan ekstrak. Test pada satu URL PDF.

```bash
docker compose exec api crawl pdf-test https://example.com/expo-brochure.pdf --expo-id manual-test
```

Output tabel berisi nama vendor, halaman, posisi, dan metode ekstraksi (`pymupdf` untuk PDF text murni, `pdfplumber_table` untuk tabel terstruktur, `surya_ocr` untuk PDF scan/image).

Kalau PDF Anda hanya hasil scan dan OCR diperlukan, pastikan `OCR_ENABLED=true` di `.env` dan image dibuild dengan `INSTALL_SURYA=true` (default).

---

## 12. Test Wikipedia

Untuk verify Wikipedia scraper bekerja, jalankan command khusus.

```bash
docker compose exec api crawl wiki-test https://en.wikipedia.org/wiki/2026_Bilderberg_Conference
```

Output tabel berisi nama organisasi, URL Wikipedia tujuan, metode ekstraksi (`wikipedia_link_company` atau `wikipedia_link_organisation`), dan skor confidence. Person diskip otomatis.

Vendor yang diidentifikasi lewat Wikipedia akan diresolusi domain aslinya saat full enrichment lewat search by name (karena Wikipedia bukan domain vendor langsung). Misal "AXA" hasil dari Wikipedia akan resolve ke `axa.com` lewat search engine.

---

## 13. Operations

### Restart container individual

```bash
docker compose restart crawler        # restart hanya scheduler
docker compose restart api            # restart hanya FastAPI
docker compose restart frontend       # restart hanya Vue dashboard
```

### Stop semua

```bash
docker compose down                   # stop, container terhapus, volume tetap
docker compose down -v                # stop, hapus juga semua volume (DESTRUCTIVE)
```

### Lihat log

```bash
docker compose logs -f crawler                   # follow log crawler
docker compose logs --tail 100 api               # 100 baris terakhir api
docker compose logs --since 1h crawler api       # 1 jam terakhir, dua container
```

### Backup data

Postgres data ada di volume `autocrawl_pgdata`. Snapshot manual.

```bash
docker compose exec autocrawl-db pg_dump -U postgres autocrawl > backup-$(date +%Y%m%d).sql
```

Restore.

```bash
cat backup-20260502.sql | docker compose exec -T autocrawl-db psql -U postgres autocrawl
```

JSON reports dan brosur PDF tersimpan di folder `./data` di host. Backup folder ini secara berkala kalau penting.

### Lihat queue Redis

```bash
docker compose exec redis redis-cli
> KEYS *
> LLEN urls:to_resolve
> exit
```

### Trigger run manual via curl

```bash
curl -X POST http://localhost:8081/api/runs/trigger -H "Content-Type: application/json" -d '{"mode":"normal"}'
```

---

## 14. Troubleshooting Umum

### Port conflict saat `docker compose up`

Pesan `bind for 0.0.0.0:8090 failed: port is already allocated`. Sudah ada service lain pakai port itu. Edit `docker-compose.yml`, cari port mapping yang konflik, ganti sisi kiri (host).

```yaml
ports:
  - "9090:80"   # ganti 8090 → 9090
```

Restart. Akses dashboard pindah ke http://localhost:9090.

### Database not ready saat first run

```
sqlalchemy.exc.OperationalError: connection refused
```

API container start sebelum Postgres siap. Tunggu 10-15 detik lalu cek `docker compose ps`. Kalau `autocrawl-db` masih belum `healthy`, lihat log nya untuk error detail.

```bash
docker compose logs autocrawl-db
```

Solusi cepat: restart api saja.

```bash
docker compose restart api
```

### DNS error `Name or service not known`

Container tidak bisa resolve hostname container lain. Biasa muncul kalau salah satu container di luar network `crawl_net`. Cek.

```bash
docker network inspect autocrawl_crawl_net
```

Container yang tidak terlihat di list "Containers" harus dijoin manual.

```bash
docker network connect autocrawl_crawl_net <nama-container>
```

### OOM (Out Of Memory)

Surya OCR atau NLLB load model bisa makan RAM. Kalau Docker Desktop di Windows/Mac, naikkan limit nya di Settings > Resources. Minimum 8 GB, recommended 16 GB.

Kalau RAM tetap tidak cukup, build tanpa NLLB.

```bash
docker compose build --build-arg INSTALL_NLLB=false
```

Translation akan fallback ke OpenAI gpt-4o-mini (billed tapi ringan).

### OpenAI 429 rate limit

Kalau hit limit `Tier 1` OpenAI (terutama saat mode aggressive), turunkan concurrency di `.env`.

```
EXPO_DISCOVERY_CONCURRENCY=2
EXHIBITOR_EXTRACTION_CONCURRENCY=5
ENRICHMENT_CONCURRENCY=10
```

Atau switch ke Ollama (lihat bagian 8).

### Frontend kosong tapi API balikin data

Browser cache. Hard refresh dengan Ctrl+Shift+R (Cmd+Shift+R di Mac). Kalau masih, buka DevTools, cek tab Network, lihat apakah `/api/overview` balikin 200 atau error.

Kalau error 502, biasanya nginx config di container frontend belum up to date. Rebuild.

```bash
docker compose build frontend
docker compose up -d frontend
```

### Trigger run balikin 409 Conflict

Pesan `A run is already active`. Tunggu run sekarang selesai, atau force kill dengan restart crawler container.

```bash
docker compose restart crawler
```

Lalu reset state active run di api.

```bash
docker compose restart api
```

Tombol di dashboard akan kembali bisa diklik.

---

## 15. FAQ

**Berapa biaya OpenAI per run?**

Ballpark per mode (asumsi gpt-4o-mini untuk light call dan gpt-4o untuk heavy merge).

- dev: 0.03 sampai 0.08 USD per run
- normal: 0.20 sampai 0.40 USD per run
- aggressive: 0.80 sampai 1.50 USD per run

Kalau mode normal jalan tiap 30 menit selama 24 jam = 48 run = 9.60 sampai 19.20 USD per hari. Untuk produksi pakai aggressive 1x sehari dan normal 4x sehari, totalnya sekitar 5 sampai 8 USD per hari.

Kalau switch ke Ollama, biaya OpenAI = 0. Tinggal listrik.

**Kapan butuh GPU?**

GPU dibutuhkan kalau Anda pakai Ollama dengan model 14b atau lebih besar. Untuk model 4b masih jalan di CPU (lambat tapi feasible). NLLB-200 distilled 600M sudah optimized int8 untuk CPU, tidak butuh GPU.

**Kapan unlock Phase 2?**

Saat kolom "Vendors enriched" mencapai 100 (default `PHASE_2_VENDOR_THRESHOLD=100`). Setelah itu, fitur paid (Crunchbase, Apollo, ZoomInfo) otomatis aktif untuk vendor yang sudah ada di DB. Tidak perlu restart, scheduler akan mendeteksi sendiri.

Untuk mengubah ambang batas, edit `.env`.

```
PHASE_2_VENDOR_THRESHOLD=50
```

**Bisakah jalan tanpa internet?**

Tidak. Crawler butuh akses ke 10times, Wikipedia, target vendor websites, plus OpenAI API. Kalau pakai Ollama dan disable Firecrawl + WHOIS lookup, secara teknis masih butuh akses ke target site untuk crawl. Internet wajib.

**Bisakah ekstrak data dari LinkedIn / Crunchbase langsung?**

Tidak via free tier. Keduanya punya anti scraping kuat dan TOS yang melarang scraping. Phase 2 (paid) pakai API resmi mereka.

**Berapa banyak data yang bisa disimpan?**

Postgres mudah handle ratusan ribu vendor. ChromaDB untuk vector dedup juga scalable. Limit utama adalah biaya OpenAI dan rate limit aggregator. Ballpark per stack lokal: 10.000 vendor enriched per minggu di mode normal.

**Bagaimana cara hapus duplikat vendor?**

Sudah otomatis lewat Chroma vector deduplication. Vendor dengan domain sama tidak akan diproses ulang. Vendor berbeda domain tapi nama mirip (misal `axa-france.com` dan `axa.com`) akan tetap dianggap dua entitas berbeda. Untuk merge manual, hapus salah satu via SQL.

```sql
DELETE FROM vendors WHERE domain = 'axa-france.com';
```

**Kenapa beberapa vendor language_code masih `en`?**

Bisa beberapa alasan.

1. Translation gagal saat enrichment (cek log `enricher.translation_failed`).
2. Vendor diimport dari JSON lama dan belum di backfill. Jalankan `crawl translate-vendors` untuk fix.
3. Field nya kosong (description null), jadi tidak ada yang perlu diterjemahkan, tapi `language_code` tetap diset `id`.

Untuk paksa translate ulang semua.

```bash
docker compose exec api crawl translate-vendors --force
```

**Apakah ada batas request ke Wikipedia?**

Wikipedia API mengizinkan 200 request per detik per IP, tanpa autentikasi. Kita batch 50 titles per request, jadi satu artikel dengan 300 link butuh 6 request. Aman untuk operasional normal.

---

Selamat menggunakan AutoCrawl. Kalau ada masalah yang tidak tercakup di sini, buka log container, cari pesan error, dan cocokkan dengan section Troubleshooting di atas. Kalau masih buntu, simpan log dan deskripsi langkah yang dilakukan, lalu konsultasikan ulang.
