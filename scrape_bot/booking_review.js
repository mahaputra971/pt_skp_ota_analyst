async function scrapeBookingReviews() {
    // Fungsi untuk memberi jeda waktu agar DOM sempat memuat ulasan baru setelah tombol Next diklik
    const delay = ms => new Promise(res => setTimeout(res, ms));
    
    let allReviews = [];
    let hasNextPage = true;
    let pageCount = 1;

    console.log("Memulai proses scraping...");

    while (hasNextPage) {
        // Ekstrak semua kartu review di halaman saat ini
        let reviewCards = document.querySelectorAll('[data-testid="review-card"]');

        reviewCards.forEach(card => {
            // Mengambil field penting berdasarkan class dan testid dari struktur HTML Anda
            let name = card.querySelector('.b08850ce41')?.innerText.trim() || '';
            let country = card.querySelector('.aea5eccb71')?.innerText.trim() || '';
            let roomType = card.querySelector('[data-testid="review-room-name"]')?.innerText.trim() || '';
            let numNights = card.querySelector('[data-testid="review-num-nights"]')?.innerText.trim() || '';
            let stayDate = card.querySelector('[data-testid="review-stay-date"]')?.innerText.trim() || '';
            let travelerType = card.querySelector('[data-testid="review-traveler-type"]')?.innerText.trim() || '';
            let reviewDate = card.querySelector('[data-testid="review-date"]')?.innerText.trim() || '';
            let title = card.querySelector('[data-testid="review-title"]')?.innerText.trim() || '';
            let score = card.querySelector('.dff2e52086')?.innerText.trim() || '';

            // Menangkap teks ulasan (Booking.com memisahkan kolom positif dan negatif)
            let posText = card.querySelector('[data-testid="review-positive-text"] .b99b6ef58f')?.innerText.trim() || '';
            let negText = card.querySelector('[data-testid="review-negative-text"] .b99b6ef58f')?.innerText.trim() || '';
            
            // Menggabungkan teks jika ada ulasan positif dan negatif, menghindari breakline agar CSV tetap rapi
            let reviewText = `Positif: ${posText} | Negatif: ${negText}`.replace(/\n/g, ' ');

            allReviews.push({
                "Nama": name,
                "Negara": country,
                "Tipe Kamar": roomType,
                "Durasi Menginap": numNights.replace('·', '').trim(),
                "Tanggal Menginap": stayDate,
                "Tipe Traveler": travelerType,
                "Tanggal Ulasan": reviewDate.replace('Reviewed: ', '').trim(),
                "Skor": score,
                "Judul": title,
                "Komentar": reviewText
            });
        });

        console.log(`Halaman ${pageCount} selesai. Total data terkumpul: ${allReviews.length}`);

        // Mencari tombol navigasi 'Next page'
        let nextBtn = document.querySelector('button[aria-label="Next page"]');
        
        // Memastikan tombol ada dan tidak memiliki atribut 'disabled'
        if (nextBtn && !nextBtn.hasAttribute('disabled')) {
            nextBtn.click();
            pageCount++;
            // Jeda 2.5 detik untuk menunggu request AJAX selesai. 
            // Jika koneksi agak lambat, angka 2500 bisa dinaikkan menjadi 3000 atau 4000.
            await delay(2500); 
        } else {
            hasNextPage = false;
        }
    }

    console.log('Scraping selesai! Mengunduh file CSV...');
    downloadCSV(allReviews);
}

// Fungsi untuk mengekspor array of objects menjadi file CSV
function downloadCSV(data) {
    if (data.length === 0) {
        console.warn("Tidak ada data yang ditemukan.");
        return;
    }
    
    const keys = Object.keys(data[0]);
    const csvContent = [
        keys.join(','), // Header baris pertama
        // Mapping setiap row dan menambahkan quote ganda (") untuk mencegah error pada string yang mengandung koma
        ...data.map(row => keys.map(k => `"${row[k] || ''}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    link.setAttribute('href', url);
    link.setAttribute('download', 'booking_reviews_data.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Eksekusi fungsinya
scrapeBookingReviews();