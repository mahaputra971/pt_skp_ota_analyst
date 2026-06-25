async function scrapeAgodaReviews() {
    // Fungsi jeda agar DOM Agoda selesai memuat data setelah klik Next
    const delay = ms => new Promise(res => setTimeout(res, ms));
    
    let allReviews = [];
    let hasNextPage = true;
    let pageCount = 1;

    console.log("Memulai proses scraping ulasan Agoda...");

    while (hasNextPage) {
        // Ambil semua container review di halaman aktif
        let reviewCards = document.querySelectorAll('.Review-comment');

        reviewCards.forEach(card => {
            // Ekstraksi Skor
            let score = card.querySelector('.Review-comment-leftScore')?.innerText.trim() || '';
            let scoreText = card.querySelector('.Review-comment-leftScoreText')?.innerText.trim() || '';
            
            // Ekstraksi Profil Reviewer
            let name = card.querySelector('[data-info-type="reviewer-name"] strong')?.innerText.trim() || '';
            
            // Agoda menyimpan negara di dalam tag span terakhir pada div reviewer-name
            let reviewerSpans = card.querySelectorAll('[data-info-type="reviewer-name"] span');
            let country = reviewerSpans.length > 0 ? reviewerSpans[reviewerSpans.length - 1].innerText.trim() : '';

            // Ekstraksi Detail Menginap
            let travelerType = card.querySelector('[data-info-type="group-name"] span')?.innerText.trim() || '';
            let roomType = card.querySelector('[data-info-type="room-type"] span')?.innerText.trim() || '';
            let stayDetail = card.querySelector('[data-info-type="stay-detail"] span')?.innerText.trim() || '';
            
            // Ekstraksi Konten Review (membersihkan tanda kutip bawaan Agoda di judul)
            let title = card.querySelector('[data-testid="review-title"]')?.innerText.replace(/“|”/g, '').trim() || '';
            let comment = card.querySelector('[data-testid="review-comment"]')?.innerText.trim() || '';
            comment = comment.replace(/\n/g, ' '); // Menghindari baris baru yang merusak CSV
            
            // Mencari elemen yang mengandung tanggal (biasanya diawali "Reviewed")
            let dateElement = Array.from(card.querySelectorAll('span')).find(el => el.innerText.includes('Reviewed '));
            let reviewDate = dateElement ? dateElement.innerText.replace('Reviewed ', '').trim() : '';

            allReviews.push({
                "Nama": name,
                "Negara": country,
                "Tipe Kamar": roomType,
                "Detail Menginap": stayDetail,
                "Tipe Traveler": travelerType,
                "Tanggal Ulasan": reviewDate,
                "Skor": score,
                "Evaluasi": scoreText,
                "Judul": title,
                "Komentar": comment
            });
        });

        console.log(`Halaman ${pageCount} selesai ditarik. Total data sementara: ${allReviews.length}`);

        // Mencari tombol 'Next' berdasarkan data-element-name
        let nextBtn = document.querySelector('button[data-element-name="review-paginator-next"]');
        
        // Cek apakah tombol Next ada dan tidak dalam kondisi 'disabled'
        if (nextBtn && !nextBtn.disabled) {
            nextBtn.click();
            pageCount++;
            // Agoda terkadang butuh waktu sedikit lebih lama untuk merender ulasan baru
            await delay(3000); 
        } else {
            hasNextPage = false;
        }
    }

    console.log('Scraping Agoda selesai! Menyiapkan unduhan file CSV...');
    downloadCSV(allReviews, 'agoda_reviews_data.csv');
}

// Fungsi untuk mengekspor array of objects menjadi file CSV
function downloadCSV(data, filename) {
    if (data.length === 0) {
        console.warn("Tidak ada data yang ditemukan.");
        return;
    }
    
    const keys = Object.keys(data[0]);
    const csvContent = [
        keys.join(','), // Header baris pertama
        // Mapping setiap row dan menambahkan quote ganda (") untuk mencegah error koma pada kalimat
        ...data.map(row => keys.map(k => `"${row[k] || ''}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Menjalankan script
scrapeAgodaReviews();