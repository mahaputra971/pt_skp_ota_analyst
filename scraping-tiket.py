import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def parse_reviews(html_content):
    """Fungsi untuk mengekstrak data dari HTML page saat ini"""
    soup = BeautifulSoup(html_content, 'html.parser')
    reviews_data = []
    
    # Mencari semua elemen card review
    cards = soup.find_all('div', {'data-testid': 'review-card'})
    
    for card in cards:
        # 1. Nama
        name_elem = card.find('span', class_='ReviewCard_customer_name__mwGEt')
        name = name_elem.text.strip() if name_elem else None
        
        # 2. Tipe Traveler (Trip Keluarga, Pasangan, dll)
        type_elem = card.find('span', class_='ReviewCard_traveler_type__U9M84')
        traveler_type = type_elem.text.strip() if type_elem else None
        
        # 3. Tanggal
        date_elem = card.find('span', class_='ReviewCard_date__Nr8Lq')
        date = date_elem.text.strip() if date_elem else None
        
        # 4. Skor
        score_elem = card.find('span', class_='ReviewCard_user_review__HvsOH')
        score = score_elem.text.strip() if score_elem else None
        
        # 5. Isi Pesan Review
        comment_elem = card.find('span', class_='ReadMoreComments_review_card_comment__R_W2B')
        if comment_elem:
            # Hapus teks "Selengkapnya" jika ada agar tidak masuk ke hasil analisa
            read_more = comment_elem.find('span', class_='ReadMoreComments_read_more__r2ZQ7')
            if read_more:
                read_more.decompose()
            comment = comment_elem.text.strip()
        else:
            comment = None

        reviews_data.append({
            'Nama': name,
            'Tipe Traveler': traveler_type,
            'Tanggal': date,
            'Skor': score,
            'Review': comment
        })
        
    return reviews_data

def scrape_all_reviews(url):
    # Setup WebDriver (Gunakan Chrome)
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Uncomment jika tidak ingin browser tampil secara visual
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    
    all_reviews = []
    page_number = 1
    
    try:
        while True:
            print(f"Scraping Halaman {page_number}...")
            
            # Tunggu sampai review card muncul (Maksimal 10 detik)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="review-card"]'))
            )
            
            # Ambil HTML dan ekstrak data
            html_source = driver.page_source
            page_reviews = parse_reviews(html_source)
            all_reviews.extend(page_reviews)
            
            # Mencari tombol Next (Chevron Right)
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="chevron-right-pagination"]')
                
                # Cek apakah tombol next bisa diklik / tidak ter-disable
                # (Biasanya class berubah menjadi inactive jika sudah di halaman terakhir)
                parent_class = next_button.get_attribute('class')
                if 'ReviewPagination_inactive' in parent_class:
                    print("Sudah mencapai halaman terakhir.")
                    break
                
                # Scroll ke tombol next dan klik
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(1) # Jeda agar scroll selesai
                next_button.click()
                
                # Jeda agar data AJAX halaman selanjutnya selesai dimuat
                time.sleep(3) 
                page_number += 1
                
            except NoSuchElementException:
                print("Tombol Next tidak ditemukan. Menghentikan scraping.")
                break
            
    except TimeoutException:
        print("Waktu habis saat menunggu elemen termuat.")
    finally:
        driver.quit()
        
    return all_reviews

# --- CARA PENGGUNAAN ---
if __name__ == "__main__":
    # Ganti URL di bawah dengan link asli target Anda
    TARGET_URL = input("Masukkan URL Tiket: ").strip()
    
    hasil_scraping = scrape_all_reviews(TARGET_URL)
    
    # Simpan ke DataFrame Pandas agar mudah dianalisa
    df = pd.DataFrame(hasil_scraping)
    
    # Tampilkan preview data
    print("\nPreview Data:")
    print(df.head())
    
    # Simpan ke CSV untuk proses analisa sentimen / NLP selanjutnya
    df.to_csv('hasil_review_hotel.csv', index=False, encoding='utf-8')
    print(f"\nBerhasil menyimpan {len(df)} review ke 'hasil_review_hotel.csv'")