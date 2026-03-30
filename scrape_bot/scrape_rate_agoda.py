from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
import time
import os
import re

def scrape_agoda_rates(url, checkin_date, checkout_date, output_filename=None):
    if output_filename is None:
        hotel_name = url.split('/')[-3] if len(url.split('/')) > 3 else "agoda_hotel"
        if not os.path.exists("dataset_agoda"):
            os.makedirs("dataset_agoda")
        output_filename = f"dataset_agoda/{hotel_name}_rates_{checkin_date}.csv"

    rates_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        page = context.new_page()
        
        print(f"Mengakses: {url}")
        try:
            page.goto(url, timeout=90000)
            # Menunggu agar skeleton loading hilang
            page.wait_for_selector('[data-selenium="searchBox"]', state='visible', timeout=20000)
            time.sleep(3)
        except Exception as e:
            print(f"Gagal membuka URL atau Searchbox tidak ditemukan: {e}")
            return

        # --- FASE 1: INTERAKSI KALENDER ---
        print(f"Mengatur tanggal Check-in: {checkin_date} & Check-out: {checkout_date}")
        try:
            # 1. Pastikan dan klik box check-in di dalam div SearchBox horizontal yang aktif
            searchbox_area = page.locator('div[data-selenium="searchBox"]')
            checkin_box = searchbox_area.locator('#check-in-box')
            checkin_box.scroll_into_view_if_needed()
            checkin_box.click(force=True)
            
            # Tunggu kontainer kalender popup muncul
            page.wait_for_selector('.DayPicker-wrapper', state='visible', timeout=15000)
            time.sleep(1)
            
            def select_date(target_date):
                date_span = page.locator(f'span[data-selenium-date="{target_date}"]')
                next_btn = page.locator('button[data-selenium="calendar-next-month-button"]')
                
                # Geser maksimal 12 kali (1 tahun ke depan)
                for _ in range(12):
                    if date_span.count() > 0 and date_span.first.is_visible():
                        date_span.first.click(force=True)
                        return True
                    
                    if next_btn.is_visible() and not next_btn.is_disabled():
                        next_btn.click(force=True)
                        time.sleep(0.5)
                    else:
                        break
                return False

            # 2. Set Check-in
            print("Mencari tanggal Check-in...")
            if not select_date(checkin_date):
                print("Gagal menemukan/klik tanggal checkin. Melanjutkan dengan default.")
            time.sleep(1)
            
            # 3. Set Check-out
            print("Mencari tanggal Check-out...")
            if not select_date(checkout_date):
                print("Gagal menemukan/klik tanggal checkout. Melanjutkan dengan default.")
            time.sleep(1)
            
            # 4. Klik Search / Update
            search_btn = page.locator('button[data-selenium="searchButton"]')
            if search_btn.is_visible():
                search_btn.click(force=True)
            else:
                page.keyboard.press('Escape')
                
            print("Menunggu Agoda memuat harga baru (10 detik)...")
            # Waktu ekstra agar Agoda selesai menarik data dari servernya (AJAX/Fetch)
            time.sleep(10)
            
        except Exception as e:
            print(f"Peringatan saat set kalender: {e}. Bot akan lanjut scrape apa yang ada.")

        # --- FASE 1.5: BYPASS LAZY LOADING ---
        print("Melakukan scroll perlahan untuk memuat semua tipe kamar (Lazy Loading)...")
        try:
            # Scroll perlahan dari atas ke bawah
            for _ in range(8):
                page.mouse.wheel(0, 800)
                time.sleep(1.5)
            # Kembalikan ke atas
            page.mouse.wheel(0, -6000)
            time.sleep(2)
        except Exception:
            pass

        # --- FASE 2: EKSTRAKSI DATA ---
        print("Mulai mengekstrak data kamar dan harga...")
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Mencari kontainer utama untuk tipe kamar (berdasarkan HTML terbaru)
        master_rooms = soup.find_all('div', class_=lambda x: x and 'MasterRoom' in x and 'ChildRoomsList' not in x)
        
        # Jika DOM Desktop standar tidak ditemukan, coba cari DOM Mobile (sebagai fallback dari script sebelumnya)
        if not master_rooms:
            print("Mode Desktop tidak terdeteksi. Mencoba mengekstrak menggunakan mode Mobile...")
            # Fallback ke pencarian data-testid="room-item" seperti sebelumnya
            master_rooms = soup.find_all('div', {'data-testid': 'room-item'})
            is_mobile_view = True
        else:
            is_mobile_view = False
            
        print(f"Ditemukan {len(master_rooms)} tipe kamar. (Format: {'Mobile' if is_mobile_view else 'Desktop'})")

        for room in master_rooms:
            if not is_mobile_view:
                # EKSTRAKSI UNTUK DOM DESKTOP (Sesuai HTML Kedua)
                title_el = room.find('span', {'data-selenium': 'masterroom-title-name'})
                room_name = title_el.text.strip() if title_el else "Unknown Room"
                
                # Satu tipe kamar (MasterRoom) memiliki banyak penawaran harga (ChildRoom)
                child_rooms = room.find_all('div', class_=lambda x: x and 'ChildRoomsList-room' in x and 'ChildRoomsList-roomCell' not in x)
                
                for child in child_rooms:
                    # Ambil Harga
                    # Kita cari atribut data-fpc-value di div data-element-name="fpc-room-price"
                    price_val = "N/A"
                    price_container = child.find('div', {'data-element-name': 'fpc-room-price'})
                    if price_container:
                        # Value-nya kadang berupa string "1,453,239" atau "Rp 1,453,239"
                        raw_price = price_container.get('data-fpc-value', "")
                        # Bersihkan karakter non-digit kecuali koma/titik desimal
                        clean_price = re.sub(r'[^\d]', '', raw_price)
                        if clean_price:
                            price_val = clean_price
                    
                    # Ambil Manfaat (Breakfast, Cancellation, dll)
                    benefits = []
                    # Cari semua paragraf yang mengandung Typographystyled di dalam kotak fitur
                    feature_bucket = child.find('div', class_='ChildRoomsList-room-featurebuckets')
                    if feature_bucket:
                        texts = feature_bucket.find_all('p', class_=lambda x: x and 'Typographystyled' in x)
                        for t in texts:
                            bt = t.text.strip()
                            if bt:
                                benefits.append(bt)
                    
                    benefit_str = " | ".join(benefits[:3]) if benefits else "Standard Offer"

                    # Ambil Badge (Diskon/Promo)
                    discount_badge = child.find('div', {'data-element-name': 'consolidated-applied-discount-badge'})
                    discount_info = discount_badge.text.strip() if discount_badge else "No Discount"
                    
                    if price_val != "N/A":
                        rates_data.append({
                            'scrape_date': time.strftime("%Y-%m-%d"),
                            'checkin_date': checkin_date,
                            'checkout_date': checkout_date,
                            'room_type': room_name,
                            'package_details': benefit_str,
                            'price_idr': price_val,
                            'discount_info': discount_info
                        })
            else:
                # --- FALLBACK UNTUK DOM MOBILE ---
                room_name_el = room.find('div', {'data-testid': 'room-name'})
                room_name = room_name_el.text.strip() if room_name_el else "Unknown Room"
                
                offers = room.find_all('div', {'data-testid': 'room-offer'})
                for offer in offers:
                    price_el = offer.find('div', {'data-element-name': 'fpc-room-price'})
                    price = price_el.get('data-fpc-value') if price_el else "N/A"
                    
                    discount_el = offer.find('div', {'data-element-name': 'mob-room-offer-downlift-badge'})
                    discount_info = discount_el.text.strip() if discount_el else "No Discount"

                    benefits = []
                    benefit_list = offer.find_all('p', class_=lambda x: x and 'Typographystyled' in x)
                    for b in benefit_list[:2]:
                        text_val = b.text.strip()
                        if text_val and "adults" not in text_val.lower() and "price" not in text_val.lower():
                            benefits.append(text_val)
                    benefit_text = " | ".join(benefits) if benefits else "Standard Offer"

                    if price != "N/A":
                        rates_data.append({
                            'scrape_date': time.strftime("%Y-%m-%d"),
                            'checkin_date': checkin_date,
                            'checkout_date': checkout_date,
                            'room_type': room_name,
                            'package_details': benefit_text,
                            'price_idr': price,
                            'discount_info': discount_info
                        })

        browser.close()

    # --- FASE 3: PENYIMPANAN DATA ---
    if rates_data:
        print(f"\nBerhasil mengekstrak {len(rates_data)} variasi harga!")
        print(f"Menyimpan data ke {output_filename}...")
        keys = rates_data[0].keys()
        
        with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(rates_data)
        print("SELESAI! Data berhasil disimpan.")
    else:
        print("\nTidak ada data harga yang berhasil diekstrak. Kemungkinan sold out atau struktur berubah lagi.")

if __name__ == "__main__":
    print("=== Agoda Rate Scraper (Robust) ===")
    # target_url = input("Masukkan URL Agoda: ").strip()
    # in_date = input("Masukkan tanggal Check-in (Format YYYY-MM-DD, contoh: 2026-03-06): ").strip()
    # out_date = input("Masukkan tanggal Check-out (Format YYYY-MM-DD, contoh: 2026-03-07): ").strip()
    
    target_url = "https://www.agoda.com/pondok-pitaya-hotel/hotel/bali-id.html"
    in_date = "2026-03-07"
    out_date = "2026-04-07"
    
    if target_url and in_date and out_date:
        scrape_agoda_rates(target_url, in_date, out_date)
    else:
        print("URL dan Tanggal tidak boleh kosong.")