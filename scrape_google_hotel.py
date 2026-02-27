"""
=============================================================================
  GOOGLE HOTELS SCRAPER  –  V10 PARALLEL (URL VERIFIER)
=============================================================================

ROOT CAUSE ERROR V6:
  undetected_chromedriver simpan 1 file binary di:
    ~/.local/share/undetected_chromedriver/undetected_chromedriver

  Ketika 5 worker start BERSAMAAN, semuanya rebutan file yang SAMA:
    W2: [Errno 26] Text file busy         ← sedang dipakai worker lain
    W3: FileNotFoundError chromedriver    ← dipindah worker lain duluan
    W1/W5: RemoteDisconnected             ← binary corrupt akibat race condition

FIX YANG DITERAPKAN (3 lapis):
  1. [UTAMA] Pre-copy chromedriver: buat N salinan ke direktori temp berbeda
             SEBELUM thread dimulai. Tiap worker punya binary sendiri.
  2. [EXTRA]  Stagger launch: Chrome di-init satu per satu via lock + jeda 3 detik.
              Cegah port conflict dan resource exhaustion di momen startup.
  3. [EXTRA]  Unique --user-data-dir per worker. Profile Chrome tidak overwrite.

=============================================================================
"""

import time
import re
import random
import traceback
import threading
import shutil
import os
import stat
import tempfile
import subprocess
import base64
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By


# ─────────────────────────────────────────────
#  THREAD-SAFE LOGGER
# ─────────────────────────────────────────────

_print_lock       = threading.Lock()
_chrome_init_lock = threading.Lock()   # Serialisasi inisialisasi Chrome

def tprint(worker_id: int, msg: str):
    with _print_lock:
        print(f"[W{worker_id}] {msg}")


# ─────────────────────────────────────────────
#  CHROMEDRIVER ISOLATION  ← FIX UTAMA
# ─────────────────────────────────────────────

def find_chromedriver_path() -> str | None:
    uc_default = os.path.join(
        os.path.expanduser("~"), ".local", "share",
        "undetected_chromedriver", "undetected_chromedriver"
    )
    if os.path.exists(uc_default):
        return uc_default
    found = shutil.which("chromedriver")
    return found or None


