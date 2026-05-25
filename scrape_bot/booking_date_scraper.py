import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_LOCATION      = "Balian Beach"
DEFAULT_START_DATE    = "2026-04-01"
DEFAULT_END_DATE      = "2026-04-30"
DEFAULT_MAX_PROPERTIES = 15
DEFAULT_MIN_PRICE     = None   # None = tidak ada batas bawah
DEFAULT_MAX_PRICE     = None   # None = tidak ada batas atas


# ── Helpers ───────────────────────────────────────────────────────────────────

def print_header():
    print("\n" + "═" * 60)
    print("  🔍  Booking.com Competitor Scraper")
    print("═" * 60)
    print("  Tekan ENTER untuk memakai nilai default [dalam kurung].")
    print("─" * 60 + "\n")


def ask(prompt: str, default=None, cast=None, allow_empty: bool = True):
    """
    Menampilkan prompt interaktif.
    - Jika user menekan ENTER (kosong) → kembalikan `default`.
    - `cast` : fungsi konversi tipe (misalnya int).
    - `allow_empty` : jika False, terus ulang sampai user mengisi nilai.
    """
    default_label = f"[{default}]" if default is not None else "[kosong/tidak ada]"
    while True:
        raw = input(f"  {prompt} {default_label}: ").strip()

        # Kosong → pakai default
        if raw == "":
            return default

        # Ada isian → coba konversi
        if cast:
            try:
                return cast(raw)
            except (ValueError, TypeError):
                print(f"    ⚠  Input tidak valid, masukkan angka yang benar.\n")
                continue

        return raw


def ask_date(prompt: str, default: str) -> str:
    """Khusus input tanggal dengan validasi format YYYY-MM-DD."""
    while True:
        raw = input(f"  {prompt} [{default}]: ").strip()
        if raw == "":
            return default
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print("    ⚠  Format tanggal salah. Gunakan YYYY-MM-DD (contoh: 2026-05-01).\n")


def collect_inputs() -> dict:
    """Tampilkan form interaktif satu per satu dan kembalikan dict konfigurasi."""
    print_header()

    location = ask(
        "Lokasi pencarian         ",
        default=DEFAULT_LOCATION
    )

    start_date = ask_date(
        "Tanggal mulai check-in   ",
        default=DEFAULT_START_DATE
    )

    end_date = ask_date(
        "Tanggal akhir check-in   ",
        default=DEFAULT_END_DATE
    )

    max_properties = ask(
        "Maks. properti per malam ",
        default=DEFAULT_MAX_PROPERTIES,
        cast=int
    )

    min_price = ask(
        "Harga minimum (Rp)       ",
        default=DEFAULT_MIN_PRICE,
        cast=int
    )

    max_price = ask(
        "Harga maksimum (Rp)      ",
        default=DEFAULT_MAX_PRICE,
        cast=int
    )

    # Output filename → dibuat otomatis, user bisa override
    auto_name = generate_unique_filename(location)
    output_file = ask(
        f"Nama file output         ",
        default=auto_name
    )

    return {
        "location":       location,
        "start_date":     start_date,
        "end_date":       end_date,
        "max_properties": max_properties,
        "min_price":      min_price,
        "max_price":      max_price,
        "output_file":    output_file,
    }


def print_summary(cfg: dict, total_nights: int):
    """Cetak ringkasan konfigurasi sebelum scraping dimulai."""
    price_parts = []
    if cfg["min_price"]:
        price_parts.append(f">= Rp {cfg['min_price']:,}")
    if cfg["max_price"]:
        price_parts.append(f"<= Rp {cfg['max_price']:,}")

    print("\n" + "─" * 60)
    print("  📋  Konfigurasi scraping:")
    print(f"      Lokasi       : {cfg['location']}")
    print(f"      Rentang      : {cfg['start_date']} s/d {cfg['end_date']}  ({total_nights} malam)")
    print(f"      Max/malam    : {cfg['max_properties']} properti")
    print(f"      Filter harga : {' & '.join(price_parts) if price_parts else 'tidak ada'}")
    print(f"      Output       : {cfg['output_file']}")
    print("─" * 60)

    confirm = input("\n  Lanjutkan scraping? [Y/n]: ").strip().lower()
    if confirm in ("n", "no", "tidak"):
        print("\n  ❌  Scraping dibatalkan.\n")
        raise SystemExit(0)
    print()


