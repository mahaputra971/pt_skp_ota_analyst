import time
import re
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

def run_scraper_v4():
    print("\n=== KONFIGURASI SCRAPING (MODE: ENTITY LOCKER v4) ===")
    start_str = input("Masukkan Tanggal Mulai (format: DD-MM-YYYY): ")
    end_str = input("Masukkan Tanggal Akhir (format: DD-MM-YYYY): ")
    duration = int(input("Durasi Menginap (malam): "))
    
    try:
        start_date = datetime.strptime(start_str, "%d-%m-%Y")
        end_date = datetime.strptime(end_str, "%d-%m-%Y")
    except ValueError:
        print("Format tanggal salah!")
        return

    # --- SETUP BROWSER ---
    chrome_options = Options()
    # chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    all_data = [] 

    # ==========================================
    # FASE 1: BERBURU HALAMAN DETAIL (HUNTING)
    # ==========================================
    print("\n[FASE 1] Mencari Halaman Detail Hotel yang VALID...")
    
    init_checkin = start_date.strftime("%Y-%m-%d")
    init_checkout = (start_date + timedelta(days=duration)).strftime("%Y-%m-%d")
    
    # Buka pencarian umum
    search_url = f"https://www.google.com/travel/search?q=daun%20lebar%20villas&checkin={init_checkin}&checkout={init_checkout}"
    driver.get(search_url)
    time.sleep(5)

    valid_detail_url = None

    # Strategi: Cari semua kartu yang mungkin, klik satu-satu, cek apakah masuk detail page
    try:
        # Cari elemen yang berisi teks "Daun Lebar Villas" (Judul Kartu)
        potential_clicks = driver.find_elements(By.XPATH, "//div[contains(text(), 'Daun Lebar Villas')]")
        
        print(f"   -> Ditemukan {len(potential_clicks)} kandidat kartu. Memeriksa satu per satu...")

        for i, elem in enumerate(potential_clicks):
            if i > 4: break # Cek max 5 kandidat teratas
            try:
                # Cek apakah elemen terlihat
                if not elem.is_displayed(): continue
                
                print(f"   -> Mencoba klik kandidat ke-{i+1}...")
                
                # Scroll & Klik JS (Biar tembus layer)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                time.sleep(1)
                
                # Coba klik tombol "View details" di dekatnya jika ada
                try:
                    # Cari parent terdekat
                    parent = elem.find_element(By.XPATH, "./ancestor::div[contains(@jscontroller, 'L8P0Xe') or contains(@class, 'I8K10') or position()=1]")
                    view_btn = parent.find_element(By.XPATH, ".//span[contains(text(), 'View details') or contains(text(), 'Lihat detail')]")
                    driver.execute_script("arguments[0].click();", view_btn)
                except:
                    # Klik elemen teks langsung
                    driver.execute_script("arguments[0].click();", elem)
                
                time.sleep(5) # Tunggu loading

                # --- VALIDASI: APAKAH KITA DI HALAMAN DETAIL? ---
                # Halaman detail WAJIB punya tab "Overview", "Prices", "Reviews"
                tabs = driver.find_elements(By.XPATH, "//div[contains(text(), 'Prices') or contains(text(), 'Harga')]")
                overview = driver.find_elements(By.XPATH, "//div[contains(text(), 'Overview') or contains(text(), 'Ringkasan')]")
                
                if tabs and overview:
                    print("   -> [SUKSES] Halaman Detail Terkonfirmasi!")
                    # Pastikan tab Prices aktif
                    tabs[0].click()
                    time.sleep(2)
                    valid_detail_url = driver.current_url
                    break # Keluar loop, kita sudah dapat URL-nya
                else:
                    print("   -> [GAGAL] Masih di list view atau salah hotel.")
                    
            except Exception as e:
                print(f"   -> Error klik: {e}")
                continue

        if not valid_detail_url:
            print("   [FATAL] Gagal menemukan halaman detail. Menggunakan URL terakhir sebagai cadangan.")
            valid_detail_url = driver.current_url

    except Exception as e:
        print(f"   [ERROR] Fase Hunting: {e}")

    print(f"   -> URL Kunci: {valid_detail_url[:60]}...")

    # ==========================================
    # FASE 2: SCRAPING STABIL
    # ==========================================
    current_date = start_date
    
    try:
        while current_date + timedelta(days=duration) <= end_date:
            s_checkin = current_date.strftime("%d-%m-%Y")
            s_checkout = (current_date + timedelta(days=duration)).strftime("%d-%m-%Y")
            u_checkin = current_date.strftime("%Y-%m-%d")
            u_checkout = (current_date + timedelta(days=duration)).strftime("%Y-%m-%d")

            print(f"\n[PROSES] {s_checkin} - {s_checkout}")

            # Ganti tanggal di URL Kunci
            if "checkin=" in valid_detail_url:
                new_url = re.sub(r'checkin=\d{4}-\d{2}-\d{2}', f'checkin={u_checkin}', valid_detail_url)
                new_url = re.sub(r'checkout=\d{4}-\d{2}-\d{2}', f'checkout={u_checkout}', new_url)
            else:
                new_url = valid_detail_url + f"&checkin={u_checkin}&checkout={u_checkout}"
            
            driver.get(new_url)
            time.sleep(5)

            # --- TEKNIK SCRAPING ARIA-LABEL (ANTI UNKNOWN) ---
            try:
                # 1. Expand
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    driver.execute_script("window.scrollTo(0, 300);")
                    
                    # Klik semua variasi tombol expand
                    expanders = driver.find_elements(By.XPATH, "//span[contains(text(), 'View') or contains(text(), 'Lihat') or contains(text(), 'options')]")
                    for btn in expanders:
                        if btn.is_displayed():
                            p_text = btn.find_element(By.XPATH, "./..").text.lower()
                            if "fewer" in p_text or "sedikit" in p_text: continue
                            
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(2)
                except: pass

                # 2. Cari Tombol "Visit site" (Ini kunci agar tidak salah ambil hotel tetangga)
                # Tombol ini hanya ada di opsi booking valid
                visit_buttons = driver.find_elements(By.CSS_SELECTOR, "[aria-label*='Visit site'], [aria-label*='Kunjungi situs'], [aria-label*='View deal']")
                
                print(f"   -> Memindai {len(visit_buttons)} opsi booking valid...")
                
                seen_key = set()
                count = 0

                for btn in visit_buttons:
                    try:
                        # A. NAMA AGENT (Dari Label Tombol - 100% Akurat)
                        label = btn.get_attribute("aria-label")
                        if not label: continue
                        
                        agent_name = label.replace("Visit site for", "").replace("Kunjungi situs", "").replace("View deal on", "").strip()
                        if "Google" in agent_name or len(agent_name) < 2: continue

                        # B. HARGA (Cari di sekitar tombol)
                        # Naik ke container baris (Parent level 3/4)
                        container = btn.find_element(By.XPATH, "./ancestor::div[3]")
                        container_text = container.text
                        
                        # Filter Kebocoran: Jika container berisi "Similar hotel", SKIP!
                        if "Similar" in container_text or "Serupa" in container_text or "People also" in container_text:
                            continue

                        # Regex Harga
                        price_match = re.search(r'(Rp|IDR)\s?([\d,.]+)', container_text)
                        if not price_match: continue
                        
                        price_str = price_match.group(2).replace('.', '').replace(',', '')
                        if not price_str.isdigit(): continue
                        final_price = int(price_str)
                        if final_price < 50000: continue 

                        # C. FILTER HOTEL TETANGGA (SAFETY NET)
                        # Jika harga > 5jt dan bukan Official Site -> kemungkinan hotel tetangga
                        if final_price > 5000000 and "Official" not in agent_name and "Daun" not in agent_name:
                            continue

                        # Simpan
                        unique_id = f"{s_checkin}-{agent_name}-{final_price}"
                        if unique_id not in seen_key:
                            all_data.append({
                                "Check-in": s_checkin,
                                "Check-out": s_checkout,
                                "Agent": agent_name,
                                "Harga IDR": final_price,
                                "Harga Teks": f"Rp {final_price:,}"
                            })
                            seen_key.add(unique_id)
                            count += 1
                            print(f"      [V] {agent_name}: Rp {final_price:,}")

                    except: continue
                
                if count == 0:
                    print("      [!] 0 Data valid.")

            except Exception as e:
                print(f"   [ERROR] Scraping: {e}")

            current_date += timedelta(days=1)

    except Exception as e:
        print(f"Error Fatal: {e}")
    finally:
        driver.quit()
        if all_data:
            df = pd.DataFrame(all_data)
            fn = f"harga_hotel_final_v4_{datetime.now().strftime('%H%M%S')}.xlsx"
            df.to_excel(fn, index=False)
            print(f"\n[SUKSES] Data disimpan: {fn}")

if __name__ == "__main__":
    run_scraper_v4()