def prepare_chromedriver_copies(n_workers: int, chrome_ver: int | None) -> tuple:
    """
    Buat N salinan chromedriver + N user-data-dir sebelum thread dimulai.
    Return: (driver_paths_list, userdata_dirs_list)
    """
    print("\n[PREP] Menyiapkan isolated environment per worker...")

    # Pastikan chromedriver sudah ada (patch uc sekali jika belum)
    src = find_chromedriver_path()
    if not src:
        print("[PREP] Belum ada chromedriver, trigger patching awal...")
        try:
            opts = uc.ChromeOptions()
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            d = uc.Chrome(options=opts, use_subprocess=True, version_main=chrome_ver)
            d.quit()
            time.sleep(2)
        except Exception as e:
            print(f"[PREP] Trigger gagal: {e}")
        src = find_chromedriver_path()

    driver_paths = []
    if src:
        print(f"[PREP] Sumber binary: {src}")
        for i in range(n_workers):
            tmp = tempfile.mkdtemp(prefix=f"uc_w{i+1}_drv_")
            dst = os.path.join(tmp, "chromedriver")
            shutil.copy2(src, dst)
            os.chmod(dst, os.stat(dst).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            driver_paths.append(dst)
            print(f"[PREP]   W{i+1} driver → {dst}")
    else:
        print("[PREP][WARN] Binary tidak ditemukan — tiap worker patch mandiri (berisiko).")
        driver_paths = [None] * n_workers

    userdata_dirs = []
    for i in range(n_workers):
        udd = tempfile.mkdtemp(prefix=f"uc_w{i+1}_profile_")
        userdata_dirs.append(udd)
        print(f"[PREP]   W{i+1} profile → {udd}")

    return driver_paths, userdata_dirs


def cleanup_temp_dirs(driver_paths: list, userdata_dirs: list):
    all_dirs = set()
    for p in driver_paths:
        if p:
            all_dirs.add(os.path.dirname(p))
    for d in userdata_dirs:
        if d:
            all_dirs.add(d)
    for d in all_dirs:
        try:
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass


# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

TS_PARAMS = {"ts", "tts", "rp", "icts", "atd"}

BUTTON_SELECTORS = [
    "[aria-label*='Visit site']",
    "[aria-label*='Kunjungi situs']",
    "[aria-label*='View deal']",
    "[aria-label*='Book on']",
    "[aria-label*='Book at']",
    # Fallback broader selectors untuk tangkap Vio.com dan OTA baru
    "[aria-label*='Visit']",
    "[aria-label*='Book']",
    "[aria-label*='Reserve']",
    "[aria-label*='Get']",
]

AGENT_CLEANERS = [
    "Visit site for ", "Kunjungi situs untuk ", "Kunjungi situs",
    "View deal on ", "Book on ", "Book at ",
    "Visit ", "Book ", "Reserve on ", "Get deal on ", "Get deal at ",
]

EXPAND_KEYWORDS = [
    "view more", "lihat lebih", "more options", "opsi lainnya",
    "view all", "lihat semua", "more prices", "harga lainnya",
]
SKIP_KEYWORDS = ["fewer", "sedikit", "less", "hide", "sembunyikan"]


# ─────────────────────────────────────────────
#  URL BUILDER
# ─────────────────────────────────────────────

def encode_guests_param(n: int) -> str:
    """
    Encode jumlah tamu ke format Google Travel ap= (protobuf base64).
    Field 6, wire type 0 (varint), value = jumlah tamu.
    Verified: 1 tamu = MAE, 2 tamu = MAI, 3 tamu = MAM, 4 tamu = MAQ
    """
    data = bytes([0x30, max(1, min(n, 9))])  # clamp 1-9
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def build_clean_url(raw_url: str, checkin: str, checkout: str, num_guests: int = 1) -> str:
    parsed = urlparse(raw_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    for key in list(params.keys()):
        if key.lower() in TS_PARAMS:
            del params[key]
    params["checkin"]  = [checkin]
    params["checkout"] = [checkout]
    params["ap"]       = [encode_guests_param(num_guests)]  # FIX: inject jumlah tamu
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


# ─────────────────────────────────────────────
#  SPA BREAKER
# ─────────────────────────────────────────────

def hard_navigate(driver, url: str, clear_cookies: bool = False):
    """Navigasi dengan full SPA reset. clear_cookies=True untuk hard retry."""
    try:
        driver.get("about:blank")
        time.sleep(0.5)
        driver.execute_script("""
            try { window.localStorage.clear(); }   catch(e) {}
            try { window.sessionStorage.clear(); } catch(e) {}
            try {
                var req = indexedDB.databases ? indexedDB.databases() : null;
                if (req && req.then) req.then(function(dbs){
                    dbs.forEach(function(db){ indexedDB.deleteDatabase(db.name); });
                });
            } catch(e) {}
        """)
        time.sleep(0.3)
        if clear_cookies:
            KEEP = {'SAPISID','SSID','SID','HSID','APISID',
                    '__Secure-1PSID','__Secure-3PSID','OGPC','OGP'}
            try:
                for ck in driver.get_cookies():
                    if ck.get('name') not in KEEP:
                        try: driver.delete_cookie(ck['name'])
                        except: pass
            except: pass
    except Exception:
        pass
    driver.get(url)


def verify_url_date(driver, expected_checkin: str) -> bool:
    """
    Ground truth: URL di browser mengandung checkin yang benar?
    expected_checkin: "2026-03-15"
    Ini 100% reliable vs DOM parsing yang sering gagal.
    """
    try:
        return f"checkin={expected_checkin}" in driver.current_url
    except Exception:
        return False


# ─────────────────────────────────────────────
#  CHROME VERSION
# ─────────────────────────────────────────────

def get_chrome_version() -> int | None:
    for cmd in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
        if not shutil.which(cmd):
            continue
        try:
            out = subprocess.check_output([cmd, "--version"], stderr=-2, timeout=5).decode()
            m = re.search(r"(\d+)\.\d+", out)
            if m:
                v = int(m.group(1))
                print(f"[INIT] Chrome {out.strip()} → major: {v}")
                return v
        except Exception:
            continue
    try:
        out = subprocess.check_output(["chromedriver", "--version"], stderr=-2, timeout=5).decode()
        m = re.search(r"(\d+)\.\d+", out)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
#  WAIT FOR PRICES
# ─────────────────────────────────────────────

def wait_for_prices(driver, timeout: int = 22) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            for sel in BUTTON_SELECTORS[:2]:
                if driver.find_elements(By.CSS_SELECTOR, sel):
                    return True
            body = driver.find_element(By.TAG_NAME, "body").text
            if re.search(r"(Rp|IDR)\s?[\d,.]{4,}", body):
                return True
        except Exception:
            pass
        time.sleep(1.5)
    return False


# ─────────────────────────────────────────────
#  EXPAND AGENTS
# ─────────────────────────────────────────────

def expand_agents(driver, max_seconds: int = 20):
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.8)
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(0.4)
    except Exception:
        pass

    clicked  = set()
    deadline = time.time() + max_seconds
    while time.time() < deadline:
        found = False
        try:
            els = driver.find_elements(
                By.XPATH, "//*[self::span or self::button or self::div or self::a]"
            )
            for el in els:
                if time.time() > deadline:
                    break
                try:
                    if not el.is_displayed():
                        continue
                    txt = (el.text or "").strip().lower()
                    if not txt or len(txt) > 50 or txt in clicked:
                        continue
                    if any(k in txt for k in EXPAND_KEYWORDS) and \
                       not any(s in txt for s in SKIP_KEYWORDS):
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});", el)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", el)
                        clicked.add(txt)
                        time.sleep(1.3)
                        found = True
                except Exception:
                    continue
        except Exception:
            pass
        if not found:
            break


