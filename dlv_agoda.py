from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
import time
import random
import re # Tambahkan library Regex untuk ambil angka

def scrape_agoda_pagination(url, output_filename="dlv_agoda_reviews.csv"):
    unique_reviews = set() 
    reviews_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"Mengakses: {url}")
        page.goto(url, timeout=90000)
        time.sleep(5) 

        page_num = 1
        
        while True:
            print(f"--- Sedang scraping Halaman {page_num} ---")
            
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            review_elements = soup.find_all('div', class_=lambda x: x and 'Review-comment' in x)
            
            new_reviews_found = 0
            for review in review_elements:
                try:
                    # 1. AMBIL RATING DULU (Filter Hantu)
                    rating_el = review.find('div', class_=lambda x: x and 'Review-comment-leftScore' in x)
                    rating = rating_el.text.strip() if rating_el else "N/A"

                    # Skip jika tidak ada rating (berarti ini div duplikat/invalid)
                    if rating == "N/A": 
                        continue

                    # 2. Text Review
                    text_el = review.find('p', class_=lambda x: x and 'Review-comment-bodyText' in x)
                    review_text = text_el.text.strip() if text_el else ""
                    
                    if not review_text: continue

                    # 3. Tanggal Review
                    date_container = review.find('div', class_=lambda x: x and 'Review-statusBar-left' in x)
                    review_date = "N/A"
                    if date_container:
                        review_date = date_container.text.replace("Reviewed", "").strip()

                    # 4. Metadata (Nama, Negara, Tipe Kamar)
                    reviewer_container = review.find('div', {'data-info-type': 'reviewer-name'})
                    reviewer_name = "Anonymous"
                    user_country = "N/A"

                    if reviewer_container:
                        # Nama
                        name_tag = reviewer_container.find('strong')
                        if name_tag:
                            reviewer_name = name_tag.text.strip()
                        else:
                            reviewer_name = reviewer_container.text.split(" from ")[0].strip()
                        
                        # Negara
                        spans = reviewer_container.find_all('span')
                        if spans:
                            user_country = spans[-1].text.strip()
                    
                    # Room Type
                    room_el = review.find('div', {'data-info-type': 'room-type'})
                    room_type = room_el.text.strip() if room_el else "N/A"

                    # 5. STAY DURATION (AMBIL ANGKA SAJA)
                    stay_el = review.find('div', {'data-info-type': 'stay-detail'})
                    stay_duration_days = "N/A"
                    
                    if stay_el:
                        full_stay_text = stay_el.text.strip() # ex: "Stayed 5 nights in January 2025"
                        
                        # Logic Regex: Cari angka (\d+) setelah kata "Stayed"
                        match = re.search(r'Stayed\s+(\d+)\s+night', full_stay_text, re.IGNORECASE)
                        if match:
                            stay_duration_days = match.group(1) # Ambil angkanya saja (misal: "5")
                        else:
                            # Fallback jika format teks beda (misal cuma "Stayed 1 night")
                            stay_duration_days = "1" if "1 night" in full_stay_text.lower() else full_stay_text

                    # 6. SIMPAN DATA
                    review_signature = f"{reviewer_name}_{rating}_{review_text[:50]}" 
                    
                    if review_signature not in unique_reviews:
                        unique_reviews.add(review_signature)
                        reviews_data.append({
                            'reviewer_name': reviewer_name,
                            'user_country': user_country,
                            'room_type': room_type,
                            'stay_duration_days': stay_duration_days, # Kolom Baru (Angka)
                            'rating': rating,
                            'review_text': review_text,
                            'review_date': review_date
                        })
                        new_reviews_found += 1
                except Exception:
                    continue
            
            print(f"  + Berhasil mengambil {new_reviews_found} review VALID.")

            # Logic Pagination
            next_button_selector = 'button[data-element-name="review-paginator-next"]'
            paginator_locator = page.locator(next_button_selector)
            
            if paginator_locator.count() > 0:
                next_button = paginator_locator.first
                if next_button.is_disabled():
                    print("Tombol Next disabled. Ini halaman terakhir.")
                    break
                
                print("Klik Next Page >>")
                try:
                    next_button.evaluate("element => element.click()")
                except Exception as e:
                    print(f"Gagal klik next: {e}")
                    break
                
                time.sleep(random.uniform(4, 6)) 
                page_num += 1
            else:
                print("Tombol Next tidak ditemukan. Berhenti.")
                break
        
        browser.close()

    if reviews_data:
        print(f"\nMenyimpan {len(reviews_data)} data bersih ke {output_filename}...")
        keys = reviews_data[0].keys()
        with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(reviews_data)
        print("SELESAI! Data berhasil disimpan.")
    else:
        print("Tidak ada review yang ditemukan.")

target_url = "https://www.agoda.com/id-id/daun-lebar-villas/hotel/bali-id.html"

if __name__ == "__main__":
    scrape_agoda_pagination(target_url)