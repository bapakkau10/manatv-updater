import os
import time
import requests
from playwright.sync_api import sync_playwright

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
    TONTON_EMAIL = os.environ.get("TONTON_EMAIL")
    TONTON_PASSWORD = os.environ.get("TONTON_PASSWORD")

    if not TONTON_EMAIL or not TONTON_PASSWORD:
        print("AMARAN: TONTON_EMAIL atau TONTON_PASSWORD tidak dijumpai dalam Environment Variables!")

    channels = {
        "tv3": "https://watch.tonton.com.my/live/tv3",
        "tv9": "https://watch.tonton.com.my/live/tv9",
        "8tv": "https://watch.tonton.com.my/live/8tv"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Proses Auto-Login Terus ke Laman Tonton
        print("Cuba log masuk ke Tonton secara automatik...")
        try:
            page.goto("https://www.tonton.com.my/signin", timeout=60000)
            time.sleep(5)
            
            # Isi emel dan password secara selamat
            page.wait_for_selector("input[type='email'], input[name='email']", timeout=15000)
            page.fill("input[type='email'], input[name='email']", str(TONTON_EMAIL))
            
            page.wait_for_selector("input[type='password'], input[name='password']", timeout=15000)
            page.fill("input[type='password'], input[name='password']", str(TONTON_PASSWORD))
            time.sleep(2)
            
            page.keyboard.press("Enter")
            time.sleep(10)
            print("Proses log masuk selesai dicuba.")
        except Exception as e:
            print(f"Amaran semasa log masuk: {e}")

        # Proses Fetch Saluran Live
        for key_name, url in channels.items():
            stream_link = None
            captured = False

            def handle_response(response):
                nonlocal stream_link, captured
                if captured:
                    return
                resp_url = response.url
                if ".m3u8" in resp_url and "bpkio_serviceid" in resp_url:
                    stream_link = resp_url
                    captured = True
                    print(f"[{key_name}] Jumpai Stream M3u8: {stream_link}")

            page.on("response", handle_response)

            print(f"Sedang akses {key_name}: {url}...")
            try:
                page.goto(url, timeout=60000, wait_until="networkidle")
                
                start_time = time.time()
                while not captured and (time.time() - start_time) < 15:
                    time.sleep(2)
                    try:
                        page.mouse.click(680, 380)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[{key_name}] Error: {e}")

            if stream_link:
                update_cloudflare_kv(key_name, stream_link)
            else:
                print(f"[{key_name}] Gagal dapatkan pautan m3u8.")

            page.remove_listener("response", handle_response)
            time.sleep(2)

        browser.close()

if __name__ == "__main__":
    main()