# ─────────────────────────────────────────────
#  SCRAPE PRICES
# ─────────────────────────────────────────────

def scrape_prices(driver) -> dict:
    raw = {}
    all_btns = []
    for sel in BUTTON_SELECTORS:
        try:
            all_btns.extend(driver.find_elements(By.CSS_SELECTOR, sel))
        except Exception:
            pass

    seen = set()
    buttons = []
    for btn in all_btns:
        try:
            eid = btn.id
            if eid not in seen:
                seen.add(eid)
                buttons.append(btn)
        except Exception:
            pass

    for btn in buttons:
        try:
            label = (btn.get_attribute("aria-label") or "").strip()
            if not label:
                continue
            agent = label
            for c in AGENT_CLEANERS:
                agent = agent.replace(c, "").strip()
            if not agent or len(agent) < 2 or "Google" in agent:
                continue

            price = None
            for depth in range(2, 8):
                try:
                    container = btn.find_element(By.XPATH, f"./ancestor::div[{depth}]")
                    ctxt = container.text
                    if any(kw in ctxt for kw in ["Similar", "Serupa", "Mirip"]):
                        break
                    m = re.search(r"(Rp|IDR)\s?([\d,.]+)", ctxt)
                    if m:
                        ps = m.group(2).replace(".", "").replace(",", "")
                        if ps.isdigit():
                            cp = int(ps)
                            if cp >= 50_000:
                                price = cp
                                break
                except Exception:
                    continue

            if price is None:
                continue
            if agent not in raw:
                raw[agent] = []
            raw[agent].append(price)
        except Exception:
            continue

    return {agent: min(prices) for agent, prices in raw.items()}




# ─────────────────────────────────────────────
#  WORKER
# ─────────────────────────────────────────────

