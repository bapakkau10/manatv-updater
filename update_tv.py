import os
import time
import zipfile
import requests
from playwright.sync_api import sync_playwright

def restore_session():
    if os.path.exists("tonton_session.zip"):
        with zipfile.ZipFile("tonton_session.zip", 'r') as zip_ref:
            zip_ref.extractall("./tonton_session")
        print("Sesi login berjaya dipulihkan daripada fail zip lokal.")

def update_cloudflare_kv(key_name, m3u8_link):
    ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
    NAMESPACE_ID = os.environ.get("CF_NAMESPACE_ID")
    API_TOKEN = os.environ.get("CF_API_TOKEN")

    kv_url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}/values/{key_name}"
    kv_headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "text/plain"
    }
    
    resp = requests.put(kv_url, data=m3u8_link, headers=kv_headers)
    if resp.status_code == 200:
        print(f"[{key_name}] Berjaya dikemaskini ke Cloudflare KV!")
    else:
        print(f"[{key_name}] Gagal simpan ke KV: {resp.text}")

def main():
    restore_session()

    channels = {
        "tv3": "https://watch.tonton.com.my/live/tv3",
        "tv9": "https://watch.tonton.com.my/live/tv9",
        "8tv": "https://watch.tonton.com.my/live/8tv"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./tonton_session",
            headless=True,
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = browser.new_page()

        for key_name, url in channels.items():
            master_link = None
            captured = False

            def handle_response(response):
                nonlocal master_link, captured
                if captured:
                    return
                resp_url = response.url
                # Cari apa-apa URL yang mengandungi m3u8 atau bpkio
                if "m3u8" in resp_url or "bpkio" in resp_url:
                    master_link = resp_url
                    captured = True
                    print(f"[{key_name}] Jumpai Stream Link: {master_link}")

            page.on("response", handle_response)

            print(f"Sedang akses {key_name}: {url}...")
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                # Tunggu dan cuba klik pada bahagian tengah skrin untuk pastikan player 'play'
                for _ in range(5):
                    if captured:
                        break
                    try:
                        time.sleep(3)
                        page.mouse.click(680, 380)
                    except Exception:
                        pass
                
                start_time = time.time()
                while not captured and (time.time() - start_time) < 10:
                    time.sleep(1)
            except Exception as e:
                print(f"[{key_name}] Error: {e}")

            if master_link:
                update_cloudflare_kv(key_name, master_link)
            else:
                print(f"[{key_name}] Gagal dapatkan master m3u8.")

            page.remove_listener("response", handle_response)
            time.sleep(2)

        browser.close()

if __name__ == "__main__":
    main()
