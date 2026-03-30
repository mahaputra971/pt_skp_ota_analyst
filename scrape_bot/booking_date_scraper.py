import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import pandas as pd
import typer
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from typing_extensions import Annotated

app = typer.Typer()

def generate_date_ranges(start_date: str, end_date: str) -> List[tuple]:
    """Menghasilkan list tuple berisi (checkin_date, checkout_date) dengan rentang 1 hari."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    date_ranges = []
    current_date = start
    
    while current_date < end:
        next_date = current_date + timedelta(days=1)
        date_ranges.append((current_date.strftime("%Y-%m-%d"), next_date.strftime("%Y-%m-%d")))
        current_date = next_date
        
    return date_ranges

def setup_driver() -> webdriver.Chrome:
    """Menginisiasi Selenium Chrome Driver."""
    chrome_options = Options()
    # Hapus tanda '#' pada baris di bawah ini jika ingin menjalankan tanpa membuka browser (background)
    # chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

@app.command()
def scrape_booking(
    location: Annotated[str, typer.Option(help="Nama lokasi pencarian")] = "Balian Beach",
    start_date: Annotated[str, typer.Option(help="Tanggal mulai (Format: YYYY-MM-DD)")] = "2026-04-01",
    end_date: Annotated[str, typer.Option(help="Tanggal selesai (Format: YYYY-MM-DD)")] = "2026-04-30",
    max_properties: Annotated[int, typer.Option(help="Maksimal property per tanggal")] = 15,
    max_price: Annotated[Optional[int], typer.Option(help="Batas maksimal harga property dalam Rupiah (contoh: 1500000)")] = None, # PARAMETER BARU
    output_file: Annotated[str, typer.Option(help="Nama file Excel output")] = "booking_competitors.xlsx"
):
    dates = generate_date_ranges(start_date, end_date)
    print(f"Total rentang tanggal yang akan di-scrape: {len(dates)} malam.")
    if max_price:
        print(f"Filter aktif: Hanya mengambil property dengan harga <= Rp {max_price:,}")
    
    driver = setup_driver()
    all_scraped_data: List[Dict] = []
    
    try:
        for checkin, checkout in dates:
            print(f"Scraping untuk tanggal: {checkin} sampai {checkout}...")
            
            location_formatted = location.replace(" ", "+")
            url = f"https://www.booking.com/searchresults.html?ss={location_formatted}&checkin={checkin}&checkout={checkout}&group_adults=2&no_rooms=1&group_children=0"
            driver.get(url)
            
            # Tunggu elemen pertama muncul
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="property-card"]'))
                )
            except Exception:
                print(f"  -> Timeout/tidak ada properti untuk {checkin}.")
                continue
            
            # SCROLLING LOGIC: Untuk memancing lazy-load gambar dan harga
            # Scroll diperbanyak jika menggunakan filter, untuk memastikan lebih banyak kartu ter-*load*
            scroll_count = 5 if max_price else 3
            for i in range(1, scroll_count + 1):
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {i/scroll_count});")
                time.sleep(1.5)
            
            # Tarik ulang ke atas perlahan
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            property_cards = driver.find_elements(By.CSS_SELECTOR, '[data-testid="property-card"]')
            
            valid_properties_count = 0
            
            for card in property_cards:
                if valid_properties_count >= max_properties:
                    break # Berhenti jika sudah mencapai batas per tanggal
                
                try:
                    # Ekstrak Nama
                    name_element = card.find_element(By.CSS_SELECTOR, '[data-testid="title"]')
                    property_name = name_element.text.strip()
                    
                    if not property_name:
                        continue
                        
                    # Ekstrak Harga
                    try:
                        price_element = card.find_element(By.CSS_SELECTOR, '[data-testid="price-and-discounted-price"]')
                        price_raw = price_element.text.strip()
                        
                        # CLEANING: Ambil hanya angka dari string
                        price_clean = re.sub(r'[^\d]', '', price_raw)
                        final_price = int(price_clean) if price_clean else None
                        
                    except Exception:
                        final_price = None
                    
                    # Jika gagal mendapatkan harga numerik (misal sold out), lewati saja agar tidak merusak filter
                    if final_price is None:
                        continue
                    
                    # LOGIKA FILTER HARGA (PARAMETER BARU)
                    if max_price is not None and final_price > max_price:
                        continue # Lewati jika harga melebihi batas maksimal yang diinginkan
                    
                    all_scraped_data.append({
                        "Tanggal Stay": f"{checkin} to {checkout}",
                        "Check-in": checkin,
                        "Check-out": checkout,
                        "Nama Property": property_name,
                        "Harga": final_price
                    })
                    
                    valid_properties_count += 1
                    
                except Exception as e:
                    # Abaikan error pada satu card spesifik
                    continue
            
            print(f"  -> Mendapatkan {valid_properties_count} property sesuai kriteria.")
                    
    finally:
        print("Menutup browser...")
        driver.quit()
    
    if all_scraped_data:
        df = pd.DataFrame(all_scraped_data)
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\nScraping selesai! Berhasil mengambil {len(all_scraped_data)} data kompetitor.")
        print(f"Data telah disimpan ke dalam file: {output_file}")
    else:
        print("\nTidak ada data yang cocok dengan kriteria Anda.")

if __name__ == "__main__":
    app()