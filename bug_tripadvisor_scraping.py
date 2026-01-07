from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
import time
import random
import re

# --- KONFIGURASI PENTING ---
# Ganti ini dengan IP Windows yang Bli dapat dari 'cat /etc/resolv.conf' di WSL
# Contoh: "172.25.160.1"
WINDOWS_IP = "172.20.80.1" 

def scrape_tripadvisor_cdp(output_filename="tripadvisor_reviews_real.csv"):
    unique_reviews = set() 
    reviews_data = []

    print(f"Menghubungkan ke Chrome Asli di Windows ({WINDOWS_IP}:9222)...")
    
    with sync_playwright() as p:
        try:
            # HUBUNGKAN WSL KE WINDOWS CHROME
            # Kita gunakan IP Windows, bukan localhost
            browser = p.chromium.connect_over_cdp(f"http://{WINDOWS_IP}:9222")
        except Exception as e:
            print(f"❌ GAGAL KONEK ke {WINDOWS_IP}:9222")
            print("Pastikan Chrome di Windows sudah dibuka via CMD dengan perintah:")
            print('chrome.exe --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="C:\\temp\\chrome_debug_profile"')
            print(f"Error detail: {e}")
            return

        # Ambil halaman yang sedang aktif di Chrome Windows
        if not browser.contexts:
            print("⚠️ Browser terhubung tapi tidak ada context. Coba buka tab baru di Chrome Windows.")
            return
            
        context = browser.contexts[0]
        if not context.pages:
            print("⚠️ Browser terhubung tapi tidak ada tab terbuka. Membuka tab baru...")
            page = context.new_page()
        else:
            page = context.pages[0] 
        
        print(f"✅ Berhasil terhubung ke halaman: {page.title()}")
        print("Mulai scraping...")

        page_num = 1
        
        while True:
            print(f"--- Sedang scraping Halaman {page_num} ---")
            
            # 1. Expand Text (Klik Selengkapnya)
            try:
                # Gunakan JS murni agar lebih cepat & tidak terdeteksi
                page.evaluate("""
                    const buttons = document.querySelectorAll("span");
                    buttons.forEach(btn => {
                        if (btn.innerText.includes('Selengkapnya')) {
                            btn.click();
                        }
                    });
                """)
                time.sleep(2) # Tunggu text terbuka
            except: pass

            # 2. Ambil HTML langsung
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Selector Kartu Review
            review_cards = soup.find_all('div', attrs={'data-test-target': 'HR_CC_CARD'})
            
            if not review_cards:
                print("⚠️ Tidak menemukan kartu review. Pastikan halaman TripAdvisor sudah terbuka di Chrome Windows.")
            
            new_reviews_found = 0
            for card in review_cards:
                try:
                    # Judul
                    title_el = card.find('div', attrs={'data-test-target': 'review-title'})
                    review_title = title_el.text.strip() if title_el else ""

                    # Text Review
                    text_span = card.find('span', class_='JguWG') 
                    if not text_span:
                        text_div = card.find('div', class_=lambda x: x and 'fIrGe' in x)
                        review_text = text_div.text.strip() if text_div else ""
                    else:
                        review_text = text_span.text.strip()
                    
                    if not review_text: continue

                    # Rating
                    rating = "N/A"
                    svg_el = card.find('svg', attrs={'title': True})
                    if not svg_el: svg_el = card.find('svg', class_='UctUV')
                    if svg_el and svg_el.find('title'):
                        title_text = svg_el.find('title').text 
                        match = re.search(r'(\d+[.,]?\d*)', title_text)
                        if match: rating = match.group(1).replace(',', '.')

                    # Nama
                    name_el = card.find('a', href=lambda x: x and '/Profile/' in x)
                    reviewer_name = name_el.text.strip() if name_el else "Anonymous"

                    # Tanggal
                    stay_date = "N/A"
                    date_label = card.find(string=re.compile("Tanggal menginap"))
                    if date_label and date_label.parent:
                        next_span = date_label.parent.find_next_sibling('span')
                        if next_span: stay_date = next_span.text.strip()

                    review_signature = f"{reviewer_name}_{review_text[:30]}"
                    if review_signature not in unique_reviews:
                        unique_reviews.add(review_signature)
                        reviews_data.append({
                            'reviewer_name': reviewer_name,
                            'rating': rating,
                            'review_title': review_title,
                            'review_text': review_text,
                            'stay_date': stay_date
                        })
                        new_reviews_found += 1
                except: continue
            
            print(f"  + Berhasil mengambil {new_reviews_found} review.")

            # 3. Pagination (Klik Next)
            next_selector = 'a[data-smoke-attr="pagination-next-arrow"]'
            
            if page.locator(next_selector).count() > 0:
                # Cek disabled
                is_disabled = page.evaluate(f"""
                    const btn = document.querySelector('{next_selector}');
                    btn && (btn.classList.contains('disabled') || btn.classList.contains('ui_button_disabled'))
                """)
                
                if is_disabled:
                    print("Tombol Next disabled. Selesai.")
                    break
                
                print("Klik Next Page >>")
                try:
                    page.locator(next_selector).first.click()
                    time.sleep(random.uniform(5, 7))
                    page_num += 1
                except Exception as e:
                    print(f"Gagal klik next: {e}")
                    break
            else:
                print("Tombol Next tidak ditemukan. Berhenti.")
                break
        
        print("Selesai scraping.")

    # Simpan CSV
    if reviews_data:
        keys = reviews_data[0].keys()
        with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(reviews_data)
        print(f"✅ Data tersimpan di {output_filename}")

if __name__ == "__main__":
    scrape_tripadvisor_cdp()