def worker(worker_id: int, date_list: list, raw_url: str,
           duration: int, num_guests: int, chrome_ver: int | None,
           driver_path: str | None, userdata_dir: str,
           progress_lock: threading.Lock, progress: dict) -> list:

    tprint(worker_id, f"START — {len(date_list)} tanggal: "
                      f"{date_list[0].strftime('%d-%m-%Y')} s/d "
                      f"{date_list[-1].strftime('%d-%m-%Y')}")

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-application-cache")
    options.add_argument("--disk-cache-size=0")
    options.add_argument(f"--user-data-dir={userdata_dir}")
    options.add_argument(f"--remote-debugging-port={9220 + worker_id}")

    driver     = None
    local_data = []

    try:
        # ── Inisialisasi serial + stagger ──────────────────────────────
        with _chrome_init_lock:
            tprint(worker_id, "Init Chrome (serialized + stagger 3s)...")
            kwargs = dict(options=options, use_subprocess=True, version_main=chrome_ver)
            if driver_path and os.path.exists(driver_path):
                kwargs["driver_executable_path"] = driver_path
            driver = uc.Chrome(**kwargs)
            time.sleep(3)   # Jeda sebelum worker berikutnya boleh init

        # ── Warmup ─────────────────────────────────────────────────────
        tprint(worker_id, "Warmup — membangun sesi cookies...")
        driver.get(raw_url)
        time.sleep(random.uniform(7, 10))
        tprint(worker_id, "Warmup selesai.")

        for current_date in date_list:
            s_checkin  = current_date.strftime("%d-%m-%Y")
            s_checkout = (current_date + timedelta(days=duration)).strftime("%d-%m-%Y")
            u_checkin  = current_date.strftime("%Y-%m-%d")
            u_checkout = (current_date + timedelta(days=duration)).strftime("%Y-%m-%d")
            target_url = build_clean_url(raw_url, u_checkin, u_checkout, num_guests)

            prices = {}
            for attempt in range(1, 4):
                do_clear = (attempt >= 3)
                try:
                    hard_navigate(driver, target_url, clear_cookies=do_clear)

                    # URL VERIFIER — ground truth, tunggu URL browser = target
                    url_ok = False
                    for _ in range(10):
                        if verify_url_date(driver, u_checkin):
                            url_ok = True
                            break
                        time.sleep(1)

                    if not url_ok:
                        tag = " [+clear cookies]" if do_clear else ""
                        tprint(worker_id,
                               f"  [{s_checkin}] ⚠ SPA cache{tag} → retry {attempt+1}/3")
                        time.sleep(random.uniform(2, 3))
                        continue

                    tprint(worker_id, f"  [{s_checkin}] ✓ URL ok (attempt {attempt})")

                    if not wait_for_prices(driver, timeout=18):
                        time.sleep(2)

                    expand_agents(driver, max_seconds=18)
                    prices = scrape_prices(driver)

                    if not prices:
                        time.sleep(2)
                        continue

                    break
                except Exception as e:
                    tprint(worker_id, f"  [{s_checkin}] Attempt {attempt} error: {e}")
                    time.sleep(2)

            if prices:
                for agent, price in sorted(prices.items(), key=lambda x: x[1]):
                    local_data.append({
                        "Check-in":   s_checkin,
                        "Check-out":  s_checkout,
                        "Agent":      agent,
                        "Harga IDR":  price,
                        "Harga Teks": f"Rp {price:,}",
                    })
                tprint(worker_id, f"  ✓ [{s_checkin}] {len(prices)} agen | "
                                  f"min Rp {min(prices.values()):,}")
            else:
                tprint(worker_id, f"  ⚠ [{s_checkin}] 0 data")

            with progress_lock:
                progress["done"] += 1
                done, total = progress["done"], progress["total"]
                with _print_lock:
                    print(f"  [PROGRESS] {done}/{total} ({done/total*100:.1f}%)")

            time.sleep(random.uniform(2, 4))

    except Exception as e:
        tprint(worker_id, f"FATAL ERROR: {e}")
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        tprint(worker_id, f"SELESAI — {len(local_data)} baris.")

    return local_data


# ─────────────────────────────────────────────
#  DATE CHUNKER
# ─────────────────────────────────────────────

