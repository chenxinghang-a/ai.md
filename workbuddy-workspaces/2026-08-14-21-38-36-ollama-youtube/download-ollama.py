import os
import time
import requests

URL = 'https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe'
OUT = 'D:/AI/Ollama/OllamaSetup.exe'
PROXIES = {
    'http': 'socks5h://127.0.0.1:10808',
    'https': 'socks5h://127.0.0.1:10808',
}

def get_total_size():
    try:
        r = requests.head(URL, proxies=PROXIES, timeout=30, allow_redirects=True)
        return int(r.headers.get('content-length', 0))
    except Exception as e:
        print(f'head fail: {e}', flush=True)
        return 0

total = get_total_size()
print(f'total size: {total} bytes ({total>>20} MB)', flush=True)

for attempt in range(30):
    already = os.path.getsize(OUT) if os.path.exists(OUT) else 0
    if total and already >= total:
        print(f'ALREADY COMPLETE: {already}/{total}', flush=True)
        break
    headers = {'Range': f'bytes={already}-'} if already else {}
    print(f'[attempt {attempt+1}] resume from {already} bytes ({already>>20} MB)', flush=True)
    try:
        r = requests.get(URL, stream=True, proxies=PROXIES, timeout=60, allow_redirects=True, headers=headers)
        r.raise_for_status()
        mode = 'ab' if r.status_code == 206 else 'wb'
        downloaded = already if mode == 'ab' else 0
        with open(OUT, mode) as f:
            for chunk in r.iter_content(chunk_size=1<<20):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (100<<20) < (1<<20):
                        pct = (downloaded*100//total) if total else 0
                        print(f'  {downloaded>>20}/{total>>20} MB ({pct}%)', flush=True)
        print(f'[attempt {attempt+1}] got to {downloaded} bytes', flush=True)
        if downloaded >= total:
            print(f'DONE: {downloaded}/{total}', flush=True)
            break
    except Exception as e:
        print(f'[attempt {attempt+1}] error: {type(e).__name__}: {e}', flush=True)
        time.sleep(2)

final = os.path.getsize(OUT)
print(f'final: {final} bytes ({final>>20} MB) { "OK" if final>=total else "INCOMPLETE"}', flush=True)
