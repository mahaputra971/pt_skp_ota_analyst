import smtplib
import time
import random  # Tambahkan library ini
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def run_email_bot():
    print("=== BOT EMAIL OTOMATIS (DENGAN JEDA ACAK) ===")
    
    # --- KONFIGURASI AKUN ---
    SENDER_EMAIL = "mahaputra971@gmail.com"
    SENDER_PASSWORD = "" 
    
    # --- DAFTAR PENERIMA ---
    receiver_list = [
        "ratihrasita99@gmail.com"
    ]
    
    # --- ISI EMAIL ---
    SUBJECT = "Update Promo Terbaru untuk Anda!"
    
    HTML_BODY = """
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Halo!</h2>
        <p>Terima kasih telah berlangganan. Berikut adalah penawaran spesial kami bulan ini:</p>
        
        <div style="text-align: center; margin: 20px 0;">
            <img src="cid:gambar_utama" alt="Banner Promo" style="max-width: 100%; border-radius: 8px;">
        </div>
        
        <p>Jangan lewatkan kesempatan ini.</p>
        <p>Salam hangat,<br><strong>Tim Kami</strong></p>
      </body>
    </html>
    """
    
    # --- PROSES KONEKSI & PENGIRIMAN ---
    try:
        print("[INIT] Menghubungkan ke server Gmail...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        print("[SUKSES] Login berhasil!\n")
        
        for index, receiver in enumerate(receiver_list):
            try:
                msg = MIMEMultipart('related')
                msg['Subject'] = SUBJECT
                msg['From'] = SENDER_EMAIL
                msg['To'] = receiver
                
                msg.attach(MIMEText(HTML_BODY, 'html'))
                
                with open('promo.jpg', 'rb') as img_file:
                    img_data = img_file.read()
                    image = MIMEImage(img_data, name='promo.jpg')
                    image.add_header('Content-ID', '<gambar_utama>')
                    msg.attach(image)
                
                server.sendmail(SENDER_EMAIL, receiver, msg.as_string())
                print(f" [V] Terkirim ke: {receiver}")
                
                # --- JEDA WAKTU ACAK (HUMAN MIMICRY) ---
                # Jangan beri jeda jika ini adalah email terakhir di daftar
                if index < len(receiver_list) - 1:
                    # Mengacak waktu antara 3.5 hingga 8.2 detik
                    jeda = random.uniform(3.5, 8.2) 
                    print(f"   -> Menunggu {jeda:.1f} detik sebelum mengirim email berikutnya...")
                    time.sleep(jeda)
                
            except Exception as e:
                print(f" [X] Gagal mengirim ke {receiver}: {e}")
                
        server.quit()
        print("\n=== SEMUA EMAIL SELESAI DIKIRIM ===")
        
    except Exception as e:
        print(f"\n[ERROR FATAL] Gagal terhubung ke server: {e}")

if __name__ == "__main__":
    run_email_bot()