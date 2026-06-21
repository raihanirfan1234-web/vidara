import requests
import time
import os
import sys
import random  # Modul pengacak waktu tunggu

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def send_telegram_large_msg(report_list, chunk_num):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    header_msg = f"🚨 <b>Laporan Pengecekan Freedl (Bagian {chunk_num}):</b>\n\n"
    current_msg = header_msg
    
    for item in report_list:
        # Jika digabung melebihi batas aman Telegram (3500 karakter), potong dan kirim
        if len(current_msg) + len(item) + 5 > 3500:
            payload = {"chat_id": CHAT_ID, "text": current_msg, "parse_mode": "HTML"}
            requests.post(url, json=payload)
            time.sleep(1.5)  # Jeda anti-spam limit Telegram
            
            # Reset isi dengan format sambungan yang bersih agar tag HTML tidak rusak
            current_msg = f"🚨 <b>Sambungan Bagian {chunk_num}:</b>\n\n"
            
        current_msg += item + "\n"
    
    # Kirim sisa potongan terakhir jika ada teks valid yang tersisa
    if current_msg and current_msg != f"🚨 <b>Sambungan Bagian {chunk_num}:</b>\n\n" and current_msg != header_msg:
        payload = {"chat_id": CHAT_ID, "text": current_msg, "parse_mode": "HTML"}
        requests.post(url, json=payload)

def check_links():
    try:
        current_chunk = int(sys.argv[1])
        total_chunks = int(sys.argv[2])
    except IndexError:
        current_chunk = 1
        total_chunks = 1

    try:
        with open('links.txt', 'r') as f:
            all_links = [line.strip() for line in f if line.strip()]
        
        if not all_links:
            print("Tidak ada link untuk dicek di links.txt")
            return

        # Distribusi link secara bergantian (Modulus) sesuai jumlah chunk paralel
        chunk_links = [url for i, url in enumerate(all_links) if (i % total_chunks) == (current_chunk - 1)]
        
        print(f"Mengambil alih Bagian {current_chunk}/{total_chunks}. Memproses {len(chunk_links)} dari {len(all_links)} total link.")

        dead_links_report = []
        dead_urls = set()
        
        for url in chunk_links:
            try:
                # User-Agent disamakan dengan browser laptop agar tidak mudah diblokir Cloudflare
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                
                # --- STRATEGI UNTUK LINK DOODSTREAM ---
                if "dood" in url or "ds2play" in url:
                    response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                    # Deteksi akurat lewat teks halaman karena video mati di Doodstream tetap merespons status 200
                    if "video_not_found" in response.text or "This video was deleted" in response.text or response.status_code == 404:
                        dead_links_report.append(f"⚠️ <b>Status Mati (Dood):</b> {url}")
                        dead_urls.add(url)
                        print(f"Dead Link (Doodstream): {url}")
                    else:
                        print(f"Checked (Dood): {url} - Status: Aktif")
                
                # --- STRATEGI UNTUK LINK FREEDL ---
                else:
                    response = requests.head(url, headers=headers, timeout=15, allow_redirects=True)
                    if response.status_code == 404:
                        dead_links_report.append(f"⚠️ <b>Status 404 (Freedl):</b> {url}")
                        dead_urls.add(url)
                        print(f"Dead Link (Freedl): {url}")
                    else:
                        print(f"Checked (Freedl): {url} - Status: {response.status_code}")
                    
            except Exception as e:
                dead_links_report.append(f"❌ <b>Error Koneksi:</b> {url}\n<i>{str(e)}</i>")
            
            # --- JEDA ACAK DISISIPKAN DI SINI ---
            # Mengacak jeda antara 5 sampai 15 detik agar aman dari proteksi bot server
            delay = random.randint(5, 15)
            print(f"Menunggu {delay} detik sebelum link berikutnya...")
            time.sleep(delay)
        
        # Proses tulis ulang file links.txt lokal jika ada link yang dihapus
        if dead_urls:
            with open('links.txt', 'r') as f:
                fresh_links = [line.strip() for line in f if line.strip()]
            
            cleaned_links = [link for link in fresh_links if link not in dead_urls]
            
            with open('links.txt', 'w') as f:
                for link in cleaned_links:
                    f.write(f"{link}\n")

        # Kirimkan rangkuman ke Telegram
        if dead_links_report:
            send_telegram_large_msg(dead_links_report, current_chunk)
        else:
            print(f"Semua link di bagian {current_chunk} aman.")

    except FileNotFoundError:
        print("Error: File links.txt tidak ditemukan!")

if __name__ == "__main__":
    check_links()