def split_dates(start_date, end_date, duration, n_workers):
    dates = []
    d = start_date
    while d + timedelta(days=duration) <= end_date:
        dates.append(d)
        d += timedelta(days=1)
    if not dates:
        return []
    k     = min(n_workers, len(dates))
    size  = len(dates) // k
    extra = len(dates) % k
    chunks, idx = [], 0
    for i in range(k):
        end_i = idx + size + (1 if i < extra else 0)
        chunks.append(dates[idx:end_i])
        idx = end_i
    return [c for c in chunks if c]


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def run_scraper_v10():
    print("\n" + "=" * 65)
    print("  GOOGLE HOTELS SCRAPER  –  V10 PARALLEL (URL VERIFIER)")
    print("=" * 65)
    print()
    print("  Rekomendasi worker:")
    print("    RAM  8GB → 3  |  RAM 16GB → 5  |  RAM 32GB → 8")
    print()

    start_str  = input("Tanggal Mulai   (DD-MM-YYYY): ").strip()
    end_str    = input("Tanggal Akhir   (DD-MM-YYYY): ").strip()
    duration   = int(input("Durasi Menginap (malam): ").strip())
    num_guests = int(input("Jumlah Tamu     (cth: 2): ").strip())
    n_workers  = int(input("Jumlah Worker   (cth: 3): ").strip())
    print()
    print("[PENTING] Copy URL dari address bar Chrome saat halaman harga terbuka.")
    raw_url   = input("URL Lengkap: ").strip()

    if "googleusercontent" in raw_url:
        print("[ERROR] URL Cache terdeteksi."); return
    if not raw_url.startswith("https://www.google.com/"):
        if input("[WARN] URL tidak diawali google.com — Lanjutkan? (y/n): ").lower() != "y":
            return

    try:
        start_date = datetime.strptime(start_str, "%d-%m-%Y")
        end_date   = datetime.strptime(end_str,   "%d-%m-%Y")
    except ValueError:
        print("[ERROR] Format tanggal salah."); return

    chunks = split_dates(start_date, end_date, duration, n_workers)
    if not chunks:
        print("[ERROR] Tidak ada tanggal valid."); return

    actual_workers = len(chunks)
    total_dates    = sum(len(c) for c in chunks)

    print(f"\n[INFO] Total tanggal: {total_dates} | Worker: {actual_workers}")
    for i, chunk in enumerate(chunks):
        print(f"       W{i+1}: {chunk[0].strftime('%d-%m-%Y')} → "
              f"{chunk[-1].strftime('%d-%m-%Y')} ({len(chunk)} hari)")

    chrome_ver = get_chrome_version()
    if not chrome_ver:
        manual = input("\n[WARN] Versi Chrome tidak terdeteksi. Masukkan manual (cth: 145): ").strip()
        chrome_ver = int(manual) if manual.isdigit() else None

    # ── Siapkan binary + profile terpisah per worker (sebelum thread) ──
    driver_paths, userdata_dirs = prepare_chromedriver_copies(actual_workers, chrome_ver)

    progress      = {"done": 0, "total": total_dates}
    progress_lock = threading.Lock()

    print(f"\n{'='*65}")
    print(f"  MULAI ({actual_workers} Chrome | stagger 3s antar init)")
    print(f"{'='*65}\n")

    start_time  = time.time()
    all_results = []

    try:
        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            futures = {
                executor.submit(
                    worker,
                    i + 1, chunk, raw_url, duration, num_guests, chrome_ver,
                    driver_paths[i], userdata_dirs[i],
                    progress_lock, progress,
                ): i + 1
                for i, chunk in enumerate(chunks)
            }
            for future in as_completed(futures):
                wid = futures[future]
                try:
                    all_results.extend(future.result())
                except Exception as e:
                    with _print_lock:
                        print(f"[ERROR] Worker {wid}: {e}")
    finally:
        cleanup_temp_dirs(driver_paths, userdata_dirs)

    elapsed = time.time() - start_time
    print(f"\n[INFO] Total waktu: {elapsed/60:.1f} menit")

    if all_results:
        df = pd.DataFrame(all_results)
        df = df.sort_values(["Check-in", "Harga IDR"]).reset_index(drop=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = f"harga_hotel_v10_{ts}.xlsx"

        with pd.ExcelWriter(fn, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Harga Detail", index=False)
            summary = df.groupby("Check-in").agg(
                Jumlah_Agen=("Agent", "count"),
                Harga_Min  =("Harga IDR", "min"),
                Harga_Max  =("Harga IDR", "max"),
                Harga_Rata =("Harga IDR", "mean"),
            ).reset_index()
            summary["Harga_Rata"] = summary["Harga_Rata"].astype(int)
            summary.to_excel(writer, sheet_name="Ringkasan", index=False)
            try:
                pivot = df.pivot_table(
                    index="Agent", columns="Check-in",
                    values="Harga IDR", aggfunc="min"
                )
                pivot.to_excel(writer, sheet_name="Pivot Agen x Tanggal")
            except Exception:
                pass

        print(f"\n{'='*65}")
        print(f"  [SUKSES] {len(all_results)} baris → {fn}")
        print(f"  Waktu: {elapsed/60:.1f} menit")
        print(f"{'='*65}")

        print("\n[VALIDASI]")
        for agent in sorted(df["Agent"].unique()):
            prices = df[df["Agent"] == agent]["Harga IDR"].unique()
            print(f"  {'✓' if len(prices)>1 else '⚠ STUCK'}  {agent:<35} {len(prices)} variasi")
    else:
        print("\n[ERROR] Tidak ada data. Periksa CAPTCHA / koneksi.")


if __name__ == "__main__":
    run_scraper_v10()