# ── Core utilities ────────────────────────────────────────────────────────────

def generate_unique_filename(location: str, prefix: str = "booking") -> str:
    timestamp_ms  = int(datetime.now().timestamp() * 1000)
    location_slug = re.sub(r'[^\w\-]', '-', location.strip()).strip('-')
    return f"{prefix}_{location_slug}_{timestamp_ms}.xlsx"


def generate_date_ranges(start_date: str, end_date: str) -> List[tuple]:
    start   = datetime.strptime(start_date, "%Y-%m-%d")
    end     = datetime.strptime(end_date,   "%Y-%m-%d")
    ranges  = []
    current = start
    while current < end:
        next_day = current + timedelta(days=1)
        ranges.append((current.strftime("%Y-%m-%d"), next_day.strftime("%Y-%m-%d")))
        current = next_day
    return ranges


def setup_driver() -> webdriver.Chrome:
    opts = Options()
    # Uncomment baris berikut untuk mode headless (tanpa buka browser):
    # opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


# ── Scraper ───────────────────────────────────────────────────────────────────

def run_scraper(cfg: dict):
    location       = cfg["location"]
    start_date     = cfg["start_date"]
    end_date       = cfg["end_date"]
    max_properties = cfg["max_properties"]
    min_price      = cfg["min_price"]
    max_price      = cfg["max_price"]
    output_file    = cfg["output_file"]

    dates = generate_date_ranges(start_date, end_date)
    print_summary(cfg, len(dates))

    driver            = setup_driver()
    all_scraped_data: List[Dict] = []

    try:
        for checkin, checkout in dates:
            print(f"  [SCRAPING] {checkin} → {checkout} ... ", end="", flush=True)

            loc_fmt = location.replace(" ", "+")
            url = (
                f"https://www.booking.com/searchresults.html"
                f"?ss={loc_fmt}&checkin={checkin}&checkout={checkout}"
                f"&group_adults=2&no_rooms=1&group_children=0"
            )
            driver.get(url)

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="property-card"]'))
                )
            except Exception:
                print("timeout / tidak ada properti.")
                continue

            scroll_count = 5 if (min_price or max_price) else 3
            for i in range(1, scroll_count + 1):
                driver.execute_script(
                    f"window.scrollTo(0, document.body.scrollHeight * {i / scroll_count});"
                )
                time.sleep(1.5)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            cards       = driver.find_elements(By.CSS_SELECTOR, '[data-testid="property-card"]')
            valid_count = 0

            for card in cards:
                if valid_count >= max_properties:
                    break
                try:
                    name_el = card.find_element(By.CSS_SELECTOR, '[data-testid="title"]')
                    name    = name_el.text.strip()
                    if not name:
                        continue

                    try:
                        price_el    = card.find_element(By.CSS_SELECTOR, '[data-testid="price-and-discounted-price"]')
                        price_clean = re.sub(r'[^\d]', '', price_el.text.strip())
                        price       = int(price_clean) if price_clean else None
                    except Exception:
                        price = None

                    if price is None:
                        continue
                    if min_price is not None and price < min_price:
                        continue
                    if max_price is not None and price > max_price:
                        continue

                    all_scraped_data.append({
                        "Tanggal Stay":  f"{checkin} to {checkout}",
                        "Check-in":      checkin,
                        "Check-out":     checkout,
                        "Nama Property": name,
                        "Harga":         price,
                    })
                    valid_count += 1

                except Exception:
                    continue

            print(f"{valid_count} properti.")

    finally:
        print("\n  Menutup browser...")
        driver.quit()

    if all_scraped_data:
        df = pd.DataFrame(all_scraped_data)
        df.to_excel(output_file, index=False, engine="openpyxl")
        print(f"\n  ✅  Scraping selesai! {len(all_scraped_data)} data tersimpan ke: {output_file}\n")
    else:
        print("\n  ⚠️   Tidak ada data yang cocok dengan kriteria Anda.\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        config = collect_inputs()
        run_scraper(config)
    except (KeyboardInterrupt, EOFError):
        print("\n\n  ❌  Dibatalkan oleh pengguna.\n")